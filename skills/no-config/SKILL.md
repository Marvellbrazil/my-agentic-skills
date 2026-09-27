---
name: no-config
description: Removes agent-facing configuration artifacts from a project — rules files (AGENTS.md, CLAUDE.md, GEMINI.md, .cursorrules), agent directories (.claude/, .agent/, .remember/, .codex/), and agent-generated planning docs — while preserving genuine project documentation. Use when the user types /no-config, asks to clean agent configuration out of a repo, wants a project free of AI-agent scaffolding, or before open-sourcing. Inventories first and confirms before deleting.
allowed-tools: Read Glob Grep Bash
---

# No Config

Strip agent-facing scaffolding from a project so it contains only the code, its real documentation, and its real tooling.

The counterpart to `/no-comment`, one level up: `no-comment` keeps AI chatter out of source files; this keeps agent configuration out of the repository.

## The Distinction That Governs Everything

**Agent configuration is not project documentation.**

| Remove                                                                  | Keep                                                      |
| ----------------------------------------------------------------------- | --------------------------------------------------------- |
| `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules` | `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE` |
| `.claude/`, `.agent/`, `.codex/`, `.remember/`, `.aider*`               | `.github/` (real CI, issue templates)                     |
| `.cursor/`, `.continue/`, `.specstory/`                                 | `docs/` with genuine architecture or API docs             |
| `*.plan.md`, `TODO.ai.md`, agent scratchpads                            | `docs/adr/` — architecture decision records               |
| `.claude/settings.json`, `mcp.json` checked into the repo               | `.editorconfig`, linters, formatters                      |
| Agent session logs, `handoff.md`, `.ai-context/`                        | `.gitignore`, `.env.example`                              |

The test: **would a human contributor who has never used an AI coding tool need this file?** If yes, keep it. If it exists only to steer an agent, remove it.

`README.md` and `CONTRIBUTING.md` are frequently _polluted_ with agent instructions rather than being agent files themselves. Do not delete them — offer to strip the agent-specific sections.

## The Safety Rules

Deleting configuration is destructive and hard to undo. Four rules:

1. **Inventory before deleting. Nothing is removed in the same step it is discovered.**
2. **Confirm before deleting, with the list in front of the user.** This is the one skill where the default answer to "should I proceed?" must be supplied by the user, not assumed.
3. **Never touch anything outside the project root.** `~/.claude/`, `~/.agents/`, and other home-directory state are the user's global setup. Ask separately, and warn that removing them affects every project.
4. **Never delete tracked files without surfacing the git consequence.** If a file is committed, deleting it is a visible history change that a team will see.

## Phase 1 — Inventory

Scan without modifying.

```bash
ls -a
```

```bash
find . -maxdepth 3 \
  \( -iname 'AGENTS.md' -o -iname 'CLAUDE.md' -o -iname 'GEMINI.md' \
     -o -iname '.cursorrules' -o -iname '.windsurfrules' -o -iname '.aider*' \
     -o -iname '*.plan.md' -o -iname 'handoff*.md' -o -iname 'TODO.ai.md' \) \
  -not -path './.git/*' -not -path '*/node_modules/*' -not -path '*/vendor/*' 2>/dev/null
```

```bash
find . -maxdepth 2 -type d \
  \( -name '.claude' -o -name '.agent' -o -name '.agents' -o -name '.codex' \
     -o -name '.remember' -o -name '.cursor' -o -name '.continue' \
     -o -name '.specstory' -o -name '.ai-context' -o -name '.aider' \) \
  -not -path './.git/*' 2>/dev/null
```

Determine what is **tracked by git** versus **local only**. This changes the advice entirely.

```bash
git ls-files | grep -iE '(^|/)(AGENTS|CLAUDE|GEMINI)\.md$|\.cursorrules$|\.claude/|\.agent|\.remember/|\.codex/' || echo "none tracked"
```

Also check `.gitignore` — a file may be ignored locally and absent from the repo, in which case deleting it has no team impact.

```bash
git check-ignore -v .claude/ .remember/ AGENTS.md 2>/dev/null
```

## Phase 2 — Classify

