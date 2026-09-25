# Rust Standards

Covers the conventions the compiler does not enforce: where ownership sits at each API boundary, how errors cross crate lines, when dispatch is static versus dynamic, and the lint gates that stop all of it from drifting. Rust's borrow checker prevents memory unsafety, not design decay — a codebase can be 100% safe and still be panic-prone, allocation-happy, and impossible to refactor. The recurring production failures are `unwrap()` on an unproven invariant, a `MutexGuard` held across an `.await` that silently makes the future `!Send`, and an error type that erased what the caller needed to react.

## Contents

- [When This Applies](#when-this-applies)
- [Toolchain, Lints, and Features](#toolchain-lints-and-features)
  - [Formatting is a merge-conflict budget, not a taste choice](#formatting-is-a-merge-conflict-budget-not-a-taste-choice)
  - [Clippy groups, and why `-D warnings` is not enough alone](#clippy-groups-and-why--d-warnings-is-not-enough-alone)
  - [Features must be additive](#features-must-be-additive)
- [Ownership, Borrowing, and API Shape](#ownership-borrowing-and-api-shape)
  - [Lifetime elision covers three cases](#lifetime-elision-covers-three-cases)
  - [Borrow in parameters, own at boundaries](#borrow-in-parameters-own-at-boundaries)
  - [`clone()` and interior mutability are design signals](#clone-and-interior-mutability-are-design-signals)
  - [Newtypes for identity and units](#newtypes-for-identity-and-units)
- [Errors, Options, and Combinators](#errors-options-and-combinators)
  - [`unwrap()` policy by crate kind](#unwrap-policy-by-crate-kind)
  - [Combinators over match pyramids](#combinators-over-match-pyramids)
  - [`?`, `thiserror`, and `anyhow`](#thiserror-and-anyhow)
- [Types, Traits, and Dispatch](#types-traits-and-dispatch)
  - [Enums with data make illegal states unrepresentable](#enums-with-data-make-illegal-states-unrepresentable)
  - [Traits for behavior, generics for static dispatch, `dyn` for dynamic](#traits-for-behavior-generics-for-static-dispatch-dyn-for-dynamic)
  - [Conversions: `From` infallible, `TryFrom` fallible](#conversions-from-infallible-tryfrom-fallible)
- [Iterators, Concurrency, and API Hygiene](#iterators-concurrency-and-api-hygiene)
  - [Iterator chains over index loops](#iterator-chains-over-index-loops)
  - [Sharing memory versus moving messages](#sharing-memory-versus-moving-messages)
  - [`Send`/`Sync` are auto traits, and the boundaries are load-bearing](#sendsync-are-auto-traits-and-the-boundaries-are-load-bearing)
  - [API hygiene, docs, and module layout](#api-hygiene-docs-and-module-layout)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- A repository contains `Cargo.toml`, `src/lib.rs`, `src/main.rs`, or any `.rs` file.
- A crate exposes a public API to other crates or publishes to crates.io — semver and API-hygiene rules bind here.
- The audit finds `unwrap()`, `expect()`, `panic!`, or `todo!()` outside `#[cfg(test)]`.
- Error types are being designed or refactored, or `anyhow` appears in a library's public signature.
- `Rc<RefCell<...>>`, `Arc<Mutex<...>>`, or channel usage is under review, or a `tokio::spawn` fails with a `Send` bound error.
- The project has no `rustfmt.toml`, no `[lints]` section in `Cargo.toml`, or no clippy step in CI.
- `Cargo.toml` declares `[features]` and no CI job tests non-default combinations.
- A public enum or struct is about to gain a variant or field, or the crate is approaching a version bump.

## Toolchain, Lints, and Features

### Formatting is a merge-conflict budget, not a taste choice

`cargo fmt` is deterministic and canonical; any deviation is a diff reviewers must read and the next formatter run will re-litigate. Commit the smallest option set that expresses your intent — every added option is one a contributor's editor disagrees with.

```toml
edition = "2024"
style_edition = "2024"
max_width = 100
use_small_heuristics = "Max"
reorder_imports = true
```

`style_edition` is separate from `edition` and has changed formatting rules between releases (import ordering, comment placement). Set it explicitly; edition-derived defaults have shifted. `imports_granularity`, `group_imports`, `wrap_comments`, `format_strings`, and `format_code_in_doc_comments` are **unstable** — they need a nightly toolchain plus `unstable_features = true`, and on stable they fail or are silently ignored depending on version. Never put them in a stable-CI repository.

```sh
cargo fmt --all -- --check   # --all covers every workspace member; --check exits non-zero instead of rewriting
```

### Clippy groups, and why `-D warnings` is not enough alone

| Group                 | Default | Contains                                                                                                                  |
| --------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------- |
| `clippy::correctness` | `deny`  | Code that is almost certainly a bug                                                                                       |
| `clippy::suspicious`  | `warn`  | Probably wrong, but compiles                                                                                              |
| `clippy::style`       | `warn`  | Non-idiomatic constructs (`ptr_arg`, `needless_range_loop`)                                                               |
| `clippy::complexity`  | `warn`  | Overly convoluted code (`needless_collect`, `type_complexity`)                                                            |
| `clippy::perf`        | `warn`  | Needless allocation or copying (`large_enum_variant`, `result_large_err`)                                                 |
| `clippy::pedantic`    | `allow` | Strict, occasionally wrong — opt in selectively                                                                           |
| `clippy::nursery`     | `allow` | Unstable lints, may have false positives                                                                                  |
| `clippy::cargo`       | `allow` | `Cargo.toml` metadata issues                                                                                              |
| `clippy::restriction` | `allow` | `unwrap_used`, `expect_used`, `panic`, `indexing_slicing`, `dbg_macro`, `todo`, `print_stdout`, `arithmetic_side_effects` |

`clippy::all` is `correctness` + `suspicious` + `style` + `complexity` + `perf` — what `cargo clippy` runs by default. `pedantic` and `restriction` are never enabled by `-D warnings`; you must opt in. Configure in `Cargo.toml` (stable since Cargo 1.74), not via `RUSTFLAGS`: changing `RUSTFLAGS` invalidates the whole build cache and forces a full rebuild every CI run.

```toml
[lints.rust]
unsafe_op_in_unsafe_fn = "deny"
missing_debug_implementations = "warn"

[lints.clippy]
all = { level = "deny", priority = -1 }
unwrap_used = "deny"
expect_used = "deny"
panic = "deny"
indexing_slicing = "warn"
```

`priority` defaults to `0`; a negative value lets a specific lint override its group. A workspace root declares `[workspace.lints.clippy]` and members opt in with `[lints] workspace = true`. Suppressions must carry a reason, and `#[expect]` (stable 1.81) beats `#[allow]` because it errors with `unfulfilled_lint_expectations` once the lint stops firing:

```rust
#[expect(clippy::cast_possible_truncation, reason = "masked to 16 bits above")]
let port = (raw & 0xFFFF) as u16;
```

Tests are the exception — `unwrap()` is idiomatic there, so gate the restriction lints off:

```rust
#![cfg_attr(not(test), deny(clippy::unwrap_used, clippy::expect_used))]
```

```sh
cargo clippy --all-targets --all-features -- -D warnings   # --all-targets = --lib --bins --tests --benches --examples
cargo test --all-features && cargo test --doc
```

Without `--all-targets`, clippy never sees test or benchmark code.

### Features must be additive

Cargo unifies features across the whole dependency graph: if two crates enable different features of yours, both are on. A feature that selects between mutually exclusive backends, or changes the public API shape, breaks under unification in a way only downstream builds reveal. Never put `#[cfg(feature = "x")]` around code whose absence is a compile error for a consumer.

```toml
[features]
default = ["json"]
json = ["dep:serde_json"]
derive = ["dep:serde?/derive"]   # dep: (1.60+) avoids an implicit same-named feature; ? marks a weak dependency
```

Declare `rust-version = "1.85"` in `[package]`: Cargo refuses older toolchains, and clippy reports std APIs newer than that MSRV. Keep it equal to the oldest toolchain a CI job actually runs. Test the matrix with `cargo hack --feature-powerset check`.

## Ownership, Borrowing, and API Shape

### Lifetime elision covers three cases

Elision applies in exactly three cases: each elided input lifetime becomes its own parameter; a single input lifetime is assigned to every elided output lifetime; with several inputs and one `&self`/`&mut self`, `self`'s lifetime wins.

```rust
fn first_word(s: &str) -> &str
impl Parser { fn name(&self) -> &str }
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str
fn pick<'a>(left: &'a str, right: &str, take_left: bool) -> &'a str
```

The last two need annotation: without it, `&right` could escape. When the relationship resists expression, the design is wrong — a borrow derived from two unrelated inputs should be an owned return. `'_` is the placeholder for "infer a lifetime here", used where elision does not apply (`Foo<'_>`, `impl Trait + '_`). In edition 2024, return-position `impl Trait` captures **all** in-scope lifetimes by default; narrow it with precise capturing (stable 1.82): `-> impl Iterator<Item = &'a str> + use<'a>`.

### Borrow in parameters, own at boundaries

`&str` accepts `&String` by deref coercion, so `&String` adds nothing and blocks callers holding a slice. Clippy's `ptr_arg` (`clippy::style`, on by default) flags exactly this.

| Signature                        | Verdict                                                                         |
| -------------------------------- | ------------------------------------------------------------------------------- |
| `fn f(s: &String)` / `&Vec<u64>` | Wrong — use `&str` / `&[u64]`; `&PathBuf` → `&Path`                             |
| `fn f(s: &str)`                  | Correct for read-only access                                                    |
| `fn f(s: impl Into<String>)`     | Correct when the callee stores the value                                        |
| `fn f(s: AsRef<str>)`            | Only for genuinely multi-type call sites; it degrades inference and diagnostics |

A constructor that stores a string returns `String`, not `&str` — otherwise the struct gains a lifetime that propagates into every type mentioning it and forces callers to keep the source buffer alive. `Cow<'_, str>` is for "usually returns the input unchanged, occasionally allocates", not for avoiding an ownership decision.

### `clone()` and interior mutability are design signals

A `.clone()` added to satisfy the borrow checker signals wrong ownership, not a fix. First ask whether the callee can take `&T`, whether the value can be moved, or whether the caller can give up ownership. `Arc::clone`/`Rc::clone` are the exception: cloning a refcount is a pointer copy, and writing `Arc::clone(&x)` rather than `x.clone()` documents that no deep copy occurs (`clippy::clone_on_ref_ptr` enforces the style). `clone_from` reuses the destination's allocation where `x = y.clone()` drops and reallocates. Interior mutability, in increasing cost: `Cell<T: Copy>` (free), `RefCell<T>` (runtime borrow counter, panics on conflict), `Rc<RefCell<T>>` (also leaks on cycles), `Mutex`/`RwLock` (OS lock, poisoning on panic), `OnceLock`/`LazyLock` (blocks on concurrent init).

`Rc<RefCell<T>>` appears whenever an object graph is ported from a garbage-collected language: cycles leak silently because refcounts never reach zero, and any re-entrant borrow panics. Prefer passing ownership, or an arena — nodes in a `Vec`/`SlotMap` with indices instead of pointers — and `Weak<T>` with `.upgrade()` for genuine back-edges. `RefCell::try_borrow`/`try_borrow_mut` return `Result`, and belong wherever a re-entrant borrow is reachable from input.

### Newtypes for identity and units

A `u64` account ID and a `u64` order ID are interchangeable to the compiler. Wrap them; the newtype is free at runtime, prevents argument transposition, and gives one place for validation.

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct AccountId(u64);

impl TryFrom<&str> for AccountId {
    type Error = ParseAccountIdError;

    fn try_from(raw: &str) -> Result<Self, Self::Error> {
        raw.parse::<u64>().map(Self).map_err(|_| ParseAccountIdError::NotNumeric)
    }
}
```

`NonZeroU64` and friends supply a niche — `Option<NonZeroU64>` is 8 bytes because zero encodes `None` — and make zero unrepresentable for IDs and divisors. For units, do **not** implement cross-unit arithmetic: `impl Add<Seconds> for Meters` compiles and is a bug. Add `#[serde(transparent)]` so the newtype serializes as its inner value, not a one-field object. The TypeScript analogue is a branded type, the Python analogue is `typing.NewType`; both erase at runtime, the Rust one does not.

## Errors, Options, and Combinators

### `unwrap()` policy by crate kind

| Context                | `unwrap()`  | `expect()`                                |
| ---------------------- | ----------- | ----------------------------------------- |
| Library (`src/lib.rs`) | Forbidden   | Forbidden — return `Result`               |
| Binary startup         | Discouraged | Allowed, message states the invariant     |
| Tests / benchmarks     | Idiomatic   | Idiomatic                                 |
| `static` initializer   | Forbidden   | Required — panic is the only failure path |

In library code there is no proven invariant: the caller is a different crate with different assumptions. Write the invariant, not the operation — `expect("config validated at startup")` beats `expect("failed to load")`. `unwrap_or_else`/`ok_or_else` defer their closure; the eager `unwrap_or`/`ok_or` allocate on the success path too.

### Combinators over match pyramids

```rust
let port: u16 = env::var("PORT").ok().and_then(|raw| raw.parse().ok()).unwrap_or(8080);
let cfg = read_config(path)
    .inspect_err(|err| tracing::warn!(%err, "falling back to defaults"))
    .unwrap_or_default();
let Some(user) = users.get(&id) else { return Err(LookupError::NoSuchUser(id)) };
```

`Option` carries `map`, `and_then`, `or_else`, `filter`, `ok_or`, `transpose`, `zip`, `take`, `get_or_insert_with`, `is_some_and`, and `is_none_or` (1.82). `Result` adds `map_err`, `inspect`, and `inspect_err` (both 1.76) for logging without consuming the value. `let ... else` (1.65) removes the early-return `match` and keeps the happy path unindented. A `match` more than two levels deep over `Option`/`Result` is a refactor signal: extract the inner logic into a function returning `Result` and use `?` at the boundary.

### `?`, `thiserror`, and `anyhow`

`?` is `match` plus `From::from` on the error plus an early return; it works in any function returning `Result`/`Option`, and in `main` when the signature is `fn main() -> Result<(), E> where E: Debug`. The `From` impls _are_ the conversion graph, so keep them narrow — a blanket `impl From<io::Error>` that discards path and operation context is worse than none.

| Crate kind          | Error type                               | Crate       |
| ------------------- | ---------------------------------------- | ----------- |
| Library, published  | Concrete enum, `#[non_exhaustive]`       | `thiserror` |
| Library, zero-dep   | `Box<dyn Error + Send + Sync + 'static>` | std         |
| Binary, application | Erased, with context                     | `anyhow`    |

```rust
#[derive(Debug, thiserror::Error)]
#[non_exhaustive]
pub enum ConfigError {
    #[error("reading config at {path}")]
    Read { path: String, #[source] source: std::io::Error },
    #[error("invalid TOML")]
    Parse(#[from] toml::de::Error),
    #[error("missing required key `{0}`")]
    MissingKey(&'static str),
    #[error(transparent)]
    Other(#[from] anyhow::Error),
}
```

A field named `source` is treated as the source without an attribute. `#[error(transparent)]` forwards both `Display` and `source()` — right for passthrough, wrong for anything you want to describe yourself. `anyhow` belongs at the application boundary only: its `Error` erases the variant, leaving callers only `.downcast_ref::<T>()` or string matching, and a library can then never change its error taxonomy without breaking downstream.

```rust
fn main() -> anyhow::Result<()> {
    let cfg = read_config("app.toml").context("loading application config")?;
    run(cfg, std::env::var("PORT").context("PORT must be set")?)
}
```

`anyhow::Context` is implemented for `Option<T>` too, turning a missing value into a contextualized error in one call; `bail!` and `ensure!` cover early-return and preconditions. The Go analogue is `fmt.Errorf("...: %w", err)` plus `errors.Is`/`errors.As` — Rust's `source()` chain plus downcast is structural rather than by value, which is why `#[from]` chains matter.

## Types, Traits, and Dispatch

### Enums with data make illegal states unrepresentable

A struct with `status: Status` plus three fields meaningful in only one status is the same model with the proof removed.

```rust
#[derive(Debug)]
#[non_exhaustive]
pub enum JobState {
    Queued { enqueued_at: SystemTime },
    Running { worker: WorkerId, started_at: SystemTime },
    Failed { error: JobError, attempts: u8 },
    Done { output: OutputRef },
}
```

Never write a `_ =>` arm over an enum defined in the same crate: it compiles, and the day someone adds a variant the new state silently takes the default branch. A wildcard is correct only over a foreign `#[non_exhaustive]` enum, where it is required. Marking your own public enums and structs `#[non_exhaustive]` is what lets you add variants and fields without a semver break — adding a variant to a public enum without it breaks downstream matches in a patch release. `clippy::large_enum_variant` (`perf`, on by default) fires when one variant dwarfs the rest; box the oversized payload.

### Traits for behavior, generics for static dispatch, `dyn` for dynamic

| Choice                      | Dispatch                  | Cost                                                | Use when                                                 |
| --------------------------- | ------------------------- | --------------------------------------------------- | -------------------------------------------------------- |
| `fn f<T: Trait>(x: T)`      | Static, monomorphized     | One code copy per type; bigger binary, slower build | Hot path, type known at the call site                    |
| `fn f(x: &dyn Trait)`       | Dynamic, vtable           | One indirect call; one code copy                    | Plugin registries, heterogeneous collections, build time |
| `fn f(x: impl Trait)` (arg) | Identical to `<T: Trait>` | Same as generics                                    | Same, with less ceremony                                 |
| `-> impl Trait`             | Opaque, one type          | Caller cannot name the type                         | Returning closures and iterator chains                   |

`impl Trait` in argument position is **not** dynamic dispatch and does not shrink the binary. A trait behind `dyn` must be object-safe: no generic methods, no method returning `Self` by value. `async fn` in traits and RPITIT (both 1.75) do not make a trait object-safe. Seal a trait when downstream impls would be a breaking change you cannot make: a private `sealed::Sealed` supertrait that only your crate implements. `Box<dyn Error + Send + Sync + 'static>` is the standard erased error — `Send + Sync` makes it usable across `tokio::spawn`, `'static` makes it storable.

### Conversions: `From` infallible, `TryFrom` fallible

Implement `From` and `Into` comes free via the std blanket impl — never implement both, never implement `Into` directly. The same holds for `TryFrom`/`TryInto`, with one trap: `impl<T, U> TryFrom<U> for T where U: Into<T>` already exists, so a type carrying a `From` impl cannot also carry a `TryFrom` impl for that same source. Implementing `std::str::FromStr` (as `AccountId` does above) is what makes `"42".parse::<AccountId>()` work. Reserve `From` for lossless or widening conversions: a `From<f64> for u64` would have to pick a rounding rule at the type level, which is exactly the decision the caller should make explicitly.

## Iterators, Concurrency, and API Hygiene

### Iterator chains over index loops

```rust
pub fn active_ids(rows: &[Row]) -> impl Iterator<Item = AccountId> + use<'_> {
    rows.iter().filter(|r| r.active).map(|r| r.id)
}
let total: u64 = rows.iter().filter(|r| r.active).map(|r| r.bytes).sum();
```

`clippy::needless_range_loop` (`style`, on by default) catches `for i in 0..v.len() { v[i] }`, and it is right: the index form invites off-by-one errors and defeats bounds-check elision. Choose deliberately — `iter()` yields `&T`, `iter_mut()` yields `&mut T`, `into_iter()` consumes and yields `T`. Indexing a `String` by byte panics on a non-char boundary; use `chars()`, `char_indices()`, or `as_bytes()`. A function that only iterates should accept `impl IntoIterator<Item = T>` or return `impl Iterator<Item = T>`, not `collect` into a `Vec` — the exception is `collect::<Result<Vec<_>, _>>()`, which short-circuits on the first `Err` and is the right way to sequence fallible transforms. Use `Vec::with_capacity(n)` when `n` is known.

### Sharing memory versus moving messages

| Need                                     | Tool                                                        |
| ---------------------------------------- | ----------------------------------------------------------- |
| Work to a worker pool                    | `std::sync::mpsc`, `crossbeam-channel`, `tokio::sync::mpsc` |
| Request/response from a spawned task     | `tokio::sync::oneshot`                                      |
| Latest value to many observers           | `tokio::sync::watch`                                        |
| Fan-out to independent consumers         | `tokio::sync::broadcast`                                    |
| Config read by all, written once         | `Arc<OnceLock<T>>` / `Arc<LazyLock<T>>`                     |
| Short critical sections on mutable state | `Arc<Mutex<T>>`; `Arc<RwLock<T>>` when read-mostly          |
| Counter or flag                          | `Arc<AtomicU64>` with `Ordering::Relaxed`                   |

`std::sync::mpsc` is multi-producer, single-consumer, and unbounded. `crossbeam-channel` adds `select!`, multiple consumers, and bounded channels whose `Sender`/`Receiver` both stay `Clone`. `tokio::sync::mpsc::channel(n)` is bounded and its `send().await` applies backpressure — an unbounded channel in a producer-faster-than-consumer pipeline is a memory leak with a delay fuse. `Mutex::lock()` returns `LockResult`, `Err` only when another thread panicked while holding it; recover with `unwrap_or_else(|e| e.into_inner())` only when the protected value is known consistent after a partial update.

### `Send`/`Sync` are auto traits, and the boundaries are load-bearing

| Type                     | `Send`                   | `Sync`              |
| ------------------------ | ------------------------ | ------------------- |
| `Rc<T>`                  | never                    | never               |
| `Arc<T>`                 | if `T: Send + Sync`      | if `T: Send + Sync` |
| `RefCell<T>` / `Cell<T>` | if `T: Send`             | never               |
| `Mutex<T>`               | if `T: Send`             | if `T: Send`        |
| `RwLock<T>`              | if `T: Send`             | if `T: Send + Sync` |
| `&T` / `&mut T`          | if `T: Sync` / `T: Send` | if `T: Sync`        |
| `*const T` / `*mut T`    | never                    | never               |

The most common production symptom: holding a `std::sync::MutexGuard` across an `.await`. The guard is `!Send`, so the whole future is `!Send` and `tokio::spawn` rejects it with an indirect trait error.

```rust
let snapshot = {
    let guard = self.inner.lock().unwrap_or_else(|e| e.into_inner());
    guard.clone()
};
send(snapshot).await;   // guard dropped before the await point
```

Either scope the guard so it drops before the await, or switch to `tokio::sync::Mutex`, whose guard is `Send` by design. `LazyLock` (1.80) and `OnceLock` (1.70) cover process-wide init without a lock crate. `unsafe impl Send for X` is a promise you must be able to justify.

### API hygiene, docs, and module layout

`#[must_use]` makes a discarded value warn; `Result` already carries it, so the cases that matter are guards and handles — `#[must_use = "the guard releases the lock when dropped"] pub fn enter(&self) -> Guard<'_>`.

`///` documents an item, `//!` the enclosing module or crate. Fenced examples are compiled and run by `cargo test`, making them the cheapest integration test you own:

````rust
/// Parses a duration such as `"150ms"` or `"2s"`.
///
/// # Errors
/// Returns [`DurationError::Empty`] for empty input and
/// [`DurationError::UnknownUnit`] for a suffix that is not `ms`, `s`, or `m`.
///
/// # Examples
/// ```
/// assert_eq!(parse_duration("150ms")?.as_millis(), 150);
/// ```
pub fn parse_duration(input: &str) -> Result<Duration, DurationError>
````

Fence attributes change the test: `no_run` compiles without executing, `ignore` skips both and hides rot, `compile_fail` asserts it does not compile, `should_panic` asserts a panic, `text` marks a non-Rust block. `#[doc = include_str!("../README.md")]` (1.54) pulls a file in as documentation — its Rust blocks are then tested too.

```
src/lib.rs           # library root, declares modules
src/main.rs          # binary root; uses the library by crate name
src/config.rs        # + src/config/parse.rs — the 2018+ file-module form, not mod.rs
src/bin/, tests/, benches/, examples/   # auto-discovered binaries, test crates, benches, examples
```

Pick one module form per crate and stay with it — mixing yields a directory of identical `mod.rs` files no editor tab can distinguish. `cargo tree -d` lists duplicate crate versions, `cargo deny check` covers licenses and advisories, `cargo machete` finds unused dependencies.

## Common Mistakes

| Mistake                                                       | Why It Breaks                                                                                                                  | Correct Approach                                                                                  |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| `fn parse(s: &String)` / `&Vec<u64>`                          | Blocks callers holding `&str` or a slice and forces borrowing an owned value                                                   | Take `&str` / `&[u64]`; return owned types at boundaries                                          |
| `self.inner.lock().unwrap()` in a library                     | A panic anywhere under the lock poisons it forever; the `unwrap` turns a recoverable state into a crash for every later caller | Propagate the poison error, or recover with `unwrap_or_else(\|e\| e.into_inner())` and justify it |
| Holding a `std::sync::MutexGuard` across `.await`             | The guard is `!Send`, so the future is `!Send` and `tokio::spawn` fails with an unrelated trait error                          | Scope the guard in a block ending before the await, or use `tokio::sync::Mutex`                   |
| `.clone()` added to satisfy the borrow checker                | Hides an ownership error; inside a loop it turns O(1) pointer work into O(n) allocation                                        | Make the callee take `&T`, move the value, or restructure so ownership does not overlap           |
| Returning `anyhow::Error` from a public library function      | Erases the variant; callers can only downcast or string-match, and the taxonomy can never change                               | Return a `thiserror` enum; keep `anyhow` at the binary boundary                                   |
| `_ => ...` over an in-crate enum                              | A new variant compiles and silently takes the default branch — no error, wrong behavior                                        | Enumerate every variant; reserve `_` for foreign `#[non_exhaustive]` enums                        |
| Adding a variant to a public enum with no `#[non_exhaustive]` | Downstream exhaustive matches stop compiling — semver-breaking in a patch release                                              | Mark public enums `#[non_exhaustive]` before the first release                                    |
| `Rc<RefCell<T>>` for a parent/child graph                     | Cycles keep refcounts above zero and leak; re-entrant borrows panic at runtime                                                 | Store nodes in a `Vec`/`SlotMap` and hold indices, or use `Weak<T>` for back-edges                |
| `.collect::<Vec<_>>()` immediately followed by iteration      | Allocates a temporary the code never needed                                                                                    | Chain the adapters, or accept/return `impl Iterator`                                              |
| `#[allow(clippy::x)]` with no reason                          | Suppressions accumulate with no audit trail, and `allow` stays silent once the lint stops firing                               | `#[expect(clippy::x, reason = "...")]`, which errors when the lint is gone                        |
| A `#[cfg(feature = "x")]` switching between two backends      | Feature unification turns both on when two graph crates disagree, producing an untested build                                  | Keep features additive; test with `cargo hack --feature-powerset check`                           |

## Checklist

1. Confirm `rustfmt.toml` exists, contains only stable options, and `cargo fmt --all -- --check` reports zero diff.
2. Run `cargo clippy --all-targets --all-features -- -D warnings` and record the failure count per workspace member.
3. Verify a workspace-root lint config exists (`[workspace.lints]` or `#![warn]`) with `clippy::all` at least `warn` and `correctness` at `deny`.
4. Grep every `unwrap()`, `expect(`, `panic!`, and `todo!()` outside `#[cfg(test)]` and `src/bin/`; each library hit is a finding.
5. Confirm every `#[allow(` carries `reason = "..."`; convert to `#[expect(..., reason = "...")]` where the lint should still fire.
6. List every `pub` item, confirm it has a doc comment, and run `cargo test --doc` to prove each example compiles and passes.
7. Confirm extensible public enums and structs are `#[non_exhaustive]`, and that no in-crate `match` uses a `_ =>` arm.
8. Confirm no `&String`, `&Vec<T>`, or `&PathBuf` appears in a parameter; `clippy::ptr_arg` must be clean.
9. Confirm no library signature exposes `anyhow::Error`, and every library error is a `thiserror` enum preserving `source()`.
10. Confirm no `Rc<RefCell<` outside a genuinely single-threaded graph, and every `Weak` back-edge handles `upgrade() == None`.
11. Confirm no lock guard is held across an `.await`, and the crate checks under a `Send`-requiring runtime.
12. Confirm each `collect::<Vec<_>>()` is returned, stored, or needed; replace the rest with chained adapters.
13. Confirm `rust-version` equals the oldest CI toolchain and no std API newer than it is used.
14. Confirm features are additive with `dep:` for optional deps, and a matrix job runs the non-default combinations.
15. Confirm `Cargo.lock` is committed for binaries and application workspaces, and gitignored for published libraries.

## References

- The Rust Programming Language — https://doc.rust-lang.org/book/
- The Rust Reference, lifetime elision — https://doc.rust-lang.org/reference/lifetime-elision.html
- The Rustonomicon, `Send` and `Sync` — https://doc.rust-lang.org/nomicon/send-and-sync.html
- The Rustonomicon, subtyping and variance — https://doc.rust-lang.org/nomicon/subtyping.html
- Rust API Guidelines — https://rust-lang.github.io/api-guidelines/
- Clippy lint list and group membership — https://rust-lang.github.io/rust-clippy/master/index.html
- Clippy configuration (`clippy.toml`, MSRV) — https://doc.rust-lang.org/clippy/configuration.html
- rustfmt configuration options and stability — https://rust-lang.github.io/rustfmt/
- The Cargo Book, `[lints]` section — https://doc.rust-lang.org/cargo/reference/manifest.html#the-lints-section
- The Cargo Book, features and `dep:` syntax — https://doc.rust-lang.org/cargo/reference/features.html
- The Edition Guide, Rust 2024 changes — https://doc.rust-lang.org/edition-guide/rust-2024/index.html
- The rustdoc Book, documentation tests — https://doc.rust-lang.org/rustdoc/documentation-tests.html
- `std::sync` — `Mutex`, `RwLock`, `OnceLock`, `LazyLock`, `mpsc` — https://doc.rust-lang.org/std/sync/index.html
- `thiserror` API — https://docs.rs/thiserror/
- `anyhow` API — https://docs.rs/anyhow/
- Related modules: [std-structure.md](std-structure.md), [std-docs.md](std-docs.md), [std-shell.md](std-shell.md), [std-go.md](std-go.md)
