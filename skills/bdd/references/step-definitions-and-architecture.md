# Step Definitions, State Management & BDD Architecture

A clean Gherkin `.feature` file is only half of BDD. If the step definitions underneath contain 50-line Playwright/Selenium scripts, raw SQL queries, or shared global variables, the test suite will become flaky and unmaintainable within weeks. This module defines the **3-Tier BDD Architecture** that keeps specifications fast, deterministic, and decoupled from implementation churn.

---

## Contents

- [1. The 3-Tier BDD Architecture](#1-the-3-tier-bdd-architecture)
- [2. Choosing the Right Execution Seam (Domain vs. API vs. UI)](#2-choosing-the-right-execution-seam-domain-vs-api-vs-ui)
- [3. Scenario State Isolation (The `World` Pattern)](#3-scenario-state-isolation-the-world-pattern)
- [4. Test Data Builders for Sensible Defaults](#4-test-data-builders-for-sensible-defaults)
- [5. Reusable Step Design & Custom Parameter Types](#5-reusable-step-design--custom-parameter-types)
- [6. Multi-Language Implementation Templates](#6-multi-language-implementation-templates)
- [7. Step Definition Anti-Patterns](#7-step-definition-anti-patterns)

---

## 1. The 3-Tier BDD Architecture

Never put application logic, HTTP calls, or DOM selectors directly inside step definitions. Enforce a strict three-layer separation:

```text
┌─────────────────────────────────────────────────────────────────┐
│ Tier 1: Specification Layer (.feature files)                    │
│ Business rules & examples in Ubiquitous Language (What, not How)│
└───────────────────────────────┬─────────────────────────────────┘
                                │ (Matched by regex / Cucumber expressions)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ Tier 2: Step Definition Layer (steps/*.steps.ts / test_*.py)    │
│ Thin translation glue (1-5 lines). Parses parameters, reads     │
│ scenario World context, delegates to a Driver/Actor.            │
└───────────────────────────────┬─────────────────────────────────┘
                                │ (Calls typed domain methods)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ Tier 3: Driver / Automation Layer (drivers/* or screenplay/*)   │
│ Encapsulates HOW the system is driven:                          │
│   • DomainDriver (calls Domain/Application Services directly)   │
│   • ApiDriver (calls Fastify/Express/FastAPI test client)       │
│   • UiDriver / PageObjects (drives Playwright/Cypress)          │
└─────────────────────────────────────────────────────────────────┘
```

**Why this separation matters**:
- When an API endpoint path or UI selector changes, you update **one method in Tier 3**. Zero `.feature` files (Tier 1) and zero step definitions (Tier 2) are touched.
- By swapping Tier 3 drivers, the **exact same Gherkin scenario** can run against the in-memory domain model in 2ms or against the full web UI in 2s.

---

## 2. Choosing the Right Execution Seam (Domain vs. API vs. UI)

Do not run every BDD scenario through a headless browser. Follow the **BDD Testing Iceberg**:

| Seam | Target | Speed | When to Use |
| :--- | :--- | :--- | :--- |
| **Domain / Service Seam (~75%)** | Aggregate roots, domain services, application use-cases (with in-memory repositories) | 1–10 ms | Complex business rules, pricing, permissions, state transitions, edge cases (`Scenario Outline` tables). |
| **HTTP / API Seam (~20%)** | Controllers, serialization, validation, DB integration (`supertest`, `httpx.AsyncClient`, `httptest`) | 20–100 ms | Contract verification, auth middleware, database persistence, error responses. |
| **UI / Browser Seam (~5%)** | Full stack via Playwright / DevTools | 1–5 sec | Critical end-to-end user journeys ("happy path" checkout, onboarding flow). |

**Rule of Thumb**: Even in a UI scenario, set up `Given` preconditions via the **Domain Builder or API/DB directly** rather than clicking through 5 setup screens in the browser before reaching the `When` action.

---

## 3. Scenario State Isolation (The `World` Pattern)

Scenarios must be 100% isolated so they can run in any order or in parallel.

### ❌ Never Use Module-Level Mutable Variables

```typescript
// BAD: Leaks state between scenarios and fails in parallel runs
let currentCart: Cart;
let lastError: Error | null = null;

Given('a shopper has an empty cart', () => {
  currentCart = new Cart();
});
```

### ✅ Always Use a Per-Scenario `World` / Context Instance

```typescript
// GOOD: Fresh context instance created per scenario
export class CheckoutWorld {
  public shopperId = 'shopper-default';
  public cart = new CartBuilder().build();
  public lastResult?: CheckoutReceipt;
  public lastError?: DomainError;
  public readonly driver = new CheckoutDomainDriver();
}
```

In `pytest-bdd`, use function-scoped `pytest.fixture` objects to hold scenario state cleanly.

---

## 4. Test Data Builders for Sensible Defaults

Gherkin steps should only mention the fields that matter for that specific scenario. Use the **Test Data Builder** pattern to fill in every other required field with valid defaults:

```typescript
export class AccountBuilder {
  private props: AccountProps = {
    id: 'acc_default',
    email: 'customer@example.com',
    status: 'active',
    balanceCents: 10_000,
    overdraftLimitCents: 0,
    tier: 'standard',
  };

  withBalance(dollars: number): this {
    this.props.balanceCents = Math.round(dollars * 100);
    return this;
  }

  withOverdraftLimit(dollars: number): this {
    this.props.overdraftLimitCents = Math.round(dollars * 100);
    return this;
  }

  suspended(): this {
    this.props.status = 'suspended';
    return this;
  }

  build(): Account {
    return Account.create(this.props);
  }
}
```

Now the step definition is one expressive line:

```typescript
Given(
  'a checking account with a balance of ${float} and an overdraft limit of ${float}',
  function (this: BankingWorld, balance: number, limit: number) {
    this.account = new AccountBuilder()
      .withBalance(balance)
      .withOverdraftLimit(limit)
      .build();
  }
);
```

---

## 5. Reusable Step Design & Custom Parameter Types

### Parameterize Variations Instead of Duplicating Steps

Do not write separate step functions for `"Given an active account"`, `"Given a suspended account"`, and `"Given a closed account"`. Define a custom parameter type or union match:

```typescript
defineParameterType({
  name: 'accountStatus',
  regexp: /active|suspended|closed/,
  transformer: (s) => s as AccountStatus,
});

Given('a(n) {accountStatus} customer account', function (this: World, status: AccountStatus) {
  this.account = new AccountBuilder().withStatus(status).build();
});
```

### Capturing Expected Rejections Cleanly

When a `Scenario` tests that an invalid action is rejected (`Then the withdrawal should be declined with "..."`), capture the outcome in the `When` step so `Then` can assert on it cleanly:

```typescript
When('the customer withdraws ${float}', async function (this: BankingWorld, amount: number) {
  this.lastOutcome = await this.driver.attemptWithdrawal(this.account, amount);
});

Then('the withdrawal should be declined for {string}', function (this: BankingWorld, reason: string) {
  expect(this.lastOutcome.ok).toBe(false);
  expect(this.lastOutcome.errorMessage).toContain(reason);
});
```

---

## 6. Multi-Language Implementation Templates

### TypeScript (Cucumber / Playwright-BDD / Vitest)

```typescript
// tests/bdd/steps/promo-code.steps.ts
import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from 'vitest';
import { CartWorld } from '../support/cart-world.js';

Given(
  'an active promo code {string} for {int}% off orders of at least ${float}',
  async function (this: CartWorld, code: string, percent: number, minOrder: number) {
    await this.driver.seedPromoCode({ code, discountPercent: percent, minSubtotal: minOrder });
  }
);

Given(
  'a shopper has a cart with items totaling ${float}',
  async function (this: CartWorld, subtotal: number) {
    await this.driver.createCartWithSubtotal(subtotal);
  }
);

When('the shopper applies the promo code {string}', async function (this: CartWorld, code: string) {
  this.lastApplyResult = await this.driver.applyPromoCode(code);
});

Then('the payable cart total should be ${float}', async function (this: CartWorld, expectedTotal: number) {
  const summary = await this.driver.getCartSummary();
  expect(summary.payableTotal).toBeCloseTo(expectedTotal, 2);
});
```

### Python (`pytest-bdd`)

```python
# tests/bdd/test_promo_code.py
from decimal import Decimal
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

scenarios("../features/promo_code.feature")

@pytest.fixture
def context(cart_driver):
    return {"driver": cart_driver, "result": None}

@given(parsers.parse('an active promo code "{code}" for {percent:d}% off orders of at least ${min_order:f}'))
def seed_promo(context, code: str, percent: int, min_order: float):
    context["driver"].seed_promo(code=code, percent=percent, min_subtotal=Decimal(str(min_order)))

@given(parsers.parse("a shopper has a cart with items totaling ${subtotal:f}"))
def create_cart(context, subtotal: float):
    context["driver"].create_cart(subtotal=Decimal(str(subtotal)))

@when(parsers.parse('the shopper applies the promo code "{code}"'))
def apply_promo(context, code: str):
    context["result"] = context["driver"].apply_promo(code)

@then(parsers.parse("the payable cart total should be ${expected:f}"))
def verify_total(context, expected: float):
    assert context["driver"].cart_total() == Decimal(str(expected))
```

---

## 7. Step Definition Anti-Patterns

| Anti-Pattern | Why It Breaks | Correct Approach |
| :--- | :--- | :--- |
| **Calling one Step Definition from inside another Step** | Creates hidden coupling across regex strings; breaks when step wording is refined. | Extract shared logic into a method on the **Tier 3 Driver** and call that method from both steps. |
| **Assertions inside `Given` or `When` steps** | Obscures whether a failure is a broken test fixture or a broken feature under test (`Then`). | Fail fast on invariant violations in builders, but keep behavioral assertions in `Then` steps. |
| **Hardcoded sleeps (`sleep(2000)`)** | Makes suites slow and flaky under CI load. | Use deterministic domain/API calls or explicit condition polling (`expect.poll` / Playwright auto-waiting) inside the UI driver. |
| **Regex spaghetti matching 10 optional clauses** | A single step with `/(?:not )?have (?:at least )?(\d+) (?:active\|pending)?/` becomes impossible to debug. | Keep step patterns focused and readable; use Cucumber Expressions (`{int}`, `{string}`, custom parameter types). |