Produce a three-way classification, not a delete list.

| Class      | Meaning                                                                      | Action                                          |
| ---------- | ---------------------------------------------------------------------------- | ----------------------------------------------- |
| **Remove** | Purely agent-facing, no human value                                          | Delete after confirmation                       |
| **Review** | Mixed content — a README with an agent section, a CONTRIBUTING with AI rules | Show the diff; offer to strip the agent portion |
| **Keep**   | Genuine project documentation that merely mentions agents                    | Leave it                                        |

For every **Review** item, extract and show the agent-specific content so the user can decide:

```bash
grep -n -iE 'claude|agent|cursor|copilot|codex|gemini|AI assistant|prompt' README.md CONTRIBUTING.md 2>/dev/null | head -30
```

Present the inventory:

```markdown
## Inventory

### Remove — agent-only (tracked by git)

| Path                    | What it is                     | Tracked         |
| ----------------------- | ------------------------------ | --------------- |
| `CLAUDE.md`             | Claude Code rules file         | yes             |
| `.claude/settings.json` | Local agent settings           | yes             |
| `.remember/`            | Agent session memory (7 files) | no — gitignored |

### Review — mixed content

| Path                    | Contains                         | Suggestion         |
| ----------------------- | -------------------------------- | ------------------ |
| `README.md:88-140`      | "AI Agent Guidelines" section    | Strip lines 88-140 |
| `CONTRIBUTING.md:12-19` | Commit rules addressed to agents | Rewrite for humans |

### Keep — genuine documentation

| Path                               | Why                               |
| ---------------------------------- | --------------------------------- |
| `docs/adr/0003-database-choice.md` | Real architecture decision record |
| `.github/workflows/ci.yml`         | Real CI, unrelated to agents      |
```

## Phase 3 — Confirm

Ask once, with the classification in front of the user. Use `AskUserQuestion` so the choice is explicit.

Offer the scope as discrete options:

- Remove only the **Remove** class.
- Remove the **Remove** class and strip the agent sections from **Review** items.
- Remove everything, including locally-ignored artifacts.
- Show me the full contents of each file first.

Two things to state plainly before the user answers:

1. **Whether the files are tracked.** "`CLAUDE.md` is committed — deleting it will appear in the next commit and your team will see it."
2. **Whether a backup exists.** Offer to write the removed content to a single archive file outside the repo, or to note the git revision so it can be recovered.

```bash
git rev-parse HEAD
```

If the user wants a backup, capture the content before deleting:

```bash
tar -czf /tmp/agent-config-backup.tar.gz $(git ls-files | grep -iE 'AGENTS\.md|CLAUDE\.md|\.claude/')
```

Never proceed on an ambiguous answer. If the user says "clean it up" without specifying scope, restate the three classes and ask which.

## Phase 4 — Remove

Delete only the paths the user confirmed, one class at a time, with a guard that refuses to act outside the project root.

**Set the guard once.** Every deletion below goes through it, so a mistyped path cannot reach outside the repository.

```bash
PROJECT_ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd -P)"

remove_inside_project() {
  target="$1"
  absolute="$(cd "$(dirname "$target")" 2>/dev/null && pwd -P)/$(basename "$target")"
  case "$absolute" in
    "$PROJECT_ROOT"/*) ;;
    *) echo "refused: $target (outside $PROJECT_ROOT)" >&2; return 1 ;;
  esac
  [ -e "$absolute" ] || { echo "skipped: $target does not exist"; return 0; }
  echo "removing: ${absolute#"$PROJECT_ROOT"/}"
  rm -r -- "$absolute"
}
```

Both sides are normalized with `cd … && pwd -P` because on Git Bash for Windows `git rev-parse --show-toplevel` returns `C:/…` while `pwd` returns `/c/…` for the same directory. Comparing the two forms directly makes every path look like it is outside the project, so the guard silently refuses everything — including the deletions you intended. Normalizing through the shell is what makes the comparison meaningful on every platform.

**Untracked / gitignored** — remove from the working tree only:

```bash
remove_inside_project .remember
remove_inside_project .claude
```

