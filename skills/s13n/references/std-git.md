# Git, Branching, and Commit Conventions

Commit history is the one artifact every engineer reads and no test suite validates. A malformed subject breaks the changelog generator that drives releases; a squash-merged PR destroys the bisectability that turns a four-hour outage into a ten-minute one; a force-push to a shared branch silently discards a colleague's commits. Getting this wrong does not fail the build — it degrades the one tool you need when the build _is_ failing.

## Contents

- [When This Applies](#when-this-applies)
- [The Commit Message](#the-commit-message)
  - [Types](#types)
  - [Scope: a module, never a file](#scope-a-module-never-a-file)
  - [Breaking changes](#breaking-changes)
  - [Subject, body, footers](#subject-body-footers)
- [Atomic Commits and Working-Tree Hygiene](#atomic-commits-and-working-tree-hygiene)
  - [Splitting a large working tree](#splitting-a-large-working-tree)
  - [Never commit](#never-commit)
  - [`.gitignore` discipline](#gitignore-discipline)
- [Branching, History, and Integration](#branching-history-and-integration)
  - [Branch naming](#branch-naming)
  - [Rebase versus merge](#rebase-versus-merge)
  - [Squash versus preserved history](#squash-versus-preserved-history)
  - [Keeping the default branch green](#keeping-the-default-branch-green)
  - [Tags, versioning, and signing](#tags-versioning-and-signing)
  - [Recovery: reflog, revert, reset](#recovery-reflog-revert-reset)
  - [Pull request size and reviewability](#pull-request-size-and-reviewability)
- [Enforcement: Hooks and CI](#enforcement-hooks-and-ci)
  - [Platform primitive: `core.hooksPath`](#platform-primitive-corehookspath)
  - [JavaScript and TypeScript: husky v9 plus commitlint](#javascript-and-typescript-husky-v9-plus-commitlint)
  - [Multi-language: the `pre-commit` framework](#multi-language-the-pre-commit-framework)
  - [CI as the backstop](#ci-as-the-backstop)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- Auditing `git log --oneline -50` for a type vocabulary that drifts (`fix:`, `Fix:`, `fixed`, `bugfix:`, `hotfix:`, `update:`).
- Unifying a repo where some contributors squash, some rebase, and some commit `wip`.
- Adding or reviewing `.gitignore`, `.gitattributes`, or a `core.hooksPath` hook directory.
- A release pipeline derives versions or changelogs from commit messages (semantic-release, release-please, git-cliff, commitizen) and its output is wrong.
- Two branch naming schemes coexist (`feature/foo` and `feat/FOO-1-foo`), or branches carry no ticket reference.
- A commit contains a secret, a build artifact, a `node_modules` tree, or a lockfile from a package manager the project does not use.
- A PR is unreviewable at >1000 lines, or a reviewer asks "which commit is the fix?".
- Someone ran `git push --force` on a shared branch, or `git reset --hard` after pushing.
- Deciding whether to adopt signed commits, required status checks, or a merge queue.
- A hotfix must ship and nobody knows whether to `revert` or `reset`.

## The Commit Message

Conventional Commits 1.0.0 defines the structure every downstream tool parses: `<type>[optional scope][!]: <description>`, then one blank line, an optional body, one blank line, and optional footers. The description follows the colon and a single space.

### Types

| Type       | Meaning                                                                   | SemVer effect |
| ---------- | ------------------------------------------------------------------------- | ------------- |
| `feat`     | A new capability in the unit's public surface                             | MINOR         |
| `fix`      | A repair of incorrect behavior                                            | PATCH         |
| `perf`     | Improves performance without changing observable behavior                 | PATCH         |
| `refactor` | Restructures code, changing neither behavior nor public surface           | none          |
| `style`    | Whitespace, formatting, quotes — no token semantics change                | none          |
| `docs`     | Documentation only: `*.md`, docstrings, generated reference               | none          |
| `test`     | Tests and fixtures only                                                   | none          |
| `build`    | Build system, bundler config, dependency manifest                         | none          |
| `ci`       | CI configuration, workflows, release automation                           | none          |
| `chore`    | Maintenance that fits nothing above (repo metadata, tooling housekeeping) | none          |
| `revert`   | Reverts a prior commit; the body names the reverted SHA                   | inverse of it |

`feat` and `fix` are the only types the spec mandates; the other nine are the Angular vocabulary that `@commitlint/config-conventional`'s `type-enum` enforces. Pin it in a rule so `hotfix` and `bugfix` cannot reappear. Classify `refactor` versus `perf` by observable behavior, not intent: if a caller can measure it, it is `perf`; if only the diff knows, it is `refactor`. A commit that both restructures and changes behavior is neither — split it.

### Scope: a module, never a file

A scope names the bounded context the change belongs to, drawn from the repository's own vocabulary — a package in a monorepo, a domain module in an application.

```
feat(billing): add proration for mid-cycle upgrades
perf(search): drop the N+1 on the facet aggregation

feat(invoice.service.ts): ...   # a file is not a context
feat(thing): ...                # locates nothing
```

Drop the scope for repo-wide changes (`ci:`, a dependency bump) rather than inventing a placeholder, and close the vocabulary so `--grep` stays usable:

```js
// commitlint.config.mjs
export default {
  extends: ["@commitlint/config-conventional"],
  rules: { "scope-enum": [2, "always", ["billing", "auth", "search", "deps"]] },
};
```

### Breaking changes

Mark one with `!` in the type/scope prefix, a `BREAKING CHANGE:` footer, or both. The `!` is what tooling reads for the version bump; the footer is what a human reads for the migration.

```
feat(api)!: require a tenant header on every endpoint

BREAKING CHANGE: requests without `X-Tenant-Id` now return 400 instead of
falling back to the default tenant. Clients must send the header.
```

`BREAKING CHANGE` must be uppercase — the single exception to the spec's rule that implementors treat messages case-insensitively; `BREAKING-CHANGE` is an accepted synonym. What counts as breaking for a published unit:

| Breaking                                                        | Not breaking                                       |
| --------------------------------------------------------------- | -------------------------------------------------- |
| Removing or renaming a public export, endpoint, or CLI flag     | Adding a new export, endpoint, or optional flag    |
| Tightening a type, or narrowing an accepted input               | Widening an accepted input                         |
| Changing a default value or default configuration               | Adding an optional parameter with the same default |
| Changing a serialized format, wire schema, or error code        | Fixing behavior to match the documented contract   |
| Raising the minimum runtime, language, or peer-dependency floor | Adding a dependency the consumer never imports     |
| Deprecating _and removing_ an API in the same release           | Deprecating with a warning and keeping the API     |

A bug fix is not breaking merely because someone depended on the bug — but if consumers plausibly did, ship it as a breaking change with a migration note rather than surprising them in a patch.

### Subject, body, footers

The subject completes `"This commit will …"`: imperative mood, present tense, no trailing period, under 72 characters. `@commitlint/config-conventional` caps the header at 100, but 72 is the real limit because `git log --oneline`, GitHub's commit list, and most terminals truncate past it. Do not capitalize the first word unless it is a proper noun — `add retry logic`, not `Added retry logic` or `added retry logic`.

The body carries **why**, never **what** — the diff states what. Write it when the change is non-obvious, recording the constraint that forced the shape, the rejected alternative, the issue it answers, migration steps a consumer must take, or benchmark numbers for a `perf`. Footers use `token: value` or `token #value`, with `-` replacing spaces in a token:

```
fix(cart): recompute totals after a partial refund

The cached subtotal was invalidated only on full refunds, so a partial
refund left the cart stale until reload.

Refs: #2210
Closes: #4182
Co-authored-by: Dana Okoro <dana@example.com>
```

Append trailers without hand-editing the message with `git commit --trailer "Co-authored-by: …" --trailer "Closes: #4182"` (git 2.32+), and inspect them with `git interpret-trailers --parse < .git/COMMIT_EDITMSG`. Set `git config commit.template ~/.gitmessage` so the shape is the default. GitHub closes an issue from `Closes #412` anywhere in the message **except** the subject line.

## Atomic Commits and Working-Tree Hygiene

An atomic commit is one logical change that builds and passes tests on its own and can be reverted alone. The test is mechanical: revert it, and exactly one thing breaks. A rename mixed with a behavior fix is not revertable, so nobody reverts it, so the fix stays broken; a refactor and a behavior change in two commits revert cleanly.

### Splitting a large working tree

Stage by hunk, not by file: `git add -N src/new-module.ts` makes a new file visible to `git add -p` (which takes `y/n/s/e` per hunk, `s` splitting one), `git reset -p` unstages a hunk staged by mistake, and `git stash push --keep-index` stashes the rest so you can test only what is staged. Order the sequence so each commit stands alone: infrastructure, refactor, behavior change, tests. Never push `wip` or `fix review comment`; attach corrections to the commit they belong to with `git commit --fixup=<sha>`, then `git rebase -i --autosquash origin/main`. On git ≥ 2.38 add `--update-refs` to keep a stack of dependent branches pointing at their rebased commits instead of orphaned SHAs.

### Never commit

- Build output a build step reproduces: `dist/`, `build/`, `target/`, `out/`, `.next/`, `__pycache__/`.
- Dependency trees: `node_modules/`, `vendor/`, `.venv/`, `Pods/`.
- A lockfile from a package manager the project does not use — two lockfiles for one manifest is a divergence, not a contribution.
- OS and editor metadata unless shared deliberately: `.DS_Store`, `Thumbs.db`, `.idea/`.
- Coverage reports, profiling output, database dumps, large binaries — a blob lives in every clone forever.
- Secrets: `.env`, `*.pem`, `*.p12`, service-account JSON.

### `.gitignore` discipline

Ignore by kind and in the right file: `.gitignore` is committed and covers artifacts every clone must skip, `.git/info/exclude` is local to your checkout, and `core.excludesFile` is your global list of editor and OS cruft. Verify rather than assume — `git check-ignore -v dist/bundle.js` prints the matching pattern and its source file, `git ls-files --others --exclude-standard` lists what would actually be added, and `git ls-files dist/` lists what is already tracked, which `.gitignore` does not affect; `git rm --cached -r dist/` untracks while leaving files on disk. `.gitattributes` handles the adjacent problems:

```gitattributes
* text=auto eol=lf
package-lock.json -diff linguist-generated=true
src/generated/** linguist-generated=true
```

`linguist-generated=true` collapses the file in review and hides it from language statistics; `-diff` suppresses its diff.

## Branching, History, and Integration

### Branch naming

`<type>/<ticket>-<slug>`, lowercase, hyphenated, ASCII: `feat/PROJ-412-oauth-refresh`, `fix/412-null-tenant`, `release/2.4.0`. Validate before pushing with `git check-ref-format --branch feat/PROJ-412-oauth-refresh`. A branch is a short-lived pointer, not a workspace; merge debt grows superlinearly with its age.

### Rebase versus merge

The rule concerns **shared** history, not aesthetics.

| Situation                   | Action                                                  |
| --------------------------- | ------------------------------------------------------- |
| Local commits, never pushed | `git rebase origin/main` — free, keeps history linear   |
| A branch others have pulled | `git merge origin/main` — rewriting discards their work |
| A PR branch only you own    | Rebase, then `git push --force-with-lease`              |
| Any forced push             | `--force-with-lease`, never `--force`                   |

`--force-with-lease` refuses the push if the remote moved since your last fetch — exactly the case where `--force` destroys someone's commit. Set `git config --global pull.ff only`, `fetch.prune true`, and `push.default simple` once. Rewriting a shared branch is the one git operation that loses data with no error and no recovery path for the victim; if a commit on a shared branch is wrong, `git revert` it.

### Squash versus preserved history

| Strategy     | History shape                           | Use when                                                |
| ------------ | --------------------------------------- | ------------------------------------------------------- |
| Squash merge | One commit per PR on the default branch | The PR's commits are scaffolding (`wip`, review fixups) |
| Rebase merge | Each commit replayed, linear            | Each commit is a revertable unit and the team bisects   |
| Merge commit | Topology preserved, merge nodes         | Release branches, long-running integration branches     |

Squash-merge and `git bisect` are in tension: over squashed history bisect can only identify a whole PR. Read what shipped with `git log --oneline --first-parent origin/main`, what happened with `git log --oneline --graph --decorate`, and what a rebase actually changed with `git range-diff origin/main...HEAD origin/main...HEAD@{1}`.

### Keeping the default branch green

The default branch must build and pass tests at every commit — the precondition for bisect, for `revert` as an incident tool, and for anyone branching off it. Require status checks and forbid direct pushes, including from maintainers; add a merge queue once more than a handful of PRs land per day, since it tests the merge result rather than the PR branch. Revert first, diagnose second: restore green with `git revert`, then fix forward — debugging on a red main blocks everyone. When the break is not obvious, bisect it with `git bisect start`, `git bisect bad`, `git bisect good v2.3.0`, `git bisect run npm test` (exit 0 is good, non-zero is bad), and `git bisect reset`.

### Tags, versioning, and signing

SemVer is `MAJOR.MINOR.PATCH`, driven by the commit types: `feat` → MINOR, `fix`/`perf` → PATCH, a breaking change → MAJOR. Versions `0.y.z` are initial development with no stability guarantee, which is why teams pin them pessimistically. Pre-release identifiers order below the release (`2.0.0-rc.1 < 2.0.0`); build metadata is ignored in precedence (`1.0.0+a` equals `1.0.0+b`). Deprecate before removing, keeping the API for at least one major.

Release tags must be **annotated**: a lightweight tag is a bare pointer with no tagger, date, or message, and `git describe` degrades on it. `user.name` is likewise a claim anyone can set, which is why signatures are required wherever a commit triggers a release.

```bash
git tag -a v1.4.0 -m "Release 1.4.0"
git tag -s v1.4.0 -m "Release 1.4.0"   # GPG/SSH-signed
git tag -v v1.4.0                      # verify the signature
git push --follow-tags                 # commits plus reachable annotated tags

git config --global commit.gpgsign true
git config --global tag.gpgsign true
git config --global gpg.format ssh                          # reuse an existing key
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git log --show-signature -3
git verify-commit HEAD
```

Branch protection that requires signed commits is the only enforcement that survives a contributor who forgets.

### Recovery: reflog, revert, reset

`git reflog` is local-only and is the recovery path for a bad rebase, a `reset --hard`, or a deleted branch. Defaults: 90 days for reachable entries, 30 for unreachable (`gc.reflogExpire`, `gc.reflogExpireUnreachable`). Find the lost SHA with `git reflog`, recreate a deleted branch with `git switch -c recovered-branch <sha>`, undo a commit while keeping changes staged with `git reset --soft HEAD~1`, and unstage one file with `git restore --staged src/app.ts`.

| Situation                     | Tool                                                                 |
| ----------------------------- | -------------------------------------------------------------------- |
| Not yet pushed                | `git commit --amend`, `git rebase -i`, `git reset`                   |
| Already pushed, shared branch | `git revert <sha>` — never reset                                     |
| Reverting a merge commit      | `git revert -m 1 <merge-sha>` (mainline = parent 1)                  |
| A secret was committed        | Rotate the credential first; `git filter-repo` is cleanup, not a fix |

Rewriting history does not un-leak a secret: the blob survives in forks, in CI caches, and in every clone.

### Pull request size and reviewability

Review effectiveness collapses with size — the widely cited SmartBear/Cisco study finds defect detection falling off sharply past roughly 200–400 changed lines in one session, with attention degrading after about an hour; a 2000-line PR is approved on faith. Target under ~400 changed lines, split by concern rather than file count, keep one logical change per PR (a refactor and a feature are two PRs), and land a large branch as a stack of dependent PRs. After a rebase, show `git range-diff` — re-reading the whole branch re-reads what was already approved. The description answers _why_; the diff answers _what_.

## Enforcement: Hooks and CI

Place each check at the cheapest stage that can catch it.

| Hook         | Budget      | Belongs here                                                      |
| ------------ | ----------- | ----------------------------------------------------------------- |
| `pre-commit` | < 2 seconds | Formatters, linters on staged files, secret and key scanning      |
| `commit-msg` | < 1 second  | Message grammar (commitlint), ticket reference, sign-off trailers |
| `pre-push`   | minutes OK  | Full test suite, type check, build, migration check               |

### Platform primitive: `core.hooksPath`

No framework required, and it works in every ecosystem. `git config core.hooksPath .githooks` points git at a committed hook directory; git passes the message-file path as `$1` to `commit-msg`.

```sh
# .githooks/commit-msg
#!/bin/sh
printf '%s' "$(head -n1 "$1")" | grep -qE \
  '^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9./-]+\))?!?: .{1,72}$' \
  || { echo "commit-msg: Conventional Commits header, <=72 chars" >&2; exit 1; }
```

A hook must be executable (`chmod +x`); a non-executable hook is silently skipped on Unix — the usual reason "the hook doesn't run".

### JavaScript and TypeScript: husky v9 plus commitlint

```json
{
  "scripts": { "prepare": "husky" },
  "devDependencies": {
    "@commitlint/cli": "^19.0.0",
    "@commitlint/config-conventional": "^19.0.0",
    "husky": "^9.0.0",
    "lint-staged": "^15.0.0"
  }
}
```

```sh
# .husky/pre-commit
npx lint-staged

# .husky/commit-msg
npx --no -- commitlint --edit "$1"
```

Husky v9 hooks are plain shell lines: the `#!/usr/bin/env sh` shebang and the `. "$(dirname -- "$0")/_/husky.sh"` source line that v4–v8 required are gone, and `husky install` is replaced by the `husky` prepare command. Two `@commitlint/config-conventional` defaults surprise people: `subject-full-stop` forbids a trailing period, and `subject-case` is `[2, 'never', ['sentence-case', 'start-case', 'pascal-case', 'upper-case']]`, so `feat: add x` passes while `feat: Add x` is **rejected** — override the rule explicitly rather than discovering this in CI.

### Multi-language: the `pre-commit` framework

It pins hook versions per repository and runs hooks written in any language, including a `repo: local` entry that shells out to the JS tooling:

```yaml
# .pre-commit-config.yaml
default_install_hook_types: [pre-commit, commit-msg]

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: detect-private-key
      - id: check-added-large-files
        args: [--maxkb=500]
      - id: end-of-file-fixer

  - repo: local
    hooks:
      - id: commitlint
        name: commitlint
        entry: npx --no -- commitlint --edit
        language: system
        stages: [commit-msg]
```

Install both hook types with `pre-commit install --hook-type commit-msg` (plus plain `pre-commit install`), backfill a repo that never had hooks with `pre-commit run --all-files`, and move the pinned `rev` tags with `pre-commit autoupdate` — a floating `rev` makes hook behavior differ between machines.

### CI as the backstop

Hooks are local and bypassable with `--no-verify`; CI is neither. Lint the PR's commit range:

```yaml
# .github/workflows/commitlint.yml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- run: npx commitlint --from ${{ github.event.pull_request.base.sha }} --to ${{ github.event.pull_request.head.sha }} --verbose
- run: docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:latest detect --source=/repo -v
```

`fetch-depth: 0` is required: a shallow clone does not contain the base SHA, so commitlint fails with a confusing range error. Server-side secret scanning and push protection catch leaks for public repos and for organizations with the feature enabled, but neither substitutes for rotating the credential. `git commit --no-verify` skips both `pre-commit` and `commit-msg` — legitimate for reverting an already-reviewed commit during an incident, never the normal path; a repo where it is normal has hooks that are too slow or too noisy. Repository convention documents (`CONTRIBUTING.md`, `CODEOWNERS`, ADRs) are covered in [std-docs.md](std-docs.md).

## Common Mistakes

| Mistake                                                 | Why It Breaks                                                                    | Correct Approach                                                                 |
| ------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `git reset --hard` + force-push on a shared branch      | Silently deletes commits others built on; no error, no recovery for them         | `git revert` on shared history; `--force-with-lease` if a rewrite is unavoidable |
| Subject in past tense or with a trailing period         | Breaks changelog generation; reads as a diff summary, not an instruction         | Imperative mood, no trailing period, under 72 chars                              |
| A scope naming a file (`feat(user.service.ts):`)        | The scope stops locating a bounded context; `--grep` queries become useless      | Scope = module, package, or context from the repo's own vocabulary               |
| `fix:` used for a refactor, or `refactor:` for a bugfix | Version bumps and release notes become wrong; the type lies about risk           | Classify by observable behavior; split commits that do both                      |
| Breaking change shipped as `fix:` with no `!`           | Consumers get a MAJOR change in a PATCH release                                  | `!` in the prefix plus a `BREAKING CHANGE:` footer with migration text           |
| A 40-file working tree committed as one `update`        | Unreviewable, unbisectable, unrevertable without collateral damage               | Split with `git add -p` / `git add -N` into a sequence of atomic commits         |
| `dist/`, `node_modules/`, or coverage committed         | Every clone carries it forever; diffs become unreadable noise                    | `.gitignore` it, then `git rm --cached` the tracked copy                         |
| `.env` or a private key committed                       | The blob is permanent in forks and caches; rewriting history is not a remedy     | Rotate the credential first; add a `detect-private-key` or gitleaks gate         |
| `wip` and `fix review` commits pushed                   | History carries no information; bisect and blame become useless                  | `git commit --fixup=<sha>` plus `git rebase -i --autosquash` before pushing      |
| Squash-merging while the team relies on `git bisect`    | Bisect can only blame the whole PR, never the commit                             | Preserve commits; require each to be atomic and independently testable           |
| Full test suite in a `pre-commit` hook                  | Adds minutes per commit; contributors learn `--no-verify` and disable everything | Keep `pre-commit` under ~2s; move slow checks to `pre-push` or CI                |
| Message validation living in `pre-commit`               | The message file does not exist yet, so the check never sees the message         | Put message checks in the `commit-msg` hook, where git passes the file path      |
| `.gitignore` used to hide an already-tracked file       | `.gitignore` does not apply to tracked paths, so the file keeps being committed  | `git rm --cached <path>`, then verify with `git check-ignore -v`                 |
| Lightweight tag used for a release                      | No tagger, date, or message; `git describe` and release tooling degrade          | Annotated tags: `git tag -a v1.0.0 -m "Release 1.0.0"`                           |
| A 2000-line PR approved on faith                        | Defect detection collapses past a few hundred lines                              | Split into stacked PRs under ~400 lines; use `git range-diff` after a rebase     |

## Checklist

1. Read `git log --oneline -50` and list every distinct type token in use; collapse synonyms (`hotfix`, `bugfix`, `update`, `fixed`) to the canonical eleven.
2. Confirm the type vocabulary is pinned by a `type-enum` rule in `commitlint.config.*` or an equivalent CI check, not merely a convention in prose.
3. Verify every scope token resolves to a real module, package, or bounded context; reject scopes naming a file or a path.
4. Grep the last 200 commits for breaking changes (`^[a-z]+(\(.*\))?!:`) and confirm each carries a `BREAKING CHANGE:` footer with migration text.
5. Check the last 50 subjects for past tense, trailing periods, and length over 72 characters; report each offender with its SHA.
6. Confirm every commit mixing a refactor with a behavior change is split, or document why it cannot be.
7. Verify `pre-commit` hooks run in under two seconds and operate on staged files only; move anything slower to `pre-push`.
8. Confirm message validation lives in a `commit-msg` hook (`commitlint --edit "$1"`), not in `pre-commit`.
9. Confirm hook scripts are executable (`git ls-files -s .githooks`) and that `core.hooksPath` or the husky `prepare` script is configured.
10. Run `git ls-files --others --exclude-standard` and `git check-ignore -v` on each expected artifact path; confirm nothing generated, secret, or vendored would be added.
11. Filter `git ls-files` for `dist/`, `build/`, `target/`, `node_modules/`, `__pycache__/`, `*.log`, `.env*`, and `*.pem`; untrack any hit with `git rm --cached`.
12. Verify `.gitattributes` marks generated and lock files (`linguist-generated=true`) and normalizes line endings (`* text=auto eol=lf`).
13. List `git branch -a` and report any branch violating the `<type>/<ticket>-<slug>` scheme or carrying no ticket reference.
14. Confirm the default branch is protected: required status checks, no direct pushes, and signed commits if the project claims them.
15. Check the last 20 entries of `git log --first-parent` and confirm the squash/merge/rebase policy is applied consistently, not per author.
16. Verify release tags are annotated (`git for-each-ref refs/tags --format='%(objecttype)'` prints `tag`, not `commit`) and follow SemVer.
17. Verify CI lints the PR commit range with `fetch-depth: 0` and runs a secret scanner; confirm `--no-verify` is not the documented workflow.
18. Measure the largest open PR's diff; if it exceeds ~400 lines, report it as a reviewability finding with a suggested split.

## References

- [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) — the normative grammar, the `!` and `BREAKING CHANGE` rules, and the case-sensitivity exception.
- [Semantic Versioning 2.0.0](https://semver.org/) — precedence, pre-release ordering, and the `0.y.z` stability caveat.
- [commitlint](https://commitlint.js.org/) and [`@commitlint/config-conventional`](https://github.com/conventional-changelog/commitlint/tree/master/%40commitlint/config-conventional) — rule names, defaults, and `scope-enum`/`subject-case` behavior.
- [husky](https://typicode.github.io/husky/) — v9 hook file format and the `prepare` script.
- [pre-commit](https://pre-commit.com/) — hook types, `default_install_hook_types`, and `autoupdate`.
- [lint-staged](https://github.com/lint-staged/lint-staged) and [lefthook](https://lefthook.dev/) — staged-file task running and a single-binary polyglot alternative.
- [Git: `git commit`](https://git-scm.com/docs/git-commit) — `--fixup`, `--squash`, `--trailer`, `--amend`, `--no-verify`.
- [Git: `git rebase`](https://git-scm.com/docs/git-rebase) — `--autosquash`, `--update-refs`, and interactive history editing.
- [Git: `git reflog`](https://git-scm.com/docs/git-reflog) and [`gc.reflogExpire`](https://git-scm.com/docs/git-config#Documentation/git-config.txt-gcreflogExpire) — the recovery window and its defaults.
- [Git: `git revert`](https://git-scm.com/docs/git-revert) — `-m` for merge commits, and why it is the shared-history tool.
- [Git: `git tag`](https://git-scm.com/docs/git-tag) and [`git push --follow-tags`](https://git-scm.com/docs/git-push) — annotated versus lightweight tags.
- [Git: `git check-ignore`](https://git-scm.com/docs/git-check-ignore), [`gitignore` patterns](https://git-scm.com/docs/gitignore), and [`gitattributes`](https://git-scm.com/docs/gitattributes) — verifying a pattern, its source file, and `text=auto`/`linguist-generated`.
- [Git: Signing your work](https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work) and [GitHub: About commit signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification) — GPG, SSH, and S/MIME signing.
- [GitHub: Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue) — testing the merge result rather than the PR branch.
- [git-filter-repo](https://github.com/newren/git-filter-repo) — the maintained replacement for `git filter-branch`, and why it is not a secret-rotation tool.
- [SmartBear: Best practices for peer code review](https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/) — the review-size and duration evidence behind the ~400-line target.
