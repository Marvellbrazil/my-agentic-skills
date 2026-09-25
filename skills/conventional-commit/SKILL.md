---
name: conventional-commit
description: Commits staged work using the Conventional Commits specification, splitting a large working tree into multiple atomic commits with short imperative subjects, scopes only when the change is localized, and a breaking-change marker when the change is a breaking point. Use when the user types /conventional-commit, says "commit this conventionally", "make a conventional commit", or asks to commit staged changes. Never adds a co-author trailer.
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

Split when any of these hold:

- The working tree spans two or more conventional types (`feat` + `fix`, `refactor` + `docs`).
- The tree touches unrelated subsystems that a reviewer would not review together.
- A mechanical rename or format sweep is mixed with a behavioral change. **Always split these** — a reviewer cannot see the real change inside 400 renamed lines.
- A dependency bump is mixed with code that uses the new dependency.
- Tests for feature A are mixed with feature B.

Do **not** split when:

- The change is genuinely one unit: a fix plus its regression test belongs in one commit.
- Splitting would produce a commit that does not build or does not pass tests. Each commit should be a working state.

Order the commits so each one builds on a valid previous state:

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

Pass the message with a heredoc so newlines and blank lines survive. Do not use multiple `-m` flags for a body — they produce a message with no blank line separation.

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

## Step 6 — Repeat and Verify

Loop back to Step 1 until the tree is clean, then verify the history you produced.

```bash
git status --short
git log --oneline -<n>
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

Validate the subjects mechanically rather than by eye:

```bash
git log --format='%s' -<n> | grep -vE '^[a-z]+(\([a-z0-9-]+\))?!?: .+$' && echo 'INVALID SUBJECTS ABOVE' || echo 'all subjects valid'
```

Check for an accidental co-author trailer:

```bash
git log --format='%B' -<n> | grep -iE 'co-authored-by|generated with' && echo 'UNWANTED TRAILER' || echo 'clean'
```

## Common Mistakes

| Mistake                                                       | Why It Breaks                                                                                     | Correct Approach                                          |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| `git add .` then one commit                                   | Unrelated work, secrets, and build output land together and the commit cannot be reverted cleanly | Stage by path, or `git add -p` for mixed files            |
| `fix: fixed the bug`                                          | Subject says nothing a reader can act on                                                          | `fix(auth): reject expired refresh tokens on rotation`    |
| `feat: Add Login`                                             | Capitalized and vague                                                                             | `feat(auth): add OAuth2 login`                            |
| Scope on a project-wide change                                | Misleads the reader about blast radius                                                            | Omit the scope                                            |
| `!` on a large but compatible refactor                        | Signals a breaking change that does not exist; breaks downstream versioning                       | Use `!` only for real contract breaks                     |
| `!` without a `BREAKING CHANGE:` footer                       | Consumers learn nothing about the migration                                                       | Always pair them                                          |
| Body pasted with `-m "a" -m "b"`                              | Git joins them without a blank line, so the body is not parsed as a body                          | Use `-F -` with a heredoc                                 |
| Rename sweep mixed with a real fix                            | The real change is invisible in review                                                            | Split into `refactor:` then `fix:`                        |
| Amending a pushed commit                                      | Rewrites shared history                                                                           | Make a new commit                                         |
| Committing a generated lockfile alone with no manifest change | Lockfile drifts from the manifest                                                                 | Commit the manifest and the lockfile together as `build:` |
| Trailing period on the subject                                | Breaks the conventional grammar and changelog tooling                                             | No trailing punctuation                                   |
| Message describing the plan, not the diff                     | Log lies about what shipped                                                                       | Read `git diff --cached` before writing the message       |
