---
name: conventional-commit-with-coauthor
description: Commits staged work using the Conventional Commits specification with a short subject message and appends a co-author trailer crediting the agent (no multi-line body or description by default). Defaults to a single commit when the working tree is one coherent change, splitting only when the changes are genuinely unrelated. Use when the user types /conventional-commit-with-coauthor or explicitly asks for a conventional commit that credits the agent as co-author. Falls back to no trailer when no real agent identity is available.
allowed-tools: Bash Read Grep Glob
---

# Conventional Commit With Co-Author

Identical to `/conventional-commit` in every respect except one: this skill appends a **co-author trailer** crediting the agent, and only when a real agent identity exists.

Read `/conventional-commit` for the full procedure — staging discipline, type taxonomy, scope rules, the `!` breaking-change marker, subject grammar, and the decision of how many commits to make. **The commit-count default is one commit**, and it applies here unchanged: a coherent working tree produces a single commit with a single trailer. This file documents only what differs: identity resolution, trailer format, placement, and the validation that the trailer is well-formed.

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

**Default to one commit.** The trailer does not change how many commits a change deserves: if the working tree is one coherent change, it is one commit with one trailer. Split only when `/conventional-commit` Step 2 says the changes are genuinely unrelated — and then repeat the trailer on **every** commit in the split, because a trailer on only the first credits the agent for a fraction of the work.

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

Set `N` to the number of commits you made and check every one — a single-commit change is `N=1`:

```bash
N=1
for sha in $(git log --format=%H -"$N"); do
  printf '%s  ' "${sha:0:7}"
  git log -1 --format='%(trailers:key=Co-authored-by,valueonly)' "$sha"
done
```

Every line must name an author. A blank line is a commit missing its trailer.

## Common Mistakes

| Mistake                                                      | Why It Breaks                                                                                          | Correct Approach                                   |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ | -------------------------------------------------- |
| Inventing `agent@example.com`                                | False attribution baked into permanent history                                                         | Omit the trailer and say so                        |
| Using the user's own identity as co-author                   | Credits the human twice                                                                                | Resolve a distinct agent identity or omit          |
| Trailer typed inline instead of via a heredoc                | A subtly malformed trailer looks correct on the command line but silently fails to render on the forge | Use `-F -` with a heredoc so the bytes are visible |
| Trailer placed mid-body                                      | Git only parses the trailing block                                                                     | Put it last, after a blank line                    |
| Email without angle brackets                                 | GitHub does not match the identity and no avatar renders                                               | `Name <email@domain>` exactly                      |
| `Signed-off-by:` added "as a credit"                         | It is a DCO legal attestation, not a co-author                                                         | Only `Co-authored-by:`                             |
| Trailer on one commit of a multi-commit split                | Under-credits and looks inconsistent in the log                                                        | Repeat on every commit in the split                |
| Splitting one coherent change to give the agent more commits | The log misstates scope; the trailer count is not a measure of contribution                            | One change, one commit, one trailer                |
| Subject modified to include the name                         | Violates the conventional grammar and breaks changelog tooling                                         | Leave the subject alone                            |
| `!` without `BREAKING CHANGE:` because a trailer is present  | The two are independent; the trailer does not replace the footer                                       | Keep both, footer above the trailer                |
| Amending a pushed commit to add the trailer                  | Rewrites shared history                                                                                | Make a new commit                                  |
