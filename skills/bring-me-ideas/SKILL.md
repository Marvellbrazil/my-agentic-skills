---
name: bring-me-ideas
description: Researches a codebase and proposes ranked next-feature ideas, each answered in full 5W+1H form (what problem, who benefits, when it matters, where it lives in the code, why this approach, how it works) with evidence from the actual project. Use when the user types /bring-me-ideas, asks "what should we build next", wants feature suggestions, a roadmap, or product ideas grounded in the existing code. Read-only; proposes, never implements.
allowed-tools: Read Grep Glob Bash
---

# Bring Me Ideas

Propose the next features this project should build, and justify each one with evidence from the code itself.

## What Makes This Not a Brainstorm

Anyone can list plausible features. "Add dark mode. Add search. Add notifications." That output is worthless because it is not grounded in the project — it would be identical for any codebase in the same category.

Four things make these ideas usable:

1. **Evidence.** Each idea cites what in the codebase justifies it — a half-built feature, a TODO, a gap between two modules, a pattern that exists in one place and not another, an error path with no handling.
2. **Ranking.** The ideas are ordered, with the ranking criteria stated. A flat list of twelve ideas is a way of refusing to make a decision.
3. **Full 5W+1H.** Every idea answers all six questions. An idea missing "who" or "why this approach" is a wish, not a proposal.
4. **Honesty about cost.** Each idea states its rough size and what it would put at risk. Ideas presented without cost get chosen blindly.

## The Contract

- **Read-only.** Propose. Do not implement, do not scaffold, do not open branches.
- **Evidence or omit.** If you cannot point at the code that justifies an idea, it is a generic suggestion — drop it.
- **Say what you do not know.** Product context, business goals, and user research are usually invisible in the code. Flag where an idea depends on information you do not have.
- **Do not pad.** Five grounded ideas beat twenty generic ones. If only four are defensible, give four.

## Phase 1 — Understand the Product

An idea is only good relative to what the project is and who it serves.

```bash
ls -a
cat README.md 2>/dev/null | head -80
```

```bash
cat package.json pyproject.toml composer.json go.mod 2>/dev/null | head -80
```

Establish:

| Question               | Source                                               |
| ---------------------- | ---------------------------------------------------- |
| What is this product?  | `README.md`, marketing copy in the app               |
| Who uses it?           | Routes, UI copy, role/permission models, seed data   |
| What is the core loop? | The main flow the app exists to serve                |
| How mature is it?      | Test coverage, CI, number of TODO/FIXME, open issues |
| What is the domain?    | Schema, entity names, business rules                 |

Also check whether a roadmap already exists — do not propose what is already planned.

```bash
find . -maxdepth 3 -iname 'ROADMAP*' -o -iname 'TODO*' -o -iname 'CHANGELOG*' \
  -o -iname '*.md' -path '*docs*' 2>/dev/null | head -20
git log --oneline -30
```

## Phase 2 — Mine the Codebase for Signals

This is the step that separates this skill from a plain prompt. Each signal is a class of evidence that points at a real gap.

| Signal                   | Command                                                                                   | What it reveals                                    |
| ------------------------ | ----------------------------------------------------------------------------------------- | -------------------------------------------------- |
| **Unfinished work**      | `grep -rn "TODO\|FIXME\|HACK\|XXX" --include='*.ts' --include='*.py' .`                   | The authors already knew; the idea is half-decided |
| **Stubbed code**         | `grep -rn "not implemented\|NotImplementedError\|throw new Error('TODO\|unimplemented" .` | A path that exists but does nothing                |
| **One-off patterns**     | Find a capability implemented once and never generalized                                  | The abstraction that should exist                  |
| **Missing counterparts** | An entity with create but no delete; a list with no search; a write with no audit         | The obvious sibling feature                        |
| **Error paths**          | `catch` blocks that only log; empty states; 500s                                          | Resilience and UX gaps                             |
| **Asymmetries**          | One module has tests/validation/caching, a peer does not                                  | Consistency debt                                   |
| **Dependency hints**     | Libraries installed but barely used                                                       | Capability already paid for, not yet exploited     |
| **Scale risks**          | Unbounded queries, missing pagination, N+1 patterns                                       | A feature that becomes necessary at volume         |
| **Config gaps**          | Hardcoded values that should be settings                                                  | Operational flexibility                            |
| **Access gaps**          | Missing roles, missing permissions, no audit log                                          | Compliance and safety features                     |

