---
name: summarize
description: Produces a structured execution summary of the current session — every action taken, issues found with their root causes, the solutions implemented, verification evidence, and outstanding work. Use when the user types /summarize, asks for a session recap, wants a handoff document, asks "what did we do", or needs a record of changes before ending a session.
allowed-tools: Read Grep Glob Bash
---

# Summarize

Produce an accurate, scannable record of what happened in this session.

The summary serves two readers: the user, who wants to confirm what changed, and a future session or teammate, who wants to continue the work without re-deriving it. Write for both.

## The Integrity Rule

**Report only what actually happened in this session.**

- Do not claim a file was changed if it was not.
- Do not claim a test passed unless you saw it pass.
- Do not present a plan as a completed action.
- Do not omit a failure, a revert, or a dead end. A summary that hides the failed attempt makes the next session repeat it.
- If you do not know whether something succeeded, say so.

Verify claims against the session record rather than recalling them. Use the tools to confirm file state and repository state.

```bash
git status --short
git diff --stat
git log --oneline -10
```

If the session made no repository changes, say that plainly rather than padding the report.

## Structure

Produce these sections in this order. Omit a section only when it is genuinely empty — and when you omit one, say so, because a missing section reads as an oversight.

### 1. Overview

Two to four sentences. What was the session about, what was the outcome, and what is the state now. A reader who stops here should know whether the work is done.

### 2. Actions Taken

Every action, in the order it happened, with the evidence.

| #   | Action | Target                   | Result                            |
| --- | ------ | ------------------------ | --------------------------------- |
| 1   | Read   | `src/auth/session.ts`    | Located the token refresh path    |
| 2   | Edit   | `src/auth/session.ts:88` | Added expiry check before refresh |
| 3   | Run    | `bun test src/auth`      | 12 passed, 0 failed               |
| 4   | Run    | `bunx tsc --noEmit`      | 2 errors, both pre-existing       |

Group by type when the list is long: **Files created**, **Files modified**, **Files deleted**, **Commands executed**, **Dependencies changed**, **Configuration changed**. For each modified file, state what changed and why — not just that it changed.

### 3. Issues and Root Causes

For each problem encountered — reported by the user or discovered during the work.

```markdown
#### Issue 1 — <one-line symptom>

**Symptom** What was observed, with the exact error text if there was one.

**Root cause** Why it happened. Not the surface location — the actual mechanism.

**Evidence** The file, line, command output, or stack frame that proves the cause.

**Fix** What was changed and why that addresses the cause rather than the symptom.

**Verification** How it was confirmed fixed, with the result.
```

Distinguish clearly between:

- **Reported by the user** — a bug or request they raised.
- **Discovered during work** — something you found while doing something else.
- **Pre-existing** — a defect you did not introduce and did not fix. **Always call these out separately.** Conflating a pre-existing problem with your own change makes the diff look worse than it is and hides real work the user still owes.

### 4. Changes Made

For each change, the substance — not the diff.

- What the code did before and what it does now.
- The key logic or structural decision, and the constraint that drove it.
- Edge cases handled, and edge cases deliberately not handled.
- Anything a reviewer must know to read the diff correctly.

For an architectural change, describe the before and after shape in a sentence or a small diagram.

### 5. Verification

What was actually run, and what it returned. This section is where trust is earned or lost.

| Check      | Command                              | Result                     |
| ---------- | ------------------------------------ | -------------------------- |
| Type check | `bunx tsc --noEmit`                  | Pass — 0 errors            |
| Unit tests | `bun test`                           | Pass — 47 passed, 0 failed |
| Lint       | `bun lint`                           | Pass                       |
| Build      | `bun build`                          | Pass                       |
| Manual     | Loaded `/login`, submitted bad creds | Correct error shown        |

If a check was **not** run, list it under Not Verified with the reason. An unverified claim stated as verified is the single most damaging thing a summary can do.

### 6. Not Verified / Known Gaps

Be specific and unflinching.

