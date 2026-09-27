---
name: enhance
description: Rewrites a user's raw prompt into a precise, unambiguous specification before any work begins — surfacing what is missing, asking only the questions that change the outcome, and returning a copy-pasteable enhanced prompt with a change log. Use when the user types /enhance, says "improve my prompt", "sharpen this", "make this prompt better", or wants a vague request turned into a real brief. Never executes the underlying task.
allowed-tools: Read Grep Glob
---

# Enhance

Turn a raw prompt into one a competent agent could execute without asking a follow-up question.

## The Contract

This skill produces a **better prompt**. It does not execute that prompt.

Three failure modes, all of which this skill exists to prevent:

1. **Executing the task.** The user asked for a prompt, not a result. If you start building, you have failed the request.
2. **Decoration.** Returning a longer, more confident-sounding prompt that carries the same ambiguities. Length is not precision.
3. **Scope injection.** Silently adding requirements the user never asked for. This is the defining failure of prompt enhancers, and it is worse than doing nothing, because the user ships work they did not request.

The deliverable is a prompt that is **executable** (an agent can start without asking anything) and **checkable** (a reviewer can decide whether the result is correct).

## When to Use

- The user explicitly wants the prompt improved rather than the task done.
- The prompt is **for another agent or model**, or will be **reused** — a system prompt, a template, a saved snippet, a prompt in a repo.
- The work is **expensive or irreversible** — a migration, a large refactor, a deploy — where a bad prompt wastes real effort.
- The request is **underspecified** and the user wants to fix the input instead of letting the agent guess.

## When Not to Use

- The user wants the task done now. Enhancing first doubles the round trips; if the request is already clear, just do it.
- The request is a single unambiguous mechanical action ("rename this variable", "fix this typo").
- The user is thinking out loud. Turning a casual question into a formal brief is a hostile response.
- The user is in a non-interactive context (CI, `/loop`, an autonomous run) where nobody can answer the questions. State the ambiguity as a blocker instead.

## Step 1 — Read the Prompt Twice

Read it once as written. Read it again asking: **what would I have to guess to start?**

Every guess is either a blocker or a cosmetic gap. Classify before asking.

An ambiguity is **blocking** when two reasonable readings produce materially different work. It is **cosmetic** when both readings converge on the same output.

| Ambiguity                                                                               | Blocking when | Cosmetic when |
| --------------------------------------------------------------------------------------- | ------------- | ------------- |
| Two readings lead to different files, different architecture, or different deliverables | Always        | —             |
| Two readings differ only in wording or ordering                                         | —             | Always        |
| The user cannot answer it and any reasonable default works                              | —             | Always        |

**Only blocking ambiguities justify a question.** Cosmetic gaps get a stated default in the enhanced prompt.

## Step 2 — Scan the Eight Dimensions

Work through every dimension. Most prompts are missing three or four.

| #   | Dimension                | The question it answers                                      | Absent looks like                               |
| --- | ------------------------ | ------------------------------------------------------------ | ----------------------------------------------- |
| 1   | **Goal**                 | What outcome, in one sentence?                               | "make it better", "fix the issue"               |
| 2   | **Scope**                | What is in, and explicitly what is out?                      | Unbounded verbs: "refactor the app", "clean up" |
| 3   | **Deliverable**          | What artifact comes back, in what form?                      | No mention of file, diff, prose, or code        |
| 4   | **Success criteria**     | How do we know it is done and correct?                       | No acceptance test, no "done when"              |
| 5   | **Constraints**          | Stack, style, compatibility, performance, budget, deadline   | Not stated, so the agent invents them           |
| 6   | **Context / inputs**     | What must the agent read or know first?                      | No paths, no links, no "see this file"          |
| 7   | **Audience**             | Who consumes the output — end user, reviewer, another agent? | Unstated, so the register is wrong              |
| 8   | **Risk / reversibility** | What must not break; what is irreversible?                   | No mention of blast radius                      |

Two more dimensions that are not part of the eight but are cheap to fix:

- **Language and register.** If the user wrote in Indonesian but the deliverable is code comments or docs for an English team, say which language each artifact uses.
- **Forbidden actions.** What the agent must not do: no new dependencies, no schema changes, no touching a specific directory.

## Step 3 — Apply the Confidence Gate

Before writing a question, answer this honestly:

> **If the user answers this, does the prompt I write change?**

If no, do not ask. Pick a default, write it into the prompt, and list it under **Assumptions**.

If yes, ask — but ask well:

- **Batch every question into one round.** One message, numbered questions, never an interrogation.
- **Attach a recommended default to each.** The user should be able to reply "yes" or "1b, 2a" and be done. A question without a recommendation outsources the thinking back to the user.
- **Cap at five.** More than five means you have not prioritized. Ask the five that change the most work, and list the rest as stated assumptions.
- **Use `AskUserQuestion` when the options are enumerable.** A structured choice is faster to answer than prose.
- **Never ask what you can find out.** If the answer is in the repo, read it. Dispatch a search rather than asking the user for a fact.

If the user declines to answer, do not stall. Write the prompt with explicit assumptions and mark each one as unconfirmed.

## Step 4 — Write the Enhanced Prompt

Rewrite, do not pad. The enhanced prompt is what the user will actually paste.

Rules:

