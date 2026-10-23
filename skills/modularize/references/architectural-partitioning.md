# Architectural Partitioning & Module Boundaries Reference

Splitting code into separate folders only helps if those folders have **enforced architectural boundaries**. Without clear rules for *what each layer is allowed to know* and *which direction dependencies may point*, separated files quickly weave back into a distributed monolith where UI components run raw database logic and domain models depend on HTTP request objects.

This reference covers macro- and meso-level architectural partitioning: **Modular Monoliths**, **Hexagonal (Ports & Adapters)**, **Functional Core / Imperative Shell**, **Deep vs. Shallow Modules**, and **Automated Boundary Enforcement**.

---

## Contents

- [1. Deep Modules vs. Shallow Modules (Ousterhout's Law)](#1-deep-modules-vs-shallow-modules-ousterhouts-law)
- [2. The Modular Monolith Architecture](#2-the-modular-monolith-architecture)
- [3. Hexagonal Architecture (Ports & Adapters)](#3-hexagonal-architecture-ports--adapters)
- [4. Functional Core, Imperative Shell](#4-functional-core-imperative-shell)
- [5. The Acyclic Dependencies Principle (ADP) & Breaking Cycles](#5-the-acyclic-dependencies-principle-adp--breaking-cycles)
- [6. Enforcing Architectural Boundaries Automatically](#6-enforcing-architectural-boundaries-automatically)

---

## 1. Deep Modules vs. Shallow Modules (Ousterhout's Law)

In *A Philosophy of Software Design*, John Ousterhout defines the quality of a module by the ratio of its **internal functionality (depth)** to its **public interface complexity (width)**:

```text
   ┌───────────────────┐           ┌──────────────────────────────────────┐
   │  Small, Simple    │           │  Wide, Leaky Public Interface        │
   │  Public Interface │           │  (10 parameters, exposes internals)  │
   ├───────────────────┤           ├──────────────────────────────────────┤
   │                   │           │  10 lines of pass-through code       │
   │  Substantial      │           └──────────────────────────────────────┘
   │  Hidden           │                      ❌ SHALLOW MODULE
   │  Implementation   │            (Adds cognitive load, hides nothing)
   │  Complexity       │
   │  (Edge cases,     │
   │   invariants,     │
   │   algorithms)     │
   │                   │
   └───────────────────┘
      ✅ DEEP MODULE
 (Hides complexity, easy to use)
```

### Rules to Avoid "Classitis" & Shallow Wrapper Slop
- **Do NOT split a cohesive 80-line algorithm into 6 tiny files** where every internal step and intermediate variable has to be exported and imported across files. That *increases* coupling and surface area!
- **DO extract a module** when you can hide a complex concern (e.g., rate-limit token bucket math, PDF invoice rendering, S3 multipart upload retry state, tax calculation rules) behind **1–3 clean functions or an interface** whose callers don't need to know how it works internally.
- **No Pass-Through Methods**: If `Controller.createUser(req)` calls `UserManager.createUser(req)` which calls `UserHelper.createUser(req)` with identical signatures and zero added policy, collapse the pass-through layer.

---

## 2. The Modular Monolith Architecture

Before splitting a system into microservices (which introduces network latency, distributed transactions, and deployment overhead), partition it as a **Modular Monolith**: a single deployable unit composed of strictly isolated domain modules.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    API Gateway / HTTP / CLI Router                      │
└───────────┬───────────────────────────────┬─────────────────────────────┘
            │                               │
            ▼                               ▼
┌────────────────────────────────┐ ┌──────────────────────────────────────┐
│   Module: Ordering             │ │   Module: Billing                    │
│  ┌──────────────────────────┐  │ │  ┌────────────────────────────────┐  │
│  │ Public Facade (index.ts) │──┼─┼─►│ Public Facade (BillingPort)    │  │
│  └──────────────────────────┘  │ │  └────────────────────────────────┘  │
│  ┌──────────────────────────┐  │ │  ┌────────────────────────────────┐  │
│  │ Internal Domain & Logic  │  │ │  │ Internal Domain & Logic        │  │
│  │ (PRIVATE to Ordering)    │  │ │  │ (PRIVATE to Billing)           │  │
│  └────────────┬─────────────┘  │ │  └───────────────┬────────────────┘  │
│               ▼                │ │                  ▼                   │
│  ┌──────────────────────────┐  │ │  ┌────────────────────────────────┐  │
│  │ Ordering Tables / Schema │  │ │  │ Billing Tables / Schema        │  │
│  └──────────────────────────┘  │ │  └────────────────────────────────┘  │
└────────────────────────────────┘ └──────────────────────────────────────┘
```

### The 4 Laws of a Modular Monolith
1. **No Reach-Around Imports**: `Ordering` may only import from `Billing`'s public contract (`modules/billing/index.ts`), never from `modules/billing/internal/stripe-mapper.ts`.
2. **Data Ownership per Module**: `Ordering` code may never directly query or mutate `Billing`'s database tables. If `Ordering` needs billing state, it calls `Billing`'s public service method or listens to `Billing` domain events.
3. **In-Process Contract First**: Because modules communicate via clean interfaces or in-process event buses using plain DTOs (not ORM entities), any single module can be extracted into a standalone microservice later by swapping the in-process adapter for an HTTP/gRPC client without rewriting a single line of domain logic.
4. **Shared Module Is Strictly Technical or Shared-Kernel**: `shared/` contains logger, config, telemetry, and foundational Value Objects (`Money`, `PaginatedResult`) — never business logic from `Ordering` or `Billing`.

---

## 3. Hexagonal Architecture (Ports & Adapters)

Inside any complex module, separate the **Core (Domain + Application)** from external drivers and infrastructure using **Ports and Adapters** (Alistair Cockburn):

```text
  Driving Adapters (Primary)                    Driven Adapters (Secondary)
  (Invoke the Application)                      (Implemented by Infrastructure)

  ┌────────────────────┐                        ┌─────────────────────────┐
  │ HTTP Controller    ├──┐                  ┌──► PostgresOrderRepository │
  └────────────────────┘  │                  │  └─────────────────────────┘
  ┌────────────────────┐  │   ┌──────────┐   │  ┌─────────────────────────┐
  │ CLI Command        ├──┼──►│  CORE    ├───┼──► StripePaymentAdapter    │
  └────────────────────┘  │   │ (Domain  │   │  └─────────────────────────┘
  ┌────────────────────┐  │   │ + Use    │   │  ┌─────────────────────────┐
  │ Queue Consumer     ├──┘   │  Cases)  │   └──► PostmarkEmailAdapter    │
  └────────────────────┘      └──────────┘      └─────────────────────────┘
                            (Defines Inbound      (Core defines Outbound
                             Use-Case APIs)        Port Interfaces)
```

### Layer Responsibilities & Forbidden Imports

| Layer | Responsibility | Allowed to Import | FORBIDDEN to Import |
| :--- | :--- | :--- | :--- |
| **Domain (`domain/`)** | Entities, Value Objects, Domain Events, pure business policies, Outbound Port interfaces. | Standard library, `shared-kernel` primitives. | `application/`, `infrastructure/`, `presentation/`, ORMs (`prisma`, `sqlalchemy`), HTTP (`express`, `fastapi`), SDKs (`stripe`, `aws-sdk`). |
| **Application (`application/`)** | Use-case orchestration, transaction boundaries, input/output DTOs, calling Ports. | `domain/`, `shared/` primitives. | `presentation/`, concrete `infrastructure/` implementations (must depend on Domain Port interfaces). |
| **Infrastructure (`infrastructure/`)** | SQL/ORM repositories, external API clients, cache adapters, message broker publishers. | `domain/`, `application/`, third-party SDKs, ORM clients. | `presentation/` (HTTP controllers, UI components). |
| **Presentation (`presentation/`)** | HTTP routes, request validation, status codes, GraphQL resolvers, CLI commands, UI views. | `application/`, `domain/` (read-only types/errors). | Direct database/ORM queries when an Application Use Case exists. |

---

## 4. Functional Core, Imperative Shell

When full Hexagonal layering feels too heavy for a smaller service, CLI tool, or frontend feature, use **Functional Core, Imperative Shell**:

1. **Functional Core (`*-core.ts`, `*-policy.py`)**:
   - Pure functions taking plain data structures and returning plain data structures or decision unions (`Result<Decision, ValidationError>`).
   - **Zero** `async/await`, **zero** database calls, **zero** `fetch`, **zero** environment variable reads, **zero** `Date.now()`.
2. **Imperative Shell (`*-handler.ts`, `*-service.py`)**:
   - Thin coordinator (~15–40 lines) that:
     1. Gathers state from the outside world (DB query, HTTP request, clock).
     2. Calls the **Functional Core** to compute the decision.
     3. Executes the side effects dictated by the decision (DB write, API call, log emission).

This pattern achieves 90% of the decoupling and testability benefits of Hexagonal Architecture with minimal boilerplate.

---

## 5. The Acyclic Dependencies Principle (ADP) & Breaking Cycles

**Rule**: The dependency graph of packages/modules must have **zero cycles**. If Module `A` imports Module `B`, and Module `B` imports Module `A`, they are no longer two modules — they are one giant tightly coupled module split across two files.

### 3 Proven Techniques to Break a Circular Dependency (`A ↔ B`)

```text
PROBLEM:
┌──────────┐   imports    ┌──────────┐
│ Module A ├─────────────►│ Module B │
│ (Orders) │◄─────────────┤ (Users)  │
└──────────┘   imports    └──────────┘

FIX 1 — Dependency Inversion (Extract Interface into A):
┌────────────────────────┐              ┌──────────┐
│ Module A (Orders)      │◄─────────────┤ Module B │
│ + OrderCustomerPort    │  implements  │ (Users)  │
└────────────────────────┘              └──────────┘

FIX 2 — Extract Shared Concept into a Lower Module C:
┌──────────┐                            ┌──────────┐
│ Module A │─────────┐        ┌─────────┤ Module B │
└──────────┘         ▼        ▼         └──────────┘
                  ┌──────────────┐
                  │   Module C   │
                  │ (Shared IDs/ │
                  │  Contracts)  │
                  └──────────────┘

FIX 3 — Event-Driven Decoupling (Mediator / Domain Event):
┌──────────┐   emits OrderPlaced    ┌───────────┐   notifies   ┌──────────┐
│ Module A ├───────────────────────►│ Event Bus ├─────────────►│ Module B │
└──────────┘                        └───────────┘              └──────────┘
```

---

## 6. Enforcing Architectural Boundaries Automatically

Architectural rules written only in a README decay as soon as someone is in a hurry. Lock module boundaries into CI using automated lint rules:

### TypeScript / JavaScript (`eslint.config.js` or `dependency-cruiser`)
Use `no-restricted-imports` or `eslint-plugin-boundaries` so illegal cross-layer or cross-feature imports fail the build immediately:

```javascript
// eslint.config.js — Forbid domain layer from importing infrastructure or presentation
export default [
  {
    files: ['src/**/domain/**/*.ts'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['**/infrastructure/**', '**/presentation/**', '@prisma/*', 'express', 'axios'],
              message: 'Domain layer must remain pure and cannot import infrastructure or HTTP libraries.',
            },
          ],
        },
      ],
    },
  },
];
```

### Python (`import-linter` in `pyproject.toml`)
```toml
[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "Clean Architecture Layer Direction"
type = "layers"
layers = [
    "app.presentation",
    "app.application",
    "app.domain",
]

[[tool.importlinter.contracts]]
name = "Feature Modules Are Independent"
type = "independence"
modules = [
    "app.modules.billing",
    "app.modules.inventory",
    "app.modules.shipping",
]
```

### Go & Rust
- **Go**: Place module internals under `internal/` so the Go compiler rejects unauthorized external package imports, and run `go vet` / `depguard` in `.golangci.yml`.
- **Rust**: Keep module fields/items private by default, use `pub(crate)` or `pub(super)` instead of unrestricted `pub`, and split large domains into workspace crates (`Cargo.toml` `[workspace]`) where Cargo itself forbids circular crate dependencies.
