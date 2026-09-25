# JavaScript Standards

Covers the runtime-level conventions no type checker enforces: module format and boundary shape, declaration and nullability discipline, asynchrony and error propagation, and the lint/format configuration that makes any of it stick. Getting these wrong produces failures that survive review and tests — a `||` default that swallows `0`, a floating promise that rejects after the response is sent, an import cycle that resolves to `undefined` under one module system and throws under the other. Every rule below is tool-enforceable; the audit's job is to find the files that drifted.

## Contents

- [When This Applies](#when-this-applies)
- [Module System and Boundaries](#module-system-and-boundaries)
  - [ESM is the target; CommonJS is a compatibility surface](#esm-is-the-target-commonjs-is-a-compatibility-surface)
  - [Module boundaries and side effects](#module-boundaries-and-side-effects)
  - [Environment boundaries](#environment-boundaries)
- [Values, Coercion, and Nullability](#values-coercion-and-nullability)
  - [Declarations, equality, and coercion](#declarations-equality-and-coercion)
  - [Nullish defaults and optional chaining](#nullish-defaults-and-optional-chaining)
  - [Immutable data patterns](#immutable-data-patterns)
- [Asynchrony and Errors](#asynchrony-and-errors)
  - [`async`/`await` over chains and callbacks](#asyncawait-over-chains-and-callbacks)
  - [Choosing a combinator](#choosing-a-combinator)
  - [Floating promises and unhandled rejections](#floating-promises-and-unhandled-rejections)
  - [Typed errors and `cause`](#typed-errors-and-cause)
- [Naming, Shape, and Tooling](#naming-shape-and-tooling)
  - [Naming](#naming)
  - [Array methods over manual loops](#array-methods-over-manual-loops)
  - [JSDoc for public APIs](#jsdoc-for-public-apis)
  - [ESLint flat config and Prettier](#eslint-flat-config-and-prettier)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- A repository contains `.js`, `.mjs`, `.cjs`, or `.jsx` files, or `package.json` declares `"type"`.
- `require()` and `import` appear in the same package, or a `.js` file uses ESM syntax without `"type": "module"`.
- The audit finds both `var` and `let`/`const`, or both `==` and `===` for the same kind of comparison.
- Async code mixes `await`, `.then()` chains, and Node-style `(err, result)` callbacks in one call path.
- Array code mutates inputs in place (`sort`, `reverse`, `splice`, `push`) where callers assume a copy.
- ESLint configuration is absent, still `.eslintrc.*`, or exists without Prettier integration.
- A build fails intermittently with `ReferenceError: Cannot access 'X' before initialization` — the circular-import symptom.
- TypeScript is present but plain JavaScript files are excluded from linting and checking ([std-ts.md](std-ts.md) governs the `.ts` side).

## Module System and Boundaries

### ESM is the target; CommonJS is a compatibility surface

Declare `"type": "module"` and write `import`/`export` everywhere. ESM is statically analyzable (tree-shaking, reliable cycle diagnostics), always strict, and supports top-level `await`. Keep CommonJS only where a consumer demands it: `.cjs` files and published dual-format entry points.

| Concern                    | ESM                                                                                                      | CommonJS                           |
| -------------------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| Strict mode                | Always on                                                                                                | Opt-in via `"use strict"`          |
| `__dirname` / `__filename` | Absent; use `import.meta.dirname` / `import.meta.filename` (added v20.11.0 / v21.2.0, `file:` URLs only) | Present                            |
| `require`                  | Absent; build one with `module.createRequire(import.meta.url)`                                           | Present                            |
| Resolution                 | `import.meta.resolve(specifier)`                                                                         | `require.resolve()`                |
| `this` at top level        | `undefined`                                                                                              | `module.exports`                   |
| Live bindings              | Yes — importers observe reassignment                                                                     | No — a snapshot at first `require` |

`import.meta.dirname` is only defined for `file:` modules. Code that may run from a `data:` URL, a blob-URL Worker, or a bundler shim must fall back to `new URL(".", import.meta.url)`.

`require(esm)` stopped throwing `ERR_REQUIRE_ESM` on Node v20.19.0, v22.12.0, and v23.0.0+ (it was behind `--experimental-require-module` before that) and is still labeled experimental. It still throws `ERR_REQUIRE_ASYNC_MODULE` when the module or any dependency uses top-level `await`. Detect support with `process.features.require_module`, gate a dual-mode package with the `"module-sync"` exports condition, and know that `--no-experimental-require-module` turns it back off.

Module syntax detection has been on by default since v22.7.0 (added v21.1.0 / v20.10.0): an ambiguous `.js` file with no controlling `"type"` is parsed as CommonJS and retried as ESM if that parse fails. It is a migration crutch with a measurable ESM parse cost, not the standard. Set `"type": "module"`.

### Module boundaries and side effects

A module boundary is an interface, not a file location.

1. **Export one thing or a named set, never both.** A module with a `default` _and_ named exports makes every consumer remember which is which, and `require(esm)` of it yields a namespace object where the default lives at `.default`. An ES module can override that by exporting the string key `"module.exports"`, but needing the escape hatch signals the shape is wrong.
2. **Barrel files (`index.js` re-exporting siblings) are convenience, not architecture.** They hide cycles and defeat tree-shaking when a re-export drags a side-effecting module into the graph.

Note the explicit `.js` extension in `export { parseConfig } from "./parse-config.js"`: ESM resolution is spec-mandated and never guesses extensions, so omitting it works in a bundler and fails under plain `node`.

Every top-level statement that is not a declaration runs on first import, in import order, exactly once — a global mutation with a hidden ordering dependency:

```js
registerPlugin("json", jsonPlugin);
process.env.APP_ENV ??= "development";
```

Prefer an explicit `createRegistry()` called from an entry point. When a side effect is unavoidable (a polyfill, a `customElements.define`), isolate it in a module whose name says so (`register-builtins.js`) and import it only from the entry point.

Import cycles surface as `ReferenceError: Cannot access 'X' before initialization` under ESM's live bindings, or as a silently `undefined` value under CommonJS — same code, two failure modes. Break the cycle by extracting the shared value into a third module, or convert the static import to a lazy `await import()` at the call site.

### Environment boundaries

Node, browsers, and edge runtimes differ, and bundlers shim one as the other.

| Capability           | Browser              | Node             | Edge / Worker                  |
| -------------------- | -------------------- | ---------------- | ------------------------------ |
| `fetch`              | Global               | Global since v18 | Global                         |
| `document`, `window` | Present              | Absent           | Absent                         |
| `process`            | Bundler-shimmed only | Global           | Partial / absent               |
| `Buffer`             | Bundler-shimmed only | Global           | Absent                         |
| `node:*` builtins    | No                   | Yes              | No (unless compatibility flag) |

Gate on the feature, never on a user-agent string or a guessed environment name:

```js
const hasStorage = typeof globalThis.localStorage !== "undefined";
const encoder = typeof TextEncoder === "function" ? new TextEncoder() : null;
```

The same applies to timers. `AbortSignal.timeout(ms)` (Node v17.3.0 / v16.14.0) and `AbortSignal.any(signals)` (Node v20.3.0 / v18.17.0) remove the hand-rolled `setTimeout` + `clearTimeout` dance:

```js
const response = await fetch(url, {
  signal: AbortSignal.any([userSignal, AbortSignal.timeout(5000)]),
});
```

## Values, Coercion, and Nullability

### Declarations, equality, and coercion

`const` by default; `let` only for a binding that is reassigned, and prefer restructuring so it isn't — accumulate with `map`/`reduce`, compute with a ternary. `var` is never correct: function-scoped, hoisted as `undefined`, re-declarable.

Use `===`/`!==` with one sanctioned exception: `value == null`, which matches `null` and `undefined` in a single check. The `"smart"` option of `eqeqeq` permits `==` for `typeof` comparisons, two literal operands, and comparisons against `null`; `["error", "always", { null: "ignore" }]` is the narrower policy allowing only the `null` case. The legacy `"allow-null"` option is deprecated in favor of that object form. Pick one policy and apply it everywhere — mixing `value === null` and `value == null` in one file means half the code silently misses `undefined`.

Traps that `===` alone does not fix:

| Expression                            | Result              | Why                                    |
| ------------------------------------- | ------------------- | -------------------------------------- |
| `[] + {}`                             | `"[object Object]"` | Both operands coerce to string         |
| `"5" * "2"`                           | `10`                | Arithmetic coerces to number           |
| `[1, 2, 3] + [4]`                     | `"1,2,34"`          | Arrays stringify via `join`            |
| `Number("")` / `Number(" ")`          | `0`                 | Empty and whitespace-only strings      |
| `parseInt("08px")`                    | `8`                 | Stops at the first non-digit, no error |
| `Number(null)` vs `Number(undefined)` | `0` vs `NaN`        | Different coercions                    |

Convert with `Number(...)` after validating, or `Number.parseInt(value, 10)` when a partial parse is genuinely intended. Validate with `Number.isFinite`, not the coercing global `isFinite` (`isFinite("5")` is `true`).

For property presence, `Object.hasOwn(obj, key)` (ES2022) beats `Object.prototype.hasOwnProperty.call(obj, key)` — shorter, and correct on `null`-prototype objects and objects that shadow `hasOwnProperty`. `key in obj` walks the prototype chain, which is rarely the intent.

### Nullish defaults and optional chaining

```js
const port = config.port ?? 8080;
const retries = options.retries ?? 0;
const city = user.address?.city ?? "Unknown";
```

`||` falls through on every falsy value: `0`, `""`, `false`, `NaN`. A retry count of `0`, an empty-string display name, and an explicitly disabled flag all silently become the fallback. Reserve `||` for boolean logic where any falsy input is equivalent.

Do not over-chain. `a?.b?.c?.d` asserts that three of four levels are expected to be absent; if that is true, the data model needs a decision, not more question marks. Optional chaining also does not guard a receiver that must exist: `obj.method?.()` still throws when `obj` is undefined. Write `obj?.method()`.

### Immutable data patterns

Treat arguments and returned structures as read-only. The non-mutating array methods (`toSorted`, `toReversed`, `toSpliced`, `with`) are ES2023, baseline widely available since July 2023, always return a new array built with the base `Array` constructor, and never mutate the receiver.

| Mutating              | Non-mutating replacement |
| --------------------- | ------------------------ |
| `arr.sort(fn)`        | `arr.toSorted(fn)`       |
| `arr.reverse()`       | `arr.toReversed()`       |
| `arr.splice(i, n, v)` | `arr.toSpliced(i, n, v)` |
| `arr[i] = v`          | `arr.with(i, v)`         |
| `arr.push(v)`         | `[...arr, v]`            |
| `arr.pop()`           | `arr.slice(0, -1)`       |
| `arr.shift()`         | `arr.slice(1)`           |
| `arr.unshift(v)`      | `arr.toSpliced(0, 0, v)` |

Objects: `{ ...state, status: "ready" }` for shallow copies, and be explicit that they are shallow.

`structuredClone(value)` (global in Node since v17.0.0, baseline in browsers since March 2022) deep-copies `Map`, `Set`, `Date`, `RegExp`, `ArrayBuffer`, and circular references. It is not a general object copier: it throws `DataCloneError` on functions and DOM nodes, does not walk or duplicate the prototype chain (a class instance returns as a plain object with its methods gone), drops property descriptors, getters, and setters, and does not preserve `RegExp.lastIndex` or class private fields. Only the built-in error names survive. Where those properties matter, write an explicit copy constructor.

Two adjacent traps: `Object.freeze` is shallow, so `obj.nested.x = 1` still succeeds; and the `to*` methods do not prevent mutation of an outer binding from inside a `map`/`filter` callback. `items.filter((item) => !seen.has(item.id) && seen.add(item.id))` works but is a side effect in a predicate — a second pass over the same input yields a different result if `seen` is reused. Prefer `Array.from(new Map(items.map((i) => [i.id, i])).values())`.

Destructuring documents the shape at the point of use, and the `= {}` is required when callers may pass nothing — without it, `connect()` throws on the destructure:

```js
function connect({ host, port = 5432, tls = false } = {}) {}
const { data: rows = [], error } = await fetchRows();
```

Defaults apply only to `undefined`, so a `null` argument bypasses them; validate nullable inputs explicitly. Keep destructured arity honest: six keys means six dependencies, and the function probably wants splitting.

## Asynchrony and Errors

### `async`/`await` over chains and callbacks

`await` reads top-to-bottom, throws at the failure point, and keeps the stack in the same frame as the `try`. `.then()` chains invert control flow and scatter the error path across `.catch()` handlers; Node-style `(err, result)` callbacks have no error path at all when the callback is never invoked. Enforce with `promise/prefer-await-to-then` (its `strict` option also flags `then`/`catch` following an `await`) and `promise/prefer-await-to-callbacks`.

```js
const response = await fetch(url);
if (!response.ok) throw new HttpError(response.status, await response.text());
const body = await response.json();
```

Where a callback cannot be avoided, wrap it once at the boundary — `new Promise((resolve, reject) => fs.readFile(path, "utf8", (error, data) => (error ? reject(error) : resolve(data))))` — instead of spreading the style inward. Never pass an `async` function where the callee ignores its return value: the rejection becomes unhandled, which is why `no-async-promise-executor` exists (a `Promise` constructor swallows an `async` executor's rejection).

### Choosing a combinator

| Combinator           | Fulfills with                                                                 | Rejects with                                   | Use when                                             |
| -------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------- | ---------------------------------------------------- |
| `Promise.all`        | Array of values, input order                                                  | First rejection                                | Every result is required; fail-fast is correct       |
| `Promise.allSettled` | Array of `{ status: "fulfilled", value }` or `{ status: "rejected", reason }` | Never (unless iteration itself throws)         | Partial results are useful; report per-item outcomes |
| `Promise.any`        | First fulfillment value                                                       | `AggregateError` with `.errors` in input order | Any one source suffices (mirrors, hedged requests)   |
| `Promise.race`       | First settled value, fulfillment or rejection                                 | First rejection                                | Whichever settles first matters — including failure  |

The edge cases carry the bugs. `Promise.all([])` fulfills with `[]`; `Promise.any([])` rejects immediately with an `AggregateError` because no input can fulfill; `Promise.allSettled([])` fulfills with `[]`. `Promise.all` does not cancel siblings when one rejects — the rest keep running and their results are discarded. `Promise.race` is a timeout only if the loser is also cancelled; otherwise the slow request keeps consuming a connection. Fan-out over a collection needs `await Promise.all(items.map(async (item) => ...))`, not `items.map(...)` alone, which returns an array of promises.

### Floating promises and unhandled rejections

A promise neither awaited nor given a rejection handler is floating. Its rejection becomes an `unhandledRejection` — fatal by default on current Node, and in browsers reported to `window.onunhandledrejection` or to nobody. `@typescript-eslint/no-floating-promises` requires one of three explicit dispositions:

```js
await saveDraft(); // await it
void warmCache(); // deliberately ignored, marked
saveDraft().catch((error) => log(error)); // handled
```

Detection needs type information: the rule must know which imports return promises. Configure `parserOptions.projectService: true`, which resolves the nearest `tsconfig.json` per file and replaces the older `parserOptions.project: true`. For plain JavaScript, enable `checkJs` so JSDoc-annotated functions participate.

`require-atomic-updates` covers the adjacent hazard — assigning to a shared variable across an `await`, where another task wrote to it in the interim:

```js
const current = count;
await persist(current);
count = current + 1;
```

Two concurrent calls lose an update. Read, transform, and write with no intervening `await`, or serialize the critical section.

### Typed errors and `cause`

Throw `Error` instances, never strings or plain objects — a string has no `stack`, and `catch (e) { e.message }` is `undefined`. Use a small hierarchy so callers branch on type instead of matching message text:

```js
export class AppError extends Error {
  constructor(message, options) {
    super(message, options);
    this.name = new.target.name;
  }
}

export class ValidationError extends AppError {
  constructor(message, { field, cause } = {}) {
    super(message, { cause });
    this.field = field;
  }
}
```

The `options` argument must reach `super()` or `cause` is never installed. `cause` (ES2022) preserves the original error across a rethrow and may hold any value — MDN's own guidance is structured data when the message is for humans but the caller must parse the failure: `throw new AppError("RSA key generation requires integer inputs.", { cause: { code: "NonInteger", values: [p, q] } })`.

`AggregateError(errors, message, options)` represents several unrelated failures from one operation; `Promise.any` produces it natively. Prefer `Error.isError(value)` over `instanceof Error` when the value may cross a realm (iframe, Worker, `vm` context) — `instanceof` fails there because constructor identity differs. `Error.isError` is not yet baseline, so feature-detect before depending on it in browser code.

In `catch` blocks the binding is `unknown` in TypeScript and untyped in JavaScript: narrow before use, and never assume the thrown value is an `Error`. `@typescript-eslint/use-unknown-in-catch-callback-variable` enforces `unknown` on rejection-callback parameters, which TypeScript would otherwise default to `any`:

```js
try {
  await risky();
} catch (error) {
  const cause = error instanceof Error ? error : new Error(String(error));
  throw new AppError("Risky operation failed.", { cause });
}
```

## Naming, Shape, and Tooling

### Naming

| Kind                             | Convention                             | Example                                           |
| -------------------------------- | -------------------------------------- | ------------------------------------------------- |
| Boolean variable or property     | `is` / `has` / `can` / `should` prefix | `isDirty`, `hasNextPage`, `canRetry`              |
| Predicate function               | `isX` / `hasX` / `canX`                | `isExpired(token)`, `hasPermission(user, action)` |
| Event handler prop               | `onX`                                  | `onSubmit`, `onClose`                             |
| Event handler implementation     | `handleX`                              | `handleSubmit`, `handleKeyDown`                   |
| Async function returning a value | Verb phrase, no `get` prefix           | `fetchProfile(id)`                                |
| Module / file                    | `kebab-case`                           | `parse-config.js`                                 |

The prefix is load-bearing: `active` and `isActive` read as different types to the next caller, and a predicate named `validEmail` reads as a value rather than a function. The `on`/`handle` split matters because `onSubmit` receives a handler while `handleSubmit` _is_ the handler — swapping them yields props that are silently never called.

### Array methods over manual loops

`map`, `filter`, `find`, `some`, `every`, `reduce`, `flatMap`, and `findLast` (ES2023) state intent; a `for` loop with a `push` states mechanics.

```js
const names = users.map((user) => user.name);
const hasAdmin = users.some((user) => user.role === "admin");
const byTeam = Object.groupBy(users, (user) => user.team);
```

Never use `forEach` to build an array — `map` returns, `forEach` does not. Keep a loop when it is genuinely right: an early exit `some`/`find` cannot express, sequential `await` for rate limits (`no-await-in-loop` flags it — suppress deliberately, with a comment explaining the ordering requirement), or in-place writes to a preallocated typed array for performance. `reduce` is the most overused method: when the accumulator is not a scalar and the callback exceeds three lines, a loop or a named helper reads better. `Array.prototype.at(-1)` (ES2022) replaces `arr[arr.length - 1]`, and `findLast` replaces `[...arr].reverse().find(...)`, which is a copy _and_ a reverse to answer one question.

### JSDoc for public APIs

Annotate anything exported from a package or consumed by another team. `@param`, `@returns`, `@throws`, and `@example` are the minimum; `@typedef` names structural types for reuse, and `@template T` makes the return type track the operation's resolution type.

```js
/** @typedef {{ attempts?: number, baseDelayMs?: number }} RetryOptions */

/**
 * @param {() => Promise<T>} operation
 * @param {RetryOptions} [options]
 * @returns {Promise<T>}
 * @template T
 */
export async function retry(operation, options = {}) {}
```

Where the project runs `checkJs`, these annotations are real checking: set `"checkJs": true` in `tsconfig.json` or `// @ts-check` at the top of a file, and a wrong `@returns` becomes a compile error. JSDoc is not a substitute for a `.d.ts` when TypeScript consumers import the package, but it is the only typed contract available to plain-JavaScript callers.

### ESLint flat config and Prettier

Flat config (`eslint.config.js`) is the default since ESLint v9.0.0; `.eslintrc.*` is legacy. Use `defineConfig` and `globalIgnores` from `eslint/config` (both added in v9.22.0, also published as `@eslint/config-helpers` for older versions).

```js
import { defineConfig, globalIgnores } from "eslint/config";
import js from "@eslint/js";
import globals from "globals";
import promise from "eslint-plugin-promise";
import node from "eslint-plugin-n";

export default defineConfig([
  globalIgnores(["dist/", "coverage/"]),
  {
    files: ["**/*.js"],
    plugins: { js, promise, n: node },
    extends: [
      "js/recommended",
      "promise/flat/recommended",
      "n/recommended-module",
    ],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.node },
    },
    rules: {
      eqeqeq: ["error", "always", { null: "ignore" }],
      "no-var": "error",
      "prefer-const": "error",
      "no-implicit-globals": "error",
      "no-await-in-loop": "warn",
      "require-atomic-updates": "error",
    },
  },
]);
```

Each `extends` entry is `pluginName/configKey`, resolved against that plugin's `configs` object — so `promise/flat/recommended` and `n/recommended-module` are the flat keys those plugins export. Two details cause real breakage. `globalIgnores` exists because an `ignores` key with no sibling properties acts globally while the same key _with_ `rules` or `files` acts as a local exclusion; the helper makes the intent explicit. And `languageOptions` is the flat-config home for what `.eslintrc` split across `parserOptions`, `globals`, and `env` — there is no `env` key, and runtime globals come from the `globals` package.

Rules this domain needs beyond `js/recommended`: `promise/prefer-await-to-then` and `promise/prefer-await-to-callbacks` (`.then()` chains and callback async), `promise/catch-or-return` / `promise/always-return` / `promise/param-names` / `promise/no-return-wrap` (malformed promise construction), `n/prefer-node-protocol` (`require("fs")` instead of `require("node:fs")`), and `import-x/no-cycle` / `import-x/order` (circular imports, inconsistent import grouping). `eslint-plugin-import-x` is the maintained fork of `eslint-plugin-import` with a lighter dependency tree — choose one, never both. `eslint-plugin-n` ships `recommended-module` (all files ESM) and `recommended-script` (all files CommonJS); pick the one matching `"type"`, not `recommended`, which guesses per file.

Prettier owns formatting, ESLint owns correctness, and neither should do the other's job — disable ESLint's stylistic rules via the Prettier config rather than hand-maintaining a conflict list. Prettier 3 defaults: `printWidth: 80`, `semi: true`, `singleQuote: false`, `trailingComma: "all"` — the last changed from `"es5"` in Prettier 3.0, so the first run reformats every function-call argument list in the repository. Pin the decision in a committed config (`prettier.config.mjs` for ESM projects).

## Common Mistakes

| Mistake                                              | Why It Breaks                                                               | Correct Approach                                                |
| ---------------------------------------------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `value \|\| fallback` for a default                  | `0`, `""`, `false`, `NaN` are replaced by the fallback                      | `value ?? fallback` when only `null`/`undefined` should trigger |
| Mixing `x === null` and `x == null` in one file      | `=== null` misses `undefined`; the checks are not equivalent                | Adopt one policy and enforce it with `eqeqeq`                   |
| `Promise.all` where partial results are needed       | One rejection discards every success, and siblings keep running uncancelled | `Promise.allSettled` and handle each `status`                   |
| `Promise.race` as a timeout without cancellation     | The losing request keeps a connection and its rejection may surface later   | `AbortSignal.any([userSignal, AbortSignal.timeout(ms)])`        |
| `await` in a loop over independent work              | Serializes I/O; `no-await-in-loop` fires for a reason                       | `await Promise.all(items.map(async (item) => ...))`             |
| Floating promise in a handler or timer               | Becomes an `unhandledRejection`; fatal by default on current Node           | `await`, `void`, or `.catch()`; enable `no-floating-promises`   |
| `throw "not found"`                                  | The value has no `stack`; `catch (e) { e.message }` is `undefined`          | Throw an `Error` subclass, pass the original via `{ cause }`    |
| Subclass constructor omits `super(message, options)` | `cause` is never installed and the original error is lost                   | Forward `options` to `super()` in every error subclass          |
| `structuredClone` on a class instance                | The prototype chain is discarded; the copy is a plain object                | Write an explicit copy constructor or `fromJSON` factory        |
| `arr.sort()` / `arr.splice()` on a caller's array    | Mutates the argument; the caller's iteration changes underneath it          | `toSorted()` / `toSpliced()` / `with()`                         |
| Module-level `process.env.X ??= ...`                 | Runs on import, in an order the importer does not control                   | Initialize inside a function called by the entry point          |
| Undeclared assignment in a sloppy-mode CJS file      | Creates an implicit global shared across the process                        | Declare with `const`/`let`; enable `no-implicit-globals`        |
| Dereferencing the `catch` binding directly           | The thrown value may be a string, plain object, or cross-realm error        | Narrow with `instanceof Error` (or `Error.isError`) first       |

## Checklist

1. Confirm `package.json` declares `"type": "module"`, every `.js` file under `src/` uses `import`/`export`, and every relative import carries an explicit `.js` extension; list remaining `.cjs` files and state why each exists.
2. Grep for `require(`, `module.exports`, `exports.`, `__dirname`, and `__filename`; replace each with its ESM equivalent or `module.createRequire(import.meta.url)`.
3. Build the dependency graph or run `import-x/no-cycle`; break each cycle by extracting the shared value or converting the edge to a dynamic `await import()`.
4. Inventory top-level statements that are not declarations, and move each into an explicitly called initialization function unless it is an isolated polyfill module.
5. Replace every `var` with `const`, then downgrade to `let` only where reassignment actually occurs.
6. Set the `eqeqeq` policy in the ESLint config and fix every inconsistent `null` comparison the policy forbids.
7. Grep for `||` used as a default-value operator and replace with `??` wherever a falsy-but-valid value (`0`, `""`, `false`) is possible.
8. Flag every optional chain longer than two `?.` links for a data-model decision rather than a code fix.
9. Replace in-place mutation of shared or parameter arrays (`sort`, `reverse`, `splice`, `push`, `pop`, `shift`, `unshift`) with the `to*` copy equivalents.
10. Replace `JSON.parse(JSON.stringify(x))` and hand-rolled deep-clone helpers with `structuredClone`, confirming the value holds no functions, DOM nodes, class instances, or getters.
11. For each `Promise.all`, confirm fail-fast is intended; otherwise switch to `Promise.allSettled` and handle `status` per item.
12. Enable `no-floating-promises` with `parserOptions.projectService: true` (and `checkJs` for JavaScript files), then give every reported promise an `await`, a `void`, or a `.catch()`.
13. Convert every `throw` of a non-`Error` value into an `Error` subclass that forwards `options` to `super()`, and verify each `catch` block narrows before dereferencing.
14. Replace manual `for`-with-`push` loops with `map`/`filter`/`reduce`, and confirm no `map`/`filter` callback mutates an outer binding.
15. Apply the naming table: bare booleans become `is`/`has`/`can`/`should`, `onX` stays a handler prop, implementations become `handleX`, predicates become `isX`.
16. Add `@param`, `@returns`, `@throws`, and `@template` JSDoc to every exported function; enable `checkJs` if the project already has a `tsconfig.json`.
17. Confirm the ESLint config is `eslint.config.js` using `defineConfig` and `globalIgnores`, with `languageOptions.sourceType: "module"` and runtime globals from the `globals` package.
18. Confirm Prettier and ESLint do not both own formatting, that the Prettier config is committed, and that `trailingComma: "all"` has been applied repository-wide.
19. Confirm no environment-specific global (`window`, `document`, `process`, `Buffer`) is referenced outside a guarded or platform-specific module, and prefer `AbortSignal.timeout`/`AbortSignal.any` over hand-rolled timer cancellation.

## References

- [ECMAScript Language Specification](https://tc39.es/ecma262/) — normative semantics for coercion, strict mode, and the array copy methods.
- [MDN: Equality comparisons and sameness](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Equality_comparisons_and_sameness) — the coercion and `SameValueZero` rules behind `===` and `Object.is`.
- [MDN: Nullish coalescing operator](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Nullish_coalescing) — the exact falsy-versus-nullish distinction.
- [MDN: Array](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array) — the authoritative mutating-to-copy method table.
- [MDN: Promise.any()](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/any) and [Promise.allSettled()](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/allSettled) — combinator result shapes and empty-iterable behavior.
- [MDN: Error cause](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error/cause) and [AggregateError()](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/AggregateError/AggregateError) — error chaining and multi-failure aggregation.
- [MDN: The structured clone algorithm](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Structured_clone_algorithm) — supported types, `DataCloneError`, and what a clone does not preserve.
- [Node.js: ECMAScript modules](https://nodejs.org/api/esm.html) — `import.meta.dirname`/`filename`, interop rules, and the ESM resolver algorithm.
- [Node.js: CommonJS modules](https://nodejs.org/api/modules.html) — `require(esm)` version history, `ERR_REQUIRE_ASYNC_MODULE`, and `process.features.require_module`.
- [Node.js v22.7.0 release notes](https://nodejs.org/en/blog/release/v22.7.0) — module syntax detection enabled by default, and its cost.
- [ESLint: Configuration Files (flat config)](https://eslint.org/docs/latest/use/configure/configuration-files) — `languageOptions`, `globalIgnores`, and global-versus-local `ignores`.
- [ESLint v9.22.0 release: `defineConfig()` and `globalIgnores()`](https://eslint.org/blog/2025/03/eslint-v9.22.0-released/) — the version that introduced both helpers.
- [ESLint: `eqeqeq`](https://eslint.org/docs/latest/rules/eqeqeq) — the `"smart"` option and the `{ null: "always" | "never" | "ignore" }` object form.
- [typescript-eslint: `no-floating-promises`](https://typescript-eslint.io/rules/no-floating-promises/) and [`use-unknown-in-catch-callback-variable`](https://typescript-eslint.io/rules/use-unknown-in-catch-callback-variable/) — sanctioned promise dispositions and `unknown` in catch callbacks.
- [typescript-eslint: typed linting](https://typescript-eslint.io/blog/typed-linting/) — why promise rules require type information, and `projectService`.
- [eslint-plugin-promise](https://github.com/eslint-community/eslint-plugin-promise), [eslint-plugin-n](https://github.com/eslint-community/eslint-plugin-n), [eslint-plugin-import-x](https://github.com/un-ts/eslint-plugin-import-x) — rule inventories and flat config names.
- [Prettier: Options](https://prettier.io/docs/options) and [Prettier 3.0 release notes](https://prettier.io/blog/2023/07/05/3.0.0.html) — the `trailingComma: "all"` default change.
