---
name: s13n
description: Standardizes a project by detecting where the same concern is solved in divergent ways across files, asking the user which variant is canonical when the codebase does not already answer it, then normalizing the code to that standard. Also aligns code with the project's documented conventions and per-language best practices. Use when the user types /s13n, asks to standardize, normalize, or unify a codebase, asks why files disagree on a pattern, or wants a project made consistent. Accepts an optional scope to standardize only selected aspects or directories.
allowed-tools: Read Write Edit Glob Grep Bash
---

# Standardization (s13n)

Make a codebase internally consistent and aligned with its own declared standards.

The core problem this skill solves: **the same concern is solved differently in different files.** Files 1, 2, and 4 call `moduleA.doThing()`, file 3 calls `moduleB.doThing()`. Nothing is broken — every file works — but the codebase now has two truths, and every future reader must learn both. This skill finds those divergences, establishes which variant is canonical, and normalizes the code.

## The One Rule That Governs Everything

**Never silently pick a winner for a divergence that the user has not authorized.**

Choosing a convention is a design decision about the user's codebase. The majority variant is evidence, not authority. A single file may hold the newer, correct pattern while three files hold the legacy one — normalizing to the majority would delete the migration.

So: detect the divergence, gather evidence, then **ask**. Ask with a recommendation, ask with the evidence attached, but ask.

## Source of Truth Precedence

Before asking anything, check whether the project already answers the question. Resolve every convention question against this chain, highest first:

| Rank | Source                                      | Example                                                                                                                                                                                |
| ---- | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | A convention document in the repo           | `AGENTS.md`, `CLAUDE.md`, `CODEBASE.md`, `CONTRIBUTING.md`, `docs/architecture.md`, `docs/conventions.md`                                                                              |
| 2    | Enforced tooling configuration              | `.editorconfig`, `eslint.config.js`, `.prettierrc`, `ruff.toml`, `pyproject.toml` `[tool.*]`, `phpstan.neon`, `.golangci.yml`, `.rubocop.yml`, `.stylelintrc`, `analysis_options.yaml` |
| 3    | A dominant, unambiguous pattern in the code | 47 of 48 files do it one way                                                                                                                                                           |
| 4    | The user's answer                           | Given in response to your question                                                                                                                                                     |
| 5    | The per-language best practice              | The `references/std-*.md` modules in this skill                                                                                                                                        |

**Ranks 1 and 2 are authoritative and are not up for a vote.** If `AGENTS.md` says "all monetary values are integer cents" and 30 files use floats, the document wins and those 30 files are the defect. Do not ask the user to choose between their own documented standard and a violation of it — report the violation and fix it.

Ranks 1 and 2 are also the reason to check before asking: a question the repo already answers wastes the user's attention.

Only rank 3 requires a question. Only rank 5 is ever overridden by a rank 4 answer.

## Reference Modules

Load a module when its concern is in scope. Each is self-contained; read it in full before normalizing that concern.

| Concern                                      | Module                                                     |
| -------------------------------------------- | ---------------------------------------------------------- |
| Repository layout, naming, file organization | [references/std-structure.md](references/std-structure.md) |
| PHP                                          | [references/std-php.md](references/std-php.md)             |
| JavaScript                                   | [references/std-js.md](references/std-js.md)               |
| TypeScript                                   | [references/std-ts.md](references/std-ts.md)               |
| Python                                       | [references/std-python.md](references/std-python.md)       |
| Go                                           | [references/std-go.md](references/std-go.md)               |
| Rust                                         | [references/std-rust.md](references/std-rust.md)           |
| Java                                         | [references/std-java.md](references/std-java.md)           |
| C# / .NET                                    | [references/std-csharp.md](references/std-csharp.md)       |
| Ruby                                         | [references/std-ruby.md](references/std-ruby.md)           |
| CSS and styling                              | [references/std-css.md](references/std-css.md)             |
| HTML and markup                              | [references/std-html.md](references/std-html.md)           |
| SQL and databases                            | [references/std-sql.md](references/std-sql.md)             |
| Shell and scripting                          | [references/std-shell.md](references/std-shell.md)         |
| YAML, JSON, configuration                    | [references/std-yaml-json.md](references/std-yaml-json.md) |
| Documentation and comments                   | [references/std-docs.md](references/std-docs.md)           |
| Git, branching, commits                      | [references/std-git.md](references/std-git.md)             |

