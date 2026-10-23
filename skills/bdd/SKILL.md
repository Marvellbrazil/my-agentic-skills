---
name: bdd
description: Executes development tasks using Behavior-Driven Development (BDD) methodologies. Establishes human-readable business specifications (declarative Gherkin syntax, Example Mapping, Given-When-Then scenarios) prior to implementation, connects them to isolated, reusable step definitions and domain/UI drivers, and drives outside-in implementation. Use when the user invokes /bdd, asks for Gherkin scenarios, acceptance criteria, feature files, Cucumber/Playwright-BDD/pytest-bdd specs, or behavior-driven development.
allowed-tools: Bash Read Grep Glob Edit Write
---

# Behavior-Driven Development (BDD)

Anchor software development in observable business behavior, shared domain vocabulary, and executable specifications (`Given-When-Then`) **before** writing production implementation code.

BDD is not "writing UI tests in English." It is a three-step collaborative loop — **Discovery (Example Mapping) → Formulation (Declarative Gherkin) → Automation (Outside-In Implementation)** — that turns ambiguous requirements into living documentation that runs in CI.

---

## Reference Modules

Load these detailed reference guides before writing feature files or step definitions:

| Concern | Reference Module | What It Covers |
| :--- | :--- | :--- |
| **Gherkin Authoring & Formulation** | [references/gherkin-best-practices.md](references/gherkin-best-practices.md) | Declarative vs. imperative style, the Golden Rules of `Given-When-Then`, `Rule` & `Background` usage, `Scenario Outline` tables,Example Mapping, and Gherkin anti-patterns |
| **Step Definitions, State & Drivers** | [references/step-definitions-and-architecture.md](references/step-definitions-and-architecture.md) | The 3-tier BDD test architecture, World/Context state isolation, Test Data Builders, Domain vs. API vs. UI execution seams, and multi-language framework patterns |

---

## The Outside-In BDD Loop

```text
1. DISCOVER (Example Mapping)
   Identify Business Rules + Concrete Examples + Edge Cases
         │
         ▼
2. FORMULATE (Declarative Gherkin .feature)
   Write Given (Context) / When (Single Action) / Then (Observable Outcome)
         │
         ▼
3. AUTOMATE (Failing Acceptance Step -> RED)
   Wire Step Definitions to a Driver / Domain Facade (never raw selectors in steps)
         │
         ▼
4. INNER TDD LOOP (Red -> Green -> Refactor)
   Implement domain & application code until the scenario passes (GREEN)
         │
         ▼
5. VERIFY & REFACTOR
   Confirm all scenarios pass and read as clean Living Documentation
```

---

## Execution Workflow

### Phase 1 — Discover the Stack & Existing Specs
Before creating files, inspect the repository to align with its existing BDD/testing setup:
- **JS/TS**: Cucumber.js (`@cucumber/cucumber`), `playwright-bdd`, Vitest/Jest with `jest-cucumber`
- **Python**: `pytest-bdd`, `behave`
- **Go**: `godog`
- **Java/JVM**: Cucumber-JVM, JUnit 5 Suite
- **C#/.NET**: Reqnroll, SpecFlow
- **Ruby**: Cucumber, RSpec `feature`/`scenario`

If no BDD runner is installed and the user did not ask to install a new framework, express the `Given / When / Then` scenarios using the repository's native test runner (`describe('Feature: ...')` / `it('Given ... When ... Then ...')` or clean helper steps) alongside `.feature` specification files.

### Phase 2 — Discovery & Example Mapping
Before writing Gherkin, break the requirement down into:
1. **The Story / Capability**: Who is the actor, what capability do they need, and what business value does it deliver?
2. **Business Rules (`Rule:`)**: What invariants govern this feature? (e.g., *"Orders over $100 qualify for free standard shipping"*).
3. **Concrete Examples (`Scenario:`)**:
   - **Happy Path**: The primary successful flow with concrete domain values.
   - **Boundary & Negative Cases**: Exact threshold values, insufficient permissions, invalid state transitions, or external failures.

### Phase 3 — Formulate Declarative Gherkin
Write `.feature` specifications following [references/gherkin-best-practices.md](references/gherkin-best-practices.md):

- **Declarative, Not Imperative**: Describe *what* the business user is doing, never *how* the UI widgets work (no CSS selectors, URLs, button clicks, or database column names in `.feature` files).
- **Strict Role Separation**:
  - `Given` establishes **preconditions and initial state** (past/present state).
  - `When` performs **one single trigger action** by the actor or system event.
  - `Then` asserts **observable business outcomes** and side effects.
- **One Behavior Per Scenario**: Never chain `When -> Then -> When -> Then` inside a single scenario. Split multi-step journeys into focused scenarios.

```gherkin
Feature: Promotional Discount Application
  In order to increase checkout conversion during seasonal campaigns
  As a registered shopper
  I want to apply valid promo codes to my shopping cart

  Rule: Percentage promo codes require a minimum cart subtotal

    Background:
      Given an active promo code "SPRING20" for 20% off orders of at least $50.00

    Scenario: Cart meets the minimum subtotal threshold
      Given a shopper has a cart with items totaling $60.00
      When the shopper applies the promo code "SPRING20"
      Then the cart discount should be $12.00
      And the payable cart total should be $48.00

    Scenario: Cart is below the minimum subtotal threshold
      Given a shopper has a cart with items totaling $49.99
      When the shopper applies the promo code "SPRING20"
      Then the promo code should be rejected with "Minimum order of $50.00 required"
      And the payable cart total should remain $49.99
```

### Phase 4 — Wire Step Definitions & Drivers (Outside-In)
Implement the automation glue following [references/step-definitions-and-architecture.md](references/step-definitions-and-architecture.md):

1. **Keep Step Definitions Thin (1–5 lines)**: Step definitions translate Gherkin parameters into calls on a **Driver / Actor / Application Facade**.
2. **Isolate Scenario State**: Store per-scenario state in a dedicated `World` / fixture context object instantiated fresh for every scenario. Never use module-level mutable globals.
3. **Target the Fastest Honest Seam**:
   - Business rule scenarios (`Rule:`) should run against the **Domain Model or Application Service / HTTP API** in milliseconds.
   - Reserve full browser/E2E drivers for a small number of critical end-to-end user journeys.

### Phase 5 — Behavioral Implementation & Validation
1. Run the scenario first and confirm it fails (`RED`) for the expected behavioral reason.
2. Implement the minimal domain and application logic to satisfy the scenario (`GREEN`).
3. Refactor production code and step helpers while keeping the Gherkin specification untouched.
4. Run the full behavioral and unit test suite to verify zero regressions.

---

## Verification Checklist

- [ ] Every requirement or business rule is represented by at least one positive and one boundary/negative `Scenario`.
- [ ] All Gherkin scenarios are **declarative** (zero UI selectors, SQL queries, HTTP status codes, or implementation details in `.feature` files unless the product itself is a technical API/CLI).
- [ ] Each `Scenario` has exactly one logical `When` trigger.
- [ ] Step definitions delegate to reusable drivers/helpers and use isolated per-scenario `World`/fixture state.
- [ ] All scenarios execute and pass using the project's test runner.
