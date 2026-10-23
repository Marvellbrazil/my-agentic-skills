# Decoupling & Safe Refactoring Patterns Reference

When you encounter a 1,500-line "God Service", a 900-line React/Vue component with 18 `useState` / `useEffect` hooks, or functions taking 12 boolean flags, you need surgical decoupling techniques that reduce complexity **without breaking existing callers**.

This reference catalogs the **Coupling Spectrum**, **Dependency Inversion**, **UI Component Decomposition**, and the **Step-by-Step Choreography for Splitting Monolithic Files Safely**.

---

## Contents

- [1. The Coupling Spectrum (From Worst to Best)](#1-the-coupling-spectrum-from-worst-to-best)
- [2. Dependency Inversion & Constructor/Parameter Injection](#2-dependency-inversion--constructorparameter-injection)
- [3. Decoupling Cross-Cutting Side Effects (Events & Pipelines)](#3-decoupling-cross-cutting-side-effects-events--pipelines)
- [4. Decomposing Bloated Frontend Components](#4-decomposing-bloated-frontend-components)
- [5. Step-by-Step Choreography: Splitting a "God File" Safely](#5-step-by-step-choreography-splitting-a-god-file-safely)
- [6. Common Modularization Anti-Patterns](#6-common-modularization-anti-patterns)

---

## 1. The Coupling Spectrum (From Worst to Best)

When refactoring tightly coupled modules, identify the *kind* of coupling present and move it down the table toward **Data / Message Coupling**:

| Coupling Type | Severity | Symptom | How to Decouple |
| :--- | :--- | :--- | :--- |
| **1. Content / Pathological Coupling** | 🔴 Worst | Module A reaches directly into Module B's private state, mutates B's internal array, or queries B's database table directly. | Encapsulate B's state behind private fields and expose a domain method on B (`b.reserveStock(qty)`). |
| **2. Common / Global Coupling** | 🔴 Severe | Multiple modules read and mutate shared global variables, singletons, or unvalidated `process.env` keys scattered everywhere. | Pass explicit configuration objects or inject dependencies at the composition root. |
| **3. Control Coupling** | 🟠 High | Caller passes a control flag (`processOrder(order, isExpress, skipEmail, isRetry)`) that tells the callee *how* to branch internally. | Split into focused functions (`processStandardOrder`, `processExpressOrder`) or inject a Strategy/Policy. |
| **4. Stamp (Data-Structure) Coupling** | 🟡 Moderate | A function only needs `userId` and `email`, but accepts the entire 40-field `Request` or `ORMUserRecord` object. | Narrow the parameter type to only the fields required (`{ id: string; email: string }`). This makes the function reusable from CLI, jobs, and tests without faking an HTTP `Request`. |
| **5. Data / Message Coupling** | 🟢 Ideal | Modules communicate solely by passing small, immutable primitive/value parameters or typed event messages through a narrow interface. | Maintain this state. |

---

## 2. Dependency Inversion & Constructor/Parameter Injection

High-level policy modules must **never** instantiate low-level infrastructure clients directly (`new Stripe(...)`, `new PrismaClient()`, `axios.post(...)`).

### Before: Hardcoded Infrastructure Coupling
```typescript
// ❌ TIGHTLY COUPLED: Cannot test InvoiceService without a live PostgreSQL DB, Stripe API key, and SMTP server
import { prisma } from '../../db/prisma.js';
import { stripe } from '../../lib/stripe.js';
import { sendgrid } from '../../lib/sendgrid.js';

export class InvoiceService {
  async payInvoice(invoiceId: string) {
    const invoice = await prisma.invoice.findUniqueOrThrow({ where: { id: invoiceId } });
    if (invoice.status === 'PAID') throw new Error('Already paid');

    await stripe.charges.create({ amount: invoice.amountCents, currency: 'usd', customer: invoice.stripeCustId });
    await prisma.invoice.update({ where: { id: invoiceId }, data: { status: 'PAID', paidAt: new Date() } });
    await sendgrid.send({ to: invoice.email, subject: 'Receipt', text: `Paid ${invoice.amountCents}` });
  }
}
```

### After: Decoupled via Narrow Ports & Dependency Injection
```typescript
// ✅ DECOUPLED: InvoiceService depends only on narrow domain ports; 100% testable in 2ms with Fakes
export interface InvoiceRepository {
  findById(id: string): Promise<Invoice | null>;
  save(invoice: Invoice): Promise<void>;
}

export interface PaymentCharger {
  chargeCustomer(customerId: string, amountCents: number): Promise<{ receiptId: string }>;
}

export interface ReceiptNotifier {
  sendPaymentReceipt(email: string, invoiceId: string, amountCents: number): Promise<void>;
}

export class InvoicePaymentService {
  constructor(
    private readonly invoices: InvoiceRepository,
    private readonly charger: PaymentCharger,
    private readonly notifier: ReceiptNotifier,
    private readonly clock: () => Date = () => new Date()
  ) {}

  async payInvoice(invoiceId: string): Promise<Invoice> {
    const invoice = await this.invoices.findById(invoiceId);
    if (!invoice) throw new InvoiceNotFoundError(invoiceId);

    // Pure domain state transition enforces invariants
    invoice.assertPayable();
    await this.charger.chargeCustomer(invoice.customerId, invoice.amountCents);
    const paidInvoice = invoice.markPaid(this.clock());

    await this.invoices.save(paidInvoice);
    await this.notifier.sendPaymentReceipt(paidInvoice.customerEmail, paidInvoice.id, paidInvoice.amountCents);
    return paidInvoice;
  }
}
```

---

## 3. Decoupling Cross-Cutting Side Effects (Events & Pipelines)

A common reason a function grows to 400 lines is **Side-Effect Accretion**:
`registerUser()` starts at 20 lines. Over a year, developers append:
1. Create default workspace
2. Send welcome email
3. Sync contact to HubSpot CRM
4. Post notification to Slack `#signups`
5. Record analytics event in PostHog
6. Grant referral bonus credits

Now `AuthService.registerUser()` imports 6 unrelated modules (`WorkspaceService`, `Mailer`, `HubSpotClient`, `SlackWebhook`, `Analytics`, `ReferralService`), and a HubSpot outage breaks user registration!

### Fix: Decouple Secondary Side Effects with Domain Events

```typescript
// AuthService stays focused on its Single Responsibility: registering the user and emitting a fact
export class UserRegistrationService {
  constructor(
    private readonly users: UserRepository,
    private readonly passwordHasher: PasswordHasher,
    private readonly events: DomainEventBus
  ) {}

  async register(input: RegisterUserInput): Promise<User> {
    const hashed = await this.passwordHasher.hash(input.password);
    const user = User.create({ email: input.email, passwordHash: hashed });
    await this.users.save(user);

    // Emit the fact; zero knowledge of HubSpot, Slack, or Referral credits
    await this.events.publish(new UserRegisteredEvent({ userId: user.id, email: user.email, referralCode: input.referralCode }));
    return user;
  }
}
```

Each downstream module (`crm/`, `notifications/`, `referrals/`) registers its own independent subscriber to `UserRegisteredEvent`. Adding or removing a 7th integration never touches `UserRegistrationService` (**Open-Closed Principle**).

---

## 4. Decomposing Bloated Frontend Components

When a React/Vue/Svelte component crosses 300–800 lines, it is almost always mixing **4 distinct concerns** in one file:
1. **Pure Data Formatting / Derived State Calculations** (filtering, sorting, price math, status badge mapping)
2. **Server State / API Fetching & Mutation Wiring** (`fetch`, React Query, form submission handlers)
3. **Interactive UI State Machine** (modal open/close, multi-step wizard step, selection state)
4. **Presentational Sub-sections** (Header, FilterBar, DataTable, EmptyState, ConfirmationDialog)

### The 4-Part Component Decomposition Pattern

```text
features/invoice-list/
├── model/
│   └── invoice-filters.ts        # 1. Pure functions: filterInvoices(), computeSummaryTotals() (Zero React!)
├── api/
│   └── use-invoices-query.ts     # 2. Data fetching & mutation hooks
├── hooks/
│   └── use-invoice-selection.ts  # 3. Focused custom hook for bulk selection state
├── components/
│   ├── InvoiceSummaryHeader.tsx  # 4a. Presentational sub-component (props in, callbacks out)
│   ├── InvoiceFilterBar.tsx      # 4b. Presentational filter controls
│   └── InvoiceTable.tsx          # 4c. Presentational table
└── InvoiceDashboard.tsx          # Thin Container (~60 lines) composing hooks + sub-components
```

---

## 5. Step-by-Step Choreography: Splitting a "God File" Safely

Never delete a 1,500-line file and try to rewrite 8 new files from scratch in one giant step. Follow this **5-Step Strangler Choreography** so the codebase stays buildable after every move:

```text
Step 1: Pin Behavior with Tests
  Ensure existing unit/integration tests pass (add characterization tests if missing).
        │
        ▼
Step 2: Extract Leaf Types, Constants & Pure Helpers First
  Move interfaces, schemas, and zero-dependency pure functions into dedicated files.
  Re-export them from the original file if external callers import them from there.
        │
        ▼
Step 3: Extract Infrastructure / I/O Adapters
  Move raw SQL queries, HTTP/SDK calls, and file I/O into focused repository/client files.
        │
        ▼
Step 4: Split Cohesive Domain/Use-Case Services or Sub-Components
  Group remaining methods by cohesion (which methods share the same state/dependencies?).
  Extract each cohesive cluster into its own module.
        │
        ▼
Step 5: Update Call Sites & Remove Facade Shims
  Update callers to import from the new focused modules (or keep a clean index.ts facade),
  then run typecheck + linter + full test suite.
```

### How to Find Cohesion Clusters Inside a God Class
Create a quick mental matrix of **Methods × Fields/Dependencies Used**:
- If methods `A()`, `B()`, and `C()` only touch `pdfRenderer` and `templateStore`, while methods `D()`, `E()`, and `F()` only touch `taxRateTable` and `currencyConverter`, that single class is actually **two separate classes** (`InvoicePdfGenerator` and `InvoiceTaxCalculator`) masquerading as one!

---

## 6. Common Modularization Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
| :--- | :--- | :--- |
| **Shotgun Surgery Split** | Splitting one 200-line cohesive algorithm into 8 tiny files that all mutate the same shared state object. | Keep cohesive logic that changes for the *same reason* together; split along **different reasons to change** (Pure Logic vs. I/O vs. Transport). |
| **Circular Split (`A ↔ B`)** | Moving half of `monolith.ts` into `part-b.ts` while `monolith.ts` imports `part-b.ts` and `part-b.ts` imports `monolith.ts`. | Extract shared types/utilities into a third leaf file `types.ts` (`A → types ← B`) so imports remain strictly one-way. |
| **Leaky Abstraction Extraction** | Extracting a `DatabaseHelper` module whose methods return raw ORM cursors or require SQL fragments from callers. | Design the extracted module around a **domain concept** (`OrderArchiveRepository.archiveOlderThan(date)`), hiding the SQL details inside. |
| **Breaking Public Imports Mid-Refactor** | Moving exported functions to new file paths without updating all callers and test files. | Always grep for every caller (`grep -rn`) before and after moving a symbol, update every import path, and verify with the compiler and test suite. |