Load `std-structure.md` for any structural divergence, and the language module for the repository's primary language. Do not load every module — a normalization pass that consults seventeen standards will apply none of them well.

## Phase 1 — Reconnaissance

**Find the convention documents first.** These are authoritative, and reading them may answer most of your questions before you ask any.

```bash
ls -a
for f in AGENTS.md CLAUDE.md CODEBASE.md CONTRIBUTING.md ARCHITECTURE.md README.md .editorconfig; do
  [ -f "$f" ] && echo "=== $f ===" && head -100 "$f"
done
ls -d docs .github 2>/dev/null && find docs .github -maxdepth 2 -name '*.md' 2>/dev/null | head -30
```

**Find the enforced tooling configuration.** A linter config is a written standard that is already enforced; aligning with it is free and non-controversial.

```bash
ls -a | grep -E '^\.(eslint|prettier|editorconfig|stylelint|rubocop|golangci)'
cat pyproject.toml setup.cfg ruff.toml mypy.ini .golangci.yml .rubocop.yml phpstan.neon 2>/dev/null | head -120
cat package.json 2>/dev/null | sed -n '/"scripts"/,/}/p'
```

**Identify the languages and their weight**, so you standardize the primary language first and do not spend effort on a vendored or generated subtree:

```bash
find . -type f -not -path './.git/*' -not -path '*/node_modules/*' -not -path '*/vendor/*' \
  -not -path '*/dist/*' -not -path '*/build/*' \
  | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -25
```

**Record the shape before touching anything:**

| Question                                                                                        | Why it matters                                                |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Is there a convention document? Where?                                                          | Ranks 1-2 short-circuit the questions you would otherwise ask |
| What is the primary language and framework?                                                     | Selects the `references/std-*.md` module                      |
| What formatter and linter are configured?                                                       | Mechanical normalization should use them, not hand edits      |
| Which directories are generated, vendored, or third-party?                                      | Never standardize them — the change is lost on the next build |
| Is the repo mid-migration? Any `TODO(migrate)`, feature flags, or two parallel implementations? | A second implementation is often deliberate, not a defect     |
| How large is the codebase?                                                                      | Determines whether this is one pass or a scoped engagement    |

If the repository is mid-migration, **stop and ask** before normalizing anything. Normalizing a migration in progress destroys the migration.

## Phase 2 — Detect Divergences

A divergence is a concern that is solved in two or more incompatible ways. Search for them systematically, by concern.

```bash
grep -rn --exclude-dir={node_modules,.git,dist,build,vendor,__pycache__} \
  -E "require\(|from ['\"]|import .* from" . | head -40

grep -rn --exclude-dir={node_modules,.git,dist,build,vendor,__pycache__} \
  -E "\.then\(|await |async function|async \(" . | head -40

grep -rn --exclude-dir={node_modules,.git,dist,build,vendor,__pycache__} \
  -E "console\.log|print\(|fmt\.Print|echo |logger\.|Log\." . | head -40

grep -rn --exclude-dir={node_modules,.git,dist,build,vendor,__pycache__} \
  -E "throw new|return Err|raise |panic\(|Result<|catch \(|except " . | head -40
```

### Divergence Taxonomy

Audit every concern in this table. Each row is a question to answer with evidence.

