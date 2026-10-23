# Gherkin Best Practices & Formulation Reference

Gherkin is a structured language for capturing **executable business specifications** and **living documentation**. When written well, a `.feature` file can be read by product owners, engineers, and QA alike, and survives UI redesigns or database migrations without changing a single word. When written poorly, it becomes a brittle, slow, natural-language macro script that breaks whenever a button label changes.

---

## Contents

- [1. Declarative vs. Imperative Gherkin](#1-declarative-vs-imperative-gherkin)
- [2. The Golden Rules of Given-When-Then](#2-the-golden-rules-of-given-when-then)
- [3. Structuring Features with `Rule` and `Background`](#3-structuring-features-with-rule-and-background)
- [4. Example Mapping to Gherkin](#4-example-mapping-to-gherkin)
- [5. Data Tables & `Scenario Outline`](#5-data-tables--scenario-outline)
- [6. Common Gherkin Anti-Patterns](#6-common-gherkin-anti-patterns)
- [7. Authoring Checklist](#7-authoring-checklist)

---

## 1. Declarative vs. Imperative Gherkin

The single most important rule in BDD is **write declarative scenarios, not imperative UI scripts**.

- **Imperative (Bad)**: Describes *how* the user interacts with mechanics (clicking elements, typing into input fields, waiting for spinners, navigating URLs).
- **Declarative (Good)**: Describes *what* the actor intends to accomplish in the language of the business domain.

### Comparison

```gherkin
# ❌ BAD: Imperative, UI-coupled, brittle, hides the business rule
Scenario: Successful login
  Given I open the browser to "https://app.example.com/login"
  When I type "alice@example.com" into the "#email-input" field
  And I type "Secret123!" into the "input[name='password']" field
  And I click the "button.submit-login" element
  And I wait 2 seconds
  Then the URL should be "https://app.example.com/dashboard"
  And the ".welcome-banner" element should contain "Welcome, Alice"
```

```gherkin
# ✅ GOOD: Declarative, domain-focused, survives UI redesigns
Scenario: Active member signs in with valid credentials
  Given an active member "alice@example.com"
  When Alice signs in with her valid password
  Then she should be directed to her account dashboard
```

Why the declarative version wins:
1. If login changes from a password form to a multi-step modal or API call, the `.feature` file does not change — only the underlying step driver changes.
2. It runs equally well against an in-memory domain model (2ms), an HTTP API (20ms), or a headless browser (2s).

---

## 2. The Golden Rules of Given-When-Then

Each keyword has a strict semantic contract:

| Keyword | Grammatical Tense | Purpose | Rules |
| :--- | :--- | :--- | :--- |
| **`Given`** | Past / Present state | Establish **context & preconditions** | Put the system into a known state before the action occurs. Never put the action under test inside a `Given`. |
| **`When`** | Present action | Trigger **the single event/action** | Exactly **one** logical `When` per scenario. If you have two `When` blocks, you are writing an end-to-end tour, not a behavioral specification. |
| **`Then`** | Observable result | Assert **business outcome & state** | Verify what changed or what was produced. Never assert internal implementation details (e.g., private function calls or raw SQL rows). |
| **`And` / `But`** | Inherits parent | Continuation | Keep to 1–3 continuations per block. If a `Given` needs 8 `And` lines, collapse irrelevant boilerplate into a domain-level concept with sensible defaults. |

### Third-Person Domain Actors Over First-Person "I"

Prefer naming the domain role (`Given a verified seller`, `When the buyer requests a refund`, `When the Fraud Reviewer flags the transaction`) over generic `"Given I am a user"`. Many business flows involve multiple actors (buyer, seller, admin, billing scheduler); explicit roles make authorization and multi-actor scenarios crystal clear.

---

## 3. Structuring Features with `Rule` and `Background`

### Grouping Scenarios by Business `Rule`

Modern Gherkin (v6+) provides the `Rule:` keyword to group scenarios under the explicit business invariant they illustrate:

```gherkin
Feature: Account Overdraft Protection
  As a retail banking customer
  I want overdraft protection to cover small shortfalls
  So that my debit transactions are not declined unexpectedly

  Rule: Overdraft is allowed up to the customer's approved limit for a $15 fee

    Scenario: Withdrawal within the overdraft limit succeeds with a fee
      Given a checking account with a balance of $50.00 and an overdraft limit of $100.00
      When the customer withdraws $120.00
      Then the withdrawal should be approved
      And the account balance should be -$85.00

    Scenario: Withdrawal exceeding the overdraft limit is declined without a fee
      Given a checking account with a balance of $50.00 and an overdraft limit of $100.00
      When the customer withdraws $155.00
      Then the withdrawal should be declined for "Insufficient funds"
      And the account balance should remain $50.00
```

### Disciplined Use of `Background`

A `Background` runs before every scenario in the `Feature` (or `Rule`). Keep it short (1–3 lines) and relevant to **every** scenario below it:
- **Do**: Put shared domain context that every scenario requires (e.g., `Given the store catalog contains: ...`).
- **Don't**: Put 15 lines of complex setup that only 2 out of 6 scenarios care about — readers will have to scroll up and mentally merge state to understand why a scenario passes or fails.

---

## 4. Example Mapping to Gherkin

Before writing Gherkin, map the requirement into four layers (Matt Wynne's Example Mapping):

```text
[ Story / Feature ]
   │
   ├──► [ Rule 1: Late cancellations (<24h) incur a 50% fee ]
   │       ├── Example 1a: Cancelled 36h before check-in -> 100% refund
   │       ├── Example 1b: Cancelled 24h before check-in -> 100% refund (boundary)
   │       └── Example 1c: Cancelled 12h before check-in -> 50% refund
   │
   └──► [ Rule 2: VIP members are exempt from late cancellation fees ]
           └── Example 2a: VIP cancels 4h before check-in -> 100% refund
```

Every **Rule card** becomes a `Rule:` block, and every **Example card** becomes a `Scenario:` (or a row in a `Scenario Outline`).

---

## 5. Data Tables & `Scenario Outline`

### When to Use `Scenario Outline`

Use `Scenario Outline` + `Examples:` when multiple scenarios share the **exact same behavioral flow** and differ only in boundary inputs and expected outputs (such as pricing tiers, tax rules, validation boundaries, or permission matrices).

Group `Examples:` into named tables to explain *why* each group of rows exists:

```gherkin
Scenario Outline: Calculating shipping cost by order weight and destination zone
  Given a standard parcel weighing <weight_kg> kg
  When shipping is calculated for destination "<zone>"
  Then the shipping fee should be <fee>

  Examples: Domestic Tier Boundaries
    | weight_kg | zone     | fee    |
    | 0.5       | Domestic | $5.00  |
    | 2.0       | Domestic | $5.00  |
    | 2.1       | Domestic | $9.50  |

  Examples: International Surcharge
    | weight_kg | zone          | fee    |
    | 1.0       | International | $24.00 |
    | 5.0       | International | $48.00 |
```

**Anti-pattern**: Do not cram 30 unrelated combinations into one `Examples:` table just to inflate test counts. Pick representative boundary values (equivalence partitioning).

---

## 6. Common Gherkin Anti-Patterns

| Anti-Pattern | Symptom | Fix |
| :--- | :--- | :--- |
| **The Ping-Pong Scenario** | `Given ... When ... Then ... When ... Then ... When ... Then` | Split into separate, independent scenarios testing one behavior each; move prior steps into `Given` preconditions. |
| **Incidental Detail Noise** | Specifying first name, last name, phone, zip code, avatar URL when testing password reset | Specify *only* the attributes that affect the outcome (`Given a registered user "alice@example.com"`). Let the Test Data Builder supply sensible defaults for the rest. |
| **Conjectural `Then`** | `Then the user should be able to edit the post` | Assert an actual observable state (`Then the post is marked editable by Alice` or perform the edit in a dedicated scenario). |
| **Database-Speak** | `Given a row in the "usr_acct_tbl" with status_cd = 2` | Translate into Ubiquitous Language: `Given a suspended customer account`. |
| **Mystery Guest** | `Given user "test_user_4" logs in` (relying on pre-seeded global DB state without stating what makes `test_user_4` special) | State the relevant trait explicitly: `Given a customer whose subscription expired yesterday`. |

---

## 7. Authoring Checklist

- [ ] Does the scenario title summarize the **context and expected outcome** (not just `"Test checkout"`)?
- [ ] Could a non-technical domain expert read the `.feature` file and confirm whether the business rule is right?
- [ ] Are all `Given` steps purely setting state, `When` triggering a single action, and `Then` asserting observable results?
- [ ] Have all incidental details (unrelated fields, UI selectors, HTTP headers) been pushed down into step definitions and builders?
- [ ] Is each scenario completely independent so the suite can run in any order or in parallel?
