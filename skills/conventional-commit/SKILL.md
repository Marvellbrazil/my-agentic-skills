---
name: conventional-commit
description: Commits staged work using the Conventional Commits specification, defaulting to a single commit when the working tree is one coherent change and splitting into multiple atomic commits only when the changes are genuinely unrelated. Short imperative subjects, scopes only when the change is localized, a breaking-change marker only at a real breaking point. Use when the user types /conventional-commit, says "commit this conventionally", "make a conventional commit", or asks to commit staged changes. Never adds a co-author trailer.
allowed-tools: Bash Read Grep Glob
---

# Conventional Commit

Commit the working tree as one or more atomic commits that follow the [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) specification, with short subjects and no co-author trailer.

## Non-Negotiables

1. **No co-author trailer.** Do not append `Co-Authored-By:`, `Signed-off-by:`, `Generated with`, or any attribution line. Not from the agent, not from a tool. This is the whole difference from `/conventional-commit-with-coauthor`.
2. **Never use `git commit -a`.** Stage deliberately so unrelated edits cannot leak into a commit.
3. **Never `git add .` or `git add -A` blindly.** Inspect the tree first. `git add .` is how `.env`, build output, and a half-finished refactor end up in an unrelated commit.
4. **Never commit without reading the diff.** The message must describe what actually changed, not what the task description said would change.
5. **Never invent a scope or a type that does not fit.** A wrong scope is worse than no scope.
6. **Never amend, rebase, or force-push a commit you did not just create in this session.** If the user asked for a commit, make a commit.

## Step 1 — Inspect Before Staging

Run these three and read the output. Do not skip the diff.

```bash
git status --short --branch
git diff --stat
git diff --cached --stat
```

Then read the actual changes. For a large diff, read per file rather than dumping everything:

```bash
git diff -- <path>
git diff --cached -- <path>
```

Classify every changed path before writing a single commit message:

| Category                   | Examples                                      | Action                                                              |
| -------------------------- | --------------------------------------------- | ------------------------------------------------------------------- |
| Source change              | `src/`, `app/`, `lib/`                        | Commit, grouped by intent                                           |
| Test change                | `*.test.ts`, `tests/`, `*_test.go`            | Commit with its subject, or separately if the tests are independent |
| Documentation              | `README.md`, `docs/`, `*.md`                  | Separate `docs:` commit                                             |
| Dependency manifest        | `package.json`, `pyproject.toml`, lockfiles   | Separate `build:` or `chore:` commit                                |
| CI configuration           | `.github/workflows/`, `.gitlab-ci.yml`        | Separate `ci:` commit                                               |
| Generated output           | `dist/`, `build/`, `*.min.js`, coverage       | Do not commit. Add to `.gitignore` and tell the user                |
| Secret or credential       | `.env`, `*.pem`, `id_rsa`, `credentials.json` | Do not commit. Stop and warn the user immediately                   |
| Unrelated work in progress | Anything you cannot attribute to this task    | Leave unstaged and tell the user                                    |

If a secret is staged, stop the commit entirely, unstage it with `git restore --staged <path>`, and report it. A secret in a commit is not fixable with a follow-up commit.

## Step 2 — Decide How Many Commits

**One logical change per commit.** A commit must be revertable on its own without dragging unrelated work with it.

### One commit is the default, not a fallback

Most changes are one logical change. **If the working tree is one coherent unit, make one commit and stop** — that is the correct answer, not a compromise. Splitting exists to separate changes that are genuinely unrelated, never to make a history look busy.

Ask one question: **if this commit were reverted tomorrow, would it take anything unrelated with it?**

| Answer                                           | Commit count                     |
| ------------------------------------------------ | -------------------------------- |
| No — everything in it belongs to the same change | **One commit**                   |
| Yes — it would also revert unrelated work        | Split until each revert is clean |

If you cannot name two commits that each stand alone and each leave the tree working, the answer is one commit. Producing several commits from one change is not thoroughness; it is noise in the log, extra review surface, and a harder `git bisect`.

### Do not split when

- The change is one unit: a feature and the test that proves it belong in the same commit. The test is part of the feature, not a separate concern.
- The change touches several files for one reason — a rename plus its call sites, a new field plus its migration plus its serializer.
- A fix and its regression test. Splitting them means the test commit is red on its own.
- Splitting would produce a commit that does not build or does not pass tests. Every commit must be a working state, and if a split breaks that, the split is wrong.
- You would have to invent a scope or a type for the second commit that does not really fit. That is a signal there was only one change.
- The "second commit" is a subset of the first with no independent meaning (`feat: add thing` + `refactor: tidy thing you just wrote`).

