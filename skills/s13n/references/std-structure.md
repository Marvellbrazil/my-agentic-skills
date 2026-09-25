# Repository Layout, Naming, and File Organization

Structure is the part of a codebase that every tool and every newcomer reads before any logic. When layout is inconsistent, imports resolve differently per subsystem, build tools silently include or exclude the wrong files, and reviewers cannot tell whether a directory is a layer, a feature, or a leftover. This module defines language-agnostic rules for top-level layout, feature-first versus layer-first organization, naming case per artifact type, module boundaries, and where tests, config, migrations, and generated code belong.

## Contents

- [When This Applies](#when-this-applies)
- [Top-Level Layout and Where Concerns Live](#top-level-layout-and-where-concerns-live)
- [Feature-First vs Layer-First, and Layer Boundaries](#feature-first-vs-layer-first-and-layer-boundaries)
- [Naming Conventions per Artifact Type](#naming-conventions-per-artifact-type)
- [Module Boundaries: Entrypoints, Barrels, and Size Limits](#module-boundaries-entrypoints-barrels-and-size-limits)
- [Colocation, Tests, Config, Migrations, and Generated Code](#colocation-tests-config-migrations-and-generated-code)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- A repository has both `src/` and top-level package directories, or two directories that hold the same kind of file.
- New files land in a folder chosen by habit rather than by a rule, so similar artifacts live in three places.
- A directory named `utils`, `helpers`, `common`, `core`, `misc`, or `manager` exists and grows on every change.
- Naming case is mixed within one artifact type: `UserProfile.tsx` beside `user-profile.tsx`, `orderService.php` beside `Order_Service.php`.
- Tests live in `tests/` while some tests are colocated, and there is no stated rule for which.
- A module's public surface is undefined: consumers import `internal/`, deep paths, or files marked private.
- Files exceed the length at which a reviewer can hold them, or a directory holds hundreds of entries.
- A monorepo has packages with cross-imports that bypass published entrypoints.
- Generated code, migrations, fixtures, or build output is committed next to hand-written source with no marker separating them.

## Top-Level Layout and Where Concerns Live

Every ecosystem has a default root contract; adopt the ecosystem's contract rather than inventing one, and state the deviations in the repo docs ([std-docs.md](std-docs.md)).

| Concern             | Convention                                                                | Notes                                       |
| ------------------- | ------------------------------------------------------------------------- | ------------------------------------------- |
| Hand-written source | `src/`, or Maven `src/main/java`                                          | Never the repo root for a packaged artifact |
| Tests               | `tests/` (Rust, Python), `src/test/java` (Maven), colocated `*.test.ts`   | One rule per repo, not per subsystem        |
| Build output        | `target/` (Maven), `dist/`, `build/`, `out/`                              | Must be git-ignored; never edited by hand   |
| Migrations          | `alembic/versions/`, `migrations/`, `db/migration/`                       | Ordered, immutable once applied             |
| Fixtures            | `fixtures/`, `testdata/` (Go), `tests/resources/`                         | Not importable by production code           |
| Scripts             | `scripts/`, `tools/`, `bin/`                                              | Executables, not library code               |
| Config              | `pyproject.toml`, `pom.xml`, `Cargo.toml`, `package.json` at package root | One manifest per package boundary           |

Maven's layout is explicit about the root: "There are just two subdirectories of this structure: `src` and `target`." Anything else at the root is a document or a metadata directory. Rust's Cargo layout fixes the same contract in different words: `src/lib.rs` is the default library, `src/main.rs` the default binary, and `benches/`, `examples/`, `tests/` are recognized top-level targets — the toolchain infers targets from those paths, so moving a file changes what is built.

```
repo/
├── src/                 # hand-written, importable
│   └── order/
├── tests/               # or colocated *.test.ts
├── migrations/          # ordered, append-only
├── scripts/             # dev/CI executables
├── docs/                # prose, ADRs
├── pyproject.toml       # manifest
└── README.md
```

Python packaging adds one non-obvious decision. The PyPA guide documents that the interpreter places the current working directory first on the import path, so a flat layout lets `import awesome_package` resolve to the in-development tree instead of the installed copy; the src layout exists to prevent exactly that. The cost is real: with `src/` you must install the project (usually editable) before running its code from the repository.

Monorepos repeat this contract per package. npm workspaces declare boundaries in the root manifest and symlink each listed package into the root `node_modules`:

```json
{
  "name": "my-workspaces-powered-project",
  "workspaces": ["packages/a", "packages/b"]
}
```

Package boundaries must be enforced, not merely declared: a sibling package imports another through its published entrypoint (`"exports"` in `package.json`), never through a relative path into its `src/`.

## Feature-First vs Layer-First, and Layer Boundaries

Choose one axis as the primary split and use the other as a secondary split inside it. Do not mix the two at the same level: `src/controllers/` beside `src/billing/` means one of them is a mistake.

| Axis          | Directory shape                                      | Choose when                                                                                                  |
| ------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Feature-first | `src/billing/{api,service,repo}.ts`                  | Teams own vertical slices; features change independently; you want deletion to be one directory removal      |
| Layer-first   | `src/{controllers,services,repositories}/billing.ts` | The framework or tooling mandates layers (Maven, Spring, Rails, Django apps); cross-cutting policy dominates |

Feature-first fails when a "feature" is really a shared capability — a second feature imports it, and the boundary dissolves. Layer-first fails when a change to one use case touches five directories and no single owner can be assigned.

Independently of that axis, separate domain, application, infrastructure, and presentation, and keep the dependency direction one-way: presentation → application → domain, with infrastructure implementing interfaces the domain or application declares.

```
domain/          entities, value objects, invariants — no framework, no I/O imports
application/     use cases, orchestration, ports (interfaces)
infrastructure/  DB, HTTP clients, queues, filesystem — implements ports
presentation/    HTTP handlers, CLI, UI — calls use cases
```

The test that this separation actually holds: `domain/` compiles with zero imports from the other three. If it cannot, the layering is decorative.

## Naming Conventions per Artifact Type

Pick one case per artifact type, write it down, and enforce it in CI. The failure mode is not a wrong choice — it is two coexisting choices.

| Artifact                    | Convention                                                                   | Verified example                                                                                                                                                   |
| --------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Directories                 | `kebab-case` (JS/TS), `snake_case` (Python), `lowercase` (Go, Java packages) | `order-history/`, `order_history/`, `orderhistory/`                                                                                                                |
| TS/JS component files       | `PascalCase.tsx`                                                             | `UserProfile.tsx`                                                                                                                                                  |
| TS/JS non-component modules | `kebab-case.ts`                                                              | `parse-invoice.ts`                                                                                                                                                 |
| Python modules              | `snake_case.py`, short, all-lowercase                                        | PEP 8: underscores allowed if they improve readability; in _packages_ underscores are discouraged                                                                  |
| Go files and packages       | `lowercase`, no `_` or `mixedCaps`                                           | Go blog: "lower case, with no under_scores or mixedCaps"                                                                                                           |
| Java classes                | `PascalCase.java`, file name equals the top-level class                      | Google Java Style §2.1; JLS §7.6 also requires `package-info.java` for package-level annotations                                                                   |
| PHP classes                 | `PascalCase.php`, path mirrors the namespace                                 | PSR-4: "Underscores have no special meaning"; sub-namespace names map to subdirectories and "The subdirectory name MUST match the case of the sub-namespace names" |
| SQL migrations              | `V<version>__<description>.sql`                                              | Flyway defaults: `sqlMigrationPrefix` `V`, `sqlMigrationSeparator` `__` → `V1.1__My_description.sql`; repeatable prefix `R` → `R__My_description.sql`              |

Naming is a contract with tooling, not a style preference:

- Rust: a package named `my-lib` produces a library crate named `my_lib`, because Cargo replaces dashes with underscores.
- npm: new package names must not contain uppercase letters and must be URL-safe; the name becomes a URL, a CLI argument, and a directory name.
- Python: distributing types requires a `py.typed` marker, and stub-only distributions must be named `<pkg>-stubs` (PEP 561).
- Go: package name and its contents are read together, so `http.Server` beats `HTTPServer`; and a package named `util`, `common`, or `misc` gives clients no signal about what belongs in it.

For identifiers inside files, the same discipline applies: booleans read as predicates (`isRetryable`, `hasExpired`, `canPublish`), constants are `SCREAMING_SNAKE_CASE` in Python/Java/Go and `UPPER_SNAKE_CASE` in JS/TS, and functions are verbs (`reconcileLedger`, not `ledgerData`). Names to ban outright: `data`, `info`, `manager`, `processor`, `util`, `helpers`, `common`, `misc`, `tmp`, `new`, `old`. Each of them means "I have not decided what this is", and each becomes a merge conflict magnet.

## Module Boundaries: Entrypoints, Barrels, and Size Limits

Every module has exactly one public entrypoint. Consumers import that entrypoint and nothing else inside the module.

| Ecosystem | Entrypoint mechanism                                                           |
| --------- | ------------------------------------------------------------------------------ |
| Node.js   | `"exports"` in `package.json`; entries not listed are unreachable to consumers |
| Python    | the package `__init__.py`, re-exporting only the intended names                |
| Go        | the exported identifiers of the package; `internal/` enforces the boundary     |
| Rust      | `pub use` re-exports in the crate root or module file                          |
| PHP       | the class FQCN autoloaded by PSR-4                                             |

Go's `internal/` rule is compiler-enforced and worth copying conceptually in any language with a linter: an import path containing the element `internal` "is disallowed if the importing code is outside the tree rooted at the parent of the `internal` directory." Node's `"exports"` gives the same effect by omission — unlisted subpaths fail to resolve — and subpath patterns keep that list maintainable:

```json
{
  "exports": {
    "./features/*.js": "./src/features/*.js"
  },
  "imports": {
    "#internal/*.js": "./src/internal/*.js"
  }
}
```

`imports` entries must start with `#`; `*` is plain string replacement and exposes nested subpaths, so `./features/y/y.js` maps to `./src/features/y/y.js`.

Barrel files (`index.ts` re-exporting a directory) are the most common way this boundary becomes expensive. Vite's performance guide states the mechanism directly: when you import a single API from a barrel, "all the files in that barrel file need to be fetched and transformed as they may contain the `slash` API and may also contain side-effects," so import `./utils/slash.js` directly. If a package does ship barrels, declare `"sideEffects": false` in its `package.json` so bundlers can prune — webpack's tree-shaking guide documents the array form (`["./src/some-side-effectful-file.js"]`) for packages that do have effectful modules, and notes patterns without a `/` are treated as `**/pattern`.

Size limits turn a design smell into a failing check. Use the linter's existing threshold instead of an invented number:

| Tool       | Rule                       | Default                                                |
| ---------- | -------------------------- | ------------------------------------------------------ |
| ESLint     | `max-lines`                | `max` = 300; supports `skipBlankLines`, `skipComments` |
| Pylint     | `too-many-lines` (`C0302`) | `max-module-lines` = 1000                              |
| Checkstyle | `FileLength`               | configurable `max`; the docs' examples use 2000        |

Treat any threshold as a review trigger, not a target: a 900-line module that is one cohesive state machine is fine, and a 250-line module that owns five unrelated exports is not. The reliable signals that a module must split are: it exports more than one concept, two groups of imports never overlap, and a change to one feature keeps editing the same file.

## Colocation, Tests, Config, Migrations, and Generated Code

Colocation wins when the artifact is meaningless without its subject; centralization wins when the artifact is discovered by a tool by path.

- **Tests.** Colocate as `<subject>.test.ts` when the test suite is per-file and the runner globs `*.test.*`; centralize in `tests/` when tests exercise a public API across modules (Rust integration tests in `tests/`, Maven `src/test/java`). Python's pytest default is `python_files = ["test_*.py", "*_test.py"]`, so a file named `order_test.py` in any directory is collected — pick one of the two patterns and never both. Shared fixtures belong in `conftest.py` (Python) or a fixtures module, not duplicated per test file.
- **Styles and types.** Colocate `Button.module.css` and `Button.types.ts` next to `Button.tsx`. TypeScript declaration files sit alongside their `.ts` source (PEP 561 applies the same preference to Python `*.pyi`); a separate `types/` directory is reserved for ambient declarations that have no owning module.
- **Configuration.** One manifest per package boundary, at that package's root. Environment-specific values belong in environment variables or an untracked `.env`, never in a checked-in config file — the same rule that governs [std-yaml-json.md](std-yaml-json.md).
- **Migrations.** Append-only, ordered, immutable once applied, and never edited to fix a deployed schema. Flyway's versioned naming (`V1.1__My_description.sql`) and Alembic's `versions/` directory with a fixed `env.py` both encode this: the file name carries the ordering, so renaming a shipped migration rewrites history.
- **Generated code.** Keep it in a dedicated directory (`generated/`, `gen/`, `*.pb.go` beside the proto), mark it in a header or a `.gitattributes` entry as generated, and exclude it from lint and review. It must be reproducible from its source in CI; a generated file that no command can regenerate is a hand-written file lying about its origin.
- **Build output.** `dist/`, `target/`, `build/`, `__pycache__/`, `node_modules/` are never committed and never imported by source.

## Common Mistakes

| Mistake                                      | Why It Breaks                                                                                               | Correct Approach                                                                                     |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Mixing `src/` and top-level packages         | Two import roots; tooling and reviewers cannot tell which tree is authoritative                             | Pick one root contract and move the other tree under it                                              |
| Both `tests/` and colocated tests, no rule   | Coverage gaps and duplicated fixtures; nobody knows where a new test goes                                   | State one rule per repo; move the minority case                                                      |
| A growing `utils/` or `common/` directory    | Go's own guidance: such packages accumulate dependencies, slow compilation, and collide with client imports | Split by concept into `stringset/`, `dates/`, `http/` — name the thing, not the category             |
| Barrel file as the default import path       | Importing one symbol pulls and transforms the whole directory, including its side effects                   | Import the concrete module; reserve barrels for a deliberate public API, with `"sideEffects": false` |
| No declared entrypoint                       | Consumers reach into private files, so every internal refactor is a breaking change                         | Declare `"exports"` / `__init__.py` / `pub use`, and make everything else unreachable                |
| Feature directory that other features import | The "feature" is a shared layer wearing a feature name; changes fan out                                     | Move the shared code into an explicit shared module and point both features at it                    |
| Domain layer importing framework or I/O code | Business rules become untestable without a database or HTTP server                                          | Invert with a port declared by the domain or application layer                                       |
| Files split by line count alone              | Mechanical splits produce modules with no cohesion and circular imports                                     | Split on export surface and change frequency; use linters as triggers                                |
| Generated code edited by hand                | Next regeneration silently reverts the fix                                                                  | Fix the generator or the source schema; regenerate                                                   |
| A shipped migration edited or renamed        | Environments that already applied it diverge from fresh installs                                            | Add a new migration; never mutate an applied one                                                     |
| Ambiguous names (`data`, `manager`, `info`)  | Reviewers must read the body to learn the role; merge conflicts cluster on these files                      | Rename to the domain concept the code actually implements                                            |

## Checklist

1. List the repository root and classify every entry as source, test, config, docs, scripts, generated, or build output; move anything unclassified.
2. Confirm exactly one importable source root exists, and that build output directories are git-ignored.
3. Record the chosen primary axis (feature-first or layer-first) and verify no directory mixes the two at the same level.
4. Verify the domain layer has zero imports from application, infrastructure, or presentation.
5. Enumerate every artifact type (directories, components, modules, classes, migrations) and its assigned naming case; flag every file that deviates.
6. Search for and rename directories or packages named `utils`, `helpers`, `common`, `misc`, `core`, or `manager` into concept-named modules.
7. Identify each module's public entrypoint and confirm consumers import only through it; add `"exports"` or equivalent where it is missing.
8. Locate every barrel/index re-export and either delete it or justify it as a deliberate public API with side effects declared.
9. Run the configured file-length check (`max-lines`, `too-many-lines`, `FileLength`) and triage every violation as a cohesion problem, not a line-count problem.
10. Confirm tests follow one placement rule and one file-naming pattern that matches the runner's configured glob.
11. Confirm styles and type declarations are colocated with their subject, or live in a documented ambient directory.
12. Verify migrations are append-only and ordered by filename, and that no applied migration has been modified.
13. Verify generated code lives in a marked directory, is excluded from lint and review, and is reproducible by a documented command.
14. In a monorepo, verify each package imports its siblings through published entrypoints, not relative paths into their sources.
15. Write the resulting rules into the repository documentation, including any deliberate deviation from the ecosystem default.

## References

- [ESLint `max-lines`](https://eslint.org/docs/latest/rules/max-lines) — default `max` of 300, `skipBlankLines`, `skipComments`
- [Pylint `too-many-lines`](https://pylint.readthedocs.io/en/stable/user_guide/messages/convention/too-many-lines.html) — `max-module-lines`, default 1000
- [Checkstyle `FileLength`](https://checkstyle.org/checks/sizes/filelength.html) — configurable maximum file length
- [Go command documentation, Internal Directories](https://pkg.go.dev/cmd/go#hdr-Internal_Directories) — import-path rule for `internal`
- [Go blog: Package names](https://go.dev/blog/package-names) — lowercase, no underscores or mixedCaps; why `util` and `common` fail
- [The Rust Book: Separating Modules into Different Files](https://doc.rust-lang.org/book/ch07-05-separating-modules-into-different-files.html) — `foo.rs` + `foo/bar.rs` versus `foo/mod.rs`
- [The Cargo Book: Package Layout](https://doc.rust-lang.org/cargo/guide/project-layout.html) and [Cargo Targets](https://doc.rust-lang.org/cargo/reference/cargo-targets.html) — target paths and dash-to-underscore crate naming
- [Maven: Introduction to the Standard Directory Layout](https://maven.apache.org/guides/introduction/introduction-to-the-standard-directory-layout.html) — `src/main/java`, `src/test/java`, `src/it`, `target`
- [PyPA: src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) — why the interpreter's cwd entry makes flat layouts risky
- [PEP 8](https://peps.python.org/pep-0008/) and [PEP 561](https://peps.python.org/pep-0561/) — module/package naming and the `py.typed` marker
- [PSR-4: Autoloader](https://www.php-fig.org/psr/psr-4/) — namespace-to-path mapping and case sensitivity
- [Java Language Specification, Chapter 7](https://docs.oracle.com/javase/specs/jls/se21/html/jls-7.html) and [Google Java Style §2.1](https://google.github.io/styleguide/javaguide.html) — package-to-directory mapping, `package-info.java`, file name equals top-level class
- [Node.js: Packages](https://nodejs.org/api/packages.html#subpath-patterns) — `"exports"`, `"imports"`, subpath patterns
- [npm: `package.json`](https://docs.npmjs.com/cli/v11/configuring-npm/package-json) and [npm workspaces](https://docs.npmjs.com/cli/v11/using-npm/workspaces) — name rules and package boundaries
- [Vite: Performance — Avoid Barrel Files](https://vite.dev/guide/performance) and [webpack: Tree Shaking](https://webpack.js.org/guides/tree-shaking/) — the cost of barrels and `"sideEffects"`
- [pytest reference](https://docs.pytest.org/en/stable/reference/reference.html) — `python_files` default `["test_*.py", "*_test.py"]`, `conftest.py`
- [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) and [Flyway migrations](https://documentation.red-gate.com/flyway/flyway-concepts/migrations) — migration directory and file-naming contracts