Run the high-signal ones:

```bash
grep -rn "TODO\|FIXME\|HACK" --include='*.ts' --include='*.tsx' --include='*.py' \
  --include='*.php' --include='*.rb' --include='*.go' \
  . 2>/dev/null | grep -v node_modules | head -40
```

```bash
grep -rn "catch\|except\|rescue" --include='*.ts' --include='*.py' --include='*.rb' \
  . 2>/dev/null | grep -iE "console\.log|print|logger\.|# ?pass|=> \{\}" | head -25
```

```bash
git log --format='%s' -60 | sed 's/(.*//' | sed 's/:.*//' | sort | uniq -c | sort -rn
```

Also read the issues if the project has a tracker, and the largest files — the largest files are usually where the next feature will be hardest.

```bash
wc -l $(git ls-files '*.ts' '*.tsx' '*.py' '*.php' 2>/dev/null | head -60) 2>/dev/null | sort -rn | head -12
```

## Phase 3 — Generate and Filter

Generate more candidates than you will present, then filter hard.

A candidate survives only if it passes all four gates:

1. **Evidence gate.** You can cite the file, line, or pattern that justifies it. No citation, no idea.
2. **Fit gate.** It serves the product's core loop or a user the project already has. Features for users who do not exist are speculation.
3. **Non-duplication gate.** It is not already implemented, already planned, or already in the issue tracker.
4. **Value gate.** You can state the concrete outcome — what becomes possible, or what stops hurting.

Kill on sight:

- Generic platform features unrelated to this product ("add i18n" to a single-locale internal tool).
- Anything requiring a business decision you have no information for ("add a paid tier").
- Rewrites dressed as features ("migrate to microservices").
- Ideas that only add surface area with no user-visible outcome.

## Phase 4 — Rank

Rank with stated criteria, not vibes. Use this table and score honestly.

| Criterion             | Weight | Question                                      |
| --------------------- | ------ | --------------------------------------------- |
| **Evidence strength** | High   | Is the gap visible in the code, or inferred?  |
| **User impact**       | High   | How much does it improve the core loop?       |
| **Effort**            | Medium | Days, not weeks? Or a multi-week project?     |
| **Risk**              | Medium | Does it touch auth, money, or data migration? |
| **Dependency**        | Low    | Does it unblock other ideas?                  |

Rank by **(evidence × impact) ÷ effort**, and break ties toward lower risk. Then present in rank order and say the criteria out loud so the user can re-rank with their own knowledge.

## Phase 5 — Write Each Idea in 5W+1H

Every idea gets all six. This is the deliverable's core, and it is where a generic suggestion becomes a proposal.

```markdown
### 1. <Idea title>

**What is the problem**
The concrete problem, grounded in the code. Cite the evidence.

**Who is the target**
Which user or role benefits. Name them from the project's own vocabulary — the roles in
the permission model, not "users" in the abstract.

**When is it useful**
The moment in the workflow where this matters. "When an admin onboards a new tenant and
must create 40 projects by hand."

**Where to implement**
The exact files and modules. Entry point, service layer, schema, UI surface.

**Why this solution**
Why this approach over the alternatives. Name at least one alternative and why it loses.

**How it works**
The mechanism, end to end, in a few steps. Enough that an engineer could estimate it.

---

**Evidence** `src/orders/service.ts:88` — bulk create exists, single create does not
**Effort** ~2 days
**Risk** Low — additive, no schema change
**Depends on** Nothing
```

### Worked example