### Split only when

- The working tree spans two or more conventional types that are genuinely independent (`feat` + `fix`, `refactor` + `docs`).
- The tree touches unrelated subsystems a reviewer would not review together.
- A mechanical rename or format sweep is mixed with a behavioral change. **Always split these** — a reviewer cannot see the real change inside 400 renamed lines.
- A dependency bump is mixed with the code that uses the new dependency.
- Tests for feature A are mixed with feature B.
- Two unrelated fixes landed in one working tree.

When you do split, order the commits so each builds on a valid previous state:

1. Dependency and config changes (`build:`, `ci:`, `chore:`)
2. Mechanical refactors and renames (`refactor:`)
3. Behavior changes (`feat:`, `fix:`, `perf:`)
4. Tests (`test:`) when they do not belong with the subject
5. Documentation (`docs:`)

## Step 3 — Stage One Logical Change

Stage by path, or interactively when a single file contains two logical changes.

```bash
git add <path> <path>
```

For a file with mixed concerns, stage hunks:

```bash
git add -p <path>
```

`-p` prompts per hunk with `y` (stage), `n` (skip), `s` (split hunk), `e` (edit hunk manually), `q` (quit). Use `s` first — it splits a hunk into the smallest pieces git can separate. Use `e` only when `s` cannot isolate the change, and remember that editing a hunk changes what gets committed.

To stage a new file's content without staging the file for creation, or to stage only deletions:

```bash
git add -N <new-file>
git add -p <new-file>
git rm --cached <path>
```

Then verify exactly what is staged, and nothing more:

```bash
git diff --cached --stat
git diff --cached
```

## Step 4 — Compose the Message

### Grammar

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

The subject line and the blank-line separation are mandatory. The body and footers are optional.

### Type

Choose exactly one. The type describes the **intent of the change**, not the file type.

| Type       | Use for                                                           | Not for                                     |
| ---------- | ----------------------------------------------------------------- | ------------------------------------------- |
| `feat`     | A new capability visible to a user or a consuming system          | Refactors that add no capability            |
| `fix`      | A correction to broken behavior                                   | A change that was never broken              |
| `docs`     | Documentation only                                                | Code comments that ship with a feature      |
| `style`    | Formatting, whitespace, semicolons, no behavior change            | Anything that alters behavior               |
| `refactor` | Restructuring with no behavior change                             | A refactor that also fixes a bug — split it |
| `perf`     | A change whose purpose is speed or memory                         | A refactor that happens to be faster        |
| `test`     | Adding or fixing tests only                                       | Production code                             |
| `build`    | Build system, bundler, dependency manifests, lockfiles            | Application source                          |
| `ci`       | CI configuration and pipeline scripts                             | The app's own scripts                       |
| `chore`    | Maintenance that fits nothing above: `.gitignore`, tooling config | User-visible behavior                       |
| `revert`   | Reverting a previous commit                                       | A forward fix                               |

Do not invent types such as `wip`, `update`, `improvement`, or `misc`. If nothing fits, the change is probably two commits.

### Scope

Add a scope **only when the change is confined to one module, package, or bounded context**, and the scope name helps a reader locate it.

Use a scope: `fix(payment-service): ...`, `feat(auth): ...`, `refactor(api)!: ...`
Omit a scope: a change that spans the whole project, or a project small enough that the scope is always the same.

Rules for scope names:

- Name a **module or bounded context**, never a file. `fix(payment-service)` not `fix(payment.service.ts)`.
- Lowercase, kebab-case, no spaces, no dots.
- Use the vocabulary the codebase already uses for that directory or package.
- **Never invent a scope for a change that is not actually localized.** A general change with a scope is a lie about blast radius.

### The breaking-change marker `!`

Put `!` immediately before the `:` when the change breaks a contract that a consumer depends on. `!` is not "this commit is big" or "this commit is important to me" — it is a promise that upgrading requires the consumer to act.

`!` is warranted for:

- A removed or renamed public function, class, endpoint, or CLI flag.
- A changed API request or response schema, a changed version in a URL, a changed event payload.
- A changed database schema that existing code or migrations cannot read.
- A changed default that silently alters behavior for existing callers.
- A bumped major version of a public dependency contract.

