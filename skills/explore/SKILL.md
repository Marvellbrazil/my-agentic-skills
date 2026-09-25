---
name: explore
description: Explores a codebase to build a complete, evidence-backed model of the project — architecture, module boundaries, entry points, data flow, conventions, standards, tooling, and its documented preferences — then returns a structured, summarized report for context gaining and planning. Use when the user types /explore, asks to explore or understand the codebase, wants a project overview, needs onboarding, or is starting a session and wants context before planning work. Read-only by default.
allowed-tools: Read Grep Glob Bash
---

# Explore

Build an accurate mental model of a codebase and hand it back in a form the user can act on.

This is a **read-only** skill unless the user asks for a written artifact. It answers three questions: what is this project, how is it organized, and what rules govern changes to it. The output is the input to planning.

## Principles

1. **Evidence, not impression.** Every claim names the file it came from. "Uses Postgres" is weak; "Uses Postgres — `docker-compose.yml:14`, `prisma/schema.prisma:1`" is usable.
2. **Conventions before code.** The documented rules (`AGENTS.md`, `CONTRIBUTING.md`, lint configs) constrain every future change. Read them first; they are cheap and they are authoritative.
3. **Read the manifest, not the whole tree.** A manifest declares the project's intent. Source files confirm it. Do not read 400 files to answer a question a manifest answers.
4. **Prefer structure over content.** Directory shape, file names, and export signatures carry most of the signal at a fraction of the cost.
5. **Say what you did not determine.** An honest gap is useful. A confident guess about the architecture is actively harmful, because the user will plan on top of it.
6. **Do not modify anything.** Exploration must not leave a trace.

## Phase 0 — Scope

Default to a full pass. Narrow it when the user named a target or the repo is large enough that a full pass would be wasteful.

| Signal                        | Action                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------- |
| Bare `/explore`               | Full pass                                                                       |
| `/explore the payment module` | Narrow to that subtree, plus its direct dependencies and consumers              |
| Monorepo with 20 packages     | Ask which package, or explore the workspace root and one representative package |
| More than ~5,000 source files | Ask for a target; do not attempt an exhaustive read                             |

If you must narrow, say so and name what you skipped. Never silently truncate coverage — the user will assume the report is complete.

## Phase 1 — Identity and Intent

Answer "what is this and what is it for" before anything else.

```bash
ls -a
cat README.md 2>/dev/null | head -80
```

Read the manifest. It declares the runtime, dependencies, and the project's own entry points.

```bash
cat package.json 2>/dev/null
cat pyproject.toml 2>/dev/null
cat composer.json Gemfile go.mod Cargo.toml pom.xml build.gradle.kts 2>/dev/null
cat deno.json bun.lockb 2>/dev/null
```

Extract and record:

| Field                             | Where to look                                                                                                                      |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Project name and one-line purpose | `README.md`, manifest `name`/`description`                                                                                         |
| Runtime and version               | `engines`, `requires-python`, `go`, `toolchain`, `.nvmrc`, `.python-version`                                                       |
| Package manager                   | `packageManager`, the lockfile present (`bun.lockb`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `uv.lock`, `poetry.lock`) |
| Primary language and framework    | Dependency list                                                                                                                    |
| Available scripts                 | `scripts` in the manifest — these are the project's real verbs                                                                     |
| Declared entry points             | `main`, `module`, `exports`, `bin`, `[project.scripts]`                                                                            |

**The scripts block is the highest-value field in the manifest.** It is the project's vocabulary for build, test, lint, and run. Record it verbatim.

## Phase 2 — Conventions and Standards

Do this before reading source. The rules constrain how you interpret everything else.

```bash
for f in AGENTS.md CLAUDE.md CODEBASE.md CONTRIBUTING.md ARCHITECTURE.md STYLE.md CONVENTIONS.md SECURITY.md; do
  [ -f "$f" ] && echo "=== $f ===" && cat "$f"
done
find . -maxdepth 3 -iname '*.md' -not -path './.git/*' -not -path '*/node_modules/*' \
  -not -path '*/vendor/*' 2>/dev/null | head -40
```

```bash
ls -a | grep -E '^\.(eslint|prettier|editorconfig|stylelint|rubocop|golangci|swiftlint|clang-format)'
cat .editorconfig eslint.config.js eslint.config.mjs .eslintrc* .prettierrc* 2>/dev/null
cat pyproject.toml 2>/dev/null | sed -n '/\[tool\./,/^\[/p'
cat .golangci.yml .rubocop.yml phpstan.neon analysis_options.yaml 2>/dev/null
```

Record a conventions table. This is what the user most needs and least often has written down:

