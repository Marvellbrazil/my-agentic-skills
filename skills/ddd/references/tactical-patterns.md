# Tactical Domain-Driven Design Patterns Reference

Tactical DDD provides the building blocks to implement a **Rich Domain Model** inside a Bounded Context. A Rich Domain Model makes illegal states unrepresentable at compile time and runtime by encapsulating business rules directly inside **Value Objects**, **Entities**, **Aggregates**, and **Domain Services**.

---

## Contents

- [1. Rich Domain Model vs. Anemic Domain Model](#1-rich-domain-model-vs-anemic-domain-model)
- [2. Value Objects](#2-value-objects)
- [3. Entities](#3-entities)
- [4. Aggregates & Aggregate Roots](#4-aggregates--aggregate-roots)
- [5. Domain Events & Eventual Consistency](#5-domain-events--eventual-consistency)
- [6. Domain Services vs. Application Services](#6-domain-services-vs-application-services)
- [7. Repositories & Persistence Mapping](#7-repositories--persistence-mapping)
- [8. Tactical Checklist](#8-tactical-checklist)

---

## 1. Rich Domain Model vs. Anemic Domain Model

An **Anemic Domain Model** looks object-oriented on the surface, but its "entities" are merely passive data structs with getters and setters, while all business rules are scattered across procedural service classes.

```typescript
// ❌ ANEMIC: Any caller can put Order into an invalid state; rules are duplicated across callers
class AnemicOrder {
  id!: string;
  status!: string;
  totalCents!: number;
  items!: Array<{ sku: string; qty: number; priceCents: number }>;
}

// Procedural service mutating fields from the outside
function cancelOrder(order: AnemicOrder) {
  if (order.status === 'SHIPPED') throw new Error('Cannot cancel');
  order.status = 'CANCELLED'; // Another caller might forget the check above!
}
```

```typescript
// ✅ RICH DOMAIN MODEL: State is private; transitions go through invariant-enforcing domain methods
export class Order {
  private _status: OrderStatus;
  private readonly _lines: OrderLine[];
  private readonly _domainEvents: DomainEvent[] = [];

  private constructor(
    public readonly id: OrderId,
    public readonly customerId: CustomerId,
    lines: OrderLine[],
    status: OrderStatus
  ) {
    if (lines.length === 0) {
      throw new DomainInvariantError('An order must contain at least one line item.');
    }
    this._lines = [...lines];
    this._status = status;
  }

  public static place(id: OrderId, customerId: CustomerId, lines: OrderLine[]): Order {
    const order = new Order(id, customerId, lines, OrderStatus.Placed);
    order.recordEvent(new OrderPlacedEvent(id, customerId, order.total()));
    return order;
  }

  public cancel(reason: CancellationReason, cancelledAt: Date): void {
    if (this._status === OrderStatus.Shipped || this._status === OrderStatus.Delivered) {
      throw new DomainInvariantError(`Cannot cancel order ${this.id.value} once ${this._status}.`);
    }
    if (this._status === OrderStatus.Cancelled) {
      return; // Idempotent
    }
    this._status = OrderStatus.Cancelled;
    this.recordEvent(new OrderCancelledEvent(this.id, reason, cancelledAt));
  }

  public total(): Money {
    return this._lines.reduce(
      (sum, line) => sum.add(line.subtotal()),
      Money.zero(this._lines[0].unitPrice.currency)
    );
  }
}
```

---

## 2. Value Objects

A **Value Object** represents a descriptive concept in the domain with **no conceptual identity**. Two Value Objects with the same attributes are interchangeable.

### The 4 Laws of Value Objects
1. **Structural Equality**: Compared by the values of all their properties, never by an `id` or memory reference.
2. **Immutability**: Once constructed, no field can ever change. Operations return a **new** Value Object instance (`moneyA.add(moneyB)` returns a new `Money`).
3. **Self-Validation at Construction**: A Value Object cannot exist in an invalid state. If construction succeeds, every downstream function can trust its invariants completely.
4. **Behavior-Rich**: Put domain operations where the data lives (`Money.allocate()`, `DateRange.overlaps(other)`, `Percentage.applyTo(money)`).

```typescript
export class Money {
  private constructor(
    public readonly amountMinor: number,
    public readonly currency: CurrencyCode
  ) {
    if (!Number.isInteger(amountMinor)) {
      throw new DomainInvariantError('Money amountMinor must be an integer (cents).');
    }
    Object.freeze(this);
  }

  public static ofMinor(amountMinor: number, currency: CurrencyCode): Money {
    return new Money(amountMinor, currency);
  }

  public static zero(currency: CurrencyCode): Money {
    return new Money(0, currency);
  }

  public add(other: Money): Money {
    this.assertSameCurrency(other);
    return new Money(this.amountMinor + other.amountMinor, this.currency);
  }

  public subtract(other: Money): Money {
    this.assertSameCurrency(other);
    return new Money(this.amountMinor - other.amountMinor, this.currency);
  }

  public multiplyByQuantity(qty: number): Money {
    if (!Number.isInteger(qty) || qty < 0) {
      throw new DomainInvariantError('Quantity must be a non-negative integer.');
    }
    return new Money(this.amountMinor * qty, this.currency);
  }

  public equals(other: Money): boolean {
    return this.currency === other.currency && this.amountMinor === other.amountMinor;
  }

  private assertSameCurrency(other: Money): void {
    if (this.currency !== other.currency) {
      throw new DomainInvariantError(
        `Currency mismatch: cannot combine ${this.currency} and ${other.currency}.`
      );
    }
  }
}
```

---

## 3. Entities

An **Entity** is defined by its **continuity of identity** across time and state changes, not by its attributes. Two customers with the exact same name and address are still distinct entities if their `CustomerId` differs.

- **Typed Identity**: Always wrap entity IDs in dedicated Value Objects or branded types (`OrderId`, `CustomerId`, `InvoiceId`) so the compiler prevents passing a `CustomerId` to a method expecting an `OrderId`.
- **Identity Equality**: Two entity references are equal if and only if their typed `id` values are equal.

---

## 4. Aggregates & Aggregate Roots

An **Aggregate** is a cluster of Entities and Value Objects treated as a **single transactional consistency boundary**, guarded by one **Aggregate Root** entity.

### Vaughn Vernon's 4 Rules of Aggregate Design

| Rule | Why It Matters | How to Enforce |
| :--- | :--- | :--- |
| **1. Protect True Invariants inside Aggregate Boundaries** | An invariant is a business rule that must be consistent at the end of every database transaction (e.g., `sum(lineItems) == orderTotal`). | Only group entities into one Aggregate if a business invariant requires them to be locked and updated together atomically. |
| **2. Design Small Aggregates** | Giant aggregates (e.g., `Customer` containing `orders[]`, `invoices[]`, `addresses[]`) cause lock contention, huge memory loads, and serialization bottlenecks. | Keep ~70%+ of Aggregates to just the Root Entity + Value Objects, or Root + 1 bounded child Entity collection. |
| **3. Reference Other Aggregates by Identity Only** | Holding object references (`order.customer.UpdateTier()`) blurs transactional boundaries and creates accidental cascading mutations. | Store `readonly customerId: CustomerId` on `Order`, never `customer: Customer`. |
| **4. Use Eventual Consistency Outside the Boundary** | If changing Aggregate A requires updating Aggregate B (e.g., placing an `Order` reserves `Inventory`), do not mutate both in one giant method. | Have `Order.place()` emit `OrderPlacedEvent`, and handle inventory reservation in a separate subscriber/use-case. |

### Encapsulating Child Collections
Never return a mutable array (`get lines(): OrderLine[] { return this._lines; }`) from an Aggregate Root — a caller could call `order.lines.push(badLine)` and bypass `Order`'s maximum-order-limit invariant! Return `ReadonlyArray<OrderLine>` and expose mutation methods on the Root (`order.addLineItem(...)`, `order.changeQuantity(...)`).

---

## 5. Domain Events & Eventual Consistency

A **Domain Event** is an immutable record of something meaningful to the business that **already happened** in the past tense.

- **Naming**: Always past-tense verb phrase (`OrderPlaced`, `InvoiceOverdueMarked`, `SeatsReserved`).
- **Payload**: Include the Aggregate ID, timestamp (`occurredAt`), event ID, and the key domain values relevant to subscribers.
- **Collection on the Aggregate**: The Aggregate Root queues events internally (`this.recordEvent(...)`) during domain method execution without touching any external message broker.
- **Transactional Outbox / Dispatch**: The Application Service saves the Aggregate and persists/publishes the recorded `order.pullDomainEvents()` inside the same unit of work so events are never lost or published for rolled-back transactions.

---

## 6. Domain Services vs. Application Services

Engineers frequently confuse **Domain Services** and **Application Services**. Keep their responsibilities strictly separated:

| Dimension | Domain Service (`domain/`) | Application Service / Use Case (`application/`) |
| :--- | :--- | :--- |
| **Contains Business Logic?** | **YES** — Pure domain rules/calculations that involve multiple Aggregates or external policies and don't naturally belong to one single Entity. | **NO** — Pure orchestration, transaction control, authorization checks, and I/O coordination. |
| **Performs I/O (DB, HTTP)?** | **NEVER** (unless via a pure domain interface passed in, though passing already-loaded domain objects/values is strongly preferred). | **YES** — Calls Repositories, Unit of Work, Event Bus, and ACL ports. |
| **Inputs & Outputs** | Domain Entities, Value Objects, Domain Primitives. | Command DTOs / Primitives in → Result DTOs / Primitives out. |
| **Example** | `CurrencyExchangePolicy.convert(money, targetCurrency, rateQuote)` | `TransferFundsUseCase.execute(TransferFundsCommand)` |

### Application Service Template

```typescript
// src/ordering/application/cancel-order.use-case.ts
export class CancelOrderUseCase {
  constructor(
    private readonly orders: OrderRepository,
    private readonly eventPublisher: DomainEventPublisher,
    private readonly clock: Clock
  ) {}

  public async execute(cmd: { orderId: string; reason: string }): Promise<void> {
    const orderId = OrderId.from(cmd.orderId);
    const reason = CancellationReason.from(cmd.reason);

    const order = await this.orders.findById(orderId);
    if (!order) {
      throw new OrderNotFoundError(orderId);
    }

    // 1. Delegate business rule & state transition to the Aggregate Root
    order.cancel(reason, this.clock.now());

    // 2. Persist Aggregate state
    await this.orders.save(order);

    // 3. Publish recorded Domain Events
    await this.eventPublisher.publishAll(order.pullDomainEvents());
  }
}
```

---

## 7. Repositories & Persistence Mapping

A **Repository** provides the illusion of an in-memory collection of **Aggregate Roots**.

### Rules of Repositories
1. **One Repository Per Aggregate Root**: Never create a repository for a child entity (`OrderLineRepository` is forbidden; load and save `OrderLine`s exclusively through `OrderRepository`).
2. **Interface in `domain/`, Implementation in `infrastructure/`**: The domain defines *what* it needs (`OrderRepository`); infrastructure defines *how* SQL/Prisma/Mongo stores it (`PostgresOrderRepository`).
3. **Explicit Reconstitution Factory (`reconstitute` / `fromPersistence`)**:
   - Creating a *new* Aggregate (`Order.place(...)`) validates creation rules and emits `OrderPlacedEvent`.
   - Loading an *existing* Aggregate from the database (`Order.reconstitute(...)`) restores its saved state **without** re-emitting creation events.

```typescript
// Infrastructure Mapper inside PostgresOrderRepository
private toDomain(row: OrderRow, lineRows: OrderLineRow[]): Order {
  return Order.reconstitute({
    id: OrderId.from(row.id),
    customerId: CustomerId.from(row.customer_id),
    status: row.status as OrderStatus,
    lines: lineRows.map((l) =>
      OrderLine.reconstitute({
        sku: Sku.from(l.sku),
        quantity: l.quantity,
        unitPrice: Money.ofMinor(l.unit_price_cents, l.currency as CurrencyCode),
      })
    ),
  });
}
```

---

## 8. Tactical Checklist

- [ ] Are constructors on Entities and Value Objects private/protected when factory methods (`create`, `of`, `reconstitute`) are needed to enforce invariants?
- [ ] Do all Value Objects validate their inputs on construction, freeze their state, and provide structural `equals()`?
- [ ] Are all collections inside Aggregate Roots protected from external mutation (`ReadonlyArray`)?
- [ ] Does every Aggregate reference other Aggregates solely by typed ID (`CustomerId`, not `Customer`)?
- [ ] Do Application Use Cases contain zero `if/else` domain policy calculations, delegating all business decisions to Aggregates, Value Objects, or Domain Services?
- [ ] Does each Repository operate exclusively on an Aggregate Root and provide an In-Memory Fake implementation for instant unit/use-case testing?