- **Preserve the original intent exactly.** If the user said "add a search box", the enhanced prompt says "add a search box", with clarified inputs and acceptance criteria — not "add a search box with fuzzy matching, analytics, keyboard shortcuts, and i18n". That is scope injection.
- **Make every requirement testable.** "Fast" becomes "p95 under 200 ms on the existing dataset". "Clean" becomes "no file over 300 lines; no new dependency".
- **Name the files and paths.** A prompt that says "the auth module" makes the agent guess. A prompt that says `src/auth/session.ts` does not.
- **State the definition of done explicitly.** The single highest-value addition to almost any prompt.
- **State what is out of scope.** The second highest-value addition. It is what stops scope creep.
- **Keep the user's voice.** If they wrote casually, do not return corporate register. Match the register of the consumer.
- **Do not add ceremony.** No "You are an expert engineer with 20 years of experience" preamble. It consumes tokens and changes nothing measurable.

### The shape

```text
## Goal
<one sentence: the outcome>

## Context
<what the agent must read first — file paths, links, prior decisions>

## Scope
In:  <what changes>
Out: <what explicitly does not change>

## Requirements
1. <testable requirement>
2. <testable requirement>

## Constraints
- <stack, style, compatibility, performance, budget>

## Definition of Done
- [ ] <checkable criterion>
- [ ] <checkable criterion>

## Do Not
- <forbidden action>
```

Drop any section that is genuinely empty. A short prompt with a definition of done beats a long prompt without one.

## Step 5 — Report the Change

The user needs to see what you did to their words, or they cannot trust the result.

````markdown
## Enhanced Prompt

```text
<the full enhanced prompt, ready to paste>
```
````

## What Changed

| Added              | Why                                                  |
| ------------------ | ---------------------------------------------------- |
| Definition of Done | The original had no way to tell success from failure |
| `Out:` scope       | "refactor the app" was unbounded                     |
| Target path        | "the module" had three plausible referents           |

## Assumptions

- **Language of code comments: English.** Not stated; matches the existing codebase (`src/auth/*.ts`).
- **No new dependencies.** Not stated; assumed from the absence of a package manager change in recent history.
- **Unconfirmed:** the target is `src/auth/`, not `src/session/`. Both exist.

````

Always separate **what you added** from **what you assumed**. An assumption the user does not notice is a bug you handed them.

## Worked Example

**Raw prompt:**

```text
/enhance bikin caching buat API calls, biar ga lambat
````

**Analysis:**

| Dimension        | Present?                                       |
| ---------------- | ---------------------------------------------- |
| Goal             | Partial — "caching for API calls"              |
| Scope            | Missing — which calls? all of them?            |
| Deliverable      | Missing — code? a library? a config change?    |
| Success criteria | Missing — "ga lambat" is not measurable        |
| Constraints      | Missing — in-memory? Redis? TTL? invalidation? |
| Context          | Missing — no paths                             |
| Audience         | N/A                                            |
| Risk             | Missing — stale data is a correctness risk     |

**Blocking ambiguities:** cache layer (in-memory vs shared store) and invalidation strategy. Both change the implementation materially. Ask these two.

**Cosmetic:** TTL duration — any sane default works, and it is trivially changed later. State a default.

**Enhanced prompt:**

```text
## Goal
Reduce latency of outbound API calls in the orders service by caching responses.

## Context
- src/orders/client.ts — the HTTP client making the calls
- src/orders/service.ts — the call sites
- Existing cache: none in this service.

## Scope
In:  caching for the GET endpoints in src/orders/client.ts
Out: auth endpoints; any write/POST call; the payments service.

## Requirements
1. Cache only idempotent GET responses.
2. Key includes the full URL and the auth subject, so tenants never share entries.
3. TTL configurable via an env var; default 60 s.
4. Invalidation on write to the same resource.

## Constraints
- No new runtime dependency unless the chosen store requires it.
- Must not change the public signature of the functions in src/orders/service.ts.

## Definition of Done
- [ ] A second identical GET within the TTL performs no network call (assert via a mocked transport).
- [ ] Two different auth subjects never share a cache entry (covered by a test).
- [ ] A write to a resource invalidates its cached GET.
- [ ] Existing tests pass unchanged.

## Do Not
- Do not cache error responses.
- Do not add a global cache shared across services.
```

Note what did **not** happen: no "add observability", no "add a circuit breaker", no "make it distributed". The user asked for caching.

## Common Mistakes

| Mistake                                   | Why It Breaks                                               | Correct Approach                              |
| ----------------------------------------- | ----------------------------------------------------------- | --------------------------------------------- |
| Executing the task                        | The user asked for a prompt                                 | Return the prompt only                        |
| Scope injection                           | Ships work nobody requested; the worst enhancer failure     | Preserve intent; clarify, never expand        |
| Padding with role preambles               | Consumes tokens, changes nothing                            | Delete "You are an expert…"                   |
| Asking cosmetic questions                 | Wastes the user's attention on decisions that do not matter | State a default and move on                   |
| Asking without a recommendation           | Outsources the thinking back to the user                    | Every question carries a default              |
| Asking ten questions                      | The user abandons the round                                 | Cap at five, batch them                       |
| Asking a fact you could look up           | The user is not a database                                  | Read the repo or dispatch a search            |
| "Fast" / "clean" / "better" left in place | Untestable; the agent invents a threshold                   | Replace with a measurable criterion           |
| No definition of done                     | The agent stops wherever it feels finished                  | Always add checkable criteria                 |
| No out-of-scope statement                 | Scope creep, the default outcome                            | Always add an `Out:` list                     |
| Rewriting in a different register         | The user cannot reuse their own prompt                      | Match their voice                             |
| Hiding assumptions                        | The user ships a prompt built on a guess                    | List assumptions separately, flag unconfirmed |
| Returning only the prompt                 | The user cannot see what changed or trust it                | Always include the change log                 |
