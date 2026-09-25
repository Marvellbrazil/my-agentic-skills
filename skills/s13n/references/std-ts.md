# TypeScript Standards

TypeScript's type system is erased at emit, so every guarantee it offers is a compile-time claim that holds only up to the first untyped value crossing into the program. A codebase that sets `strict` but reaches for `any`, `as`, and `!` has annotations that describe intent without enforcing it, and the resulting failure — `undefined` on a property access, a typo'd discriminant, a raw string where a validated ID was expected — surfaces at runtime with no compile-time trace. This module defines the compiler configuration, modeling idioms, and boundary-validation discipline that make the checker load-bearing rather than decorative.

## Contents

- [When This Applies](#when-this-applies)
- [Compiler Configuration Is the Contract](#compiler-configuration-is-the-contract)
- [Types That Cannot Lie](#types-that-cannot-lie)
- [Modeling State and Identity](#modeling-state-and-identity)
- [Runtime Validation at the Boundary](#runtime-validation-at-the-boundary)
- [Module and Declaration Hygiene](#module-and-declaration-hygiene)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- A `tsconfig.json` exists, is being created, or is being normalized across packages in a monorepo.
- The codebase contains `any`, `@ts-ignore`, `@ts-nocheck`, `@ts-expect-error`, or postfix `!` non-null assertions.
- Types are declared by hand next to an API/JSON/form boundary instead of being derived from a runtime schema.
- `enum` declarations, `namespace` with runtime code, or parameter properties appear in source that must run under Node's type stripping or a bundler.
- A published library needs `.d.ts` output, an `exports` map, or a `types` condition to resolve correctly for consumers.
- New code targets TypeScript 6 or 7 and must survive the deprecations that became hard errors in 7.0.

## Compiler Configuration Is the Contract

Strictness is a migration cost that only grows: a project that enables it at file one pays nothing, and a project that enables it at file ten thousand pays for every file at once. `strict` is a family flag — turning it on enables `alwaysStrict`, `strictNullChecks`, `strictBindCallApply`, `strictBuiltinIteratorReturn`, `strictFunctionTypes`, `strictPropertyInitialization`, `noImplicitAny`, `noImplicitThis`, and `useUnknownInCatchVariables`. The flags below it are _not_ in the family and must be set explicitly.

```jsonc
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitReturns": true,
    "noPropertyAccessFromIndexSignature": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,

    "module": "nodenext",
    "moduleResolution": "nodenext",
    "moduleDetection": "force",
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "noUncheckedSideEffectImports": true,

    "target": "es2023",
    "lib": ["es2023"],
    "types": ["node"],

    "skipLibCheck": true,
    "sourceMap": true,
    "declaration": true,
    "declarationMap": true,
  },
}
```

What each non-obvious flag actually buys, and what breaks without it:

| Flag                                 | Effect                                                                              | Failure it prevents                                                                                                                       |
| ------------------------------------ | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `noUncheckedIndexedAccess`           | Every index signature and array access yields `T \| undefined`.                     | `text.split(" ")[0].toLowerCase()` throwing `TypeError` on an empty string (`TS2532`).                                                    |
| `exactOptionalPropertyTypes`         | `age?: number` means the key is absent or a `number` — never `number \| undefined`. | `{ name: filters.name }` silently writing an explicit `undefined` key (`TS2375`), which changes `"key" in obj` and `Object.keys` results. |
| `noImplicitOverride`                 | Subclass members that shadow a base member require the `override` keyword.          | A base method renamed during refactor leaving the subclass method orphaned and never called (`TS4114`).                                   |
| `noPropertyAccessFromIndexSignature` | Dotted access on an index signature is an error; bracket access is required.        | A misspelled property silently typed `T \| undefined` instead of flagged (`TS4111`).                                                      |
| `verbatimModuleSyntax`               | Emit preserves exactly what you wrote; nothing is elided or rewritten.              | A type-only import becoming a runtime `require` under a single-file transpiler (`TS1484`).                                                |
| `erasableSyntaxOnly`                 | Rejects `enum`, runtime `namespace`, parameter properties, `import =`/`export =`.   | Source that compiles under `tsc` but throws under Node type stripping or a bundler (`TS1294`).                                            |
| `noUncheckedSideEffectImports`       | A bare `import "./x"` must resolve.                                                 | A typo'd CSS or polyfill import that silently no-ops (`TS2882`).                                                                          |
| `moduleDetection: "force"`           | Every non-declaration file is a module.                                             | A file without imports becoming a global script whose top-level names collide.                                                            |

`verbatimModuleSyntax` also means `import type { X }` and `import { type X }` are the only ways to import a type, and it forbids ESM syntax in a file emitted as CommonJS (`TS1287`). That is the point: under `module: "nodenext"`, forgetting `"type": "module"` in `package.json` becomes a compile error instead of a silent CommonJS emit.

**Version drift is a real migration.** TypeScript 6.0 made `strict` default `true`, `module` default `esnext`, `types` default `[]`, and `rootDir` default to the config's directory; it also deprecated `target: es5`, `downlevelIteration`, `moduleResolution: node`/`node10`/`classic`, `module: amd|umd|systemjs|none`, `baseUrl`, the `module` keyword for namespaces, and `asserts` on imports. TypeScript 7.0 — the native Go port, distributed as `typescript@7` — turns those into hard errors and additionally assumes `alwaysStrict` and forbids `esModuleInterop: false`. A `tsconfig.json` copied from a 5.x project will not build. Pin the version, and let `tsc --init` (which since 5.9 emits a minimal config with `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` already on) or `@andrewbranch/ts5to6` do the mechanical migration.

For a library, declaration output is part of the contract:

```jsonc
{
  "compilerOptions": {
    "declaration": true,
    "declarationMap": true,
    "isolatedDeclarations": true,
  },
}
```

`isolatedDeclarations` requires `declaration` or `composite` (`TS5069`) and forces explicit return types and exported-variable annotations so that declaration emit never needs cross-file inference. It reports `TS9010` (variable needs an annotation), `TS9013` (expression type can't be inferred in isolation), and `TS9039` (exported type references a private name). Locals are exempt — only the public surface is constrained.

## Types That Cannot Lie

The banned constructs are banned because each one converts a compile-time question into a runtime one without leaving a trace:

- **`any`** disables checking transitively through every assignment it touches, and it is contagious: `any` in, `any` out.
- **`@ts-ignore`** suppresses an error and stays silent forever, including after the underlying bug is fixed.
- **`@ts-nocheck`** disables the file, which is the same as deleting the file from the type graph.
- **`@ts-expect-error`** is the only acceptable suppression, because the compiler reports it as unused (`TS2578`) once the error disappears.
- **Postfix `!`** asserts non-nullness at a point the compiler could not verify; it is a runtime crash deferred to whichever input path reaches it first.

`unknown` is the replacement for `any` at every untyped entry point, and narrowing is the replacement for assertion:

```ts
export function readLength(raw: unknown): number {
  if (typeof raw !== "string") {
    throw new TypeError("expected a string");
  }
  return raw.length;
}

export function readMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === "string") return err;
  return "unknown error";
}
```

Type predicates close the loop for reusable guards, and TypeScript 5.5+ infers them for simple bodies, so `(x): x is T` is often unnecessary:

```ts
const ROLES = ["admin", "editor", "viewer"] as const;
export type Role = (typeof ROLES)[number];

export function isRole(value: string): value is Role {
  return (ROLES as readonly string[]).includes(value);
}
```

Predicates have if-and-only-if semantics. `filter((v) => !!v)` infers no predicate for `number | undefined` (falsy `0` breaks the negative case) and yields `TS18048` downstream; `filter((v) => v !== undefined)` narrows correctly.

`satisfies` validates an expression against a type _without_ widening it, which is the correct tool whenever an annotation would destroy useful literal information:

```ts
type Route = "home" | "search" | "settings";

export const routes = {
  home: { title: "Home", requiresAuth: false },
  search: { title: "Search", requiresAuth: false },
  settings: { title: "Settings", requiresAuth: true },
} satisfies Record<Route, { title: string; requiresAuth: boolean }>;
```

A typo'd key or a missing route fails here; `routes.settings.requiresAuth` keeps its precise type. Contrast with `const routes: RouteConfig = {...}`, which type-checks but erases the per-property types, and with `as const satisfies`, which additionally preserves literal values.

The last resort, `as`, is a claim the compiler does not verify. `input as PaymentEvent` compiles cleanly on `unknown` input and will produce an object with `undefined` where `amountCents` was expected. Assertions belong only where a preceding runtime check has already established the invariant — a `parseUserId` that validates a regex and then returns `raw as UserId` is honest; a function whose whole body is `return input as T` is a lie with a type annotation.

## Modeling State and Identity

**Discriminated unions for state, exhaustive switch for handling.** A union of object types sharing a literal discriminant makes illegal states unrepresentable — no `isLoading`/`isError`/`data` triple where two fields can be set at once.

```ts
type Order =
  | { status: "pending"; createdAt: Date }
  | { status: "paid"; paidAt: Date; amountCents: number }
  | { status: "shipped"; trackingId: string };

export function describeOrder(order: Order): string {
  switch (order.status) {
    case "pending":
      return `pending since ${order.createdAt.toISOString()}`;
    case "paid":
      return `paid ${order.amountCents} at ${order.paidAt.toISOString()}`;
    case "shipped":
      return `tracking ${order.trackingId}`;
    default: {
      const unhandled: never = order;
      throw new Error(`unhandled order status: ${String(unhandled)}`);
    }
  }
}
```

The `default` branch assigns to `never`, so adding a fourth variant to `Order` breaks the build at every switch that handles it. The same discipline exists outside TypeScript: Java 21 requires `switch` over a sealed hierarchy with pattern labels to be exhaustive at compile time, and Go's `exhaustive` analyzer checks enum switches because the language does not.

**`type` vs `interface`.** Use `interface` when the shape is an object contract that consumers may extend or that benefits from declaration merging (augmenting a library's `Request` type); use `type` for everything else — unions, tuples, mapped types, conditional types, branded primitives. Interfaces cannot express a union or an intersection-with-conditional, and a `type` cannot be reopened. The practical rule: if it is a union, it must be a `type`.

**No `enum`.** Numeric enums are not erasable (`TS1294`), `const enum` breaks under `isolatedModules` and single-file transpilers, and both emit a runtime object with reverse mappings. Use an `as const` object plus a derived union:

```ts
export const OrderStatus = {
  Pending: "pending",
  Paid: "paid",
  Shipped: "shipped",
} as const;

export type OrderStatus = (typeof OrderStatus)[keyof typeof OrderStatus];

export const TERMINAL_STATUSES: readonly OrderStatus[] = [OrderStatus.Shipped];
```

This is JSON-serializable, tree-shakable, erasable, and gives string literal types rather than opaque numbers.

**Branded types for IDs and units.** `UserId`, `OrderId`, and `ProductId` are all `string`; `Cents` and `Milliseconds` are both `number`. A structural type system cannot distinguish them, so argument-order bugs pass review.

```ts
declare const CentsBrand: unique symbol;
export type Cents = number & { readonly [CentsBrand]: "Cents" };

export function toCents(dollars: number): Cents {
  return Math.round(dollars * 100) as Cents;
}

declare function charge(user: UserId, amount: Cents): void;

charge(parseUserId("usr_0123456789abcdef"), toCents(12.5));
charge(parseUserId("usr_0123456789abcdef"), 1250);
//                                              ~~~~ Argument of type 'number' is not
//                                                   assignable to parameter of type 'Cents'.
```

The assertion is confined to the constructor, which is the one place the invariant is established. Other ecosystems express the same idea with the language's own nominal machinery — Python's `typing.NewType` and Rust's newtype struct — but the TypeScript version costs nothing at runtime.

**Generics relate types; a parameter used once relates nothing.** `<T extends string>(x: T): T` is fine; `<T>(x: string): T` is not generics, it is `any` with extra steps. Constrain with `extends`, prefer inference over explicit type arguments at call sites, and use `const T extends readonly string[]` (TypeScript 5.0) to get literal-tuple inference without callers writing `as const`:

```ts
declare function on<const T extends readonly EventName[]>(
  names: T,
  handler: (name: T[number]) => void,
): void;

on(["click", "focus"], (name) => {
  const narrowed: "click" | "focus" = name;
});
```

Use `NoInfer<T>` (5.4) when one parameter must not feed inference — the canonical case is a default value that must be drawn from the primary argument's inferred union, not widen it.

**Utility types over hand-rolled duplicates.** `Partial`, `Required`, `Pick`, `Omit`, `Record`, `ReturnType`, `Parameters`, `Awaited`, and `NoInfer` are the standard vocabulary. A locally declared `type MyReturn = { id: string; name: string }` that duplicates what `Awaited<ReturnType<typeof fetchUser>>` would derive will drift the moment the function changes. Note `Awaited<Promise<Promise<number>>>` resolves recursively to `number` — it models `await`, not a single unwrap.

**Annotate at boundaries, infer in the body.** Local variables should be inferred; exported functions, exported constants, and object-literal returns should be annotated so that changing an implementation detail cannot silently change a public type. With `isolatedDeclarations` on, this stops being a style preference and becomes a build requirement.

## Runtime Validation at the Boundary

Types are erased, so a value typed `Order` is only an `Order` if something checked it. JSON responses, `localStorage`, query strings, env vars, form input, IPC messages, and CLI arguments are all `unknown` until parsed. The schema is the single source of truth; the type is derived from it.

```ts
import { z } from "zod";

export const OrderSchema = z.discriminatedUnion("status", [
  z.object({ status: z.literal("pending"), createdAt: z.iso.datetime() }),
  z.object({
    status: z.literal("paid"),
    paidAt: z.iso.datetime(),
    amountCents: z.int().nonnegative(),
  }),
  z.object({ status: z.literal("shipped"), trackingId: z.string().min(1) }),
]);

export type Order = z.infer<typeof OrderSchema>;

export function parseOrder(input: unknown): Order {
  const result = OrderSchema.safeParse(input);
  if (!result.success) {
    throw new Error(
      result.error.issues
        .map((i) => `${i.path.join(".")}: ${i.message}`)
        .join("; "),
    );
  }
  return result.data;
}
```

`z.infer` is `z.output`; when a schema transforms, `z.input` differs and is what the caller must supply — a schema with `.default(3)` accepts `{}` and produces `{ retries: 3 }`, so the wire type and the domain type are genuinely different types and both need names. `z.strictObject` rejects unknown keys (`unrecognized_keys`), which is the right default for internal payloads and the wrong one for forward-compatible third-party APIs. Zod 4 hoists formats to top level (`z.email()`, `z.uuid()`, `z.iso.datetime()`, `z.int()`), accepts an array in `z.literal(["paid", "pending"])`, and supports `z.brand()` so a schema can both validate and produce a nominal type.

Valibot 1.5 trades the fluent API for a functional one with per-schema tree-shaking, which matters for client bundles:

```ts
import * as v from "valibot";

const OrderSchema = v.variant("status", [
  v.object({
    status: v.literal("pending"),
    createdAt: v.pipe(v.string(), v.isoDateTime()),
  }),
  v.object({
    status: v.literal("paid"),
    amountCents: v.pipe(v.number(), v.integer(), v.minValue(0)),
  }),
]);

type Order = v.InferOutput<typeof OrderSchema>;
type OrderInput = v.InferInput<typeof OrderSchema>;

const result = v.safeParse(OrderSchema, { status: "paid", amountCents: 1250 });
```

The concept is not JavaScript-specific. Pydantic does the same thing with `model_validate` and `ConfigDict(strict=True, extra="forbid")`, where strict mode disables the coercion that would otherwise turn `"123"` into `123` — the same trap Zod's `z.coerce.number()` opens deliberately.

Two rules make schema-first work:

1. **Never derive the schema from the type.** `z.ZodType<Order>` as an annotation is acceptable only to satisfy `isolatedDeclarations`; deriving validation from a hand-written interface is not possible, which is the whole point.
2. **Validate once, at the edge.** Re-parsing inside the domain means the domain does not trust its own types. Parse at the HTTP client, the env loader, the `JSON.parse` wrapper — then pass typed values inward.

## Module and Declaration Hygiene

- **Type-only imports must be explicit.** Under `verbatimModuleSyntax`, `import { type UserId }` or `import type { UserId }` is mandatory for anything that is not a value (`TS1484`); the fix is `import { USER_ID_PREFIX, type UserId } from "./domain.js"`.
- **Relative specifiers carry the emitted extension.** Under `module: "nodenext"`, write `./util.js`. If the source is run directly by Node's type stripping, `./util.ts` is valid only with `allowImportingTsExtensions`, which itself requires `noEmit`, `emitDeclarationOnly`, or `rewriteRelativeImportExtensions` (`TS5096`); `rewriteRelativeImportExtensions` (5.7) is what rewrites `./util.ts` to `./util.js` in the emitted output.
- **No barrel-file type churn.** A `index.ts` that re-exports every type from every module creates import cycles, defeats `isolatedDeclarations` fast paths, and makes every consumer's compile depend on the whole graph. Export from the owning module; reserve the barrel for a curated public API.
- **Declaration hygiene.** `stripInternal` removes `@internal`-marked declarations from `.d.ts` output but the compiler does not verify the result is still valid — use it knowingly, or use API Extractor for real visibility tiers. `declarationMap` makes go-to-definition land on source rather than on the emitted declaration.
- **Verify the published artifact, not the source.** `npx publint` catches `exports`/`types` misconfiguration, and `npx --yes @arethetypeswrong/cli --pack .` resolves the package under `node10`, `node16` (from CJS and from ESM), and `bundler`, flagging masquerading CJS/ESM and false default exports. A package that type-checks locally can still be unimportable by consumers.

## Common Mistakes

| Mistake                                                                        | Why It Breaks                                                                                                                       | Correct Approach                                                                                                    |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `catch (e) { e.message }`                                                      | `useUnknownInCatchVariables` (part of `strict`) types `e` as `unknown`; the property access is `TS18046`.                           | Narrow first: `if (e instanceof Error) return e.message;`.                                                          |
| `value as SomeType` on parsed JSON                                             | Assertions are unchecked claims; a renamed or missing field flows into the domain as `undefined` with the declared type.            | Parse with Zod/Valibot at the boundary and derive the type with `z.infer` / `v.InferOutput`.                        |
| `// @ts-ignore` above a real error                                             | Suppresses silently and permanently, surviving the fix that made it unnecessary.                                                    | `// @ts-expect-error` with a one-line reason, so the compiler flags it as unused (`TS2578`) when the error is gone. |
| `x!.y` after `x` came from a lookup                                            | The assertion is unverified; the crash moves to the input path that produces the miss.                                              | Narrow (`if (!x) return;`) or use `noUncheckedIndexedAccess` and handle the `undefined` branch.                     |
| `enum Status { Pending, Paid }`                                                | Not erasable (`TS1294` under `erasableSyntaxOnly`), breaks under Node type stripping, emits a runtime object with reverse mappings. | `const OrderStatus = { Pending: "pending" } as const` plus `(typeof OrderStatus)[keyof typeof OrderStatus]`.        |
| `const config: Config = {...}` where literals matter                           | The annotation widens values, losing the literal types and autocomplete that made the object useful.                                | `satisfies Config` (or `as const satisfies Config` to also freeze literals).                                        |
| `<T>(items: T[]): T` on a one-use parameter                                    | A type parameter used once relates nothing and is `any` in disguise; callers lose inference quality.                                | Take the concrete type (`(items: string[]): string`), or constrain the parameter so it relates two positions.       |
| Hand-written `interface ApiResponse` beside the fetch call                     | The interface and the wire format drift independently; nothing fails when the server changes a field.                               | Define the schema once, infer the type, and validate the response body through it.                                  |
| `import { UserId } from "./types"` under `verbatimModuleSyntax`                | `UserId` is a type; the import is a compile error (`TS1484`) or becomes a runtime import under a transpiler.                        | `import { type UserId } from "./types"`.                                                                            |
| `export function makeThing() { return internal; }` with `isolatedDeclarations` | Declaration emit needs cross-file inference, which the flag forbids (`TS9039`/`TS9013`).                                            | Annotate the return type explicitly, or keep the value unexported.                                                  |
| `const routes: Record<Route, Cfg>` with a typo'd key                           | A `Record` annotation accepts the typo if the key is not checked, or silently widens each value's type.                             | `satisfies Record<Route, Cfg>` so a missing or extra key is an error and per-key types survive.                     |
| `type ApiResponse = {...}` re-exported from a barrel `index.ts`                | Every consumer's compile now depends on the full module graph; cycles and slow builds follow.                                       | Export from the owning module; keep the barrel to a curated public surface.                                         |

## Checklist

1. Confirm `strict: true` is set in the root `tsconfig.json` and no `// @ts-nocheck` or `// @ts-ignore` remains anywhere in `src/`.
2. Confirm `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` are enabled; fix every new `TS2532`/`TS18048` and `TS2375` by narrowing or by constructing objects conditionally rather than by widening the type.
3. Confirm `noImplicitOverride`, `noFallthroughCasesInSwitch`, `noImplicitReturns`, and `noPropertyAccessFromIndexSignature` are enabled, and that every subclass member shadowing a base member carries `override`.
4. Confirm `verbatimModuleSyntax` is enabled and that every type-only import uses `import type` or an inline `type` modifier.
5. Confirm `module`/`moduleResolution` are `nodenext` (or `bundler`) and that no `node10`, `classic`, `baseUrl`, `amd`, `umd`, or `es5` target survives; migrate with `ts5to6` if the config predates TypeScript 6.
6. Confirm `erasableSyntaxOnly` is enabled where source runs under Node type stripping or a bundler, and that no `enum`, runtime `namespace`, parameter property, or `import =` remains.
7. Search for `: any`, `as any`, `<any>`, and `any[]`; replace each with `unknown` plus narrowing, a generic constraint, or a precise interface.
8. Search for `!` used as a postfix non-null assertion and for `as ` casts outside constructor/parser functions; each one must be preceded by a check that establishes the invariant.
9. Verify every external input — HTTP responses, env vars, `JSON.parse` results, `localStorage`, query parameters, CLI args — passes through a Zod or Valibot schema, and that the corresponding type is derived with `z.infer` or `v.InferOutput` rather than declared separately.
10. Confirm each state machine is a discriminated union with a shared literal discriminant and that every `switch` over it has a `default` assigning to `never`.
11. Replace every `enum` with an `as const` object plus a `(typeof X)[keyof typeof X]` union, and every `const enum` reference with the same.
12. Confirm object literals that must match a known shape use `satisfies` rather than a type annotation, and that IDs and units that are structurally identical use branded types with the assertion confined to a validating constructor.
13. Confirm every exported function has an explicit return type, and that library builds enable `declaration`, `declarationMap`, and (where tooling requires it) `isolatedDeclarations`.
14. Run `npx publint` and `npx --yes @arethetypeswrong/cli --pack .` on any published package and resolve every resolution, masquerading-CJS/ESM, and false-default-export finding.
15. Run `npx tsc --noEmit` (or the project's `typecheck` script) and `typescript-eslint` with `strictTypeChecked`; treat any `no-explicit-any`, `no-non-null-assertion`, `no-unsafe-assignment`, `switch-exhaustiveness-check`, or `no-unnecessary-type-parameters` finding as blocking.

## References

- [TypeScript: `strict`](https://www.typescriptlang.org/tsconfig/strict.html) — the strict-mode family and its members.
- [TypeScript: `noUncheckedIndexedAccess`](https://www.typescriptlang.org/tsconfig/noUncheckedIndexedAccess.html) and [TypeScript 4.1 release notes](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-1.html) — checked indexed accesses.
- [TypeScript: `exactOptionalPropertyTypes`](https://www.typescriptlang.org/tsconfig/exactOptionalPropertyTypes.html) — optional properties interpreted as written.
- [TypeScript: `noImplicitOverride`](https://www.typescriptlang.org/tsconfig/noImplicitOverride.html) and [TypeScript 4.3 release notes](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-3.html) — the `override` keyword.
- [TypeScript: `verbatimModuleSyntax`](https://www.typescriptlang.org/tsconfig/verbatimModuleSyntax.html) and [TypeScript 5.0 release notes](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-0.html) — type-only import/export semantics, `const` type parameters.
- [TypeScript: `erasableSyntaxOnly`](https://www.typescriptlang.org/tsconfig/erasableSyntaxOnly.html) and [TypeScript 5.8 release notes](https://devblogs.microsoft.com/typescript/announcing-typescript-5-8/) — the erasable-syntax subset.
- [TypeScript: `isolatedDeclarations`](https://www.typescriptlang.org/tsconfig/isolatedDeclarations.html) and [TypeScript 5.5 release notes](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-5.html) — declaration emit without a type checker, plus inferred type predicates.
- [TypeScript: `noUncheckedSideEffectImports`](https://www.typescriptlang.org/tsconfig/noUncheckedSideEffectImports.html) — side-effect import checking.
- [TypeScript 4.9 release notes — `satisfies`](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-9.html) — validation without widening.
- [TypeScript: Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) — `never` exhaustiveness checking in `switch`.
- [TypeScript: Utility Types](https://www.typescriptlang.org/docs/handbook/utility-types.html) — `Awaited`, `Partial`, `Pick`, `Omit`, `Record`, `ReturnType`, `NoInfer`.
- [TypeScript: Symbols — `unique symbol`](https://www.typescriptlang.org/docs/handbook/symbols.html) — the basis for branded types.
- [TypeScript 6.0 announcement](https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/) and [TypeScript 7.0 announcement](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/) — changed defaults and the deprecations that became hard errors.
- [Node.js: Modules: TypeScript](https://nodejs.org/api/typescript.html) — type stripping defaults, stability, and `--no-strip-types`.
- [Zod documentation](https://zod.dev/) and [Zod 4 changelog](https://zod.dev/v4/changelog) — `z.infer`/`z.input`/`z.output`, `z.discriminatedUnion`, `z.strictObject`, top-level formats, `z.brand`.
- [Valibot documentation](https://valibot.dev/) — `v.variant`, `v.strictObject`, `v.brand`, `InferInput`/`InferOutput`.
- [typescript-eslint: shared configurations](https://typescript-eslint.io/users/configs/) and the rule index — `strictTypeChecked`, `switch-exhaustiveness-check`, `no-explicit-any`, `no-non-null-assertion`, `ban-ts-comment`, `no-unnecessary-type-parameters`.
- [publint](https://publint.dev/docs/) and [Are The Types Wrong?](https://arethetypeswrong.github.io/) — packaging and resolution verification for published types.
- [Python `typing` — `assert_never` and `Never`](https://docs.python.org/3/library/typing.html) — the same exhaustiveness discipline in a nominally checked ecosystem.
- [JEP 441: Pattern Matching for `switch`](https://openjdk.org/jeps/441) and [Java 21 pattern matching](https://docs.oracle.com/en/java/javase/21/language/pattern-matching-switch.html) — compile-time exhaustiveness over sealed hierarchies.
- [PHP: Backed enumerations](https://www.php.net/manual/en/language.enumerations.backed.php) and [Rust: the `non_exhaustive` attribute](https://doc.rust-lang.org/reference/attributes/type_system.html) — the enum-modeling trade-offs TypeScript's `as const` unions avoid.
