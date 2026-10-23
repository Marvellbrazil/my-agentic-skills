---
name: todolist
description: Manages bidirectional, persistent daily planning and task tracking between human user and AI agent using an ephemeral root file `TODOLIST.md`. Enforces hyper-detailed, atomic task decomposition so instructions are unambiguous, self-contained, and verifiable. Prevents losing track, scope drift, and rabbit-hole traps during complex coding sessions, tracks real-time progress, and automatically deletes `TODOLIST.md` once all tasks are completed. Use whenever the user shares a plan for the day, lists tasks to accomplish, asks to "create a todolist", "track my todos", "check todo", "update todolist", "add to todolist", "show todos", or when starting multi-task work to stay on track.
allowed-tools: Bash Read Grep Glob Edit Write
---

# To-do List for Agents (TODOLIST.md)

Keep developers and AI agents aligned, focused, and immune to rabbit-hole traps through an ephemeral, shared, and **atomic** `TODOLIST.md` file located at the repository root.

---

## Why This Exists

During engineering sessions, three common failure patterns derail progress:
1. **The Vague Task Trap**: High-level todos like *"Implement authentication"* or *"Fix checkout bug"* hide 10 unspoken sub-decisions. When an agent or developer starts executing a vague item, they have to figure out architecture, file paths, and verification on the fly — leading to half-baked implementations or stalls.
2. **The Rabbit-Hole Trap**: While working on Task A, an obscure error or tempting refactor appears. The session spirals into micro-optimizations, the remaining plan is forgotten, and work stops prematurely with Tasks B and C abandoned.
3. **The Invisible State Problem**: AI agents have internal memory and scratchpads, but these are opaque to the human developer in their IDE. The developer cannot see the plan, cannot adjust granularity or priority, and cannot tell if the agent has drifted off-course.

`TODOLIST.md` solves all three problems:
- **Atomic & Self-Contained**: Every task is broken down into small, unambiguous, independently verifiable units specifying exact target files, concrete changes, and verification commands.
- **Shared & Accessible**: Lives right in the project root where the developer can inspect, edit, or reorder tasks in their own editor.
- **Anchor Against Drift**: After every completed atomic step, the agent re-anchors itself to `TODOLIST.md` before picking the next task.
- **Clean Ephemerality**: The file exists *only* while tasks are active. The moment all tasks are completed and verified, `TODOLIST.md` is automatically deleted, leaving zero clutter in the git tree.

---

## Atomicity & Detail Standard (Mandatory)

Never write vague, coarse-grained tasks. Before writing `TODOLIST.md`, briefly inspect the relevant files so every task item carries concrete, actionable instructions.

### The 4 Rules of Atomic Tasks
1. **One Concern Per Item**: Each checkbox (`- [ ] **#1.1**`) must represent a single, cohesive change (e.g., one schema migration, one function/endpoint implementation, one component state wiring, or one test suite addition) that can be completed and verified in a single focused turn.
2. **Explicit Target Locations**: Name the exact file path(s), function/class symbols, or routes to create or modify (e.g., `src/auth/session.ts -> revokeSession()`, not *"in the auth module"*).
3. **Concrete Implementation Instructions**: State *what* must change and *how* — input/output shapes, validation rules, error handling, edge cases, and invariants. Another engineer or fresh agent reading `TODOLIST.md` cold must be able to execute the item without guessing.
4. **Executable Verification ("Done When")**: Every atomic task must specify how to prove it works (e.g., a specific test command, typecheck, CLI invocation, or expected response).

### Bad (Vague) vs. Good (Atomic & Detailed)