| Concern           | Rule                                          | Source             | Enforced?   |
| ----------------- | --------------------------------------------- | ------------------ | ----------- |
| Language standard | PHP 8.3, `declare(strict_types=1)`            | `AGENTS.md`        | No          |
| Formatting        | 2-space, single quotes, no semicolons         | `.prettierrc`      | Yes (CI)    |
| Type strictness   | TS `strict: true`, `noUncheckedIndexedAccess` | `tsconfig.json`    | Yes (build) |
| Naming            | kebab-case files, PascalCase components       | `CONTRIBUTING.md`  | No          |
| Import style      | Absolute from `@/`, no barrels                | `eslint.config.js` | Yes (lint)  |
| Comments          | No inline comments; self-documenting code     | `AGENTS.md`        | No          |
| Commit style      | Conventional Commits, no co-author            | `AGENTS.md`        | No          |
| Testing           | Vitest, colocated `*.test.ts`                 | `package.json`     | Yes (CI)    |

**Mark whether each rule is enforced.** A rule enforced by CI is a fact; a rule in a prose document is an intention. This distinction tells the user where drift is likely.

If there is **no** conventions document, say so explicitly and derive the conventions from the code instead, labeling them as observed rather than declared.

## Phase 3 — Structure and Boundaries

Map the tree without reading every file.

```bash
find . -maxdepth 2 -type d -not -path './.git*' -not -path '*/node_modules*' \
  -not -path '*/vendor*' -not -path '*/dist*' -not -path '*/build*' \
  -not -path '*/.next*' -not -path '*/__pycache__*' | sort | head -60
```

```bash
find . -type f -not -path './.git/*' -not -path '*/node_modules/*' -not -path '*/vendor/*' \
  -not -path '*/dist/*' -not -path '*/build/*' \
  | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20
```

```bash
find . -maxdepth 3 -type f \( -name 'index.*' -o -name 'main.*' -o -name 'app.*' \
  -o -name 'server.*' -o -name 'routes.*' -o -name 'mod.rs' -o -name '__init__.py' \) \
  -not -path './.git/*' -not -path '*/node_modules/*' -not -path '*/vendor/*' 2>/dev/null | head -30
```

Identify and label:

- **Architecture style.** Layer-first (`controllers/`, `services/`, `models/`) vs feature-first (`orders/`, `billing/`) vs hexagonal vs monorepo packages. Name it from the evidence.
- **Module boundaries.** Which directories are cohesive units with a public surface, and which are shared utilities.
- **Entry points.** Where execution begins, per target: HTTP server, CLI, worker, scheduled job, mobile app, library export.
- **The dependency direction.** Which layers may import which. A violation here is the most common architectural defect; note any you observe.

Detect boundaries from import edges, not from directory names:

```bash
grep -rn --include='*.ts' --include='*.tsx' -E "^import .* from ['\"]\.\." src/ 2>/dev/null | head -20
```

## Phase 4 — Data and Runtime

```bash
cat docker-compose.yml docker-compose.yaml Dockerfile .dockerignore 2>/dev/null | head -100
find . -maxdepth 3 \( -name '*.sql' -o -name 'schema.prisma' -o -name '*.migration' -o -path '*migrations*' \) \
  -not -path './.git/*' -not -path '*/node_modules/*' 2>/dev/null | head -30
find . -maxdepth 2 -name '.env*' -not -path './.git/*' 2>/dev/null
```

Record: datastore and version, cache, queue, external services, and how configuration is supplied. **Never print the contents of a `.env` file.** List which keys it declares, and treat values as secrets:

```bash
sed 's/=.*/=<redacted>/' .env.example 2>/dev/null | head -30
```

## Phase 5 — Workflow and Tooling

```bash
cat Makefile justfile Taskfile.yml 2>/dev/null | head -60
ls -R .github/workflows 2>/dev/null
cat .github/workflows/*.yml 2>/dev/null | grep -E 'name:|run:|uses:' | head -40
```

Record: the build command, the test command, the lint command, the dev-server command, and what CI actually gates on. **CI is the real definition of "done" in the repo** — if CI runs `lint && test && build`, that is the contract.

Note any pre-commit hooks and what they enforce.

## Phase 6 — Synthesize

Read selectively, only to confirm or refute what the structure implies. Read one representative file per architectural layer — not all of them.

```bash
wc -l $(git ls-files '*.ts' '*.tsx' 2>/dev/null | head -50) 2>/dev/null | sort -rn | head -15
```

The largest files are where the architecture is weakest and where the user's future work will hurt. Report them.

```bash
git log --oneline -15
git log --format='%s' -60 | sed 's/(.*//' | sed 's/:.*//' | sort | uniq -c | sort -rn
```

The commit history reveals what the team actually works on and whether they follow their own commit convention.

## Output

