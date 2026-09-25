---
name: conventional-commit-with-coauthor
description: Commits staged work using the Conventional Commits specification and appends a co-author trailer crediting the agent, splitting a large working tree into multiple atomic commits. Use when the user types /conventional-commit-with-coauthor or explicitly asks for a conventional commit that credits the agent as co-author. Falls back to no trailer when no real agent identity is available.
allowed-tools: Bash Read Grep Glob
---

# Conventional Commit With Co-Author

Identical to `/conventional-commit` in every respect except one: this skill appends a **co-author trailer** crediting the agent, and only when a real agent identity exists.

Read `/conventional-commit` for the full procedure — staging discipline, type taxonomy, scope rules, the `!` breaking-change marker, subject grammar, and the multi-commit split strategy are all the same. This file documents only what differs: identity resolution, trailer format, placement, and the validation that the trailer is well-formed.

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
- The trailer block goes **last**, after the body, separated from it by one blank line. A trailer in the middle of the body is treated as prose and is not parsed.
- Do not wrap the trailer line.

```
feat(auth): add OAuth2 login

Replaces the legacy session cookie flow. The callback handler now
validates state on every exchange.

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
- The body still explains the why, not the what.
- `BREAKING CHANGE:` still goes in the footer block, **above** the co-author trailer, with the blank line between body and footers preserved.
- Do not add `Signed-off-by:` unless the user asked for a DCO sign-off. It is a legal attestation, not a credit.
- Do not add a `Generated with` line. That is a tool banner, not a co-author, and this skill's job is the co-author trailer specifically.

Correct footer ordering:

```
refactor(api)!: change schema version into v3

The v2 envelope is no longer accepted on any endpoint.

BREAKING CHANGE: v2 request envelopes are rejected with 400. Clients must
send the v3 envelope, which moves `payload` to the top level and drops the
`meta.version` field.

Refs: #512
Co-authored-by: Claude Code <noreply@anthropic.com>
```

## Committing

Use a heredoc so the blank lines and the trailer block survive intact. Do not assemble the message from multiple `-m` flags — git concatenates them without a blank line and the trailer ends up inside the body paragraph, where it is not parsed.

```bash
git commit -F - <<'EOF'
feat(auth): add OAuth2 login

Replaces the legacy session cookie flow.

Co-authored-by: Claude Code <noreply@anthropic.com>
EOF
```

For a multi-commit split, repeat the trailer on **every** commit in the split. A trailer on only the first commit credits the agent for a fraction of the work.

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

Check every commit in the split:

```bash
git log --format='%h %(trailers:key=Co-authored-by,valueonly)' -<n>
```

## Common Mistakes

| Mistake                                                     | Why It Breaks                                                                                  | Correct Approach                          |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------- |
| Inventing `agent@example.com`                               | False attribution baked into permanent history                                                 | Omit the trailer and say so               |
| Using the user's own identity as co-author                  | Credits the human twice                                                                        | Resolve a distinct agent identity or omit |
| Building the message with `-m "subject" -m "trailer"`       | Git joins them with no blank line; the trailer is parsed as body prose and no forge renders it | Use `-F -` with a heredoc                 |
| Trailer placed mid-body                                     | Git only parses the trailing block                                                             | Put it last, after a blank line           |
| Email without angle brackets                                | GitHub does not match the identity and no avatar renders                                       | `Name <email@domain>` exactly             |
| `Signed-off-by:` added "as a credit"                        | It is a DCO legal attestation, not a co-author                                                 | Only `Co-authored-by:`                    |
| Trailer on one commit of a five-commit split                | Under-credits and looks inconsistent in the log                                                | Repeat on every commit                    |
| Subject modified to include the name                        | Violates the conventional grammar and breaks changelog tooling                                 | Leave the subject alone                   |
| `!` without `BREAKING CHANGE:` because a trailer is present | The two are independent; the trailer does not replace the footer                               | Keep both, footer above the trailer       |
| Amending a pushed commit to add the trailer                 | Rewrites shared history                                                                        | Make a new commit                         |
