---
name: bring-me-ideas
description: Researches a codebase and proposes ranked feature improvement ideas (both enhancements to existing features and net-new features), each answered in full 5W+1H form (what problem, who benefits, when it matters, where it lives in the code, why this approach, how it works) with evidence from the actual project. Accepts [total_ideas] (e.g. `/bring-me-ideas 10` or `/bring-me-ideas berikan saya 10 ide untuk feature improvements`) to deliver the exact requested number of ideas. Read-only; proposes, never implements.
argument-hint: "[total_ideas]"
allowed-tools: Read Grep Glob Bash
---

# Bring Me Ideas

Propose the next feature improvements — both **enhancements to existing capabilities** and **net-new features** — that this project should build, and justify each one with evidence from the code itself.

## Arguments & Idea Count (`[total_ideas]`)

When invoked with arguments (`$ARGUMENTS`), parse both the **requested idea count (`[total_ideas]`)** and any **topic/focus constraint**:

1. **Extract `[total_ideas]`**:
   - Direct number: `/bring-me-ideas 10` → generate **10** ranked ideas.
   - Natural-language prompt with a number: `/bring-me-ideas berikan saya 10 ide untuk feature improvements` or `/bring-me-ideas give me 8 ideas for onboarding` → extract `total_ideas = 10` (or `8`) and honor the focus area (`feature improvements`, `onboarding`, etc.).
   - No number provided: default to **5** ranked ideas.
2. **Enhancements + New Features**:
   - Unless the user restricts the scope to only one type, include a balanced mix of:
     - **Enhancement**: Upgrades, extensions, workflow multipliers, UX/DX improvements, or missing capabilities on top of features that already exist in the codebase.
     - **New Feature**: Net-new product capabilities that solve an unaddressed problem in the project's domain and fit naturally into its architecture and core user loop.
3. **Deliver the Requested Count**:
   - Mine enough signals in Phase 2 to generate at least `1.5 × total_ideas` candidates so that after filtering in Phase 3, you deliver the full `total_ideas` requested by the user without resorting to generic filler.
   - Only if the repository is genuinely too small to support `total_ideas` evidence-backed proposals after exhaustive code mining, deliver all defensible ideas and explicitly state why the codebase ceiling was reached.

## What Makes This Not a Brainstorm

Anyone can list plausible features. "Add dark mode. Add search. Add notifications." That output is worthless because it is not grounded in the project — it would be identical for any codebase in the same category.

Four things make these ideas usable:

1. **Evidence.** Each idea cites what in the codebase justifies it — a half-built feature, a TODO, a gap between two modules, a pattern that exists in one place and not another, an error path with no handling, or a domain workflow that stops one step short of completion.
2. **Ranking.** The ideas are ordered `1..[total_ideas]`, with the ranking criteria stated. A flat unranked list is a way of refusing to make a decision.
3. **Full 5W+1H.** Every idea answers all six questions. An idea missing "who" or "why this approach" is a wish, not a proposal.
4. **Honesty about cost.** Each idea states its category (`Enhancement` or `New Feature`), rough size, and what it would put at risk. Ideas presented without cost get chosen blindly.

## The Contract

- **Read-only.** Propose. Do not implement, do not scaffold, do not open branches.
- **Honor `[total_ideas]`.** Deliver the exact count requested by the user (default: 5), ranked from highest leverage to lowest.
- **Evidence or omit.** Every enhancement or new feature must point at concrete files, schemas, routes, or patterns in the repository that anchor it.
- **Say what you do not know.** Product context, business goals, and user research are usually invisible in the code. Flag where an idea depends on information you do not have.

## Phase 1 — Understand the Product

An idea is only good relative to what the project is and who it serves.

```bash
ls -a
cat README.md 2>/dev/null | head -80
```