`!` is **not** warranted for:

- A large diff.
- A refactor with identical external behavior.
- An internal rename that no consumer can observe.
- A bug fix that restores documented behavior.

When you use `!`, you **must** also add a `BREAKING CHANGE:` footer explaining the migration. `!` in the subject is the signal; the footer is the substance.

### Subject description

- Imperative mood: `add`, `fix`, `remove`, `rename` — not `added`, `adds`, `adding`. It must complete the sentence "This commit will ___".
- Lowercase first letter unless the word is a proper noun or an identifier (`feat: add OAuth2 support`, not `feat: Add oauth2 support`).
- No trailing period.
- Aim for 50 characters; hard-stop at 72. Git tooling truncates at 72 and the rest is invisible in `git log --oneline`.
- Describe the **what**, concretely. `fix: handle null user id in session lookup` beats `fix: bug fix`.

### Body

Add a body when the **why** is not obvious from the subject. Separate it from the subject with one blank line.

Wrap at 72 characters. Explain the problem, the constraint that forced this approach, and what was rejected. Do not restate the diff — the diff already says what changed.

### Footers

One blank line after the body. Each footer is a token followed by `: ` or ` #`.

```
BREAKING CHANGE: <what breaks and what the consumer must do>
Refs: #412
Closes: #418
```

Use `BREAKING CHANGE:` (uppercase) — it is the only token the spec defines, and tooling keys on it for the major version bump. `BREAKING-CHANGE:` is accepted as an alias.

### The four required shapes

```
feat: added chatbot feature using claude
perf!: optimalized images across all features
fix(payment-service): fixed request timed out error on client side
refactor(api)!: changed schema version into v3
```

In practice, prefer the imperative form (`feat: add chatbot feature using claude`) — it matches the convention git itself uses and reads correctly in a changelog. If the project's existing log uses past tense, match the log.

## Step 5 — Commit

Pass the message with a heredoc. Multiple `-m` flags do work — git inserts a blank line between each — but a heredoc keeps the exact bytes visible in the command, which matters once a body or a footer is involved.

```bash
git commit -F - <<'EOF'
fix(payment-service): handle client-side request timeout

The gateway returns 504 when the upstream exceeds 30s, which the client
treated as a fatal error instead of a retryable one.

Closes: #412
EOF
```

For a subject-only commit:

```bash
git commit -m "docs: document the skill scan workflow"
```

## Step 6 — Verify and Repeat

Record how many commits you intended before you started. Then loop back to Step 1 until the tree is clean.

```bash
git status --short
git log --oneline -5
```

Confirm:

- [ ] Every commit's subject matches `^[a-z]+(\([a-z0-9-]+\))?!?: .+$`
- [ ] No subject exceeds 72 characters
- [ ] No commit contains a co-author or attribution trailer
- [ ] Each commit is independently revertable
- [ ] No commit mixes a mechanical sweep with a behavioral change
- [ ] Every `!` has a matching `BREAKING CHANGE:` footer
- [ ] No secrets, build output, or editor cruft was committed
- [ ] Nothing left staged that should not have been
- [ ] The commit count is the one you decided in Step 2 — not more

Set `N` to the number of commits you just made (usually `1`), then run these.

Validate the subjects mechanically rather than by eye:

```bash
N=1
git log --format='%s' -"$N" | grep -vE '^[a-z]+(\([a-z0-9-]+\))?!?: .+$' && echo 'INVALID SUBJECTS ABOVE' || echo 'all subjects valid'
```

Check for an accidental co-author trailer using git's own trailer parser:

```bash
N=1
for sha in $(git log --format=%H -"$N"); do
  t=$(git log -1 --format='%(trailers:key=Co-authored-by,valueonly)' "$sha")
  [ -n "$t" ] && echo "UNWANTED TRAILER on ${sha:0:7}: $t"
done
echo 'trailer check done'
```

Prefer the trailer parser over grepping `git log --format='%B'`, for two reasons:

- **It tells you which commit.** A grep over a range reports that _a_ trailer exists somewhere; the loop above names the offending SHA, which is what you need to fix it.
- **It is case-insensitive on the key.** The trailer is conventionally written `Co-Authored-By` (capital `A` and `B`), so a case-sensitive `grep 'Co-authored-by'` silently matches nothing and reports a false all-clear. The parser accepts `Co-authored-by`, `Co-Authored-By`, and `CO-AUTHORED-BY` alike.