| Bad (Coarse & Ambiguous) | Good (Atomic, Detailed & Verifiable) |
| :--- | :--- |
| `- [ ] **#1** Add rate limiting to API` | `- [ ] **#1.1** Create sliding-window rate limiter middleware in \`src/middleware/rate-limit.ts\` using Redis key \`rl:{ip}:{route}\`, limiting to 60 req/min and returning HTTP 429 with \`Retry-After\` header.`<br>`- [ ] **#1.2** Wire \`rateLimitMiddleware\` into public auth routes (\`POST /api/auth/login\`, \`POST /api/auth/register\`) in \`src/routes/auth.ts\`.`<br>`- [ ] **#1.3** Add integration tests in \`tests/middleware/rate-limit.test.ts\` covering under-limit (200), at-limit boundary, and over-limit (429 + header) cases.` |
| `- [ ] **#2** Fix pagination bug` | `- [ ] **#2.1** Clamp \`limit\` parameter in \`src/orders/repository.ts -> listOrders()\` to \`Math.min(Math.max(1, limit ?? 20), 100)\` and fix off-by-one cursor offset when \`cursorId\` is passed.`<br>`- [ ] **#2.2** Add regression test in \`tests/orders/repository.test.ts\` verifying \`limit=0\`, \`limit=500\`, and sequential cursor pages return non-overlapping items.` |

---

## The Lifecycle Contract

```text
User states plans / tasks
          │
          ▼
   Quick reconnaissance (identify files & scope)
          │
          ▼
   Decompose into atomic steps & create TODOLIST.md ◄──────┐
          │                                                │
          ▼                                                │
   Execute Atomic Task #1.1                                │
          │                                                │
          ▼                                                │
   Verify Task #1.1 & mark [x] in TODOLIST.md              │
          │                                                │
          ▼                                                │
   Are all tasks [x] complete?                             │
     ├── NO  ──► Focus on next pending atomic task         │
     └── YES ──► Delete TODOLIST.md cleanly                │
                         │                                 │
                         ▼                                 │
                  Clean Workspace                          │
                         │                                 │
                         └──── New tasks later? ───────────┘
```

### Core Rules
1. **Always in Repository Root**: The file must be named `TODOLIST.md` and located in the workspace root.
2. **Two-Way Synchronization**:
   - The agent updates `TODOLIST.md` as tasks transition (`[ ]` pending -> `[/]` in progress -> `[x]` done).
   - If the user modifies `TODOLIST.md` in their editor, the agent respects the user's edits as the source of truth.
3. **One Active Atomic Task at a Time**: Mark the currently active atomic item with `[/]` and state it in the `Current Focus` section. Never multitask across multiple items simultaneously.
4. **Verify Before Checking Off**: Never mark a task `[x]` until its `Verify` step has actually been executed and passed.
5. **Auto-Deletion on Completion**: When the last remaining task is marked `[x]` and verified, the agent **must delete `TODOLIST.md`**.
6. **Fresh Re-creation**: If new tasks are introduced in a subsequent session or turn, create a fresh `TODOLIST.md`.

---

## TODOLIST.md Template Format

When creating `TODOLIST.md`, decompose the user's request into logical parent groups (`### #1 ...`) containing atomic, detailed sub-tasks (`- [ ] **#1.1** ...`):

```markdown
# Session To-Do List

> **Goal**: [Clear 1-sentence summary of the session's objective and end state]  
> **Status**: Active ([X]/[Y] Atomic Tasks Completed)  
> **Created**: YYYY-MM-DD  

---

## Tasks

### #1 [Milestone / Feature Area 1 Title]
- [ ] **#1.1** **[Short Action Title]**
  - **Files**: `path/to/file.ts` (`symbolOrFunctionName`)
  - **Action**: [Specific, unambiguous instructions: exact inputs/outputs, logic changes, validation rules, and edge cases to handle]
  - **Verify**: [Exact command or check to prove completion, e.g., `npm test -- path/to/file.test.ts`]
- [ ] **#1.2** **[Short Action Title]**
  - **Files**: `path/to/other.ts`, `tests/path/to/other.test.ts`
  - **Action**: [Specific implementation and test cases to add]
  - **Verify**: [Exact verification command and expected outcome]

### #2 [Milestone / Feature Area 2 Title]
- [ ] **#2.1** **[Short Action Title]**
  - **Files**: `path/to/module.py`
  - **Action**: [Specific instructions]
  - **Verify**: [Exact verification command]

---

## Current Focus
- **Active Task**: **#1.1** — [Short Action Title]
- **Target Files**: `path/to/file.ts`
- **Done Criteria**: [What exact test or check proves this atomic step is finished]

---

## Completed
*(Completed atomic tasks are logged here with verification evidence)*

---

<!-- AUTOMATIC CLEANUP CONTRACT:
This file is temporary. When all atomic tasks above are checked [x], the agent will automatically delete TODOLIST.md.
-->
```