```bash
cat package.json pyproject.toml composer.json go.mod Cargo.toml 2>/dev/null | head -80
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

This is the step that separates this skill from a plain prompt. Scale your mining depth to `[total_ideas]` — if the user asks for 10+ ideas, inspect multiple modules, schemas, routes, and UI/CLI surfaces to uncover both **feature enhancements** and **new feature opportunities**.

| Signal                       | Command / Inspection                                                                      | What it reveals (Enhancement vs. New Feature)                      |
| ---------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| **Unfinished work**          | `grep -rn "TODO\|FIXME\|HACK\|XXX" --include='*.ts' --include='*.py' .`                   | **Enhancement / New Feature**: Authors already saw the need        |
| **Stubbed code**             | `grep -rn "not implemented\|NotImplementedError\|throw new Error('TODO\|unimplemented" .` | **New Feature**: A planned path that exists in structure only      |
| **One-off patterns**         | Find a capability implemented once and never generalized                                  | **Enhancement**: Generalize a proven power-feature across modules  |
| **Missing counterparts**     | An entity with create/read but no export, bulk action, clone, archive, or webhook         | **New Feature / Enhancement**: The high-value sibling capability   |
| **Workflow dead-ends**       | A user flow that produces data/state with no next action, notification, or automation     | **New Feature**: Closing the loop on an existing user journey      |
| **Data model underuse**      | Schema fields/relations stored in DB or config but barely surfaced in UI/API/CLI          | **New Feature**: Unlocking value from data already captured        |
| **Error & UX friction**      | `catch` blocks that only log; missing dry-run, preview, undo, or recovery paths           | **Enhancement**: Resilience, safety, and user confidence           |
| **Asymmetries**              | Module A has filtering/caching/batching/validation, peer Module B does not                | **Enhancement**: Bringing lagging modules up to parity             |
| **Dependency hints**         | Libraries installed in manifests but barely utilized                                      | **New Feature**: Capability already paid for, not yet exploited    |
| **Scale & operational gaps** | Unbounded queries, missing pagination, hardcoded policy values, no audit trail            | **Enhancement / New Feature**: Scale readiness and admin controls  |

Run the high-signal searches:

```bash
grep -rn "TODO\|FIXME\|HACK" --include='*.ts' --include='*.tsx' --include='*.py' \
  --include='*.php' --include='*.rb' --include='*.go' --include='*.md' \
  . 2>/dev/null | grep -v node_modules | head -40
```

```bash
grep -rn "catch\|except\|rescue" --include='*.ts' --include='*.py' --include='*.rb' \
  . 2>/dev/null | grep -iE "console\.log|print|logger\.|# ?pass|=> \{\}" | head -25
```

```bash
git log --format='%s' -60 | sed 's/(.*//' | sed 's/:.*//' | sort | uniq -c | sort -rn
```

Also read the issues if the project has a tracker, and the largest files — the largest files are usually where core workflows live and where enhancements or adjacent features have the highest leverage.

```bash
wc -l $(git ls-files '*.ts' '*.tsx' '*.py' '*.php' '*.go' '*.md' 2>/dev/null | head -60) 2>/dev/null | sort -rn | head -12
```

## Phase 3 — Generate and Filter

Generate at least `ceil(1.5 × total_ideas)` candidates across both **Enhancements** and **New Features**, then filter down to the strongest `[total_ideas]`.

A candidate survives only if it passes all four gates:

1. **Evidence gate.** You can cite the file, line, schema, or pattern that justifies it. No citation, no idea.
2. **Fit gate.** It serves the product's core loop or a user role the project already has, and matches any focus prompt in `$ARGUMENTS`.
3. **Non-duplication gate.** It is not already implemented, already planned in `ROADMAP.md`, or already tracked in open issues.
4. **Value gate.** You can state the concrete outcome — what becomes possible (New Feature) or what becomes faster/safer/more capable (Enhancement).

Kill on sight:

- Generic platform features unrelated to this product ("add i18n" to a single-locale internal tool).
- Anything requiring a business decision you have no information for ("add a paid tier").
- Pure architectural rewrites dressed as features ("migrate to microservices") with no user-visible capability gain.
- Ideas that only add surface area with no user-visible outcome.

## Phase 4 — Rank

Rank all `[total_ideas]` ideas with stated criteria, not vibes. Use this table and score honestly.

| Criterion             | Weight | Question                                      |
| --------------------- | ------ | --------------------------------------------- |
| **Evidence strength** | High   | Is the gap visible in the code, or inferred?  |
| **User impact**       | High   | How much does it improve the core loop?       |
| **Effort**            | Medium | Days, not weeks? Or a multi-week project?     |
| **Risk**              | Medium | Does it touch auth, money, or data migration? |
| **Dependency**        | Low    | Does it unblock other ideas?                  |

Rank by **(evidence × impact) ÷ effort**, and break ties toward lower risk. Then present in rank order (`1` through `[total_ideas]`) and state the criteria out loud so the user can re-rank with their own knowledge.

## Phase 5 — Write Each Idea in 5W+1H

Every idea from `1` to `[total_ideas]` gets all six questions answered plus metadata tags (`Category`, `Evidence`, `Effort`, `Risk`, `Depends on`).

```markdown
### 1. <Idea title> (`Enhancement` | `New Feature`)

