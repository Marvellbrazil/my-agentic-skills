import argparse
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
SKILLS_DIR = os.path.join(ROOT, "skills")
ARCHIVE_DIR = os.path.join(ROOT, "archive")
INDEX_HEADER = "## Active Skills Index"
UNCATEGORIZED_HEADER = "### Uncategorized"
PLACEHOLDERS = {"", "---"}
BLOCK_INDICATORS = {"", ">", ">-", ">+", "|", "|-", "|+"}
MAX_DESCRIPTION = 160
ROW = re.compile(r"^\|\s*(?P<name>.+?)\s*\|\s*`/(?P<slug>[\w-]+)`\s*\|\s*(?P<desc>.*?)\s*\|$")


def read_description(frontmatter_text):
    match = re.match(r"^---\n(.*?)\n---", frontmatter_text, re.S)
    if not match:
        return ""
    lines = match.group(1).split("\n")
    for index, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        head = line[len("description:"):].strip()
        continuation = []
        for following in lines[index + 1:]:
            if following and not following[0].isspace():
                break
            continuation.append(following.strip())
        parts = ([] if head in BLOCK_INDICATORS else [head]) + continuation
        value = " ".join(part for part in parts if part)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value
    return ""


def summarize(description):
    sentence = re.match(r"(.+?[.!?])(\s|$)", description)
    text = sentence.group(1) if sentence else description
    if len(text) > MAX_DESCRIPTION:
        text = text[:MAX_DESCRIPTION - 3].rsplit(" ", 1)[0].rstrip(",;:—- ") + "..."
    return text.replace("|", "\\|")


def display_name(slug):
    return " ".join(word.capitalize() for word in slug.split("-"))


def list_skills(directory):
    return sorted(
        entry for entry in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, entry, "SKILL.md"))
    )


def load_descriptions(slugs):
    descriptions = {}
    for slug in slugs:
        with io.open(os.path.join(SKILLS_DIR, slug, "SKILL.md"), encoding="utf-8") as handle:
            descriptions[slug] = summarize(read_description(handle.read().replace("\r\n", "\n")))
    return descriptions


def count_archive():
    counts = {}
    for category in sorted(os.listdir(ARCHIVE_DIR)):
        path = os.path.join(ARCHIVE_DIR, category)
        if os.path.isdir(path):
            counts[category] = len(list_skills(path))
    return counts


def rebuild_index(lines, descriptions, report):
    start = lines.index(INDEX_HEADER)
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
    seen = set()
    rebuilt = []
    for line in lines[start:end]:
        row = ROW.match(line)
        if not row:
            rebuilt.append(line)
            continue
        slug = row.group("slug")
        if slug not in descriptions:
            report["removed"].append(slug)
            continue
        seen.add(slug)
        if row.group("desc").strip() in PLACEHOLDERS:
            report["filled"].append(slug)
            line = "| %s | `/%s` | %s |" % (row.group("name"), slug, descriptions[slug])
        rebuilt.append(line)

    missing = [slug for slug in descriptions if slug not in seen]
    if missing:
        report["uncategorized"].extend(missing)
        while rebuilt and rebuilt[-1] == "":
            rebuilt.pop()
        if UNCATEGORIZED_HEADER not in rebuilt:
            rebuilt += ["", UNCATEGORIZED_HEADER, "", "| Skill Name | Command | Description |", "| --- | --- | --- |"]
        rebuilt += ["| %s | `/%s` | %s |" % (display_name(slug), slug, descriptions[slug]) for slug in missing]
        rebuilt.append("")
    return lines[:start] + rebuilt + lines[end:]


def update_counts(text, active, archive_counts):
    archived = sum(archive_counts.values())
    text = re.sub(r"(collection of )\d+( active skills)", r"\g<1>%d\g<2>" % active, text)
    text = re.sub(r"(# )\d+( Main Active Skills)", r"\g<1>%d\g<2>" % active, text)
    text = re.sub(r"\d+( specialized\s+and niche skills)", r"%d\g<1>" % archived, text)
    text = re.sub(r"(# )\d+( Archived)", r"\g<1>%d\g<2>" % archived, text)
    for category, count in archive_counts.items():
        text = re.sub(r"(\(`archive/%s/`\) \| )\d+" % re.escape(category), r"\g<1>%d" % count, text)
        text = re.sub(r"(%s/\s*# )\d+" % re.escape(category), r"\g<1>%d" % count, text)
    return text


def generate(original):
    slugs = list_skills(SKILLS_DIR)
    descriptions = load_descriptions(slugs)
    report = {"removed": [], "filled": [], "uncategorized": []}
    lines = rebuild_index(original.split("\n"), descriptions, report)
    return update_counts("\n".join(lines), len(slugs), count_archive()), report


def self_test():
    wrap = lambda body: "---\nname: x\n%s\nlicense: MIT\n---\n# X" % body
    assert read_description(wrap("description: Plain text.")) == "Plain text."
    assert read_description(wrap('description: "Quoted: text."')) == "Quoted: text."
    assert read_description(wrap("description: >\n  Folded\n  text.")) == "Folded text."
    assert read_description(wrap("description: |-\n  Literal\n  text.")) == "Literal text."
    assert read_description(wrap("description:\n  Indented plain\n  text.")) == "Indented plain text."
    assert read_description("no frontmatter") == ""
    assert summarize("First sentence. Second one.") == "First sentence."
    assert summarize("Has a | pipe.") == "Has a \\| pipe."
    long_text = summarize("word " * 60)
    assert long_text.endswith("...") and len(long_text) <= MAX_DESCRIPTION
    assert display_name("skill-ship") == "Skill Ship"
    padded = ROW.match("| Ping        | `/ping`        | Health-checks.   |")
    assert padded and padded.group("name") == "Ping" and padded.group("desc") == "Health-checks."
    print("self-test: ok")


def main():
    parser = argparse.ArgumentParser(description="Regenerate the README skill index and counts.")
    parser.add_argument("--check", action="store_true", help="exit 1 if README is out of date, write nothing")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0

    with io.open(README, encoding="utf-8", newline="") as handle:
        raw = handle.read()
    newline = "\r\n" if "\r\n" in raw else "\n"
    original = raw.replace("\r\n", "\n")
    updated, report = generate(original)

    for key, slugs in report.items():
        if slugs:
            print("%s: %s" % (key, ", ".join(slugs)))
    if updated == original:
        print("README: up to date")
        return 0
    if args.check:
        print("README: out of date, run python scripts/gen-readme.py")
        return 1
    with io.open(README, "w", encoding="utf-8", newline="") as handle:
        handle.write(updated.replace("\n", newline))
    print("README: updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