| Concern                      | Typical divergence                                                                          |
| ---------------------------- | ------------------------------------------------------------------------------------------- |
| **Module/API usage**         | `moduleA.doThing()` vs `moduleB.doThing()` — the user's core case                           |
| **Import style**             | Default vs named; relative vs absolute; extension or not; barrel vs direct path             |
| **Naming**                   | `camelCase` vs `snake_case`; file naming; boolean prefixes; verb choice in function names   |
| **Async style**              | Callbacks vs promises vs `async/await`; `then` chains mixed with `await`                    |
| **Error handling**           | Throw vs return codes; custom error classes vs bare `Error`; catch-and-swallow vs propagate |
| **Null handling**            | `=== null` vs `== null`; `??` vs `\|\|`; optional chaining vs guards                        |
| **State management**         | Local state vs store vs context; mutable vs immutable updates                               |
| **Data access**              | ORM vs raw query; repository vs inline query; eager vs lazy loading                         |
| **Validation**               | Schema at the boundary vs inline checks vs none; one validator or three                     |
| **Logging**                  | Structured vs string; logger instance vs global; log levels used inconsistently             |
| **Configuration**            | Env vars vs config file vs constants; one accessor or many                                  |
| **Testing**                  | Test framework; `describe/it` vs flat; mocking style; fixture location; assertion library   |
| **Formatting**               | Indentation, quotes, semicolons, line width, trailing commas — **defer to the formatter**   |
| **Type strictness**          | `strict` on or off; `any` vs `unknown`; assertions vs narrowing                             |
| **File structure**           | One export per file vs many; colocated tests vs a parallel `tests/` tree                    |
| **Date and number handling** | Native `Date` vs a library; float money vs integer minor units                              |
| **HTTP/client usage**        | `fetch` vs `axios` vs a project wrapper; retry and timeout policy                           |
| **Component/module pattern** | Class vs function; HOC vs hooks; inheritance vs composition                                 |

### The Divergence Record

For each divergence, record it with enough evidence that the user can decide in one read.

```markdown
### D1 — Module accessor for date arithmetic

**Variant A** — `dayjs` — 34 files
src/orders/created.ts:12, src/cart/total.ts:8, src/user/profile.ts:31 (+31 more)
`dayjs(order.createdAt).add(7, 'day')`

**Variant B** — native `Date` + a local helper — 6 files
src/reports/range.ts:44, src/export/csv.ts:19 (+4 more)
`addDays(new Date(order.createdAt), 7)`

**Variant C** — `date-fns` — 2 files
src/billing/invoice.ts:57, src/billing/proration.ts:22
`addDays(new Date(order.createdAt), 7)`

**Conflict** Three libraries for one concern. `dayjs` and `date-fns` are both
direct dependencies; `addDays` in `src/lib/date.ts` duplicates both.
**Recommendation** A — `dayjs` is the majority and already a direct dependency.
**Counter-signal** Variant C is confined to `billing/`, which may be a newer
module with a deliberate choice. Confirm before normalizing.
```

**Count the occurrences, do not estimate.** "Most files" is not evidence; "34 of 42 files" is. Run the count:

```bash
grep -rIl "dayjs" --exclude-dir={node_modules,.git,dist,build,vendor} . | wc -l
grep -rIl "date-fns" --exclude-dir={node_modules,.git,dist,build,vendor} . | wc -l
```

**Look for the counter-signal.** A minority variant confined to one directory, one author, or one recent commit range is often the intended direction. Check before recommending the majority:

```bash
git log --oneline -20 -- src/billing/
git log -S "date-fns" --oneline | head -5
```

## Phase 3 — Ask the User

This is the step that makes the skill correct rather than merely clever.

Ask **one question per divergence**, and batch related divergences into a single round of questions so the user is not interrogated one item at a time. Use the `AskUserQuestion` tool.

Each question must carry:

- **The concern**, stated in one line.
- **The variants**, each with its file count and a representative location.
- **A recommendation**, marked as such, with the reason (usually: majority, or already a dependency, or the project's documented standard).
- **The counter-signal**, if there is one, so the user is not blindsided by the recommendation.

Prefer a preview showing the concrete code for each variant — the user is choosing between code shapes, and seeing them side by side decides faster than reading prose about them.

```
Which is the standard for date arithmetic?

A (Recommended) — dayjs           34 files   `dayjs(x).add(7, 'day')`
B                 — native Date    6 files   `addDays(new Date(x), 7)`
C                 — date-fns        2 files   `addDays(new Date(x), 7)`
```

Rules for asking:

- **Never ask about something the convention document or linter already answers.** Fix it and report it.
- **Never ask a question whose answer does not change what you do.** If you will normalize either way, do not ask.
- **Never offer a variant you would not implement.** Do not present a broken or deprecated option as a choice.
- **Cap the round at four questions.** More than four means you have not prioritized; report the rest as findings and ask about the top four.
- **If the user declines to choose**, do not guess. Report the divergence as an open decision, standardize only the aspects they did authorize, and leave the rest untouched.
- **If the user picks a variant that conflicts with a rank 1-2 source**, flag the conflict explicitly and ask them to confirm they intend to override their own documented standard. Do not silently override.

## Phase 4 — Normalize

Normalize in this order: mechanical first, semantic second. Mechanical changes are safe and reviewable; semantic changes carry risk and deserve their own review.

### Step 1 — Mechanical normalization, via the project's own tooling

**Prefer the configured formatter over hand-editing.** A formatter produces a canonical result, is already trusted by the project, and cannot introduce a typo.

| Stack     | Command                                                 |
| --------- | ------------------------------------------------------- |
| JS/TS     | `npx prettier --write .` then `npx eslint . --fix`      |
| Python    | `ruff format .` then `ruff check . --fix`, or `black .` |
| Go        | `gofmt -w .` then `goimports -w .`                      |
| PHP       | `vendor/bin/pint` or `vendor/bin/php-cs-fixer fix`      |
| Ruby      | `rubocop -a` (safe autocorrect only; `-A` is unsafe)    |
| Rust      | `cargo fmt` then `cargo clippy --fix`                   |
| Java      | `mvn spotless:apply` or `gradle spotlessApply`          |
| CSS       | `npx stylelint --fix`                                   |
| Shell     | `shfmt -w .`                                            |
| YAML/JSON | `npx prettier --write .`                                |

Run the formatter, then review the diff. **Do not run an unsafe autocorrect mode** (`rubocop -A`, `eslint --fix-dry-run` with aggressive rules, `clippy --fix` on unsafe lints) without reading each change — those modes change behavior.

If a formatter rewrites a file you did not intend to touch, that is a finding: the file was already non-conforming. Say so.

### Step 2 — Semantic normalization, by hand

Apply the authorized variant one concern at a time, and one commit's worth of change at a time.

- Replace the losing variant with the winning one. Do not leave the losing variant behind a flag or a compatibility shim unless the user asked for one.
- **Update every call site, not just the definition.** A renamed helper with a stale caller is a broken build.
- **Update the tests** that assert the old shape.
- **Update the documentation** that describes the old pattern.
- **Update the linter configuration** so the losing variant is now an error, not merely absent. This is what prevents the divergence from returning.

```js
// eslint.config.js
'no-restricted-imports': ['error', {
  paths: [
    { name: 'date-fns', message: 'Use dayjs (see AGENTS.md).' },
    { name: 'src/lib/date', message: 'Use dayjs (see AGENTS.md).' },
  ],
}]
```

```toml
# pyproject.toml
[tool.ruff.lint.flake8-tidy-imports.banned-api]
"requests".msg = "Use httpx (see AGENTS.md)."
```

**Adding the guard is not optional.** Without it, the next contributor reintroduces the variant and the standardization decays. This is the single highest-value step in the whole skill.

### Step 3 — What not to normalize

Do not touch:

- Generated, vendored, or third-party code (`dist/`, `build/`, `vendor/`, `node_modules/`, `*.generated.*`, `*.min.js`, lockfiles).
- Code under an active migration or behind a documented feature flag, unless the user authorized it.
- Test fixtures and golden files whose exact bytes are the assertion.
- A divergence the user declined to resolve.
- Code you do not understand. Read it until you do, or report it as unresolved.

## Phase 5 — Verify

Standardization breaks builds in a specific way: a definition changes and a call site does not. Verify accordingly.

- [ ] The project builds.
- [ ] The full test suite passes — not a subset.
- [ ] The linter passes with the new rule enabled, which proves the losing variant is gone.
- [ ] A repository-wide search for the losing variant returns zero hits outside the documented exceptions.
- [ ] No file outside the authorized scope was modified.
- [ ] The formatter produces no further diff (`--check` mode is clean), proving formatting is canonical.
- [ ] Each divergence the user resolved is either fully normalized or explicitly listed as unresolved.

Run the search that proves the variant is gone:

```bash
grep -rn "date-fns" --exclude-dir={node_modules,.git,dist,build,vendor} . && echo 'REMAINING HITS' || echo 'clean'
```

```bash
npx prettier --check . 2>&1 | tail -5
ruff format --check . && ruff check .
```

Report the actual command output. "Should be consistent now" is not verification.

## Phase 6 — Report

```markdown
## Sources of Truth

- AGENTS.md — documented conventions (authoritative)
- .prettierrc, eslint.config.js — enforced tooling
- No CODEBASE.md present

## Divergences Found

| ID  | Concern         | Variants                             | Authoritative source          | Resolution                                   |
| --- | --------------- | ------------------------------------ | ----------------------------- | -------------------------------------------- |
| D1  | Date arithmetic | dayjs (34), native (6), date-fns (2) | Not documented → user chose A | Normalized to dayjs                          |
| D2  | Error handling  | throw (41), return codes (3)         | AGENTS.md §Errors             | Normalized to throw; 3 files were violations |
| D3  | Import style    | relative (52), absolute (7)          | eslint config                 | Normalized to relative                       |

## Changes Applied

<per concern: files touched, call sites updated, tests updated>

## Guards Added

<the linter rules that now prevent regression>

## Verification

<the checklist, with actual command output>

## Unresolved

<declined divergences, out-of-scope findings, and anything you did not understand>
```

## Common Mistakes

| Mistake                                                                    | Why It Breaks                                                                 | Correct Approach                                |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------- |
| Normalizing to the majority without asking                                 | The minority may be the newer, correct pattern; you delete a migration        | Ask, with the majority as a recommendation only |
| Asking about something `AGENTS.md` already answers                         | Wastes the user's attention and invites them to contradict their own standard | Read the convention docs first                  |
| Overriding a documented standard because the code disagrees                | Inverts the precedence chain                                                  | The document wins; the code is the defect       |
| Hand-editing formatting                                                    | Introduces typos and fights the project's own formatter                       | Run the formatter                               |
| Running an unsafe autocorrect without reading it                           | Changes behavior silently                                                     | Review every hunk of `-A`/aggressive fixes      |
| Renaming a definition without its call sites                               | Broken build                                                                  | Search and update every caller                  |
| Leaving the losing variant legal in the linter                             | The divergence returns within a sprint                                        | Add a restriction rule                          |
| Standardizing vendored or generated code                                   | The change is destroyed on the next build                                     | Exclude those paths                             |
| Normalizing a migration in progress                                        | Destroys the migration's intermediate state                                   | Stop and ask                                    |
| Touching files outside the authorized scope                                | Turns a review into an archaeology exercise                                   | Scope the change; report the rest               |
| Reporting "should be consistent"                                           | Unverified claim                                                              | Run the greps and paste the output              |
| Normalizing a divergence the user declined                                 | Ignores an explicit decision                                                  | Leave it; list it as unresolved                 |
| Standardizing one file's style to another file's style when both are wrong | Propagates a defect consistently                                              | Escalate to the best-practice module, then ask  |
