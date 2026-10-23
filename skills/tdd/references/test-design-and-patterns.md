# Test Design, Patterns & Determinism Reference

Tests are executable specifications. A well-designed test fails for **one clear behavioral reason**, runs in milliseconds without network or clock flakiness, and survives internal code refactorings without requiring test edits. This module covers the patterns that make unit and integration tests high-signal and low-maintenance.

---

## Contents

- [1. Behavioral State Testing vs. Implementation Coupling](#1-behavioral-state-testing-vs-implementation-coupling)
- [2. DAMP Over DRY & Test Data Builders](#2-damp-over-dry--test-data-builders)
- [3. Table-Driven (Parameterized) Testing](#3-table-driven-parameterized-testing)
- [4. Boundary Value & Edge-Case Matrix](#4-boundary-value--edge-case-matrix)
- [5. Eliminating Non-Determinism (Time, IDs, Randomness, Concurrency)](#5-eliminating-non-determinism-time-ids-randomness-concurrency)
- [6. Property-Based & Invariant Testing](#6-property-based--invariant-testing)
- [7. Preventing Tautological & False-Positive Tests](#7-preventing-tautological--false-positive-tests)

---

## 1. Behavioral State Testing vs. Implementation Coupling

Always test **public contracts (inputs → returned outputs / observable state changes)** rather than internal call sequences or private helpers.

### The Refactoring Litmus Test
Ask two questions of every test:
1. *"If I break the user-visible behavior, will this test definitely fail?"* (Sensitivity)
2. *"If I refactor the internal algorithm or extract a helper without changing behavior, will this test still pass?"* (Resilience)

```typescript
// ❌ BAD: Coupled to internal helper calls and SQL formatting
it('applies discount by calling calculateTierDiscount and updating DB', async () => {
  const spy = vi.spyOn(pricingInternals, 'calculateTierDiscount');
  await checkoutService.applyCoupon(cartId, 'VIP25');
  expect(spy).toHaveBeenCalledWith(expect.any(Object), 0.25);
});

// ✅ GOOD: Verifies observable state through the public interface
it('reduces payable total by 25% when a valid VIP coupon is applied', async () => {
  const cart = await checkoutService.createCart({
    items: [{ sku: 'BOOK-1', unitPriceCents: 4000, quantity: 1 }],
  });

  const updated = await checkoutService.applyCoupon(cart.id, 'VIP25');

  expect(updated.discountCents).toBe(1000);
  expect(updated.payableTotalCents).toBe(3000);
});
```

---

## 2. DAMP Over DRY & Test Data Builders

In production code, DRY (Don't Repeat Yourself) prevents divergence. In test code, aggressive DRY (deep `beforeEach` pyramids and shared helper functions that hide assertions) destroys readability. Prefer **DAMP (Descriptive And Meaningful Phrases)** combined with **Test Data Builders**.

### Why Deep `beforeEach` Pyramids Fail
When a test file has 5 nested `describe` blocks each mutating shared `let` variables in `beforeEach`, a developer reading line 240 cannot see what state the test starts with, and changing line 15 in the top `beforeEach` breaks 18 unrelated tests.

### The Builder Pattern for Clean Arrange Blocks
Use a builder function/class that provides valid defaults for all uninteresting fields, so the test body highlights **only the exact inputs that drive the assertion**:

```typescript
function buildInvoice(overrides: Partial<InvoiceInput> = {}): InvoiceInput {
  return {
    id: 'inv_default',
    customerId: 'cust_default',
    subtotalCents: 10_000,
    taxRateBps: 800, // 8.00%
    status: 'draft',
    dueDate: new Date('2026-06-01T00:00:00Z'),
    ...overrides,
  };
}

it('marks an unpaid invoice overdue after the due date', () => {
  // Only the two fields relevant to THIS behavior are visible in the test:
  const invoice = createInvoice(
    buildInvoice({
      status: 'issued',
      dueDate: new Date('2026-05-01T00:00:00Z'),
    })
  );

  const evaluated = evaluateInvoiceStatus(invoice, new Date('2026-05-02T00:00:00Z'));

  expect(evaluated.status).toBe('overdue');
});
```

---

## 3. Table-Driven (Parameterized) Testing

When testing a pure function, parser, validator, or pricing rule across multiple boundary inputs, use **table-driven tests** (`it.each` in Vitest/Jest, `@pytest.mark.parametrize` in Python, table slices in Go) instead of copy-pasting 10 nearly identical test blocks.

```typescript
describe('parsePaginationParams', () => {
  it.each([
    { rawLimit: undefined, rawOffset: undefined, expected: { limit: 20, offset: 0 }, reason: 'defaults when omitted' },
    { rawLimit: '1',       rawOffset: '0',       expected: { limit: 1, offset: 0 },  reason: 'minimum valid boundary' },
    { rawLimit: '100',     rawOffset: '50',      expected: { limit: 100, offset: 50 }, reason: 'maximum allowed limit' },
    { rawLimit: '500',     rawOffset: '0',       expected: { limit: 100, offset: 0 }, reason: 'clamps limit above 100' },
    { rawLimit: '-5',      rawOffset: '-10',     expected: { limit: 1, offset: 0 },  reason: 'clamps negative values to floor' },
  ])('$reason (limit=$rawLimit, offset=$rawOffset)', ({ rawLimit, rawOffset, expected }) => {
    expect(parsePaginationParams({ limit: rawLimit, offset: rawOffset })).toEqual(expected);
  });
});
```

**Rule**: Never put `if/else` branching inside a parameterized test body. If valid cases assert return values and invalid cases assert thrown errors, split them into two separate `it.each` tables (`valid inputs` and `rejected inputs`).

---

## 4. Boundary Value & Edge-Case Matrix

Whenever implementing a function during the TDD loop, systematically check this boundary matrix for the next `RED` test:

| Data Type | Boundaries to Test |
| :--- | :--- |
| **Numbers / Money / Counts** | `0`, `1`, `-1`, exact threshold `N`, `N - 1` (off-by-one below), `N + 1` (off-by-one above), `Number.MAX_SAFE_INTEGER`, `NaN`/`Infinity` (if untyped boundary). |
| **Strings / Identifiers** | Empty `""`, whitespace-only `"   "`, single char, exact max length, `max + 1`, Unicode/emoji/combining chars, SQL/HTML special chars. |
| **Collections / Arrays** | Empty `[]`, single element `[x]`, duplicate elements `[x, x]`, already sorted vs. reverse sorted, maximum batch size. |
| **Dates & Time** | Exact timestamp equality (`now === deadline`), `1ms` before/after, leap day (`Feb 29`), month-end rollover (`Jan 31 + 1 month`), UTC vs. timezone offset boundaries. |
| **State Machines** | Valid transition, duplicate/idempotent transition (calling `complete()` twice), forbidden backward transition (`cancelled -> paid`). |

---

## 5. Eliminating Non-Determinism (Time, IDs, Randomness, Concurrency)

Flaky tests destroy confidence in a test suite. A test that fails 1% of the time is a bug in the test or the boundary design.

| Source of Flakiness | Bad Pattern | Deterministic Pattern |
| :--- | :--- | :--- |
| **System Clock** | Calling `new Date()` or `Date.now()` deep inside domain logic and asserting `expect(res.expiresAt).toBeCloseTo(...)`. | Inject a `Clock` interface (`clock = () => new Date()`) or pass `now: Date` as an explicit parameter; use fixed timestamps (`new Date('2026-10-23T00:00:00Z')`) in tests. |
| **Timers & Delays** | `await new Promise(r => setTimeout(r, 1000))` in retry/backoff tests. | Inject a configurable `sleep` / scheduler function (`sleep = (ms) => Promise.resolve()`) or use fake timers (`vi.useFakeTimers()`). |
| **Randomness / UUIDs** | Asserting regex format only because the ID is random, or failing on random collisions. | Inject an `IdGenerator` or seeded PRNG for deterministic snapshot/equality assertions when identity routing matters. |
| **Shared Database / Filesystem** | Tests reading/writing the same table or temp file path without isolation. | Wrap each test in a rolled-back transaction, use per-test schema/in-memory DB, or create a unique `mkdtemp` directory cleaned up in `afterEach`. |
| **Unordered Queries** | Asserting `expect(rows).toEqual([a, b])` when the query has no `ORDER BY`. | Always define a deterministic sort order in the query, or assert with `expect.arrayContaining` when order is explicitly unspecified. |

---

## 6. Property-Based & Invariant Testing

Example-based tests verify known inputs; **Property-Based Tests** (`fast-check` in TS/JS, `Hypothesis` in Python, `proptest` in Rust, `rapid` in Go) generate hundreds of arbitrary inputs and shrink any failure down to the minimal counterexample.

Use property-based tests for:
1. **Round-trip / Serialization pairs**: `decode(encode(x)) === x`
2. **Idempotency**: `normalize(normalize(x)) === normalize(x)`
3. **Conservation invariants**: Splitting an invoice total across `N` installments always sums back to the exact original `totalCents` (no lost or invented pennies).
4. **Oracle comparison**: A new optimized algorithm produces the exact same output as a simple reference implementation for all inputs.

```typescript
import fc from 'fast-check';

it('allocates money across N shares without losing or gaining a single cent', () => {
  fc.assert(
    fc.property(
      fc.integer({ min: 0, max: 10_000_000 }),
      fc.integer({ min: 1, max: 100 }),
      (totalCents, parts) => {
        const shares = allocateCents(totalCents, parts);
        const sum = shares.reduce((a, b) => a + b, 0);
        expect(shares).toHaveLength(parts);
        expect(sum).toBe(totalCents);
        expect(Math.max(...shares) - Math.min(...shares)).toBeLessThanOrEqual(1);
      }
    )
  );
});
```

---

## 7. Preventing Tautological & False-Positive Tests

1. **Never Recompute the Production Formula in the Test**:
   - ❌ `expect(calculateTax(amount)).toBe(Math.round(amount * TAX_RATE))` — copies the bug from production into the test.
   - ✅ `expect(calculateTax(10_00)).toBe(80)` — asserts against an independent, hand-computed literal.
2. **Always Watch the Test Fail First (`RED`)**:
   - An async test missing `await` or `expect.assertions(1)` inside a callback can pass while asserting nothing at all. Running the test before implementing the fix proves the assertion actually executes and fails when the behavior is absent.
3. **Assert Specific Error Types / Messages, Not Bare `.toThrow()`**:
   - ❌ `expect(() => parseOrder(badInput)).toThrow()` — passes even if `parseOrder` crashes with `TypeError: Cannot read properties of undefined`.
   - ✅ `expect(() => parseOrder(badInput)).toThrow(OrderValidationError)` and check the offending field/reason.