- What was not tested and why (no test exists, no fixture, requires a live service).
- Assumptions made that were not confirmed.
- Behavior you changed that has no test coverage.
- Anything you are uncertain about.

### 7. Follow-Up

Concrete, ordered next steps. Each names what to do and why it matters.

1. **Add a regression test** for the expiry boundary at `src/auth/session.ts:88` — the fix is untested, so it can silently regress.
2. **Migrate the two callers** of the deprecated helper — they still use the old signature.
3. **Pre-existing:** `tsc` reports 2 errors in `src/legacy/*` — unrelated to this session, still open.

Separate **blocking** from **optional**. Do not pad this list with speculative work.

## Output Rules

- **Lead with the outcome.** The first line answers "did it work".
- **Use tables for anything enumerable.** Actions, files, verification results.
- **Cite locations.** `src/auth/session.ts:88`, not "the session file".
- **Quote exact errors and exact command output.** Paraphrasing an error loses the string the reader needs to search for.
- **Distinguish done from planned from blocked.** Use explicit labels.
- **Be concise but complete.** Cut adjectives, not facts. No "successfully", no "carefully", no "it's worth noting".
- **Keep it readable.** A reader should be able to skim the headings and tables and get the shape in ten seconds, then read one section for detail.
- **No emoji, no decorative formatting.** This is a record.

## Handling an Empty or Trivial Session

If the session was a question, a review with no edits, or an exploration, do not manufacture sections. Report what happened in the honest shape:

```markdown
## Overview

Reviewed the proposed caching layer. No code changed — the design has a
correctness problem that should be resolved first.

## Findings

| #   | Finding                                                 | Severity | Location             |
| --- | ------------------------------------------------------- | -------- | -------------------- |
| 1   | Cache key omits the tenant id, so tenants share entries | Critical | src/cache/keys.ts:14 |

## Actions Taken

Read-only. No files modified, no commands run beyond search.

## Recommendation

Fix the cache key before implementing. See finding 1.
```

A short accurate summary beats a long padded one.

## Handoff Form

When the user wants to hand off to another session or teammate, add a section that a fresh agent can act on without reading the transcript:

```markdown
## Handoff

**State** Feature implemented and tested; not yet committed.
**Branch** `feat/session-expiry` — 3 commits ahead of `main`
**Entry point** `src/auth/session.ts` — `refreshSession()` is the changed function
**How to verify** `bun test src/auth && bun run dev`, then load `/login`
**Open** Two callers still use the old signature — see Follow-Up 2.
**Do not** Revert the `!` on the schema change; it is intentional.
```

## Common Mistakes

| Mistake                                       | Why It Breaks                                                 | Correct Approach                               |
| --------------------------------------------- | ------------------------------------------------------------- | ---------------------------------------------- |
| Claiming tests passed without running them    | Destroys trust the moment it is checked                       | Run them, or list under Not Verified           |
| Mixing pre-existing defects with your changes | Makes the diff look worse and hides the user's remaining work | Separate "pre-existing" explicitly             |
| Listing files without saying what changed     | Unreadable; the user must open every file                     | One line per file describing the change        |
| Paraphrasing an error message                 | The reader cannot search for it                               | Quote it exactly                               |
| Reporting a plan as done                      | The next session builds on something that does not exist      | Label done / planned / blocked                 |
| Omitting the failed attempt                   | The next session repeats it                                   | Record dead ends and why they failed           |
| Padding with "successfully" and "carefully"   | Buries the facts                                              | Cut the adverbs                                |
| No verification section                       | The reader cannot tell whether anything was checked           | Always state what was run and what it returned |
| Writing prose where a table belongs           | Slow to scan                                                  | Tables for enumerables                         |
| Burying the outcome at the end                | The reader must read everything to learn whether it worked    | Lead with the outcome                          |
| Inventing follow-up work                      | Wastes the reader's attention                                 | Only real, actionable next steps               |
| Manufacturing sections for a trivial session  | Signals padding and undermines the whole report               | Report the honest shape, however short         |
