# Strategic Domain-Driven Design Reference

Tactical patterns (Entities, Value Objects, Repositories) fail when applied inside a single monolithic model where every department's concept of `User`, `Product`, and `Order` is tangled together. **Strategic Design** prevents the "Big Ball of Mud" by establishing clear linguistic and architectural boundaries before writing tactical code.

---

## Contents

- [1. Ubiquitous Language](#1-ubiquitous-language)
- [2. Subdomains: Core, Supporting, and Generic](#2-subdomains-core-supporting-and-generic)
- [3. Bounded Contexts](#3-bounded-contexts)
- [4. Context Mapping & Integration Patterns](#4-context-mapping--integration-patterns)
- [5. Anti-Corruption Layer (ACL) Implementation](#5-anti-corruption-layer-acl-implementation)
- [6. Directory & Package Layout for Bounded Contexts](#6-directory--package-layout-for-bounded-contexts)
- [7. Strategic Anti-Patterns](#7-strategic-anti-patterns)

---

## 1. Ubiquitous Language

The **Ubiquitous Language** is a shared, rigorous vocabulary used consistently by domain experts, product specs, tests, and the source code itself within a Bounded Context.

### Rules for Codebase Vocabulary
1. **Eliminate Translation Layers in Your Head**: If the business calls an adjustment a *"Chargeback"* or a *"Credit Memo"*, the class must be `CreditMemo`, not `NegativeInvoiceAdjustmentRecord`.
2. **Model Verbs as Domain Commands, Not Setters**:
   - ❌ CRUD-speak: `subscription.setStatus('CANCELLED'); subscription.setEndDate(now);`
   - ✅ Ubiquitous Language: `subscription.cancelImmediately(reason, now);` or `subscription.scheduleCancellationAtPeriodEnd();`
3. **Model Past-Tense Facts as Domain Events**:
   - `SubscriptionCancelledAtPeriodEnd`, `CreditMemoIssued`, `ShipmentCustomsCleared`.
4. **Flag Ambiguous Terms Immediately**: Words like `Account`, `User`, `Item`, `Status`, `Process`, and `Data` are red flags when overloaded. Split them into their real domain roles (`Policyholder`, `Claimant`, `Underwriter`).

---

## 2. Subdomains: Core, Supporting, and Generic

Not every part of a system deserves the same engineering investment. Classify every problem area into one of three subdomain types:

| Subdomain Type | Definition | Engineering Strategy | Example (in an E-Commerce Platform) |
| :--- | :--- | :--- | :--- |
| **Core Domain** | The competitive differentiator — why the business exists and wins. High complexity, frequent change. | Full Tactical DDD (Rich Aggregates, Value Objects, Domain Events, exhaustive tests). | Dynamic pricing engine, fraud scoring, or custom fulfillment routing. |
| **Supporting Subdomain** | Custom to the business, necessary to support the Core, but not a competitive moat. Simple or moderate logic. | Clean modular boundaries, simpler domain model or Transaction Script where invariants are trivial. | Vendor catalog onboarding, internal admin reporting. |
| **Generic Subdomain** | Solved problems identical across every company. | Buy SaaS, use battle-tested open-source libraries, and wrap behind an **Anti-Corruption Layer (ACL)**. | Identity/OAuth (`Auth0`/`Clerk`), payment rails (`Stripe`), email delivery (`Postmark`). |

---

## 3. Bounded Contexts

A **Bounded Context** is an explicit linguistic and architectural boundary within which a domain model and its Ubiquitous Language have a single, unambiguous meaning.

### Recognizing Context Boundaries
When the same real-world noun has **different attributes, invariants, and lifecycles** in two parts of the system, you have two Bounded Contexts — **not** one shared entity:

```text
Real-world concept: "Book"

┌───────────────────────────────┐   ┌───────────────────────────────┐   ┌───────────────────────────────┐
│   Catalog Context             │   │   Inventory / Warehouse Ctx   │   │   Royalty / Finance Context   │
├───────────────────────────────┤   ├───────────────────────────────┤   ├───────────────────────────────┤
│ • ISBN (Identity)             │   │ • SKU / Barcode (Identity)    │   │ • ContractId + ISBN           │
│ • Title, Synopsis, CoverUrl   │   │ • Physical Dimensions, Weight │   │ • Author Split Percentage     │
│ • Author Bio, Categories      │   │ • Warehouse Bin Location      │   │ • Net Revenue Tier Rules      │
│ • Search Ranking Score        │   │ • Quantity On Hand / Reserved │   │ • Tax Withholding Rate        │
└───────────────────────────────┘   └───────────────────────────────┘   └───────────────────────────────┘
```

### Rules of Autonomy Between Bounded Contexts
1. **No Shared Database Tables**: Bounded Context A must never `JOIN` or directly query Bounded Context B's database tables.
2. **No Shared Domain Entities**: Do not import `CatalogBook` into the `Inventory` context. Each context owns its own representation containing only the fields its invariants require.
3. **Communicate via Contracts**: Contexts integrate through **Domain/Integration Events**, **Application APIs**, or an **Anti-Corruption Layer**.

---

## 4. Context Mapping & Integration Patterns

When two Bounded Contexts (Upstream `U` and Downstream `D`) must interact, choose an explicit Context Map relationship:

| Pattern | Relationship | When to Use |
| :--- | :--- | :--- |
| **Anti-Corruption Layer (ACL)** | `U ──► [ACL] ──► D` | **Default choice** when integrating with legacy systems, external APIs (Stripe, ERP), or another team's Bounded Context. Downstream translates Upstream's model into its own pure domain model at the boundary. |
| **Open Host Service (OHS) + Published Language (PL)** | `U [OHS/PL] ──► D1, D2` | Upstream exposes a stable, versioned protocol (REST/gRPC schema, AsyncAPI integration events) designed for multiple downstream consumers. |
| **Customer–Supplier** | `U (Supplier) ◄──► D (Customer)` | Two internal contexts where Upstream prioritizes Downstream's needs and both agree on contract evolution tested via **Consumer-Driven Contract Tests**. |
| **Shared Kernel** | `[ Context A (Shared) Context B ]` | A tiny, strictly versioned set of shared Value Objects (e.g., `Currency`, `TenantId`, `Money`) co-owned by two closely collaborating contexts. Keep as small as possible. |
| **Conformist** | `U ──► D (adopts U's model)` | Downstream has no leverage to change Upstream and the translation cost isn't worth an ACL (e.g., thin wrapper over an industry-standard schema). Never use inside a Core Domain. |

---

## 5. Anti-Corruption Layer (ACL) Implementation

Never allow external SDK types (e.g., `Stripe.PaymentIntent`, `ShopifyOrderPayload`) inside your `domain/` or `application/` directories.

```typescript
// 1. Domain Layer: Pure port & domain types (src/billing/domain/payment-gateway.ts)
export interface PaymentGateway {
  authorizeCharge(request: {
    invoiceId: InvoiceId;
    customerId: CustomerId;
    amount: Money;
  }): Promise<PaymentAuthorizationResult>;
}

export type PaymentAuthorizationResult =
  | { status: 'authorized'; authorizationId: AuthorizationId; authorizedAt: Date }
  | { status: 'declined'; reason: DeclineReason; rawProviderCode: string };

// 2. Infrastructure Layer: Anti-Corruption Layer adapter (src/billing/infrastructure/stripe-payment-acl.ts)
export class StripePaymentGatewayACL implements PaymentGateway {
  constructor(private readonly stripe: Stripe) {}

  async authorizeCharge(req: {
    invoiceId: InvoiceId;
    customerId: CustomerId;
    amount: Money;
  }): Promise<PaymentAuthorizationResult> {
    try {
      const intent = await this.stripe.paymentIntents.create({
        amount: req.amount.toMinorUnits(),
        currency: req.amount.currency.toLowerCase(),
        capture_method: 'manual',
        metadata: { invoiceId: req.invoiceId.value },
      });

      return {
        status: 'authorized',
        authorizationId: AuthorizationId.from(intent.id),
        authorizedAt: new Date(intent.created * 1000),
      };
    } catch (err) {
      return this.translateStripeErrorToDomain(err);
    }
  }

  private translateStripeErrorToDomain(err: unknown): PaymentAuthorizationResult {
    // Maps Stripe-specific error codes ('card_declined', 'insufficient_funds')
    // into pure domain DeclineReason values.
    ...
  }
}
```

---

## 6. Directory & Package Layout for Bounded Contexts

Group files **by Bounded Context first, then by architectural layer** (Package-by-Context, never top-level Package-by-Layer across the whole enterprise):

```text
src/
├── shared-kernel/                  # Tiny shared primitives (Money, Entity base, DomainEvent)
│   └── domain/
├── ordering/                       # Bounded Context 1: Ordering
│   ├── domain/                     # Pure TS/Python/Go — ZERO framework/ORM imports
│   │   ├── order.ts                # Aggregate Root
│   │   ├── order-line.ts           # Child Entity inside Order Aggregate
│   │   ├── shipping-address.ts     # Value Object
│   │   ├── order-events.ts         # OrderPlaced, OrderCancelled
│   │   └── order-repository.ts     # Repository Interface (Port)
│   ├── application/                # Use Cases / Command & Query Handlers
│   │   ├── place-order.use-case.ts
│   │   └── cancel-order.use-case.ts
│   ├── infrastructure/             # Adapters (Prisma/SQL, Event Bus, External ACLs)
│   │   ├── prisma-order-repository.ts
│   │   └── inventory-reservation.acl.ts
│   └── presentation/               # HTTP Controllers, GraphQL Resolvers, CLI
│       └── order.controller.ts
└── fulfillment/                    # Bounded Context 2: Fulfillment
    ├── domain/
    ├── application/
    ├── infrastructure/
    └── presentation/
```

---

## 7. Strategic Anti-Patterns

| Anti-Pattern | Symptom | Fix |
| :--- | :--- | :--- |
| **The Canonical Enterprise Data Model** | One giant `User` or `Order` class with 95 fields shared by Billing, Support, Marketing, and Shipping. | Split into context-specific models (`Subscriber`, `TicketRequester`, `Lead`, `Recipient`) mapped by `UserId`. |
| **Anemic Service Sprawl** | Data bags with public fields + 2,000-line `OrderManagerService` classes doing all validation and state mutation. | Move invariants and state transitions onto the Aggregate Root and Value Objects ([tactical-patterns.md](tactical-patterns.md)). |
| **Leaky Third-Party Types** | Domain methods accepting `Stripe.Customer` or `Prisma.OrderGetPayload`. | Introduce an Anti-Corruption Layer (`ACL`) and Repository Mapper in `infrastructure/`. |
| **Database-Driven Modeling** | Starting feature design by writing a SQL migration and auto-generating classes from table columns. | Model behaviors and invariants in the Domain first; design persistence tables to store the resulting state. |
