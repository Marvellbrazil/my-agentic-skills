# Folder & File Structure Best Practices Reference

A project's directory tree is the first architectural diagram every engineer and AI agent reads. When a folder structure is organized around technical mechanics (`controllers/`, `services/`, `utils/`, `helpers/`) instead of domain capabilities, adding or modifying a single feature forces edits across 10 distant folders and turns `utils/` into a 5,000-line dumping ground.

This guide defines best practices for structuring directories, files, co-location, and module exports across backend, frontend, full-stack, and multi-language repositories.

---

## Contents

- [1. Package-by-Feature (Vertical Slice) vs. Package-by-Layer](#1-package-by-feature-vertical-slice-vs-package-by-layer)
- [2. Screaming Architecture & Top-Level Layout](#2-screaming-architecture--top-level-layout)
- [3. Backend / Service Directory Blueprints (TS, Python, Go, Rust)](#3-backend--service-directory-blueprints-ts-python-go-rust)
- [4. Frontend / Full-Stack Directory Blueprint (Feature-Sliced)](#4-frontend--full-stack-directory-blueprint-feature-sliced)
- [5. File Granularity, Naming & Co-Location Rules](#5-file-granularity-naming--co-location-rules)
- [6. Public Module Facades vs. The Barrel File (`index.ts`) Trap](#6-public-module-facades-vs-the-barrel-file-indexts-trap)
- [7. Killing the `utils/` and `helpers/` Junk Drawer](#7-killing-the-utils-and-helpers-junk-drawer)

---

## 1. Package-by-Feature (Vertical Slice) vs. Package-by-Layer

### ❌ Package-by-Layer (Low Cohesion at Scale)
Grouping the entire repository at the top level by technical layer scatters every business feature across the whole tree:

```text
# ❌ BAD once the project grows beyond 3-4 entities:
src/
├── controllers/
│   ├── billing.controller.ts
│   ├── inventory.controller.ts
│   └── shipping.controller.ts
├── services/
│   ├── billing.service.ts
│   ├── inventory.service.ts
│   └── shipping.service.ts
├── repositories/
│   ├── billing.repo.ts
│   ├── inventory.repo.ts
│   └── shipping.repo.ts
└── utils/
    └── helpers.ts          # 3,000 lines of unrelated functions
```

**Why it fails**:
- Everything is `export`ed publicly so `controllers/` can reach `services/` and `services/` can reach `repositories/` — nothing is private to a domain.
- Deleting or refactoring the `shipping` feature requires hunting through every folder in `src/`.

### ✅ Package-by-Feature / Vertical Slice (High Cohesion, Encapsulated)
Group by **domain capability / feature first**, and place internal layers *inside* each feature module:

```text
# ✅ GOOD: High cohesion, clear module boundaries, easy to navigate and delete/extract
src/
├── modules/
│   ├── billing/
│   │   ├── domain/                 # Pure billing entities, value objects, pricing rules
│   │   ├── application/            # Use cases (charge-invoice, issue-refund)
│   │   ├── infrastructure/         # Stripe adapter, SQL invoice repository
│   │   ├── presentation/           # HTTP routes & request DTOs
│   │   └── index.ts                # Curated public facade (exports ONLY what other modules may call)
│   ├── inventory/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   ├── presentation/
│   │   └── index.ts
│   └── shipping/
│       └── ...
├── shared/                         # Cross-cutting, domain-agnostic primitives ONLY
│   ├── http/
│   ├── logger/
│   ├── money/
│   └── clock/
└── app.ts                          # Composition root (wires modules together)
```

---

## 2. Screaming Architecture & Top-Level Layout

Robert C. Martin's **Screaming Architecture** principle: looking at the top-level directory of a repository should immediately tell the reader **what problem the system solves** (`orders/`, `underwriting/`, `claims/`, `ledger/`), not just what framework it uses.

### Golden Rules for Directory Depth & Breadth
1. **Flat Until Proven Necessary**: Do not create a subfolder for a single file (`src/modules/billing/validators/date-validator/index.ts`). Keep a module flat (4–7 files) until it crosses ~7–10 files, then introduce sub-directories (`domain/`, `infrastructure/`).
2. **Maximum Nesting Depth ≤ 4 Levels Inside `src/`**: Deeply nested trees (`src/core/services/domain/impl/v2/handlers/...`) are a smell of over-abstraction.
3. **One Composition Root**: Keep a single entry point (`main.ts`, `app.py`, `cmd/server/main.go`) responsible for instantiating concrete infrastructure adapters and injecting them into modules.

---

## 3. Backend / Service Directory Blueprints (TS, Python, Go, Rust)

### TypeScript / Node.js (Modular Service)
```text
src/
├── config/                     # Validated env config (zod/valibot schema)
├── modules/                    # Domain/Feature vertical modules
│   └── orders/
│       ├── order.domain.ts     # Pure domain types & invariant functions
│       ├── order.service.ts    # Application use-case orchestration
│       ├── order.repo.ts       # Persistence port + implementation
│       ├── order.routes.ts     # HTTP handler / controller
│       ├── order.test.ts       # Co-located unit/service tests
│       └── index.ts            # Public contract for other modules
├── shared/                     # Technical & shared-kernel utilities
│   ├── db/
│   ├── errors/
│   └── telemetry/
└── server.ts                   # Composition root & graceful shutdown
```

### Python (FastAPI / Modular Service)
```text
src/
└── app/
    ├── config.py               # Pydantic Settings startup validation
    ├── main.py                 # FastAPI app assembly & lifespan hooks
    ├── modules/
    │   ├── invoicing/
    │   │   ├── __init__.py     # Explicit __all__ public interface
    │   │   ├── domain.py       # Pure dataclasses / Value Objects / rules
    │   │   ├── service.py      # Use-case orchestration
    │   │   ├── repository.py   # SQLAlchemy / asyncpg adapter
    │   │   ├── router.py       # FastAPI APIRouter & Pydantic DTOs
    │   │   └── schemas.py
    │   └── payments/
    │       └── ...
    └── shared/
        ├── database.py
        └── logging.py
```

### Go (Idiomatic `cmd/` + `internal/`)
Go's compiler natively enforces modular encapsulation via the `internal/` directory:
```text
.
├── cmd/
│   ├── api/
│   │   └── main.go             # HTTP server composition root (thin: <80 lines)
│   └── worker/
│       └── main.go             # Background job runner composition root
├── internal/                   # Compiler-enforced private packages
│   ├── checkout/               # Feature package (domain + service + handler)
│   │   ├── cart.go
│   │   ├── service.go
│   │   ├── postgres_repo.go
│   │   └── handler_test.go
│   ├── catalog/
│   └── platform/               # Internal shared infrastructure (db, auth, telemetry)
└── pkg/                        # Only packages intentionally safe for external repos to import
```

---

## 4. Frontend / Full-Stack Directory Blueprint (Feature-Sliced)

For React, Next.js, Vue, SvelteKit, and mobile apps, follow **Feature-Sliced Design (FSD)** principles so UI components, state hooks, and API calls stay modular and unidirectional:

```text
src/
├── app/ (or pages/routes)      # Routing, layouts, global providers ONLY (thin shell)
│   └── checkout/
│       └── page.tsx            # Imports <CheckoutPage /> from features/checkout
├── features/                   # Business-domain UI & client workflows
│   ├── auth/
│   ├── catalog-search/
│   └── checkout/
│       ├── components/         # Feature-private UI components
│       │   ├── OrderSummaryCard.tsx
│       │   └── PromoCodeForm.tsx
│       ├── hooks/              # Stateful hooks & client orchestration
│       │   └── useCheckoutSubmit.ts
│       ├── api/                # Typed API client calls & query keys
│       │   └── checkout.api.ts
│       ├── model/              # Pure validation schemas, types, price math
│       │   └── checkout-totals.ts
│       └── index.ts            # Exports only <CheckoutFlow /> and public hooks/types
├── components/ (or shared/ui/) # Design-system primitives (Button, Modal, DataTable)
│                               # ZERO business/domain imports allowed here!
└── lib/ (or shared/lib/)       # Pure technical utilities (http-client, date-format, cn)
```

**Strict Unidirectional Import Rule for Frontends**:
```text
app (routes)  ──►  features/*  ──►  shared/ui & shared/lib
```
- `shared/ui` (`Button`, `Modal`) may **never** import from `features/*`.
- `features/checkout` may **never** reach into `features/catalog-search/components/internal-file.tsx`; cross-feature composition happens in `app/` (the page/route layer) or through an explicit public contract.

---

## 5. File Granularity, Naming & Co-Location Rules

### File Size & Responsibility Heuristics
| File Length | Signal & Action |
| :--- | :--- |
| **< 250 lines** | Healthy, scannable in one screenful. Keep cohesive functions together rather than prematurely splitting into 20-line micro-files. |
| **250 – 450 lines** | Watch zone. Check if the file mixes pure business logic with I/O adapters or multiple distinct sub-components. |
| **> 500 lines** | **Split candidate.** Almost always contains 2–4 distinct responsibilities (e.g., data fetching + transformation + caching + rendering) that should be extracted into focused sibling modules. |

### Co-Location Principle
Keep files that change together **next to each other**:
- Unit tests (`order.service.test.ts`), component styles, and feature-specific types/schemas belong right beside the source file they test or support (or in a `tests/` folder mirroring the module structure if the language ecosystem mandates it, like Python/Java).
- Only promote a component or type to `shared/` when **at least 2–3 distinct features** genuinely depend on it (**The Rule of Three**). Prematurely putting single-feature code in `shared/` couples the whole repository to one feature's churn.

---

## 6. Public Module Facades vs. The Barrel File (`index.ts`) Trap

Barrel files (`index.ts` that blindly do `export * from './a'; export * from './b';` at every directory level) cause two severe problems in large TypeScript/JavaScript codebases:
1. **Circular Dependency Explosions**: File `a.ts` inside `features/orders` imports a helper from `../orders/index.ts`, which re-exports `a.ts`, causing `undefined` imports at runtime.
2. **Build & Test Performance Collapse**: Importing one tiny constant from a barrel file forces bundlers and test runners (Vitest/Jest) to parse and execute 150 transitive modules.

### The Safe Module Facade Rule
- **Inside a module (`features/orders/*`)**: Files must import their siblings via **direct relative paths** (`import { calculateTax } from './order-math.js'`), **never** via the module's own `index.ts`.
- **At the module boundary (`features/orders/index.ts`)**: Use `index.ts` **only** as an intentional, curated **Public Facade** exporting the 2–5 symbols external modules are allowed to use (named exports, no wildcard `export *`), OR import directly from explicit entry points (`features/orders/order.service.js`).
- **Never create a root-level `src/index.ts` or `src/components/index.ts` mega-barrel** in an application.

---

## 7. Killing the `utils/` and `helpers/` Junk Drawer

Files named `utils.ts`, `helpers.py`, `common.go`, or `misc.js` have zero cohesion — they act as magnets for unrelated code until they become untestable monoliths imported by every file in the project.

When modularizing a `utils` file, classify every function and move it to a **capability-named module**:

| Function Found in `utils.ts` | Where It Actually Belongs |
| :--- | :--- |
| `calculateVipOrderDiscount(order, user)` | **Domain logic!** Move into `modules/orders/domain/order-pricing.ts`. |
| `formatCurrencyCents(cents, locale)` | `shared/format/currency.ts` |
| `retryWithExponentialBackoff(fn, opts)` | `shared/resilience/retry.ts` |
| `parseJwtBearerHeader(header)` | `modules/auth/token-parser.ts` (or `shared/auth/jwt.ts`) |
| `slugifyProductTitle(title)` | `modules/catalog/domain/product-slug.ts` |
