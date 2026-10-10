---
name: human-comment
description: Write useful code comments and documentation in a natural developer voice, with lowercase prose and no decorative or generic AI-style filler. Use when the user invokes /human-comment, asks to add explanatory comments, document code with human-sounding comments, or rewrite robotic comments into short natural notes. Applies only to requested code and documentation; not a blanket instruction to comment every implementation.
allowed-tools: Read Grep Glob Edit Write
---

# Human Comment

Leave the note a teammate would need to understand the code. Use lowercase prose, plain language, and enough explanation to be useful. Human-sounding means specific and accurate, not slang, deliberate typos, or a manufactured personality.

## Scope

- Read the requested code and its surrounding context before commenting. Explain observed behavior, not a guessed intention.
- Add or rewrite comments and documentation only within the requested scope. Keep executable code, identifiers, imports, and behavior unchanged.
- Leave unrelated existing comments alone. Do not perform a repository-wide cleanup unless asked.
- Treat an explicit request for this skill as opting into comments for that task rather than applying `no-comment` by default. Follow higher-priority instructions; if an applicable project rule forbids the requested comments and cannot be overridden, surface the conflict instead of silently ignoring it.
- Use the user's requested language. Otherwise follow nearby useful documentation; if there is none, use the language of the request. Do not translate code identifiers.

## Voice

Write lowercase prose, including the start of a sentence. Preserve exact spelling inside the prose when it carries meaning: `getUserByID`, `UserID`, `Buffer`, `DateTime`, `SameSite`, paths, URLs, literal values, and error strings.

```js
// menggunakan getUserByID agar pemeriksaan akses tidak terlewati di jalur lain sebelum lookup selesai
```

Lowercase is a writing style, not a text transform over the file. Never lowercase executable code or machine-readable comment syntax. Preserve licenses, copyright notices, shebangs, build tags, source-map directives, linter suppressions, type-checker pragmas, and documentation tags or types exactly. Keep `@param {UserID} userID` intact; lowercase only its human-readable description.

Use the language of a developer leaving a useful note. Avoid "this function is responsible for", "it is important to note", "robust", "seamless", and other wording that adds no concrete fact. Do not introduce first-person stories, jokes, or claims about who wrote the code.

## What earns a comment

A comment can explain why **or how**. Prefer information the reader cannot get by glancing at the next statement:

- a non-obvious algorithm or transformation;
- a business rule, unit, boundary, or assumption;
- a security constraint, race condition, or compatibility workaround;
- a side effect, failure mode, or public API contract.

Do not force a comment onto every function, block, or line. Skip trivial narration such as `// menambah count` above `count++`. A short explanation of a meaningful block is fine even when it describes what the block does. The goal is understanding, not a blanket ban on explaining behavior.

```js
// menggunakan bcrypt terhadap password
```

That style is fine when the block hashes the password. Call hashing hashing, not encryption; bcrypt does not provide reversible encryption. If the actual block compares a password against an existing hash, describe comparison instead.

Prefer a short line. Use more lines only when the requested documentation needs them to explain a real contract or subtle behavior. Brevity should not erase information the reader needs.

## No decoration

Do not add emoji, repeated-character separators, boxes, all-caps headings, section banners, "fase 1", "step 2", or end markers. A comment should carry information, not label visible control flow.

Instead of a banner announcing password processing, write the relevant note directly:

```js
// hash password sebelum disimpan
```

Do not replace a decorative banner with an equally empty lowercase label such as `// proses utama`. Replace it with a specific explanation, or remove it if nothing useful remains.

## Documentation

Use the language's existing documentation syntax when documentation is requested, such as JSDoc, PHPDoc, docstrings, or Rust doc comments. Required delimiters and tags are syntax, not decoration.

Document what a caller needs to know: input meaning or units, return behavior, edge cases, mutation, side effects, and errors actually visible in the implementation. Do not repeat the signature with filler like `@param price the price`.

```js
/** returns null when UserID has no matching record; does not create one */
```

Do not invent guarantees such as constant-time comparison, atomic writes, automatic retries, or validation that the implementation does not provide. When context is missing, omit the claim or ask for the missing information.

## Procedure

1. Read the target and enough surrounding code to understand its behavior.
2. Identify where an explanation would help, or which existing comments were requested for rewriting.
3. Write natural lowercase prose while preserving exact technical tokens and machine-readable comments.
4. Review the diff: only scoped comments or documentation changed; no decorative filler, unsupported claims, or incidental code formatting.
5. Run existing relevant checks when available. If a directive or doctest was touched, verify its behavior rather than assuming comments are inert.

## Final check

- Does each new comment teach something concrete?
- Does the description match the actual code?
- Is prose lowercase without corrupting identifiers or directives?
- Are language and wording natural for the surrounding work?
- Are executable code and unrelated comments unchanged?

If the code needs no explanation, say so rather than adding noise to satisfy a comment quota.
