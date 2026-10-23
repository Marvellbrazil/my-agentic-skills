---
name: modularize
description: Restructures monolithic files, God classes/components, and tightly coupled projects into high-cohesion, loosely coupled modules with clean folder/file structures and explicit architectural boundaries. Enforces Single Responsibility Principle (SRP), Dependency Inversion (DIP), Acyclic Dependencies (no circular imports), and Deep Module design. Use when the user invokes /modularize, asks to split large files, decouple modules, reorganize project folder structure, or refactor a monolith into clean modular boundaries.
allowed-tools: Bash Read Grep Glob Edit Write
---

# Modularize & Decouple Architecture

Transform monolithic files, tangled "God" modules, and flat or chaotic directory trees into **high-cohesion, loosely coupled modules** with explicit public contracts and enforced architectural boundaries.

True modularization is **not** chopping one 1,000-line file into ten 100-line files that all import each other in a circle. Good modularity means **each module hides a meaningful piece of complexity behind a small, stable interface** (John Ousterhout's *Deep Modules*), dependencies flow in **one direction (DAG)**, and changing one feature or infrastructure adapter does not ripple across unrelated files.

---

## Reference Modules

Load the appropriate reference guide before restructuring files, folders, or architectural layers:

| Concern | Reference Module | What It Covers |
| :--- | :--- | :--- |
| **Folder & File Organization** | [references/folder-and-file-structure.md](references/folder-and-file-structure.md) | Package-by-Feature (Vertical Slice) vs. Package-by-Layer, Frontend Feature-Sliced Design (FSD), Backend/Service layouts across TS/Python/Go/Rust, Co-location rules, and Public API Facades vs. Barrel (`index.ts`) traps |
| **Architectural Partitioning & Boundaries** | [references/architectural-partitioning.md](references/architectural-partitioning.md) | Modular Monolith design, Hexagonal (Ports & Adapters) & Clean Architecture, Functional Core / Imperative Shell, Deep vs. Shallow modules, Acyclic Dependencies Principle (ADP), and automated boundary enforcement |
| **Decoupling & Safe Extraction Patterns** | [references/decoupling-and-refactoring-patterns.md](references/decoupling-and-refactoring-patterns.md) | Coupling & Cohesion taxonomy, Dependency Inversion (DIP), Event/Command decoupling, UI Component decomposition (Container/Hook/View), and the step-by-step Strangler workflow for splitting God files safely |

---

## Core Principles of Modularity

1. **High Cohesion (Things That Change Together Stay Together)**:
   Group code by **business capability / domain feature** first, and by technical role second. A change to `billing` should stay inside `src/features/billing/` (or `src/modules/billing/`), not require edits across 8 top-level `controllers/`, `services/`, `helpers/`, and `utils/` directories.
2. **Loose Coupling & Narrow Interfaces**:
   Modules communicate exclusively through minimal, explicitly typed public interfaces. Internal data structures, database queries, and private helpers stay unexported.
3. **Strict Dependency Direction (No Cycles)**:
   The module dependency graph must form a **Directed Acyclic Graph (DAG)**:
   `Entry/UI/HTTP → Feature/Application → Domain/Core ← Infrastructure Adapters` (via Dependency Inversion), and `Feature Modules → Shared/Core` (never `Shared → Feature`).
4. **Deep Modules Over Pass-Through Slop**:
   Do not create 5 layers of 1-line wrapper classes that just forward arguments unchanged. Extract a module when it encapsulates distinct state, policy, I/O boundary, or reusable algorithm behind a simpler signature.

---

## Execution Workflow

### Phase 1 — Reconnaissance & Coupling Diagnosis
Before moving or splitting any file, map the current dependency graph and identify the coupling hotspots:

```bash
# 1. Find the largest files (God files / monolith candidates)
wc -l $(git ls-files '*.ts' '*.tsx' '*.py' '*.go' '*.rs' '*.java' '*.php' 2>/dev/null) 2>/dev/null | sort -rn | head -20

# 2. Inspect who imports the target file (blast radius of callers)
grep -rn "from ['\"].*<target-module>" src/ app/ tests/ 2>/dev/null

# 3. Inspect what the target file imports (fan-out / mixed responsibilities)
grep -nE "^(import |from .* import |require\()" <path/to/target-file>
```

Identify which axes of change are tangled inside the target:
- **Pure Domain / Business Policy** (calculations, validations, state machines)
- **State / Orchestration** (use-case flow, hooks, stores, transaction boundaries)
- **External I/O & Infrastructure** (SQL/ORM queries, `fetch`/SDK calls, filesystem, Redis)
- **Presentation / Transport** (JSX/HTML rendering, CLI flag parsing, HTTP request/response formatting)

### Phase 2 — Design the Target Module Structure
Select the appropriate structure from [references/folder-and-file-structure.md](references/folder-and-file-structure.md) and [references/architectural-partitioning.md](references/architectural-partitioning.md):

- **Splitting a Single Monolithic File / Component**:
  Decompose along responsibility seams into cohesive sibling files:
  - `*.types.ts` / `models.py` — Domain types, schemas, contracts
  - `*.logic.ts` / `policy.py` — Pure, zero-I/O business transformations & validations
  - `*.repository.ts` / `*.client.ts` — External I/O and data-access adapters
  - `*.service.ts` / `use-*.ts` — Orchestration / stateful hook wiring pure logic + I/O
  - `*.view.tsx` / `*.controller.ts` — Thin UI rendering or HTTP/CLI transport handler
- **Restructuring a Whole Project / Directory Tree**:
  Migrate from flat or technical-layer sprawl (`utils/`, `helpers/`, `misc/`) to **Feature/Domain Modules** (`modules/<feature>/` or `features/<feature>/`) + a strictly pure `shared/` (or `pkg/` / `internal/`) foundation.

### Phase 3 — Incremental, Caller-Safe Extraction
Follow the safe extraction choreography in [references/decoupling-and-refactoring-patterns.md](references/decoupling-and-refactoring-patterns.md):

1. **Extract Pure Functions & Types First (Zero Dependencies)**:
   Move pure calculations, validators, constants, and types into dedicated modules first — they depend on nothing and are trivial to unit-test.
2. **Invert Hardcoded I/O Dependencies**:
   Replace inline database calls, `fetch` requests, or third-party SDK instantiations with narrow Port interfaces or injected dependencies.
3. **Preserve Public Entry Points During Transition**:
   If external callers import `from './orders'`, keep `orders/index.ts` (or the original file path) re-exporting the public API while you update call sites, then remove dead shims once all callers are updated.
4. **Eliminate Circular Dependencies**:
   If Module A and Module B import each other, either:
   - Extract the shared contract/type into a lower-level module `C` (`A → C ← B`), or
   - Invert one direction using an interface or Domain Event.

### Phase 4 — Verify Build, Tests & Dependency Graph
After modularizing:
1. Run the compiler / typechecker (`tsc --noEmit`, `mypy`, `pyright`, `cargo check`, `go build ./...`).
2. Run the full test suite to confirm zero behavioral regressions.
3. Verify zero circular dependencies (`npx madge --circular src/` or language equivalent) and zero broken imports.

---

## Verification Checklist

- [ ] **Single Responsibility**: Every new file/module has one clear, nameable responsibility and one primary axis of change.
- [ ] **No "Junk Drawer" Files**: Zero new `utils.ts`, `helpers.ts`, `common.ts`, or `misc.py` files created — every helper is named after its domain/technical capability (`currency-format.ts`, `retry-backoff.ts`).
- [ ] **Acyclic Dependency Graph**: Zero circular imports (`A ↔ B`); dependencies strictly flow `Presentation → Application/Feature → Domain ← Infrastructure` and `Features → Shared`.
- [ ] **Pure Core Separated from I/O**: Business calculations and validations can be imported and tested without booting a database, HTTP server, or UI renderer.
- [ ] **All Call Sites & Tests Green**: Every import path across source and test files is updated and verified by passing build and test runs.