**What is the problem**
The concrete problem or opportunity, grounded in the code. Cite the evidence.

**Who is the target**
Which user or role benefits. Name them from the project's own vocabulary — the roles in
the permission model, not "users" in the abstract.

**When is it useful**
The moment in the workflow where this matters. "When an admin onboards a new tenant and
must create 40 projects by hand."

**Where to implement**
The exact files and modules. Entry point, service layer, schema, UI/CLI surface.

**Why this solution**
Why this approach over the alternatives. Name at least one alternative and why it loses.

**How it works**
The mechanism, end to end, in a few steps. Enough that an engineer could estimate it.

---

**Category** Enhancement (or New Feature)
**Evidence** `src/orders/service.ts:88` — bulk create exists, single create does not
**Effort** ~2 days
**Risk** Low — additive, no schema change
**Depends on** Nothing
```

### Worked example

```markdown
### 1. Bulk project import for tenant onboarding (`Enhancement`)

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

**Category** Enhancement
**Evidence** `src/onboarding/wizard.tsx:44` (serial loop), `src/api/orders.ts:112` (bulk precedent)
**Effort** ~2 days
**Risk** Low — additive endpoint, no schema change
**Depends on** Nothing
```

## Output Shape

```markdown
# Feature Improvement Ideas (<total_ideas>) — <project name>

<2-3 sentences on what the project is, what the core loop is, and the requested focus/count so the ranking has context.>

## Summary Table

| Rank | Idea | Category | Effort | Risk | Primary Evidence |
| ---- | ---- | -------- | ------ | ---- | ---------------- |
| 1 | <Idea 1 title> | Enhancement | ~2d | Low | `path/to/file:line` |
| 2 | <Idea 2 title> | New Feature | ~3d | Medium | `path/to/file:line` |
| ... | ... | ... | ... | ... | ... |
| <total_ideas> | <Idea N title> | Enhancement | ~1d | Low | `path/to/file:line` |

## How These Were Ranked

Evidence strength × user impact ÷ effort, ties broken toward lower risk.

## Ideas

### 1. <highest ranked> (`Enhancement` | `New Feature`)

<full 5W+1H>

### 2. <second> (`Enhancement` | `New Feature`)

<full 5W+1H>

... (up to `<total_ideas>`)

## Considered and Rejected

| Idea      | Why rejected                                                          |
| --------- | --------------------------------------------------------------------- |
| Dark mode | No evidence of demand; the app has no theming layer and one user role |

## Open Questions

- <what you could not determine from the code that would change the ranking>
```

The **Considered and Rejected** section is not filler. It shows the user the search space was wider than the output, and it often contains the idea they actually want.

## Common Mistakes

| Mistake                                    | Why It Breaks                                         | Correct Approach                                                      |
| ------------------------------------------ | ----------------------------------------------------- | --------------------------------------------------------------------- |
| Ignoring `[total_ideas]` in `$ARGUMENTS`   | User asked for 10 ideas and got 4, or vice versa      | Parse `[total_ideas]` from arguments (e.g., `10`) and deliver all 10  |
| Only proposing tiny tweaks or only new big features | Misses half the opportunity space            | Balance **Enhancements** (existing features) and **New Features**     |
| Generic feature lists                      | Identical for any project in the category; no value   | Cite code evidence for every idea                                     |
| No ranking                                 | A flat list refuses to make a decision                | Rank with stated criteria and include the Summary Table               |
| Missing 5W+1H fields                       | The idea is a wish, not a proposal                    | All six questions answered for every single idea                      |
| "Users" as the target                      | Says nothing about who benefits                       | Name the project's real roles                                         |
| No effort estimate                         | The user cannot sequence the work                     | Rough size, in days                                                   |
| Hiding risk                                | Auth, money, and migrations get chosen blind          | State what the idea puts at risk                                      |
| Proposing what is already planned          | Wastes the user's attention                           | Read the roadmap, TODOs, and issue tracker first                      |
| Rewrites disguised as features             | "Migrate to microservices" is not a feature           | Only user-visible or developer-workflow outcomes                      |
| Implementing instead of proposing          | Answers a different question                          | Read-only                                                             |
| Ignoring the codebase's own vocabulary     | The proposal does not read like it belongs            | Use the project's entity and role names                               |
| No rejected section                        | Hides the search space                                | List what you considered and why it lost                              |
| Claiming business knowledge you lack       | Confident proposals built on invented context         | Flag what depends on information you do not have                      |
