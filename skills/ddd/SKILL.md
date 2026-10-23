---
name: ddd
description: Enforces Domain-Driven Design (DDD) principles across architectural and implementation tasks. Structures software around Ubiquitous Language, Bounded Contexts, Context Maps, Anti-Corruption Layers (ACL), Rich Domain Models (Entities, Value Objects, Aggregates, Domain Services, Domain Events), and Clean/Hexagonal layered isolation. Use when the user invokes /ddd, designs or refactors business logic, models complex domains, or wants strict separation between domain rules and infrastructure.
allowed-tools: Bash Read Grep Glob Edit Write
---

# Domain-Driven Design (DDD)

Structure software around the business domain it serves. Keep the core business rules pure, expressive, and completely isolated from database schemas, HTTP frameworks, and external third-party SDKs.

DDD operates on two complementary scales:
1. **Strategic Design**: Discovering the **Ubiquitous Language**, carving the system into autonomous **Bounded Contexts**, and defining explicit integration contracts (**Context Maps**, **Anti-Corruption Layers**) so models do not bleed into a "Big Ball of Mud."
2. **Tactical Design**: Modeling invariants inside each Bounded Context using **Value Objects**, **Entities**, **Aggregates**, **Domain Services**, **Domain Events**, and **Repositories** arranged in a **Hexagonal / Clean Layered Architecture**.

---

## Reference Modules

Load these detailed reference guides before designing or refactoring domain code:

| Scale | Reference Module | What It Covers |
| :--- | :--- | :--- |
| **Strategic Design & Boundaries** | [references/strategic-design.md](references/strategic-design.md) | Ubiquitous Language enforcement, Subdomains (Core, Supporting, Generic), Bounded Contexts, Context Mapping patterns (ACL, Shared Kernel, Open Host, Customer-Supplier), and modular monorepo/package layout |
| **Tactical Building Blocks & Code** | [references/tactical-patterns.md](references/tactical-patterns.md) | Rich vs. Anemic Domain Models, Value Objects, Entities, Aggregate Roots & consistency rules, Domain Events & Outbox, Domain vs. Application Services, Repository contracts, and concrete code examples |

---

## Dependency Direction & Layered Architecture

All source code dependencies must point **inward** toward the Domain Layer. The Domain Layer knows nothing about databases, ORMs, HTTP routers, or external APIs.

```text
┌────────────────────────────────────────────────────────────────────┐
│ Presentation / Interface Layer (HTTP Controllers, CLI, Consumers)  │
└─────────────────────────────────┬──────────────────────────────────┘
                                  │ calls
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│ Application Layer (Use Cases, Command/Query Handlers, DTOs)        │
│ Orchestrates transactions, loads Aggregates via Repositories,      │
│ dispatches Domain Events. Contains NO business rules.              │
└───────────────────┬─────────────────────────────┬──────────────────┘
                    │ invokes                     │ depends on interfaces
                    ▼                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                        DOMAIN LAYER (PURE)                         │
│  • Aggregate Roots & Entities (identity + state-transition rules)  │
│  • Value Objects (immutable, self-validating, structural equality) │
│  • Domain Services (stateless cross-aggregate business rules)      │
│  • Domain Events (immutable facts of what happened)                │
│  • Repository Interfaces / Ports (defined in domain terms)         │
└─────────────────────────────────────────────────▲──────────────────┘
                                                  │ implements
┌─────────────────────────────────────────────────┴──────────────────┐
│ Infrastructure Layer (ORM Models, SQL/NoSQL Repos, Stripe/S3 ACLs) │
│ Implements Domain Repository interfaces, maps Persistence Models   │
│ <-> Domain Aggregates, houses Anti-Corruption Layers (ACLs).       │
└────────────────────────────────────────────────────────────────────┘
```

---

## Execution Workflow