**Tracked** — unstage from git first so the deletion is visible in the diff, then remove the working copy:

```bash
git rm -r --cached --quiet .claude 2>/dev/null || true
remove_inside_project .claude

git rm --quiet CLAUDE.md 2>/dev/null || true
remove_inside_project CLAUDE.md
```

`--` before each path stops a filename that begins with `-` from being read as a flag. `--quiet` keeps the output readable when many files are involved.

**Never** use a glob in the delete position (`rm -rf .claude/*`, `rm -rf "$HOME/.claude"`). A glob that expands to nothing still runs, and a home-directory path is outside the guard for a reason.

Then check `.gitignore` and add the patterns so the artifacts do not return:

```bash
printf '\n# Agent configuration\n.claude/\n.remember/\nAGENTS.md\nCLAUDE.md\n.cursorrules\n' >> .gitignore
```

Do not add ignore patterns for files the user chose to keep.

**Strip, do not delete, for mixed files.** Edit the agent-specific section out of `README.md` / `CONTRIBUTING.md` and leave the rest intact.

## Phase 5 — Verify

- [ ] Every **Remove** item is gone from the working tree.
- [ ] Every **Review** item still exists and retains its human content.
- [ ] Every **Keep** item is untouched.
- [ ] `git status` shows only the intended changes — no accidental deletions.
- [ ] `.gitignore` covers the agent artifacts that should not return.
- [ ] The project still builds and tests pass. Removing a config file can break a hook, a script, or a lint step that referenced it.
- [ ] No reference to a deleted file remains in scripts, CI, or docs.

```bash
grep -rn -iE 'CLAUDE\.md|AGENTS\.md|\.remember/|\.claude/' \
  --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=vendor . 2>/dev/null | head -20
```

A dangling reference to a deleted rules file is the most common way this skill breaks a project. Run the grep.

## Output

```markdown
## Removed

| Path         | Class          | Tracked | Recoverable via                             |
| ------------ | -------------- | ------- | ------------------------------------------- |
| `CLAUDE.md`  | agent rules    | yes     | `git show HEAD:CLAUDE.md`                   |
| `.claude/`   | agent settings | yes     | `git show HEAD:.claude/settings.json`       |
| `.remember/` | session memory | no      | backup at `/tmp/agent-config-backup.tar.gz` |

## Stripped

| Path        | Lines removed | Content                       |
| ----------- | ------------- | ----------------------------- |
| `README.md` | 88-140        | "AI Agent Guidelines" section |

## Kept

| Path        | Reason                      |
| ----------- | --------------------------- |
| `docs/adr/` | Real architecture decisions |

## Verification

<the checklist, with actual command output>

## Follow-up

- `CONTRIBUTING.md:12-19` still addresses agents; rewrite for humans if you want.
```

## Common Mistakes

| Mistake                                                    | Why It Breaks                                            | Correct Approach                                                     |
| ---------------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------------------- |
| Deleting without inventorying                              | Removes real documentation alongside agent files         | Inventory and classify first                                         |
| Deleting `README.md` because it mentions agents            | Destroys the project's front door                        | Strip the agent section, keep the file                               |
| Touching `~/.claude/` as if it were project-local          | Breaks the user's setup for every other project          | Never leave the project root without explicit, separate confirmation |
| `rm` on a tracked file                                     | Deletion is invisible until a later commit; easy to miss | `git rm` so it is staged and reviewable                              |
| Deleting without a backup                                  | Irreversible loss of accumulated rules                   | Offer a tarball or record the git revision                           |
| Leaving `.gitignore` untouched                             | The artifacts regenerate and reappear in the next commit | Add the ignore patterns                                              |
| Missing a dangling reference                               | CI or a script references the deleted file and fails     | Grep for references after deleting                                   |
| Not re-running the build                                   | A hook or lint step depended on the removed config       | Build and test after removal                                         |
| Assuming "clean it up" means everything                    | Destroys files the user wanted                           | Restate the classes and confirm scope                                |
| Removing a real `.github/` because it sounds agent-related | Breaks CI                                                | `.github/` is project tooling, not agent config                      |
