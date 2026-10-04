---
name: conventional-commit-with-coauthor
description: Commits staged work using the Conventional Commits specification with a short subject message (no multi-line body or description by default) and appends a co-author trailer crediting the agent. Lands one commit per concern so the commit count follows the working tree, repeating the trailer on every commit in a split. The repository's own commit convention and an explicit user instruction both override the per-concern default. Use when the user types /conventional-commit-with-coauthor or explicitly asks for a conventional commit that credits the agent as co-author. Falls back to no trailer when no real agent identity is available.
allowed-tools: Bash Read Grep Glob
---

# Conventional Commit With Co-Author

Identical to `/conventional-commit` in every respect except one: this skill appends a **co-author trailer** crediting the agent, and only when a real agent identity exists.

Read `/conventional-commit` for the full procedure — staging discipline, type taxonomy, scope rules, the `!` breaking-change marker, subject grammar, the precedence chain, and the decision of how many commits to make. **The commit-count rule is one commit per concern**, and it applies here unchanged: the working tree's concerns each become a commit, each carrying its own trailer. This file documents only what differs: identity resolution, trailer format, placement, and the validation that the trailer is well-formed.

## Rule 1 — Never Fabricate an Identity

A co-author trailer is a claim about who authored the commit. A fabricated trailer is a false attribution in permanent history.

**Resolve the identity from a real source, in this order:**

1. **Explicit user instruction.** If the user named the co-author (name and email), use exactly that.
2. **A configured agent identity.** Check whether the environment defines one:

```bash
git config --get user.name
git config --get user.email
git config --get coauthor.name
git config --get coauthor.email
echo "${GIT_COAUTHOR_NAME:-unset} / ${GIT_COAUTHOR_EMAIL:-unset}"
```

3. **A documented convention in the repository.** Check `CONTRIBUTING.md`, `AGENTS.md`, `CLAUDE.md`, or a `git log` that already shows an established agent trailer:

```bash
git log --format='%B' -20 | grep -i 'co-authored-by' | sort -u
```

If the log already contains a consistent agent trailer, reuse that exact string so the history stays uniform.

**If none of these yields a real identity, omit the trailer entirely and continue with the commit.** The user's instruction for this case is explicit: if the agent cannot produce a co-author, skip it. A missing trailer is correct; an invented one is not. Tell the user you omitted it and why.

Do not use a placeholder such as `agent@example.com`, `noreply@localhost`, or the repository owner's own identity. Do not reuse the user's `user.name`/`user.email` as the co-author — that would credit the human twice and is worse than no trailer.

## Rule 2 — Trailer Format

Git trailers follow `Token: Value`, and `Co-authored-by` is the token GitHub, GitLab, and most forges parse to render an avatar on the commit.

```
Co-authored-by: Name <email@example.com>
```

Formatting rules that forges actually enforce:

- The token is case-insensitive to git but **use `Co-authored-by:` exactly** — GitHub's parser matches this spelling.
- The value must be `Display Name <addr@domain>` with the email in angle brackets. A bare email with no name, or a name with no email, will not render.
- One trailer per co-author, one line each.
- The trailer block goes **last**, after the subject (or body if extended), separated by one blank line. A trailer in the middle of text is treated as prose and is not parsed.
- Do not wrap the trailer line.
- **Short message only by default**: do not write multi-line bodies or descriptions unless explicitly requested.

Default format (subject + blank line + trailer):

```
feat(auth): add OAuth2 login

Co-authored-by: Claude Code <noreply@anthropic.com>
```

Multiple co-authors:

```
Co-authored-by: Claude Code <noreply@anthropic.com>
Co-authored-by: Pair Partner <partner@example.com>
```

## Rule 3 — The Trailer Is the Only Addition

Everything else stays exactly as `/conventional-commit` prescribes. Specifically:

- The subject is unchanged. Never append `(co-authored)` or a name to the subject.
- **Omit body by default.** Only add an explanatory body if the user explicitly requests one or when documenting breaking changes.
- `BREAKING CHANGE:` still goes in the footer block, **above** the co-author trailer, with the blank line preserved.
- Do not add `Signed-off-by:` unless the user asked for a DCO sign-off. It is a legal attestation, not a credit.
- Do not add a `Generated with` line. That is a tool banner, not a co-author, and this skill's job is the co-author trailer specifically.

Correct footer ordering for breaking changes:

