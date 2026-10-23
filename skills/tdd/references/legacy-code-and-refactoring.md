# Legacy Code, Bug Reproduction & Safe Refactoring Reference

Writing tests first in a greenfield repository is straightforward. Applying TDD to an existing, coupled, or partially untested codebase requires specialized techniques (popularized by Michael Feathers' *Working Effectively with Legacy Code*) to break dependencies safely and lock down existing behavior before changing it.

---

## Contents

- [1. The Prove-It Pattern for Bug Fixes](#1-the-prove-it-pattern-for-bug-fixes)
- [2. Characterization Tests (Pinning Existing Behavior)](#2-characterization-tests-pinning-existing-behavior)
- [3. Finding Seams to Break Dependencies](#3-finding-seams-to-break-dependencies)
- [4. Sprout Method & Sprout Class](#4-sprout-method--sprout-class)
- [5. Wrap Method & Wrap Class (Decorator Seam)](#5-wrap-method--wrap-class-decorator-seam)
- [6. Safe Refactoring Choreography (Two Hats Rule)](#6-safe-refactoring-choreography-two-hats-rule)

---

## 1. The Prove-It Pattern for Bug Fixes

Whenever a bug report arrives, resist the urge to jump straight into editing production code. Follow the **Prove-It Protocol**:

1. **Locate the Root Cause & Sibling Callers**: Trace the bug from symptom to root cause, and grep for every caller of the affected function.
2. **Write the Minimal Reproduction Test (`RED`)**:
   - Construct the exact input/state that triggers the bug.
   - Assert the **correct** expected behavior.
   - Run the test and confirm it **fails with the exact symptom** described in the bug report.
3. **Apply the Minimal Root-Cause Fix (`GREEN`)**:
   - Fix the production code and watch the reproduction test turn green.
4. **Temporarily Revert to Double-Check (Optional Sanity Check)**:
   - If the fix was tricky, stashing the production fix must make the test fail again.
5. **Run the Full Suite**: Ensure zero regressions across sibling callers.

---

## 2. Characterization Tests (Pinning Existing Behavior)

When you must modify or refactor a complex legacy module that has **zero existing tests**, do not start refactoring blind. First, write **Characterization Tests** (also called Pinning Tests or Golden Master Tests) to record what the system *actually does today* — bugs, quirks, and all.

### Characterization Workflow
1. Call the legacy function with a representative set of inputs covering its main branches.
2. If you don't know the exact output ahead of time, assert a dummy value (`expect(result).toBe('DISCOVER')`), run the test to see the actual output produced by the legacy code, and lock that actual output into the assertion.
3. Add characterization cases until every branch you plan to touch is pinned by a passing test.
4. **Now** refactor the legacy code or add your new behavior test (`RED -> GREEN -> REFACTOR`), confident that any unintended behavior change in existing paths will trip a characterization test.

---

## 3. Finding Seams to Break Dependencies

A **Seam** is a place where you can alter program behavior (e.g., substituting a test double for an external HTTP call or database connection) without editing the complex logic inside the function under test.

### Parameterize Constructor / Function (Default Parameter Seam)

When a legacy function instantiates a hard dependency internally, expose it as an **optional parameter with the production implementation as the default value**. Existing callers do not change at all, while tests gain a clean injection seam:

```typescript
// BEFORE: Untestable without network access and environment secrets
export async function syncExchangeRates(): Promise<RateMap> {
  const client = new LiveForexApiClient(process.env.FOREX_API_KEY!);
  const raw = await client.fetchLatest('USD');
  return normalizeRates(raw);
}

// AFTER: Default parameter seam preserves 100% backward compatibility for all callers
export interface ForexClient {
  fetchLatest(baseCurrency: string): Promise<RawForexPayload>;
}

export async function syncExchangeRates(
  client: ForexClient = new LiveForexApiClient(process.env.FOREX_API_KEY!)
): Promise<RateMap> {
  const raw = await client.fetchLatest('USD');
  return normalizeRates(raw);
}
```

---

## 4. Sprout Method & Sprout Class

When you need to add a **new feature or validation rule** inside a 500-line legacy monster function that is too tangled to unit-test in full right now, use **Sprout Method**:

1. Do **not** inline 30 new lines of `if/else` logic directly inside the 500-line monster function.
2. **Sprout** a brand-new, pure, standalone function (`export function filterEligibleLineItems(items: LineItem[], now: Date): LineItem[]`) using strict **RED → GREEN → REFACTOR** TDD.
3. Call that newly tested 1-line function from inside the legacy method.

**Result**: 100% of your new logic is cleanly isolated and unit-tested in milliseconds, and the legacy monster function got 1 line longer instead of 30 lines worse.

---

## 5. Wrap Method & Wrap Class (Decorator Seam)

When you need to add cross-cutting behavior (auditing, metrics, rate-limiting, pre/post validation, event emission) before or after an existing legacy method without risking its internal logic:

```typescript
// Wrap Method pattern: Rename original to internal helper, wrap with new tested behavior
export class LegacyOrderProcessor {
  public processOrder(order: Order): Receipt {
    this.validateOrderFraudScore(order); // Newly TDD'd method
    const receipt = this.dispatchOrderInternally(order); // Original untouched logic
    this.recordAuditEntry(order, receipt); // Newly TDD'd method
    return receipt;
  }

  private dispatchOrderInternally(order: Order): Receipt {
    // ... original legacy code ...
  }
}
```

---

## 6. Safe Refactoring Choreography (Two Hats Rule)

Kent Beck's **Two Hats Rule**: During TDD, there are only two hats you can wear, and you may **never wear both at the same time**:

| Hat | Goal | Allowed Actions | Test Suite State |
| :--- | :--- | :--- | :--- |
| **1. Adding Behavior Hat (`RED -> GREEN`)** | Change observable system behavior (new feature, bug fix). | Write failing test, add minimal code to pass. Do **not** reorganize unrelated files or rename unrelated abstractions simultaneously. | Starts `RED`, ends `GREEN`. |
| **2. Refactoring Hat (`REFACTOR`)** | Improve internal structure without changing observable behavior. | Extract functions, rename symbols, remove duplication, simplify conditionals. Do **not** add new features or change public outputs while refactoring. | Starts `GREEN`, stays `GREEN` after every small edit. |

**Rule**: If a test breaks during a `REFACTOR` step and you cannot fix it within 60 seconds, **`git checkout` / undo back to the last green state** and take smaller steps.