```markdown
### 1. Bulk project import for tenant onboarding

**What is the problem**
Admins can create projects one at a time only. The onboarding flow
(`src/onboarding/wizard.tsx:44`) loops over a single-create call, so a 40-project
tenant takes 40 round trips and fails halfway with no recovery. The API already
exposes a bulk path for orders (`src/api/orders.ts:112`); projects have no equivalent.

**Who is the target**
Tenant administrators — the `admin` role in `src/auth/roles.ts:8`. They onboard
customers and are the only role with `project:create`.

**When is it useful**
During tenant onboarding, and during quarterly restructures when an org re-plans
its project hierarchy. Both are currently done by hand.

**Where to implement**

- `src/api/projects.ts` — add `POST /projects/bulk`, mirroring `orders.ts:112`
- `src/onboarding/wizard.tsx:44` — replace the loop with one call
- `src/db/schema.ts` — no change; reuse the existing `projects` table
- `tests/api/projects.test.ts` — new cases

**Why this solution**
A bulk endpoint rather than a client-side parallel loop. A parallel loop still
leaves partial state on failure and multiplies load; one transactional bulk call
is atomic and matches the existing orders precedent. The alternative — a background
job with a progress UI — is more correct at 10k rows but overbuilt for the observed
40-row case, and can be added later behind the same endpoint.

**How it works**

1. `POST /projects/bulk` accepts `{ tenantId, projects: [...] }`, validated by the
   existing Zod schema from `src/api/schemas.ts`.
2. The handler opens one transaction and inserts all rows via `db.insert(projects).values([...])`.
3. On any constraint violation the transaction rolls back and returns the offending
   index, so the wizard can highlight the bad row.
4. The wizard submits one request and shows a single success or failure.

---

**Evidence** `src/onboarding/wizard.tsx:44` (serial loop), `src/api/orders.ts:112` (bulk precedent)
**Effort** ~2 days
**Risk** Low — additive endpoint, no schema change
**Depends on** Nothing
```

## Output Shape

```markdown
# Next Feature Ideas — <project name>

<2-3 sentences on what the project is and what the core loop is, so the ranking has context.>

## How These Were Ranked

Evidence strength × user impact ÷ effort, ties broken toward lower risk.

## Ideas

### 1. <highest ranked>

<full 5W+1H>

### 2. <second>

<full 5W+1H>

...

## Considered and Rejected

| Idea      | Why rejected                                                          |
| --------- | --------------------------------------------------------------------- |
| Dark mode | No evidence of demand; the app has no theming layer and one user role |

## Open Questions

- <what you could not determine from the code that would change the ranking>
```

The **Considered and Rejected** section is not filler. It shows the user the search space was wider than the output, and it often contains the idea they actually want.

## Common Mistakes

| Mistake                                | Why It Breaks                                       | Correct Approach                                 |
| -------------------------------------- | --------------------------------------------------- | ------------------------------------------------ |
| Generic feature lists                  | Identical for any project in the category; no value | Cite code evidence for every idea                |
| No ranking                             | A flat list refuses to make a decision              | Rank with stated criteria                        |
| Missing 5W+1H fields                   | The idea is a wish, not a proposal                  | All six, every idea                              |
| "Users" as the target                  | Says nothing about who benefits                     | Name the project's real roles                    |
| No effort estimate                     | The user cannot sequence the work                   | Rough size, in days                              |
| Hiding risk                            | Auth, money, and migrations get chosen blind        | State what the idea puts at risk                 |
| Proposing what is already planned      | Wastes the user's attention                         | Read the roadmap, TODOs, and issue tracker first |
| Rewrites disguised as features         | "Migrate to microservices" is not a feature         | Only user-visible outcomes                       |
| Implementing instead of proposing      | Answers a different question                        | Read-only                                        |
| Padding to a round number              | Dilutes the good ideas                              | Four strong ideas beat twelve weak ones          |
| Ignoring the codebase's own vocabulary | The proposal does not read like it belongs          | Use the project's entity and role names          |
| No rejected section                    | Hides the search space                              | List what you considered and why it lost         |
| Claiming business knowledge you lack   | Confident proposals built on invented context       | Flag what depends on information you do not have |
