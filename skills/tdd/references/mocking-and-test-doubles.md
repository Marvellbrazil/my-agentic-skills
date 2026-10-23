# Mocking, Test Doubles & System Boundaries Reference

Over-mocking is the #1 cause of test suites that are **100% green in CI while production is on fire**. When you mock internal classes or chain 6 `mockReturnValue` calls together, your test stops testing your software and starts testing your own assumptions about how mocks behave.

This reference defines the **Test Double Hierarchy**, how to design **System Boundaries**, and how to write **Contract-Verified In-Memory Fakes** that run at unit-test speed with integration-test fidelity.

---

## Contents

- [1. The Test Double Hierarchy](#1-the-test-double-hierarchy)
- [2. Functional Core, Imperative Shell](#2-functional-core-imperative-shell)
- [3. In-Memory Fakes + Shared Contract Tests](#3-in-memory-fakes--shared-contract-tests)
- [4. Mocking at True System Boundaries](#4-mocking-at-true-system-boundaries)
- [5. Anti-Patterns of Over-Mocking](#5-anti-patterns-of-over-mocking)

---

## 1. The Test Double Hierarchy

Always reach for the **highest** option in this table that satisfies speed and determinism constraints:

| Rank | Test Double Type | What It Is | Fidelity | Maintenance Cost | When to Use |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1 (Best)** | **Real Implementation** | The actual production class/function. | Highest | Lowest | All pure domain logic, value objects, validators, formatters, serializers, state machines, and fast local databases (SQLite/Testcontainers in integration tests). |
| **2** | **In-Memory Fake** | A working, lightweight implementation of a boundary interface (e.g., `InMemoryUserRepository` backed by a `Map`). | High | Low | Repositories, queues, object storage (`FakeBlobStore`), caches, and clock/id services during application/use-case tests. |
| **3** | **Stub** | Returns pre-configured canned responses for specific inputs (`paymentGateway.StubDeclined()`). | Medium | Low | Simulating specific external failure modes (HTTP 429, network timeout, declined credit card) at third-party boundaries. |
| **4** | **Spy** | Wraps a real/fake implementation and records calls for post-hoc verification (`sentEmails[]`). | Medium | Medium | Verifying outgoing side effects at the edge of the system (e.g., asserting 1 welcome email was queued with the right recipient). |
| **5 (Last Resort)** | **Interaction Mock** (`vi.fn()`, `unittest.mock.MagicMock`) | Replaces an object and asserts exact method call arguments and call counts. | Lowest | Highest | Only when an external boundary has no return value and a Fake/Spy is impractical. **Never use for internal collaborators.** |

---

## 2. Functional Core, Imperative Shell

The easiest code to test requires **zero test doubles**. Separate business decisions from I/O side effects using the **Functional Core, Imperative Shell** pattern (Gary Bernhardt):

```text
┌────────────────────────────────────────────────────────────────┐
│ Imperative Shell (Thin Controller / Handler — ~20 lines)       │
│  1. Fetch raw data from DB / APIs (I/O)                        │
│  2. Call Functional Core with plain values                     │
│  3. Persist returned decisions / side-effect commands (I/O)    │
└───────────────────────────────┬────────────────────────────────┘
                                │ Pure values in / Pure decisions out
                                ▼
┌────────────────────────────────────────────────────────────────┐
│ Functional Core (Pure Domain Logic — 90% of complexity)        │
│  • Zero I/O, zero async, zero mocks, zero database imports     │
│  • 100% tested with fast, small input -> output unit tests     │
└────────────────────────────────────────────────────────────────┘
```

### Example Refactoring Away Need for Mocks

```typescript
// ❌ HARD TO TEST: Mixes DB reads, business rules, and email sending in one function
async function processSubscriptionRenewal(userId: string, db: Db, mailer: Mailer, stripe: Stripe) {
  const sub = await db.getSubscription(userId);
  const invoices = await db.getUnpaidInvoices(userId);
  if (invoices.length > 2 && sub.plan !== 'enterprise') {
    await db.suspendSubscription(userId);
    await mailer.sendSuspensionNotice(sub.email);
    return;
  }
  await stripe.charge(sub.customerId, sub.priceCents);
}

// ✅ EASY TO TEST: Pure Functional Core takes data and returns a decision union
export type RenewalDecision =
  | { action: 'suspend'; reason: 'too_many_unpaid_invoices'; notifyEmail: string }
  | { action: 'charge'; customerId: string; amountCents: number }
  | { action: 'skip'; reason: 'already_cancelled' };

export function decideRenewal(sub: SubscriptionSnapshot, unpaidInvoiceCount: number): RenewalDecision {
  if (sub.status === 'cancelled') {
    return { action: 'skip', reason: 'already_cancelled' };
  }
  if (unpaidInvoiceCount > 2 && sub.plan !== 'enterprise') {
    return { action: 'suspend', reason: 'too_many_unpaid_invoices', notifyEmail: sub.email };
  }
  return { action: 'charge', customerId: sub.customerId, amountCents: sub.priceCents };
}
```

Now 100% of the branching business logic in `decideRenewal` can be tested with **zero mocks, zero async, and zero setup boilerplate**!

---

## 3. In-Memory Fakes + Shared Contract Tests

When testing application services that depend on a Repository or Storage Port, prefer an **In-Memory Fake** over `vi.fn()` mocks:

```typescript
export class InMemoryTaskRepository implements TaskRepository {
  private readonly store = new Map<string, Task>();

  async save(task: Task): Promise<void> {
    this.store.set(task.id, structuredClone(task));
  }

  async findById(id: string): Promise<Task | null> {
    const found = this.store.get(id);
    return found ? structuredClone(found) : null;
  }

  async listByAssignee(assigneeId: string): Promise<Task[]> {
    return [...this.store.values()].filter((t) => t.assigneeId === assigneeId);
  }
}
```

### Keeping Fakes Honest with a Shared Contract Suite
How do you guarantee `InMemoryTaskRepository` and `PostgresTaskRepository` behave identically? Run the **exact same contract test suite** against both implementations:

```typescript
export function runTaskRepositoryContractSuite(
  name: string,
  createRepo: () => Promise<{ repo: TaskRepository; cleanup: () => Promise<void> }>
) {
  describe(`TaskRepository Contract (${name})`, () => {
    it('saves and retrieves a task by id', async () => {
      const { repo, cleanup } = await createRepo();
      try {
        const task = createSampleTask({ id: 'task-1', title: 'Write contract test' });
        await repo.save(task);
        expect(await repo.findById('task-1')).toEqual(task);
      } finally {
        await cleanup();
      }
    });

    it('returns null for unknown task id', async () => {
      const { repo, cleanup } = await createRepo();
      try {
        expect(await repo.findById('non-existent')).toBeNull();
      } finally {
        await cleanup();
      }
    });
  });
}

// Runs in 5ms:
runTaskRepositoryContractSuite('InMemory', async () => ({
  repo: new InMemoryTaskRepository(),
  cleanup: async () => {},
}));

// Runs against test DB in integration suite:
runTaskRepositoryContractSuite('Postgres', async () => {
  const tx = await testDb.beginTransaction();
  return {
    repo: new PostgresTaskRepository(tx),
    cleanup: () => tx.rollback(),
  };
});
```

---

## 4. Mocking at True System Boundaries

When you must stub/mock an external system (Stripe, SendGrid, OAuth provider, S3):

1. **Never Mock What You Don't Own Directly**:
   - Do not mock `fetch`, `axios`, or the 200-method `Stripe` SDK object directly in 30 different test files.
   - Wrap the third-party library behind a narrow, domain-owned interface (`PaymentGateway`, `EmailSender`) with 1–4 methods, and fake/stub **your own interface**.
2. **Test the Adapter Separately**:
   - Test your `StripePaymentGateway` adapter in one dedicated integration test file (using recorded HTTP fixtures, MSW / WireMock, or the provider's official test sandbox).
   - Everywhere else in the codebase, inject `FakePaymentGateway`.

---

## 5. Anti-Patterns of Over-Mocking

| Anti-Pattern | Symptom | Fix |
| :--- | :--- | :--- |
| **Mocking Internal Collaborators** | `ServiceA` test mocks `ServiceB` and `HelperC` from the same codebase. | Use the real `ServiceB` and `HelperC`; only replace I/O boundaries at the edge. |
| **Mocking Return Chains (Law of Demeter Violation)** | `mockDb.select.mockReturnValue({ from: vi.fn().mockReturnValue({ where: ... }) })` | Never mock query builders or fluent ORMs. Use an in-memory database (SQLite / PGlite / Testcontainers) or wrap the query behind a Repository interface. |
| **Stale Mock Shapes** | The real API changed `user.fullName` to `user.displayName` 3 months ago, but unit tests still pass because the mock returns `{ fullName: 'Alice' }`. | Derive mock/stub fixtures from the shared TypeScript type or Zod schema (`satisfies ApiUserResponse`) so typechecking fails when the contract changes. |
| **Verifying Exact Call Counts on Queries** | `expect(repo.findById).toHaveBeenCalledTimes(1)` | Queries are side-effect-free reads; caching or batching them later should not break behavioral tests. Only verify side-effecting commands when the side effect *is* the requirement. |