Deliver a single structured report. Lead with the summary — the user may read only that.

```markdown
# Project Profile — <name>

<2-3 sentence summary: what it is, what it does, how it is built.>

**Stack** TypeScript 5.6 · React 19 · Vite 6 · Postgres 16 · Bun
**Architecture** Feature-first, colocated tests, no barrel files
**Entry points** `src/main.tsx` (browser), `server/index.ts` (API)
**Health** 1 conventions gap, 3 oversized files, no type-check in CI

## 1. What This Is

<purpose, domain, who uses it, and what it is not>

## 2. Stack and Runtime

| Layer | Choice | Version | Evidence |
| ----- | ------ | ------- | -------- |

## 3. Structure

<annotated tree of the meaningful directories, with a one-line purpose each>

## 4. Module Boundaries

<which units exist, their public surface, and the allowed dependency direction>

## 5. Entry Points and Flow

<how a request or command travels from entry to storage, naming the files>

## 6. Conventions and Standards

<the conventions table from Phase 2, including what is enforced vs merely stated>

## 7. Commands

| Purpose | Command     | Source          |
| ------- | ----------- | --------------- |
| Dev     | `bun dev`   | package.json:12 |
| Test    | `bun test`  | package.json:14 |
| Lint    | `bun lint`  | package.json:15 |
| Build   | `bun build` | package.json:16 |

## 8. CI Gates

<what CI enforces, and what it does not>

## 9. Observations

<the non-obvious: architectural risks, oversized files, drift from documented
rules, missing tests, dead code, inconsistencies worth a /s13n pass>

## 10. Unknowns

<what could not be determined, and the file or question that would resolve it>
```

## Output Rules

- **Summarize; never dump.** Do not paste file contents or whole manifests. Extract and interpret.
- **Every claim carries evidence.** A file path, a line number, or a command output.
- **Separate declared from observed.** "Documented: no inline comments" vs "Observed: 3 files use inline comments."
- **Rank observations by what the user should do first.** A missing CI type-check outranks a stale comment.
- **Keep it readable.** Tables over prose, a tree over a paragraph, and no wall of text. If a section has nothing, omit it rather than printing "N/A".
- **Flag genuine uncertainty as uncertainty.** Write "could not determine" and move on.
- **Do not recommend a rewrite.** Describe the project as it is. Recommendations belong in a planning step the user asks for.

## Persisting the Profile

If the user wants the model kept for later sessions, write it to `.claude/context/project-profile.md` or a path they name, and tell them the path. Do not create a file unless asked — exploration must not leave a trace by default.

## Depth

Scale the effort to the repository and the ask.

| Repository                     | Approach                                                                                     |
| ------------------------------ | -------------------------------------------------------------------------------------------- |
| Small (under ~50 source files) | Read the manifests, the conventions docs, and most source files. Be exhaustive.              |
| Medium (~50-500 files)         | Manifests, conventions, structure, one representative file per layer, and the largest files. |
| Large (~500-5,000)             | Manifests, conventions, structure, and CI only. Ask the user to name a target for depth.     |
| Monorepo                       | Workspace root plus the packages the user names, or one representative package.              |

## Common Mistakes

| Mistake                                                       | Why It Breaks                                                     | Correct Approach                                            |
| ------------------------------------------------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------- |
| Skipping the conventions docs                                 | You describe a project and miss the rules that govern changing it | Read `AGENTS.md`, `CONTRIBUTING.md`, and lint configs first |
| Reading files instead of structure                            | Burns enormous context for a fraction of the signal               | Read manifests, tree shape, and signatures                  |
| Reporting a convention as enforced when it is only documented | The user plans on a gate that does not exist                      | Check whether CI or lint actually enforces it               |
| Guessing the architecture from directory names                | Names lie; `services/` is often not a service layer               | Confirm with import edges and one representative file       |
| Claiming completeness after sampling                          | The user plans on a partial picture they believe is whole         | State what you skipped, explicitly                          |
| Dumping file contents                                         | Unreadable and destroys the value of the summary                  | Extract, interpret, cite                                    |
| Printing a `.env` file                                        | Leaks secrets into the transcript and the user's history          | List keys only; redact values                               |
| Writing files unprompted                                      | Exploration should leave no trace                                 | Read-only unless asked                                      |
| Recommending a rewrite                                        | Not what was asked, and it undermines trust in the findings       | Describe; let the user decide                               |
| Reporting stale docs as fact                                  | Docs drift; the code is the truth                                 | Separate declared from observed, and note disagreement      |
| One giant prose section                                       | Unreadable                                                        | Tables, trees, and a scannable structure                    |
| Ignoring the commit history                                   | It reveals real priorities and convention drift                   | Read the recent log and the subject patterns                |