```
refactor(api)!: change schema version into v3

BREAKING CHANGE: v2 request envelopes are rejected with 400. Clients must
send the v3 envelope, which moves `payload` to the top level and drops the
`meta.version` field.

Refs: #512
Co-authored-by: Claude Code <noreply@anthropic.com>
```

## Committing

**One commit per concern.** The trailer does not change how many commits a change deserves: enumerate the concerns the way `/conventional-commit` Step 2 says, and land one commit each — every one of them carrying the trailer. A trailer on only the first commit of a split credits the agent for a fraction of the work and reads as an inconsistency in the log.

The precedence chain still governs: if the user asks for a single commit, or the repository's convention prescribes a different granularity, that wins and the per-concern default does not apply.

The message stays short by default, and a trailer does not require a body.

Use a heredoc to keep bytes and blank lines exact:

```bash
git commit -F - <<'EOF'
feat(auth): add OAuth2 login

Co-authored-by: Claude Code <noreply@anthropic.com>
EOF
```

## Verification

After committing, verify the trailer is present, well-formed, and parsed as a trailer rather than as body text.

```bash
git log -1 --format='%B'
```

Confirm the trailer appears in git's own trailer parsing, which proves the format is valid:

```bash
git log -1 --format='%(trailers:key=Co-authored-by,valueonly)'
```

If that prints nothing, the trailer is malformed or misplaced — fix the message with `git commit --amend -F -` (only for a commit created in this session and not yet pushed).

The trailer parser is case-insensitive on the key, so `Co-authored-by`, `Co-Authored-By`, and `CO-AUTHORED-BY` all match. A case-sensitive `grep 'Co-authored-by'` does **not** — the convention is written with capital `A` and `B`, so a plain grep reports a false all-clear. Use the parser, or always pass `-i` to grep.

Set `N` to the number of commits you made — the concern count from `/conventional-commit` Step 2 — and check every one:

```bash
# N is the concern count, not a fixed 1
N=4
for sha in $(git log --format=%H -"$N"); do
  t=$(git log -1 --format='%(trailers:key=Co-authored-by,valueonly)' "$sha")
  [ -n "$t" ] && echo "ok      ${sha:0:7}  $t" || echo "MISSING ${sha:0:7}"
done
```

Every line must read `ok`. A `MISSING` line is a commit that needs the trailer added.

Capturing the value and testing it for emptiness is what detects a missing trailer. Printing the format directly with `printf '%s  '` does not: an empty result and a present trailer both produce a line that looks blank at a glance, because `%(trailers:...)` emits its own trailing newline.

## Common Mistakes

| Mistake                                                     | Why It Breaks                                                                                          | Correct Approach                                   |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | -------------------------------------------------- |
| Inventing `agent@example.com`                               | False attribution baked into permanent history                                                         | Omit the trailer and say so                        |
| Using the user's own identity as co-author                  | Credits the human twice                                                                                | Resolve a distinct agent identity or omit          |
| Trailer typed inline instead of via a heredoc               | A subtly malformed trailer looks correct on the command line but silently fails to render on the forge | Use `-F -` with a heredoc so the bytes are visible |
| Trailer placed mid-body                                     | Git only parses the trailing block                                                                     | Put it last, after a blank line                    |
| Email without angle brackets                                | GitHub does not match the identity and no avatar renders                                               | `Name <email@domain>` exactly                      |
| `Signed-off-by:` added "as a credit"                        | It is a DCO legal attestation, not a co-author                                                         | Only `Co-authored-by:`                             |
| Trailer on only one commit of a per-concern split           | Under-credits the agent and looks inconsistent in the log                                              | Repeat on every commit in the split                |
| Splitting **one** concern to give the agent more trailers   | The fragments are incomplete and the trailer count is not a measure of contribution                    | One concern, one commit, one trailer               |
| Body added just to carry the trailer                        | The trailer needs only a blank line, not prose                                                         | Subject plus trailer is a complete commit          |
| Subject modified to include the name                        | Violates the conventional grammar and breaks changelog tooling                                         | Leave the subject alone                            |
| Ignoring a repo convention or a user's "one commit" request | The precedence chain puts both above the per-concern default                                           | Follow the instruction or the convention           |
| `!` without `BREAKING CHANGE:` because a trailer is present | The two are independent; the trailer does not replace the footer                                       | Keep both, footer above the trailer                |
| Amending a pushed commit to add the trailer                 | Rewrites shared history                                                                                | Make a new commit                                  |
