---
name: skill-ship
description: Ships changed skills from this repository in one ordered pass — runs the SkillSpector security gate, regenerates the README skill index and counts, syncs changed skills one-way into the local agent skills directory, and hands off to /conventional-commit. Use when the user types /skill-ship, says "ship the skills", "release these skills", "sync and commit skills", or has finished editing anything under skills/. Stops at the first failed gate; never deletes installed skills.
allowed-tools: Read Grep Glob Bash
---

# Skill Ship

Release changed skills in one ordered pass: **scan → index → sync → commit**. Each phase is a gate. A red gate stops the run and reports; it is never skipped, bypassed, or worked around.

## Contract

- **Order is fixed.** Scan before index, index before sync, sync before commit. A skill that fails the scan must never reach the installed directory or the remote.
- **Scripts do the mechanical work.** Never hand-edit the README index tables or counts. `scripts/gen-readme.py` owns them; editing by hand is how the index drifted.
- **Sync is one-way and additive.** Copy repo → installed. Never delete from the installed directory: it holds archived and third-party skills that are not in this repo.
- **Push only when asked.** Committing is part of the pass; pushing is a separate, explicit request.

## Phase 0 — Preflight

```bash
git status --short
git diff --stat
```

Establish what changed under `skills/`. If nothing under `skills/` or `README.md` changed, say so and stop — there is nothing to ship.

Resolve the installed skills directory. Default is `~/.claude/skills`; on Windows Git Bash that is `$HOME/.claude/skills` (`/c/Users/<name>/.claude/skills`). Confirm it exists before Phase 3.

```bash
SKILLS_HOME="${SKILLS_HOME:-$HOME/.claude/skills}"
test -d "$SKILLS_HOME" && echo "installed: $SKILLS_HOME" || echo "missing: $SKILLS_HOME"
```

## Phase 1 — Scan

```bash
bash scripts/scan-skills.sh skills
```

| Exit | Meaning                            | Action                                                               |
| ---- | ---------------------------------- | -------------------------------------------------------------------- |
| 0    | `gate: clean`                      | Continue.                                                            |
| 1    | A batch scored above the threshold | Stop. Show `skillspector-reports/summary.md` and the flagged skills. |
| 2    | Scanner missing or a batch failed  | Stop. Report the error text verbatim.                                |

On exit 1, read the flagged lines before judging them. Security-aware skill content often trips the scanner; that is a finding to investigate and report, not a reason to lower the threshold or exclude the skill.

`skillspector-reports/` is a build artifact. Do not commit it.

## Phase 2 — Index

```bash
python scripts/gen-readme.py
git diff --stat README.md
```

The generator keeps each skill in the README section it already lives in and keeps its curated display name and description. It only:

- fills rows whose description is empty or `---`,
- removes rows whose skill folder no longer exists (`removed:`),
- appends new skills under `### Uncategorized` (`uncategorized:`),
- updates the active and archived counts.

Report every `removed:` and `uncategorized:` line. An uncategorized skill means a human decision is pending: move its row into the right section by hand (the generator preserves placement on the next run), then run the generator again.

Confirm the result is stable:

```bash
python scripts/gen-readme.py --check
```

Exit 0 is required to continue. The Featured Skills table is hand-written and is never touched by the generator; update it manually only when a featured skill changed behavior.

## Phase 3 — Sync

Copy only skills that exist in the repo and differ from their installed copy.

```bash
SKILLS_HOME="${SKILLS_HOME:-$HOME/.claude/skills}"
before=$(find "$SKILLS_HOME" -mindepth 1 -maxdepth 1 -type d | wc -l)
for dir in skills/*/; do
  name=$(basename "$dir")
  [ -f "$dir/SKILL.md" ] || continue
  if ! diff -rq --strip-trailing-cr "$dir" "$SKILLS_HOME/$name" >/dev/null 2>&1; then
    mkdir -p "$SKILLS_HOME/$name"
    cp -R "$dir." "$SKILLS_HOME/$name/"
    echo "synced: $name"
  fi
done
after=$(find "$SKILLS_HOME" -mindepth 1 -maxdepth 1 -type d | wc -l)
echo "installed skills: $before -> $after"
```

Verify, do not assume:

```bash
for dir in skills/*/; do
  name=$(basename "$dir")
  diff -rq --strip-trailing-cr "$dir" "$SKILLS_HOME/$name" >/dev/null 2>&1 || echo "MISMATCH: $name"
done
```

No `MISMATCH` lines, and `after >= before`. A drop in the installed count means something deleted a skill — stop and report.

`cp -R` overwrites changed files but leaves files that were removed from the repo in the installed copy. If a skill's file was deliberately deleted, name the stale installed file and ask before removing it.

## Phase 4 — Commit

Hand off to `/conventional-commit`, which splits the working tree into one commit per concern. Typical concerns in a ship:

| Concern             | Example subject                         |
| ------------------- | --------------------------------------- |
| A new skill         | `feat(skills): add skill-ship`          |
| A changed skill     | `docs(skills): tighten explore phase 2` |
| Script or CI change | `feat(scripts): add readme generator`   |
| Regenerated index   | `docs: regenerate skill index`          |

The repository's own commit rules and the user's instructions override these examples. Do not push unless the user asked.

## Report

```text
Skill ship
  scan     gate: clean (91 skills)
  index    filled 2, removed 0, uncategorized 0 — --check clean
  sync     3 synced, 0 mismatches, installed 146 -> 147
  commit   2 commits (not pushed)
```

On a stop, the report names the phase that failed, the exact error, and what the user must decide. Phases after the failure are listed as `not run`, never as passed.

## Common Mistakes

| Mistake                                      | Why It Breaks                                       | Correct Approach                               |
| -------------------------------------------- | --------------------------------------------------- | ---------------------------------------------- |
| Editing README index rows or counts by hand  | Drifts from the frontmatter; the next run disagrees | Run `scripts/gen-readme.py`                    |
| Syncing before the scan passes               | Installs a skill the gate would have rejected       | Scan first, always                             |
| Raising the threshold to make the gate green | Disables the gate for every skill                   | Investigate the flagged lines and report them  |
| Deleting from the installed directory        | Removes archived and third-party skills             | One-way, additive sync only                    |
| Reporting a skipped phase as passed          | Hides that a gate never ran                         | Mark it `not run` with the reason              |
| Committing `skillspector-reports/`           | Commits build artifacts                             | Leave it untracked                             |
| Pushing because the commit succeeded         | Push is a separate, explicit request                | Stop after commit unless asked                 |
| Leaving a skill under `### Uncategorized`    | The index loses its structure                       | Ask where it belongs, move the row, regenerate |