---

## Operational Commands

### 1. Initialize or Intake (`/todolist init` or `/todolist <tasks>`)
1. Read the user prompt for task descriptions, milestones, or plans.
2. Perform a fast, read-only scan (`Glob`/`Grep`/`Read`) of the affected codebase areas so you can name real file paths, symbols, and test commands instead of placeholders.
3. Decompose high-level requests into atomic sub-tasks (`#1.1`, `#1.2`, `#2.1`, ...) following the **Atomicity & Detail Standard**.
4. Create `TODOLIST.md` at the repository root using the standard template.
5. Output a concise summary confirming the atomic task count and immediately begin **#1.1** (or wait for confirmation if the user only asked to plan).

### 2. Update Progress (`/todolist progress` or inline execution)
As each atomic task is worked on and completed:
1. Before starting an item, mark it `- [/]` and set it under `## Current Focus`.
2. Execute the code/test changes described in `Action` and run the `Verify` check.
3. Re-read `TODOLIST.md` to ensure no user edits are overwritten.
4. Update the completed task checkbox from `- [/]` to `- [x]`.
5. Append a concise completion record under `## Completed` with verification proof (e.g., `- [x] **#1.1** Add sliding-window rate limiter — verified via vitest (4/4 passing)`).
6. Update `## Current Focus` to point to the next pending atomic item.
7. Check if all items are complete.

### 3. Check for Full Completion & Automatic Deletion
When updating `TODOLIST.md`:
1. Scan all checkboxes under `## Tasks`.
2. If any unchecked `- [ ]` or in-progress `- [/]` item remains: keep `TODOLIST.md`, inform the user of progress, and proceed to the next atomic item.
3. If **100% of atomic tasks are marked `- [x]`**:
   - Inform the user that all planned items are complete and verified.
   - Delete `TODOLIST.md` (`rm TODOLIST.md` or file removal tool).
   - Announce: `All todos completed and verified. TODOLIST.md has been removed.`

### 4. Append or Split Tasks (`/todolist add <task>`)
- If a new requirement emerges, decompose it into atomic steps (`Files`, `Action`, `Verify`) and append to `## Tasks`.
- If an existing task turns out to be larger than expected during execution, **split it in place** into `#N.1`, `#N.2`, `#N.3` in `TODOLIST.md` before continuing, and update the total count in `Status`.

### 5. Inspect / Status (`/todolist status`)
1. Read `TODOLIST.md`.
2. Report:
   - Completed atomic tasks: `X/Y`
   - Current active task and its verification target
   - Next queued atomic tasks

---

## Agent Behavioral Discipline

- **Decompose before executing**: If the user gives a broad goal ("build feature X and fix bug Y"), never copy-paste those two lines as two giant checkboxes. Break them down into 4–10 crisp, atomic steps with real file paths and verification commands first.
- **Never ignore the list**: When you finish an atomic step, do not ask "What should I do next?" without checking `TODOLIST.md` first. Read `TODOLIST.md`, pick the next pending atomic item, mark it `[/]`, and continue.
- **Resist Scope Creep**: If you notice an unrelated bug or tempting cleanup during an atomic task:
  - Do NOT derail the current atomic task.
  - Either log it as a new pending atomic task at the end of `TODOLIST.md` (if in scope) or ask the user whether to add it.
- **Preserve User Edits**: The user may open `TODOLIST.md` in their IDE to tweak instructions, reorder tasks, or add notes. Always read `TODOLIST.md` immediately before writing to merge state cleanly.
