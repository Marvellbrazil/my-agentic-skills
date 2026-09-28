---
name: todolist
description: Manages bidirectional, persistent daily planning and task tracking between human user and AI agent using an ephemeral root file `TODOLIST.md`. Prevents losing track, scope drift, and rabbit-hole traps during complex coding sessions. Keeps the plan visible and accessible to both user and agent in the repository, tracks real-time progress, and automatically deletes `TODOLIST.md` once all tasks are completed. Use whenever the user shares a plan for the day, lists tasks to accomplish, asks to "create a todolist", "track my todos", "check todo", "update todolist", "add to todolist", "show todos", or when starting multi-task work to stay on track.
allowed-tools: Bash Read Grep Glob Edit Write
---

# To-do List for Agents (TODOLIST.md)

Keep developers and AI agents aligned, focused, and immune to rabbit-hole traps through an ephemeral, shared `TODOLIST.md` file located at the repository root.

---

## Why This Exists

During engineering sessions, two common failure patterns derail progress:
1. **The Rabbit-Hole Trap**: A developer or agent starts with a clear plan (e.g. "implement feature A, fix bug B, write test C"). While working on A, an obscure error or tempting refactor appears. The session spirals into micro-optimizations, the developer forgets the remaining plan, and work stops prematurely with B and C abandoned.
2. **The Invisible State Problem**: AI agents have internal memory and scratchpads, but these are completely opaque to the human developer sitting in their IDE. The developer cannot see the plan, cannot easily adjust priorities, and cannot tell if the agent has drifted off-course.

`TODOLIST.md` solves both problems:
- **Shared & Accessible**: Lives right in the project root where the developer can inspect, edit, or reorder tasks in their own editor.
- **Anchor Against Drift**: After every completed step, the agent re-anchors itself to `TODOLIST.md` before picking the next task.
- **Clean Ephemerality**: The file exists *only* while tasks are active. The moment all tasks are completed and verified, `TODOLIST.md` is automatically deleted, leaving zero clutter in the git tree.

---

## The Lifecycle Contract

```text
User states plans / tasks
          │
          ▼
   Create TODOLIST.md  ◄───────────────────────────┐
          │                                        │
          ▼                                        │
   Execute Task #1                                 │
          │                                        │
          ▼                                        │
   Mark Task [x] in TODOLIST.md                    │
          │                                        │
          ▼                                        │
   Are all tasks [x] complete?                     │
     ├── NO  ──► Focus on next pending task        │
     └── YES ──► Delete TODOLIST.md cleanly        │
                         │                         │
                         ▼                         │
                  Clean Workspace                  │
                         │                         │
                         └──── New tasks later? ───┘
```

### Core Rules
1. **Always in Repository Root**: The file must be named `TODOLIST.md` and located in the workspace root.
2. **Two-Way Synchronization**:
   - The agent updates `TODOLIST.md` as tasks transition (`[ ]` -> `[/]` in progress -> `[x]` done).
   - If the user modifies `TODOLIST.md` in their editor, the agent respects the user's edits as the source of truth.
3. **One Active Task at a Time**: Mark the currently active item with `[/]` or state it in the `Current Focus` section. Never multitask across three items simultaneously.
4. **Auto-Deletion on Completion**: When the last remaining task is marked `[x]` and verified, the agent **must delete `TODOLIST.md`**.
5. **Fresh Re-creation**: If new tasks are introduced in a subsequent session or turn, create a fresh `TODOLIST.md`.

---

## TODOLIST.md Template Format

When creating `TODOLIST.md`, always use this clean, standardized format:

```markdown
# Session To-Do List

> **Goal**: [Brief 1-sentence summary of the day's objective]  
> **Status**: Active ([X]/[Y] Completed)  
> **Created**: YYYY-MM-DD  

---

## Tasks

- [ ] **#1** [Task 1 title and short description]
- [ ] **#2** [Task 2 title and short description]
- [ ] **#3** [Task 3 title and short description]

---

## Current Focus
- **Active**: [Task #1]
- **Target Outcome**: [What proves this task is done]

---

## Completed
*(Completed tasks will be recorded here with timestamps or brief outcome notes)*

---

<!-- AUTOMATIC CLEANUP CONTRACT:
This file is temporary. When all tasks above are checked [x], the agent will automatically delete TODOLIST.md.
-->
```

---

## Operational Commands

### 1. Initialize or Intake (`/todolist init` or `/todolist <tasks>`)
- Read user prompt for task descriptions, milestones, or plans.
- Create `TODOLIST.md` at root using the standard format.
- Output a concise summary confirming the active list and stating the first task being started.

### 2. Update Progress (`/todolist progress` or inline execution)
When a task is completed:
1. Re-read `TODOLIST.md` to ensure no user edits are overwritten.
2. Update the completed task checkbox from `- [ ]` to `- [x]`.
3. Move the task note under `## Completed` with a brief evidence line (e.g. `- [x] #1 Add auth endpoint — tested and passing`).
4. Update `## Current Focus` to point to the next pending item.
5. Check if all items are complete.

### 3. Check for Full Completion & Automatic Deletion
When updating `TODOLIST.md`:
1. Scan all checkboxes under `## Tasks`.
2. If any unchecked `- [ ]` or in-progress `-[/]` item remains: keep `TODOLIST.md`, inform the user of progress, and proceed to the next item.
3. If **100% of tasks are marked `- [x]`**:
   - Inform the user that all planned items are complete.
   - Delete `TODOLIST.md` using the file deletion tool (`rm TODOLIST.md` or dedicated removal).
   - Announce: `All todos completed. TODOLIST.md has been removed.`

### 4. Append Tasks (`/todolist add <task>`)
If the user or agent uncovers an essential secondary task that belongs to the current scope:
1. Append the new item to `## Tasks` as `- [ ] #N ...`.
2. Update the status count.

### 5. Inspect / Status (`/todolist status`)
1. Read `TODOLIST.md`.
2. Report:
   - Completed tasks: `N/M`
   - Current active task
   - Next queued tasks

---

## Agent Behavioral Discipline

- **Never ignore the list**: When you finish fixing a bug or implementing a component, do not ask "What should I do next?" without checking `TODOLIST.md` first. Read `TODOLIST.md`, pick the next pending item, update the status, and continue.
- **Resist Scope Creep**: If you notice an unrelated bug or tempting cleanup during a task:
  - Do NOT derail the current task.
  - Ask the user if it should be added to `TODOLIST.md` as an explicit next item.
- **Preserve User Edits**: The user might open `TODOLIST.md` in VS Code and reorder lines or add a comment. Before writing back to `TODOLIST.md`, read the file to merge state cleanly.