### Phase 1 — Ubiquitous Language & Strategic Alignment
Before writing classes or tables, inspect existing domain docs (`CONTEXT.md`, `AGENTS.md`, ADRs) and codebase vocabulary ([references/strategic-design.md](references/strategic-design.md)):
1. **Speak the Domain's Language**: Use exact domain verbs and nouns (`policy.endorse()`, `invoice.writeOff()`, `shipment.reroute()`) instead of CRUD database jargon (`updateStatus()`, `setFlag()`, `patchData()`).
2. **Respect Bounded Context Boundaries**: Recognize that the same word means different things in different contexts (e.g., an `Order` in *Sales* tracks pricing and discounts; an `Order` in *Fulfillment* tracks package weight and warehouse bins). Never merge them into one "God `User`" or "God `Order`" class.
3. **Guard External Boundaries with an ACL**: Never let a third-party payload (Stripe webhook object, legacy SOAP response, external ERP schema) leak into the Domain or Application layer. Translate it at the edge through an **Anti-Corruption Layer (ACL)**.

### Phase 2 — Tactical Modeling (Rich Domain over Anemic CRUD)
Design domain building blocks following [references/tactical-patterns.md](references/tactical-patterns.md):

1. **Replace Primitive Obsession with Value Objects**:
   - Wrap domain primitives (`Money`, `EmailAddress`, `Percentage`, `DateRange`, `Sku`, `TaxId`) in immutable, self-validating Value Objects compared by value, not memory reference.
2. **Push Behavior into Entities & Aggregate Roots**:
   - Forbid public property setters (`order.status = 'SHIPPED'`) that bypass invariants.
   - Expose command methods (`order.markShipped(trackingNumber, shippedAt)`) that verify business invariants first, mutate internal state, and record a `DomainEvent`.
3. **Enforce Aggregate Rules**:
   - **One Transaction = One Aggregate**: A single transaction modifies one Aggregate Root instance.
   - **Reference Other Aggregates by ID Only**: Hold `CustomerId` (a Value Object), never a live object reference to `Customer` inside `Order`.
   - **Keep Aggregates Small**: Only include child entities (`OrderLine`) that *must* stay strongly consistent with the root under every concurrent write.
4. **Separate Domain Services from Application Services**:
   - **Domain Service**: Pure business logic spanning multiple aggregates or policies (e.g., `PricingPolicy.calculateDiscount(cart, coupon, customerTier)`), zero I/O.
   - **Application Service / Use Case**: Fetches aggregates from repositories, calls domain methods, commits the unit of work, and publishes events. Zero `if/else` business policy inside the application handler.

### Phase 3 — Persistence Ignorance & Repository Mapping
1. Define Repository interfaces in the **Domain Layer** using domain types (`findById(id: OrderId): Promise<Order | null>`, `save(order: Order): Promise<void>`).
2. Implement the Repository in the **Infrastructure Layer**, explicitly mapping between ORM/DB records and the rich Domain Aggregate.
3. Never decorate Domain Entities with ORM/serialization annotations that compromise constructors or force public mutable fields when avoidable.

---

## Verification Checklist

- [ ] **Zero Infrastructure Leaks in Domain**: The `domain/` package imports nothing from `infrastructure/`, `presentation/`, HTTP frameworks, or ORM libraries.
- [ ] **Ubiquitous Language**: Class, method, and event names express business intent (`loan.approve()`, `LoanApprovedEvent`) rather than CRUD mechanics (`updateLoan()`).
- [ ] **No Primitive Obsession**: Monetary values, identifiers, emails, quantities, and statuses are modeled as self-validating Value Objects or discriminated types.
- [ ] **Rich Aggregates**: Invariants are enforced inside Aggregate Root methods; invalid state transitions throw typed `DomainError`s (or return typed failure `Result`s).
- [ ] **Aggregate Independence**: Aggregates reference other aggregates by typed ID only and emit Domain Events for cross-aggregate side effects.
- [ ] **Unit Tested in Isolation**: Core domain aggregates, value objects, and domain services are tested with fast, zero-I/O unit tests.
