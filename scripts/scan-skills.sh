#!/usr/bin/env bash
set -euo pipefail

SKILLS_DIR="${1:-skills}"
BATCH_SIZE="${BATCH_SIZE:-30}"
OUT_DIR="${OUT_DIR:-skillspector-reports}"
SCANNER="${SCANNER:-skillspector}"
JOBS="${JOBS:-4}"

if ! command -v "$SCANNER" >/dev/null 2>&1; then
  echo "error: '$SCANNER' not found on PATH. Install with:" >&2
  echo "  uv tool install git+https://github.com/NVIDIA/skillspector.git" >&2
  exit 2
fi

if [ ! -d "$SKILLS_DIR" ]; then
  echo "error: skills directory '$SKILLS_DIR' not found" >&2
  exit 2
fi

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/sarif" "$OUT_DIR/json" "$OUT_DIR/logs"

mapfile -t skills < <(
  find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d -print |
    sort |
    while read -r dir; do
      [ -f "$dir/SKILL.md" ] && printf '%s\n' "$dir"
    done
)

total="${#skills[@]}"
if [ "$total" -eq 0 ]; then
  echo "error: no skills with a SKILL.md found under '$SKILLS_DIR'" >&2
  exit 2
fi

echo "Scanning $total skills in batches of $BATCH_SIZE ($JOBS concurrent)"

work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

batch_count=0
for ((i = 0; i < total; i += BATCH_SIZE)); do
  batch_count=$((batch_count + 1))
  label="$(printf 'batch-%02d' "$batch_count")"
  batch_dir="$work_dir/$label"
  mkdir -p "$batch_dir"

  for ((j = i; j < i + BATCH_SIZE && j < total; j++)); do
    ln -s "$(cd "${skills[$j]}" && pwd)" "$batch_dir/$(basename "${skills[$j]}")"
  done
done

run_batch() {
  local label="$1" batch_dir="$2"
  local log="$OUT_DIR/logs/$label.stdout"
  local status_file="$OUT_DIR/logs/$label.status"

  : >"$log"

  "$SCANNER" scan "$batch_dir" \
    --recursive --no-llm \
    --format json --output "$OUT_DIR/json/$label.json" \
    >>"$log" 2>&1
  local json_status=$?

  "$SCANNER" scan "$batch_dir" \
    --recursive --no-llm \
    --format sarif --output "$OUT_DIR/sarif/$label.sarif" \
    >>"$log" 2>&1
  local sarif_status=$?

  if [ "$json_status" -eq 2 ] || [ "$sarif_status" -eq 2 ]; then
    echo 2 >"$status_file"
  elif [ "$json_status" -eq 1 ] || [ "$sarif_status" -eq 1 ]; then
    echo 1 >"$status_file"
  else
    echo 0 >"$status_file"
  fi
}

export -f run_batch
export OUT_DIR SCANNER

for batch_dir in "$work_dir"/batch-*; do
  label="$(basename "$batch_dir")"
  size=$(find "$batch_dir" -mindepth 1 -maxdepth 1 | wc -l | tr -d ' ')

  while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do
    wait -n 2>/dev/null || true
  done

  echo "  $label: $size skills"
  run_batch "$label" "$batch_dir" &
done

wait

failed_batches=0
flagged_batches=0
for status_file in "$OUT_DIR"/logs/*.status; do
  [ -f "$status_file" ] || continue
  status="$(cat "$status_file")"
  if [ "$status" -eq 2 ]; then
    failed_batches=$((failed_batches + 1))
  elif [ "$status" -eq 1 ]; then
    flagged_batches=$((flagged_batches + 1))
  fi
done

echo
echo "Scanned $total skills across $batch_count batches"

python - "$OUT_DIR" <<'PY'
import io, json, os, sys

out_dir = sys.argv[1]
json_dir = os.path.join(out_dir, "json")

reported = 0
unscanned = 0
rows = []
seen = set()

for name in sorted(os.listdir(json_dir)):
    if not name.endswith(".json"):
        continue
    with io.open(os.path.join(json_dir, name), encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            print("  warn: unreadable report %s" % name)
            continue

    reported += data.get("skill_count") or 0
    unscanned += data.get("skills_omitted") or 0

    for skill in data.get("skills") or []:
        key = skill.get("path") or skill.get("name")
        if key in seen:
            continue
        seen.add(key)
        rows.append((
            skill.get("risk_score") or 0,
            skill.get("risk_severity") or "LOW",
            skill.get("finding_count") or 0,
            key,
        ))

rows.sort(key=lambda r: (-r[0], r[3]))

summary_path = os.path.join(out_dir, "summary.md")
with io.open(summary_path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("# SkillSpector Scan Summary\n\n")
    fh.write("| Metric | Value |\n| --- | --- |\n")
    fh.write("| Skills discovered | %d |\n" % len(rows))
    fh.write("| Skills reported | %d |\n" % reported)
    fh.write("| Skills omitted by scanner | %d |\n" % unscanned)
    fh.write("| Max risk score | %d |\n" % (rows[0][0] if rows else 0))
    fh.write("\n")

    flagged = [r for r in rows if r[0] > 20]
    if flagged:
        fh.write("## Skills above the low-risk threshold\n\n")
        fh.write("| Skill | Score | Severity | Findings |\n| --- | --- | --- | --- |\n")
        for score, sev, findings, key in flagged:
            fh.write("| `%s` | %d | %s | %d |\n" % (key, score, sev, findings))
        fh.write("\n")
    else:
        fh.write("No skill scored above the low-risk threshold.\n\n")

print("  skills reported: %d" % len(rows))
print("  skills omitted:  %d" % unscanned)
print("  max risk score:  %d" % (rows[0][0] if rows else 0))
for score, sev, findings, key in rows:
    if score > 0:
        print("    %-46s %3d %-8s %d findings" % (key, score, sev, findings))
PY

if [ "$failed_batches" -gt 0 ]; then
  echo "error: $failed_batches batch(es) failed to scan — see $OUT_DIR/logs/" >&2
  exit 2
fi

if [ "$flagged_batches" -gt 0 ]; then
  echo "gate: $flagged_batches batch(es) reported findings above the risk threshold"
  exit 1
fi

echo "gate: clean"