If you do grep, always pass `-i`:

```bash
N=1
git log --format='%B' -"$N" | grep -i -E 'co-authored-by|generated with' && echo 'UNWANTED TRAILER (find the SHA above)' || echo 'clean'
```

Confirm the tree is clean and every commit is pushed as expected:

```bash
git status --short --branch
```

### If you made more commits than intended

A working tree that yielded three commits where one change existed is a real defect, not a stylistic one. Fix it before pushing — history is cheap to rewrite while it is local.

Squash the extras into the intended commit, keeping the message you want:

```bash
# Collapse the last 3 commits into one, reusing the message of the oldest
git reset --soft HEAD~3
git commit -F - <<'EOF'
feat(scope): the single message for the whole change
EOF
```

`--soft` keeps every change staged and rewrites nothing on disk.

`HEAD~3` requires **four** commits to exist, not three — the count is the number of parents to walk back, so squashing the last three needs a fourth behind them. On a repository where the commits to squash reach the root commit, `git reset --soft HEAD~3` fails with `fatal: ambiguous argument`.

To collapse everything down to a single root commit, reset to the root and then `--amend` it. A plain `git commit` here would leave two commits — the root plus a new one:

```bash
# Collapse all history into one commit
git reset --soft "$(git rev-list --max-parents=0 HEAD)"
git commit --amend -F - <<'EOF'
feat: the single initial message
EOF
```

Verify the count is what you intended before pushing:

```bash
git rev-list --count HEAD
```

**Only do this for commits you created in this session and have not pushed.** If the branch is already pushed, do not rewrite it — leave the history as it is and note the mistake, rather than forcing a rewrite on anyone who has fetched it.

## Common Mistakes

| Mistake                                                       | Why It Breaks                                                                                                    | Correct Approach                                          |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| `git add .` then one commit                                   | Unrelated work, secrets, and build output land together and the commit cannot be reverted cleanly                | Stage by path, or `git add -p` for mixed files            |
| `fix: fixed the bug`                                          | Subject says nothing a reader can act on                                                                         | `fix(auth): reject expired refresh tokens on rotation`    |
| `feat: Add Login`                                             | Capitalized and vague                                                                                            | `feat(auth): add OAuth2 login`                            |
| Scope on a project-wide change                                | Misleads the reader about blast radius                                                                           | Omit the scope                                            |
| `!` on a large but compatible refactor                        | Signals a breaking change that does not exist; breaks downstream versioning                                      | Use `!` only for real contract breaks                     |
| `!` without a `BREAKING CHANGE:` footer                       | Consumers learn nothing about the migration                                                                      | Always pair them                                          |
| Body or footer passed as a second `-m`                        | Works — git inserts a blank line — but the message is easy to mis-assemble and impossible to read in the command | Prefer `-F -` with a heredoc for anything past a subject  |
| Rename sweep mixed with a real fix                            | The real change is invisible in review                                                                           | Split into `refactor:` then `fix:`                        |
| Amending a pushed commit                                      | Rewrites shared history                                                                                          | Make a new commit                                         |
| Committing a generated lockfile alone with no manifest change | Lockfile drifts from the manifest                                                                                | Commit the manifest and the lockfile together as `build:` |
| Trailing period on the subject                                | Breaks the conventional grammar and changelog tooling                                                            | No trailing punctuation                                   |
| Message describing the plan, not the diff                     | Log lies about what shipped                                                                                      | Read `git diff --cached` before writing the message       |
| Splitting one coherent change into several commits            | The log lies about scope; `git bisect` and revert both get harder for no benefit                                 | Default to one commit unless each part stands alone       |
| `feat: add X` + `refactor: tidy X`                            | The second commit is a subset of the first and cannot be reverted independently                                  | One commit — the tidy-up is part of adding X              |
| Feature and its test in separate commits                      | The test commit is red on its own; each commit must be a working state                                           | Commit them together                                      |
| Inventing a scope to justify a second commit                  | If no scope or type genuinely fits, there was only one change                                                    | Reconsider; make one commit                               |
| Splitting to make the history "look thorough"                 | Review surface and log noise grow while clarity drops                                                            | Thoroughness is a clean diff, not a commit count          |
