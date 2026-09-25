# Go Standards

Covers what `go build` accepts but production rejects: formatting and identifier casing, error wrapping and inspection, context propagation and goroutine ownership, interface placement, zero-value design, and the static-analysis gates that stop the rest from decaying. Go's toolchain is unusually opinionated and unusually forgiving at once — `gofmt` decides layout for you, but nothing in the compiler stops a `util` package, a `GetOwner` method, a `context.WithCancel` whose `cancel` is dropped on one return path, or a `WaitGroup.Add(1)` inside the goroutine it guards. All four are mechanically detectable.

## When This Applies

- The repository contains `go.mod` or any `.go` file, including a single-package tool or a `cmd/`-only binary.
- Files are not `gofmt`-clean, or imports are grouped by hand rather than by `goimports`.
- An error is returned, logged, or compared with `==` instead of `errors.Is`/`errors.As`.
- A `context.Context` parameter is missing, not first, not named `ctx`, or stored in a struct field.
- A `go` statement has no stated exit condition, or a `WaitGroup`/`errgroup` is built outside the function that waits.
- A package named `util`, `common`, `helpers`, `misc`, `api`, or `types` exists, or two packages claim overlapping domain vocabulary.
- Tests are hand-rolled loops rather than table-driven `t.Run` subtests, or there are no `_test.go` files at all.
- `.golangci.yml` is absent, still v1-shaped, or lists `stylecheck`/`gosimple` separately (v2 merged them).
- The audit finds `init()` functions, package-level mutable variables, or `panic` outside a deliberate boundary.

## Formatting, Naming, and Package Shape

### `gofmt` and `goimports` are not a style preference

There is one Go layout. `gofmt` uses tabs for indentation and blanks for alignment; a file that differs is a finding. Since Go 1.19 it also reformats doc comments — list indentation, blank lines around headings, trailing whitespace — so a diff on a file whose _code_ is already formatted still means the file was non-conforming.

```sh
gofmt -l .        # list non-conforming files; empty output is the only pass
gofmt -s -w .     # -s applies simplifications, e.g. a[b:len(a)] -> a[b:]
gofmt -r 'interface{} -> any' -w ./...     # -s does NOT rewrite interface{}; a rule does
goimports -w -local github.com/acme ./...  # gofmt plus import add/remove/grouping
```

`goimports` is `gofmt` plus import maintenance, and `-local` takes a comma-separated prefix list that gets its own trailing group. Because it formats identically to `gofmt`, `gofmt -l` must be empty _after_ `goimports -w`, never before. Install it with `go install golang.org/x/tools/cmd/goimports@latest`.

### Naming

| Rule                                       | Wrong                                  | Right                                |
| ------------------------------------------ | -------------------------------------- | ------------------------------------ |
| Initialisms keep one case                  | `Url`, `ServeHttp`, `appId`            | `URL`, `ServeHTTP`, `appID`          |
| Multiple initialisms concatenate           | `XMLHttpRequest`                       | `xmlHTTPRequest` or `XMLHTTPRequest` |
| Receivers are short and consistent         | `func (self *Client) Do()`             | `func (c *Client) Do()`              |
| Getters drop the `Get` prefix              | `GetOwner()`                           | `Owner()`; setter stays `SetOwner`   |
| One-method interfaces are method + `-er`   | `interface{ Read() }` named `Readable` | `io.Reader`                          |
| Error strings are lowercase, unpunctuated  | `fmt.Errorf("Failed to open %s.", p)`  | `fmt.Errorf("open %s: %w", p, err)`  |
| Error variables are `ErrX`, types `XError` | `var NotFound = ...`                   | `var ErrNotFound = ...`              |
| Packages are lowercase single words        | `user_service`, `userService`          | `user`, or `userservice` at worst    |

The receiver name must be identical across every method of a type — `ST1016` exists because mixing `c` and `cl` is a real drift signal. Protobuf-generated code is exempt from the initialism rule; human-written code is not. Package names are already in scope at every call site, so a package must not repeat its name in its own identifiers: in package `chubby` the type is `File` (`chubby.File`), never `ChubbyFile`. `util`, `common`, `misc`, `api`, `types`, `interfaces` are prohibited — they carry no domain information and become the gravity well that collects unrelated code. When a helper has no home, name it after the thing it operates on: `chunked.Reader`, not `util.ChunkedReader`. Layout follows what the toolchain recognizes: `cmd/<binary>/main.go` (one `main` package per binary, nothing else), `internal/` for code no external module may import, module path as import root. [std-structure.md](std-structure.md) governs placement above this.

## Errors

### Wrap with `%w`; inspect with `Is`, `As`, `AsType`

`%w` installs an `Unwrap` method; `%v` produces a string `errors.Is` can never match again.

```go
var ErrNotFound = errors.New("not found")

type StatusError struct {
	Code int
	Err  error
}

func (e *StatusError) Error() string { return fmt.Sprintf("status %d: %v", e.Code, e.Err) }
func (e *StatusError) Unwrap() error { return e.Err }

func lookup(id string) (Item, error) {
	if id == "" {
		return Item{}, fmt.Errorf("lookup %q: %w", id, ErrNotFound)
	}
	return Item{}, nil
}
```

| Tool                                          | Use for                                                                         | Constraint                                                                                             |
| --------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `errors.Is(err, target)`                      | Sentinels: `os.ErrNotExist`, `fs.ErrExist`, `context.Canceled`, `sql.ErrNoRows` | Walks the whole tree; a custom `Is(error) bool` method declares equivalence                            |
| `errors.As(err, &target)`                     | Typed errors, to read fields                                                    | `target` must be a pointer to a type implementing `error`; `go vet`'s `errorsas` rejects anything else |
| `errors.AsType[E error](err error) (E, bool)` | Typed errors, Go 1.26+                                                          | Generic and type-safe, replacing the `var e *T; errors.As(err, &e)` dance                              |

Multiple `%w` verbs in one `fmt.Errorf` yield an error whose `Unwrap() []error` returns all operands (Go 1.20+); `errors.Join(errs...)` does the same for a slice, discards nils, and returns `nil` when every element is nil. Both trees are fully traversed by `Is` and `As`. Sentinels are for conditions callers must branch on; typed errors are for conditions carrying data. Never ship both for one condition. Error strings are lowercase and unpunctuated because callers print them mid-sentence; logging is exempt, being line-oriented.

Every ecosystem layers the same way, spelled differently: Python's `raise ConfigError(f"load {path}") from exc` sets `__cause__`; Rust's `Error::source(&self) -> Option<&(dyn Error + 'static)>` returns the inner error; Java's `Throwable(String message, Throwable cause)` plus `getCause()`, and JavaScript's `new Error(msg, { cause })`, are the identical idea. Go's distinguishing property is that the chain is walkable by the standard library — `errors.Is` needs no language support and no per-type boilerplate.

### Never ignore an error; never `panic` for control flow

Assigning an error to `_` is the most common Go defect that survives review, because it compiles and reads cleanly. Every returned error is handled, wrapped and returned, or explicitly documented as discarded. `errcheck` enforces this; `check-blank: true` also flags `n, _ := strconv.Atoi(s)`, and `check-type-assertions: true` flags single-value type assertions.

`panic` is for unrecoverable programmer error — an invariant that cannot hold if the code is correct — and for initialization failures the process cannot survive. Not validation, not "this should never happen" in request handling, not absence signalling. `recover` belongs only at a boundary that must keep running: a goroutine's entry function, an `http.Handler` middleware, a `defer` in a long-lived worker. Two hard constraints: `sync.WaitGroup.Go`'s function must not panic (the docs state it outright), so panicking code inside it needs its own `recover`; and a panic in an unrecovered goroutine terminates the whole process, taking unrelated requests with it.

## Context and Goroutine Ownership

### `ctx` is first, and it propagates rather than being replaced

`context.Context` carries deadlines, cancellation, and request-scoped values across API boundaries. The rules are mechanical: named `ctx` and first (`func Fetch(ctx context.Context, url string) (*Response, error)`); never stored in a struct field, since `containedctx` catches that — the one accepted exception is a method whose signature an interface you do not own dictates; never nil, with `context.TODO()` when the right context is genuinely undecided and `SA1012` flagging a literal `nil`; values carrying request-scoped data only (request IDs, principals, trace spans), never optional parameters, with an unexported struct type as key rather than a string (`SA1029`); and outgoing calls deriving from the incoming one via `http.NewRequestWithContext(ctx, ...)` or `req.WithContext(ctx)`, never `http.NewRequest`, because a call that invents its own context silently escapes the caller's deadline.

```go
func (s *Server) handler(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()
	if err := s.process(ctx, r.URL.Query().Get("id")); err != nil {
		slog.ErrorContext(ctx, "process failed", "err", err)
	}
}
```

Every `WithCancel`, `WithTimeout`, and `WithDeadline` returns a `CancelFunc` that must be called on every path, error paths included: until it is, the parent holds a reference to the child, so the child and its subtree leak. `defer cancel()` immediately after the call is the default, and `go vet`'s `lostcancel` analyzer reports every path where the function is discarded. When the _reason_ matters, `WithCancelCause`/`WithTimeoutCause`/`WithDeadlineCause` plus `context.Cause(ctx)` record why cancellation happened rather than only that it did. Two helpers: `context.WithoutCancel(parent)` detaches a context so cleanup can outlive the request that started it, and `context.AfterFunc(ctx, f)` runs `f` in its own goroutine on cancellation, returning a `stop func() bool` reporting whether it prevented the run. For signal-driven shutdown, `signal.NotifyContext(parent, os.Interrupt)` returns a context and a `stop` that unregisters the handler, with `context.Cause` reporting the signal; `signal.Notify` on a raw channel never blocks, so a channel for one signal needs buffer ≥ 1.

Other ecosystems carry the same contract with different ergonomics. Python's `async with asyncio.TaskGroup()` cancels siblings on the first failure and `async with asyncio.timeout(3)` makes the deadline a scope rather than a parameter — and `asyncio.CancelledError` must be re-raised after cleanup, because swallowing it breaks both, which are built on cancellation. In the browser, `AbortSignal.timeout(ms)` and `AbortSignal.any([...])` compose the same cancellation tree `ctx` composes in Go, and like Go's context the signal is threaded into every call, not stored.

### Every goroutine is owned and has a stated exit

When you spawn a goroutine, say when — or whether — it exits. A goroutine blocked forever on a channel send or receive is never collected: it holds its stack, its captured variables, and every channel it references for the life of the process. Both safe shapes below are bounded — the first by a context the caller owns, the second by a `WaitGroup` the waiting function owns:

```go
func consume(ctx context.Context, ch <-chan int, handle func(int)) {
	go func() {
		for {
			select {
			case v := <-ch:
				handle(v)
			case <-ctx.Done():
				return
			}
		}
	}()
}

func fanOut(ctx context.Context, items []Item) {
	var wg sync.WaitGroup
	for _, it := range items {
		wg.Go(func() { process(ctx, it) }) // WaitGroup.Go: Go 1.25+
	}
	wg.Wait()
}
```

`sync.WaitGroup.Go(f func())` starts `f` and adds it to the group, so `wg.Add(1)` before `go` and `defer wg.Done()` inside both disappear. Two constraints: `f` must not panic, and when the group is empty `Go` must happen before `Wait` — the natural reading order. `go vet`'s `waitgroup` analyzer (Go 1.25) reports `Add` called from inside the goroutine it guards, the classic race where `Wait` can return before the counter increments. For groups that return errors, `errgroup.WithContext(ctx)` cancels the derived context the first time any `Go` function returns non-nil — or on `Wait`, whichever comes first — and `Wait` returns that first error; `g.SetLimit(8)` caps concurrency (negative means unlimited, zero refuses new work) and must not change while goroutines are active, while `g.TryGo` starts work only if the limit permits and reports whether it did. For weighted permits rather than a goroutine count, `golang.org/x/sync/semaphore`'s `NewWeighted(n int64)` gives `Acquire(ctx, n) error`, `TryAcquire(n) bool`, and `Release(n)`.

### Channels for ownership transfer, mutexes for shared state

"Share memory by communicating" is a design heuristic, and the guidance itself warns against over-applying it: reference counts are usually best protected by a mutex around an integer, not a goroutine and a channel. Choose by what the data _is_:

| Situation                                                            | Tool                                                | Why                                                                                   |
| -------------------------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Handing a value or work item between goroutines                      | Channel                                             | The transfer _is_ the synchronization; the sender stops touching the value            |
| A map, counter, cache, or buffer read and written by many goroutines | `sync.Mutex` / `RWMutex`                            | The data outlives any single transfer; a channel would serialize it into a bottleneck |
| Goroutines that must all finish before the next step                 | `WaitGroup` or `errgroup`                           | Counting, not data movement                                                           |
| A flag or single pointer on a hot path                               | `sync/atomic` (`atomic.Pointer[T]`, `atomic.Int64`) | Lock-free, and the zero value is valid                                                |
| A rarely-written, frequently-read keyed map                          | `sync.Map`                                          | Only when the access pattern is genuinely read-mostly with stable keys                |

An unbuffered channel synchronizes sender and receiver; a buffer of size _n_ decouples them by _n_ items and then blocks. `select` with a `default` in a loop spins and starves the scheduler (`SA5004`); `for {}` with no `select` spins outright (`SA5002`). Never close a channel from the receiving side, never close one twice, and never close one with more than one sender — closing is the sender saying "no more values," and `v, ok := <-ch` is how the receiver learns it. `time.Tick` was a documented leak before Go 1.23; since then the GC recovers unreferenced tickers, so `Ticker.Stop` is no longer needed for collection, though `SA1015` still flags the pattern where a bounded function should have stopped one.

## Interfaces, Types, and Zero Values

### Accept interfaces, return structs, define the interface at the consumer

An interface belongs in the package that _uses_ values of it, not the package that implements them; the implementing package returns concrete types, usually pointers, so methods can be added without forcing every consumer to change. The fake that satisfies it lives in the consumer's own test file:

```go
// consumer.go — the interface and its user
type Thinger interface{ Thing() bool }

func Foo(t Thinger) string { /* ... */ }

// consumer_test.go — the fake lives here, not in the implementor
type fakeThinger struct{}

func (fakeThinger) Thing() bool { return true }
```

That is what "do not define interfaces on the implementor side for mocking" means: a producer-side `Thinger` exists only so tests can substitute it, coupling the producer to a test concern and hiding the real dependency. Do not define an interface before something uses it either — without a concrete consumer there is no evidence about which methods it needs, and the interface ends up too wide (implementations grow no-op methods) or too narrow (it widens on first real use). Keep them small, ideally one or two methods, with `io.Reader`, `io.Writer`, `fmt.Stringer`, and `error` the canonical shapes. A struct that happens to satisfy an interface needs no declaration; to have the compiler guarantee it, assert once at package scope with `var _ io.Writer = (*buffer)(nil)`. `ireturn` enforces the "return structs" half; `iface` and `interfacebloat` flag polluted and oversized interfaces. Never return an interface holding a nil concrete pointer — the interface is non-nil, so `err != nil` is true for a nil receiver (`nilnil` flags the `(nil, nil)` variant).

### Embedding is composition, not inheritance

Embedding promotes the embedded type's methods and fields into the outer type. That is all — no subtype relation, no virtual dispatch, no override. Use it to borrow an implementation, not to model is-a: below, `Log` and `Name` are promoted from `base` (so `Service` satisfies `Logger` through them), while `buf` and `mu` stay reachable only as fields.

```go
type Service struct {
	base              // promoted: Log, Name
	buf bytes.Buffer  // named: not promoted, reached as s.buf
	mu  sync.Mutex
}

var _ Logger = Service{}
```

Two consequences. Promotion leaks: adding a method to `base` silently adds it to `Service`'s method set, which can satisfy an interface you never intended. And embedding a `sync.Mutex` in an exported struct exposes `Lock`/`Unlock` to every caller and makes the struct non-copyable — `go vet`'s `copylocks` reports `assignment copies lock value` on any by-value copy, and the copy has an independent lock, silently breaking mutual exclusion. Embed a pointer, or use an unexported named field and pass `*T`. For interface composition embedding _is_ the right tool: `io.ReadWriter` is `Reader` and `Writer` embedded.

### Make the zero value useful

A well-designed type works when declared `var x T` with no constructor. `sync.Mutex`, `sync.WaitGroup`, `bytes.Buffer`, `sync.Map`, `atomic.Pointer[T]`, and `strings.Builder` all do. Design yours the same — the zero value means "empty and ready," and nil checks live in the methods rather than in a required constructor:

```go
type Counter struct {
	mu sync.Mutex   // zero value is unlocked — no init needed
	n  int
}

func (c *Counter) Inc() { c.mu.Lock(); c.n++; c.mu.Unlock() }
```

| Zero value                | Behavior                                                 | Guidance                                                                  |
| ------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------- |
| `nil` slice               | `len` 0, `range` safe, `append` allocates                | Usable; prefer it over `[]T{}` when empty                                 |
| `nil` map                 | Read returns the zero value; **write panics** (`SA5000`) | `make` it; guard with `if m == nil`                                       |
| `nil` channel             | Send and receive block forever                           | Legitimate as a permanently disabled `select` case                        |
| `nil` interface           | `x == nil` is true                                       | Never store a nil concrete pointer in an interface and test the interface |
| `sync.Mutex`, `WaitGroup` | Unlocked / empty                                         | Must not be copied after first use                                        |
| `atomic.Pointer[T]`       | nil                                                      | Valid; `Store`/`Load` work uninitialized                                  |

Where the zero value cannot be ready — a nil map, an unopened file, a nil `*sql.DB` — provide `NewX` and document the zero value as invalid. Do not split the difference: a type whose zero value _mostly_ works but panics on first write is worse than one that clearly requires construction. `maps.Clone(nil)` returns nil and `slices.Clone(nil)` preserves nilness, so a cloned nil map still panics on write. Use the three-index slice expression to stop `append` writing through an alias:

```go
base := []int{1, 2, 3, 4}
s := base[:2]
_ = append(s, 99)     // base is now [1 2 99 4] — append wrote into base's array

s2 := base[:2:2]      // a[low:high:max]: len 2, cap 2
_ = append(s2, 99)    // base unchanged; append allocated
```

A slice of pointers aliases the pointed-to values, not just the header: `slices.Clone` on `[]*Item` gives a new slice of the _same_ items, so mutation through either is visible through both. Prefer `slices` and `maps` over hand-rolled loops — `slices.SortFunc` (not stable; `SortStableFunc` when order of equals matters) with `cmp.Compare` as comparator, `slices.Contains`, `IndexFunc`, `DeleteFunc`, `Sorted`/`Collect` for iterators, `maps.Equal`, `maps.Clone`. `strings.Cut`, `CutPrefix`, and `CutSuffix` replace the `Index`-plus-slice idiom and return a `found` bool instead of a sentinel index.

### No `init()`, no package-level mutable state

`init` runs after every imported package initializes, in an order the importing package does not control — a global side effect with a hidden dependency graph, where two packages mutating a shared registry behave differently depending on linker resolution order. `gochecknoinits` flags every `init`; the fix is an explicit `NewX()` or `Setup()` called from `main`. Package-level mutable variables add a data race to the same problem: `var cache = map[string]string{}` is written by whichever goroutine arrives first, and `gochecknoglobals`/`reassign` flag them. Immutable package-level values are fine — sentinels, `regexp.MustCompile` declarations, exported constants. Everything else belongs on a struct constructed once and passed explicitly.

## Testing, Benchmarking, and Static Analysis

### Table-driven tests, subtests, parallelism

A test repeating its body with different inputs should be a table. `t.Run` names each case, so a failure reports `TestLookup/empty_id` and `-run TestLookup/empty_id` re-runs just that case (the pattern splits on unbracketed `/`).

```go
func TestLookup(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name    string
		id      string
		wantErr error
	}{{"empty id", "", ErrNotFound}, {"valid id", "abc", nil}}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			if _, err := lookup(tt.id); !errors.Is(err, tt.wantErr) {
				t.Fatalf("lookup(%q) err = %v, want %v", tt.id, err, tt.wantErr)
			}
		})
	}
}
```

Loop variables are per-iteration since Go 1.22, so capturing `tt` is correct without `tt := tt` — and `copyloopvar` flags the now-redundant copy. `t.Parallel` runs the test only alongside other parallel tests, and under `-count` or `-cpu` instances of the _same_ test never run in parallel with each other; `-parallel n` defaults to `GOMAXPROCS`. Parallelism constrains process-global state, which the testing package now enforces:

| Helper                              | Restriction                                                                                 |
| ----------------------------------- | ------------------------------------------------------------------------------------------- |
| `t.Setenv(k, v)`, `t.Chdir(dir)`    | Rejected in parallel tests or tests with parallel ancestors; both restore via `Cleanup`     |
| `testing.AllocsPerRun`              | Panics if parallel tests are running (Go 1.25) — its result is meaningless with others live |
| `t.TempDir()`, `t.Cleanup(f)`       | Safe; cleanup runs last-added-first-called                                                  |
| `t.Context()` (1.24)                | Canceled just before `Cleanup` runs — the right parent for a test-started server or worker  |
| `t.Attr(k, v)` (1.25), `t.Output()` | Key/value test-log attribute; an `io.Writer` without `t.Log`'s file/line prefix             |

`TestMain` must call `os.Exit(m.Run())`; returning normally discards the exit code and CI goes green on a broken build (`SA3000`). In CI, run `go test -race -shuffle=on -count=1 ./...` — `-shuffle=on` seeds from the clock and reports the seed for reproduction, and `-count=1` defeats the cache, which otherwise reports a cached PASS without running anything.

### Benchmarks and fuzzing

`testing.B.Loop` (Go 1.24) replaces `for i := 0; i < b.N; i++`. It resets the timer on first call, stops it on the last, and keeps loop-local arguments and results alive through a `runtime.KeepAlive` transformation so the compiler cannot optimize the measured work away — which the `b.N` form could not guarantee. Use `Loop` _or_ a `b.N` loop, never both, and write the condition exactly as `for b.Loop()` for the transformation to apply. Run with `go test -run=^$ -bench=. -benchmem ./...`: `-run=^$` keeps unit tests out of the benchmark run, and `-benchmem` adds the `B/op` and `allocs/op` columns that make an allocation regression visible. Never assign to `b.N` inside a benchmark (`SA3001`).

Fuzzing is the tool for parsers, decoders, and any `[]byte` or `string` boundary. `f.Add` seeds the corpus, `f.Fuzz` takes the target, and failing inputs land in `testdata/fuzz/<FuzzTestName>/` as permanent regression cases.

```go
func FuzzReverse(f *testing.F) {
	f.Add("hello")
	f.Fuzz(func(t *testing.T, s string) {
		if !utf8.ValidString(s) {
			t.Skip()
		}
		if got := strings.ToValidUTF8(s, ""); got != s {
			t.Errorf("changed %q to %q", s, got)
		}
	})
}
```

Target arguments are limited to `[]byte`, `string`, `bool`, `byte`, `rune`, `float32`, `float64`, and the sized integer types. Inside `F.Fuzz` only `*T` methods may be called (`F.Failed` and `F.Name` are the exceptions), the target must not retain or mutate supplied memory, and it must be fast and deterministic. `go test` runs the seed corpus only; `-fuzz <regexp>` starts mutation and the regexp must match exactly one package and one fuzz test. `-fuzztime` defaults to forever and accepts `Nx` (`-fuzztime 1000x`); `-fuzzminimizetime` defaults to `60s`.

### The gates that enforce all of the above

`go vet` is the baseline and needs no installation, but it only runs a subset of its analyzers during `go test`, so run it explicitly. Its set includes `copylocks`, `lostcancel`, `waitgroup` (1.25), `hostport` (1.25), `errorsas`, `loopclosure`, `nilfunc`, `printf`, `slog`, `stdversion`, `testinggoroutine`, `timeformat`, and `unreachable`. `go fix -diff ./...` (rewritten in Go 1.26) exits non-zero when a modernizer applies, and is how you migrate to current idioms instead of maintaining a style guide by hand. Verified transformations include `rangeint` (`for i := 0; i < n; i++` → `for i := range n`), `stringsseq` (`range strings.Split(s, "\n")` → `range strings.SplitSeq(s, "\n")`), `stringscut`/`stringscutprefix` (`strings.Index`, `HasPrefix` + `TrimPrefix` → `strings.Cut`/`CutPrefix`), `hostport` (`fmt.Sprintf("%s:%d", host, port)` → `net.JoinHostPort`), `waitgroup` (`wg.Add(1)` + `go func(){ defer wg.Done() }()` → `wg.Go`), and `newexpr` (Go 1.26's `new(expr)`). A `//go:fix inline` directive on your own function lets the `inline` modernizer apply your API migrations.

`staticcheck` covers what `go vet` does not attempt, configured per subtree by `staticcheck.conf` (TOML; deeper files override shallower ones, and the value `"inherit"` extends array options). `staticcheck -explain SA1019` prints a check's rationale; `staticcheck -go 1.25 ./...` overrides the version targeted, which otherwise comes from `go.mod`'s `go` directive.

| Family        | Meaning                            | Representative checks                                                                                                                                                                                                                       |
| ------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SA1`         | Standard library misuse            | `SA1004` tiny constant in `time.Sleep`; `SA1012` nil context; `SA1015` leaking `time.Tick`; `SA1019` deprecated identifier; `SA1029` bad `WithValue` key                                                                                    |
| `SA2` / `SA3` | Concurrency and testing            | `SA2000` `WaitGroup.Add` inside the goroutine; `SA2002` `t.FailNow` in a goroutine; `SA3000` `TestMain` without `os.Exit`; `SA3001` assigning to `b.N`                                                                                      |
| `SA4` / `SA5` | Dead code and correctness          | `SA4006` assigned then overwritten; `SA4010` `append` result never observed; `SA4023` impossible interface/nil comparison; `SA5000` assignment to nil map; `SA5001` deferring `Close` before checking the open error                        |
| `SA6` / `SA9` | Performance and dubious constructs | `SA6002` non-pointer value in `sync.Pool`; `SA9003` empty `if`/`else` body; `SA9010` returned function should be called in `defer`                                                                                                          |
| `ST1` / `QF1` | Style and quickfixes               | `ST1000` missing package comment; `ST1003` identifier; `ST1005` error string; `ST1006` receiver; `ST1008` error not last; `ST1016` inconsistent receivers; `QF1003` if/else-if to tagged switch; `QF1008` omit embedded field from selector |

`golangci-lint` runs the whole set in one pass, and its v2 schema differs from v1. Note that `gofmt` and `goimports` are _formatters_ in v2, not linters, and that `stylecheck`/`gosimple` no longer exist as separate entries — both were merged into `staticcheck`:

```yaml
version: "2"
linters:
  default: standard # errcheck, govet, ineffassign, staticcheck, unused
  enable:
    [
      bodyclose,
      contextcheck,
      copyloopvar,
      errorlint,
      exhaustive,
      gocritic,
      gosec,
      intrange,
      nilnil,
      noctx,
      nolintlint,
      paralleltest,
      predeclared,
      recvcheck,
      rowserrcheck,
      sloglint,
      sqlclosecheck,
      unconvert,
      unparam,
      usetesting,
    ]
  settings:
    errcheck: { check-type-assertions: true, check-blank: true }
    govet: { enable-all: true }
  exclusions:
    generated: strict
    rules: [{ path: (.+)_test\.go, linters: [dupl, funlen] }]
formatters:
  enable: [gofmt, goimports]
  settings:
    gofmt:
      simplify: true
      rewrite-rules: [{ pattern: "interface{}", replacement: "any" }]
    goimports: { local-prefixes: [github.com/acme/project] }
```

`linters.default` takes `standard`, `all`, `none`, or `fast`; `linters.exclusions` replaces the v1 `issues.exclude-rules`, with `generated: strict|disable` controlling generated files. `golangci-lint run --fix` applies the autofixes the enabled linters support; the CI gate is `golangci-lint run --new-from-rev=<base>` so only new findings block a pull request. Drive all of it from the project's task runner rather than a hand-typed command line, so local and CI invocation cannot diverge — [std-shell.md](std-shell.md) covers script conventions and [std-yaml-json.md](std-yaml-json.md) the config formatting.

## Common Mistakes

| Mistake                                             | Why It Breaks                                                                                       | Correct Approach                                                                   |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `fmt.Errorf("open %s: %v", path, err)`              | `%v` discards the chain; `errors.Is` can never match the original                                   | `%w` for errors, `%v` only for non-error values                                    |
| `if err == io.EOF`                                  | Fails for any wrapped `io.EOF`; `errorlint` flags it                                                | `errors.Is(err, io.EOF)`                                                           |
| `var e *MyError; errors.As(err, e)`                 | `errors.As` needs a pointer to the target, so it never matches                                      | `errors.As(err, &e)`, or `errors.AsType[*MyError](err)` on Go 1.26+                |
| `n, _ := strconv.Atoi(s)`                           | The failure silently becomes `n == 0`                                                               | Handle the error; enable errcheck's `check-blank`                                  |
| `errors.New` inside a hot function                  | A new value per call, so identity-based matching breaks                                             | One sentinel declared at package scope                                             |
| `ctx, _ := context.WithTimeout(...)`                | Leaks the child and its subtree until the parent is canceled                                        | `ctx, cancel := ...; defer cancel()`; `lostcancel` confirms                        |
| `ctx` stored in a struct field                      | Escapes the request's lifetime; `containedctx` flags it                                             | Pass `ctx` first on each method that needs it                                      |
| `http.NewRequest` inside a handler                  | The outgoing call ignores the caller's deadline and cancellation                                    | `http.NewRequestWithContext(ctx, ...)` / `req.WithContext(ctx)`                    |
| `wg.Add(1)` inside the goroutine                    | `Wait` can return before the counter increments — a data race                                       | `wg.Add(1)` before `go`, or `wg.Go(func(){...})` on 1.25+                          |
| A goroutine with no exit path                       | The GC never collects a blocked goroutine; it leaks its stack and channels for the process lifetime | Bound it with a caller-owned `ctx` or a `WaitGroup` the caller waits on            |
| `for { select { ... default: } }`                   | The empty `default` makes it a busy loop that starves the scheduler                                 | Drop `default`, or add a `ctx.Done()`/`time.After` case                            |
| `var m map[string]int; m["k"] = 1`                  | Assignment to a nil map panics at runtime                                                           | `make(map[string]int)`, or initialize in the constructor                           |
| `append(s[:2], x)` where `s` is shared              | Writes into the caller's backing array, changing data underneath it                                 | `s[:2:2]` to clamp capacity, or `slices.Clone(s[:2])`                              |
| `package common` / `type util struct{}`             | A name-free package becomes a dumping ground and hides ownership                                    | Name it after the domain: `chunked`, `retry`, `billing`                            |
| Inconsistent receiver names on one type             | Signals a copy-paste type with split ownership; `ST1016` reports it                                 | One short name, identical across every method                                      |
| `func (u *User) GetName() string`                   | `Get` prefixes are unidiomatic and add noise at every call site                                     | `Name()`; the setter stays `SetName()`                                             |
| `type Foo struct{ sync.Mutex }` copied by value     | `copylocks` reports it; the copy has an independent lock, silently breaking exclusion               | Embed `*sync.Mutex`, or use an unexported field and pass `*Foo`                    |
| `init()` registering into a package-level map       | Import-order-dependent global mutation; untestable and racy under `t.Parallel`                      | An explicit `NewRegistry()` called from `main`                                     |
| A producer-side interface defined only for mocking  | Couples the implementation to a test concern and freezes the interface before real use              | Define it in the consuming package; keep the fake in that package's `_test.go`     |
| `x == nil` after storing a nil `*T` in an interface | The interface is non-nil even though the pointer is nil                                             | Return concrete types; test the pointer, not the interface                         |
| `t.Setenv` inside a `t.Parallel` test               | The environment is process-global; the testing package rejects it                                   | Keep the test serial, or pass configuration explicitly                             |
| `for i := 0; i < b.N; i++` with an elidable body    | The compiler may remove the work; results are meaningless                                           | `for b.Loop()` (Go 1.24+), which keeps arguments and results alive                 |
| `TestMain` returning without `os.Exit(m.Run())`     | Failures produce exit code 0, so CI goes green on a broken build                                    | `os.Exit(m.Run())`                                                                 |
| Relying on `go test` alone for analysis             | It runs only a subset of `go vet`'s analyzers                                                       | Add `go vet ./...`, `staticcheck ./...`, and `golangci-lint run` as explicit gates |

## Checklist

1. Run `gofmt -l .` and confirm the output is empty, then `goimports -w -local <module> ./...` and confirm it produces no further diff.
2. Verify `gofmt -s` has been applied and that `interface{}` → `any` is either enforced by a rewrite rule or already absent.
3. Grep for `util`, `common`, `misc`, `helpers`, `api`, and `types` as package names and rename each after the domain it serves.
4. Check every exported identifier for initialism casing (`URL`, `ID`, `HTTP`, `API`, `SQL`, `EOF`, `TLS`) and for a `Get` prefix on getters.
5. Confirm every method receiver is short, identical across all methods of its type, and never `this`, `self`, or `me`.
6. Grep for `%v` applied to an `error` operand inside `fmt.Errorf` and replace each with `%w` unless the error is deliberately flattened.
7. Replace every `err == target` comparison with `errors.Is`, and every two-step `errors.As` with `errors.As(err, &target)` (or `errors.AsType` on Go 1.26+).
8. Inventory sentinels and typed errors; confirm no condition has both, and each sentinel is declared once at package scope with `errors.New`.
9. Enable `errcheck` with `check-blank: true` and `check-type-assertions: true`, then resolve every discard, including `_` assignments and unchecked assertions.
10. Grep for `panic(` and `recover(`; confirm each `panic` is an unrecoverable invariant and each `recover` sits at a goroutine entry point, handler boundary, or `defer` in a long-lived worker.
11. Verify every `WithCancel`/`WithTimeout`/`WithDeadline` call site calls its `CancelFunc` on all paths, and confirm with `go vet -lostcancel ./...`.
12. Confirm every `context.Context` parameter is first, named `ctx`, non-nil, and not a struct field; check that no function receiving a context also calls `context.Background()`.
13. Trace every outgoing HTTP, database, and RPC call to confirm it derives from the incoming context (`NewRequestWithContext`, `req.WithContext`, `QueryContext`, `ExecContext`).
14. List every `go` statement with its exit condition in one line, and add a `ctx`-bounded or `WaitGroup`-bounded exit to any that has none.
15. Replace `wg.Add(1)` + `go func(){ defer wg.Done() }()` pairs with `wg.Go(...)` on Go 1.25+, and run `go vet -waitgroup ./...` to confirm no `Add` remains inside a goroutine.
16. Confirm every channel has exactly one closer, that the closer is the sender, and that buffered channels used with `signal.Notify` hold the expected signal rate.
17. For each shared map, counter, or buffer, confirm the primitive matches the access pattern: mutex for shared state, channel for transfer, `atomic` for single-word hot paths, `sync.Map` only for read-mostly keyed data.
18. Audit interfaces: each is defined in the package that consumes it, is satisfied by at least two types or a fake in the consumer's `_test.go`, and was not written before its first use.
19. Verify each struct embedding borrows an implementation rather than standing in for inheritance, and that no embedded mutex makes a struct copyable — `go vet -copylocks ./...`.
20. Confirm the zero value of every exported type is usable as declared or documented as requiring a constructor, and that every nil map field is `make`-d on all construction paths.
21. Grep for `init()` and for package-level `var` declarations that are not immutable; move each into a constructor called from `main`.
22. Confirm tests are table-driven with `t.Run`, use `t.Parallel` where cases are independent, and confine `t.Setenv` and `t.Chdir` to serial tests.
23. Confirm every benchmark uses `for b.Loop()` or a `b.N` loop but not both, that CI passes `-benchmem`, and that no benchmark assigns to `b.N`.
24. Confirm every parser or decoder has a `FuzzXxx` target with `f.Add` seeds and a committed `testdata/fuzz/<FuzzTestName>/` corpus.
25. Verify `.golangci.yml` declares `version: "2"`, that `gofmt`/`goimports` sit under `formatters`, and that `stylecheck`/`gosimple` are absent.
26. Run `go vet ./...`, `staticcheck ./...`, `go fix -diff ./...`, and `golangci-lint run` to a clean exit, then wire all four into the project's task runner so CI runs the identical commands.

## References

- [Effective Go](https://go.dev/doc/effective_go) — getters, package names, embedding, `init`, and the "share memory by communicating" passage with its own caveat about over-application.
- [Go Code Review Comments](https://go.dev/wiki/CodeReviewComments) — initialisms, receiver names, error strings, interface placement at the consumer, goroutine lifetimes, indent-error-flow.
- [The Go Programming Language Specification](https://go.dev/ref/spec) — normative rules for `for` loops, full slice expressions, method sets, and embedding.
- [Go blog: Package names](https://go.dev/blog/package-names) — why `util`, `common`, and `types` are prohibited, and how to choose a domain-bearing name.
- [Go blog: Go Doc Comments](https://go.dev/doc/comment) — the comment syntax `gofmt` reformats since Go 1.19.
- [Go blog: Contexts and structs](https://go.dev/blog/context-and-structs) — the canonical argument against storing a context in a struct field.
- [Go blog: Context](https://go.dev/blog/context) — request-scoped values, deadlines, and propagation through a call chain.
- [Go blog: Working with Errors in Go 1.13](https://go.dev/blog/go1.13-errors) — `%w`, `errors.Is`, `errors.As`, and when not to wrap.
- [Go blog: Error handling and Go](https://go.dev/blog/error-handling-and-go) — sentinel versus typed errors and the `(value, error)` convention.
- [Go blog: Pipelines and cancellation](https://go.dev/blog/pipelines) — goroutine ownership, channel closure, and the leak patterns to avoid.
- [Go wiki: Mutex or Channel](https://go.dev/wiki/MutexOrChannel) — the decision table for shared state versus message passing.
- [Go blog: Using Subtests and Sub-benchmarks](https://go.dev/blog/subtests) — `t.Run`, `-run` with `/`, and table-driven structure.
- [Go fuzzing documentation](https://go.dev/doc/fuzz/) and [tutorial](https://go.dev/doc/tutorial/fuzz) — `f.Add`, `f.Fuzz`, allowed argument types, and `testdata/fuzz` corpus handling.
- [Go memory model](https://go.dev/ref/mem) — the happens-before guarantees that make `WaitGroup`, `Mutex`, and channel operations correct.
- [Package `testing/synctest`](https://pkg.go.dev/testing/synctest) — the fake-clock bubble API for deterministic concurrency tests, with `synctest.Test` and `synctest.Wait` restrictions.
- [Package `golang.org/x/sync/errgroup`](https://pkg.go.dev/golang.org/x/sync/errgroup) — `WithContext` cancellation semantics, `SetLimit`, and `TryGo`.
- [Package `cmd/vet`](https://pkg.go.dev/cmd/vet) — the full analyzer list, including `copylocks`, `lostcancel`, `waitgroup`, `hostport`, and `errorsas`.
- [Staticcheck: all checks](https://staticcheck.dev/docs/checks/) — the `SA`, `S`, `ST`, and `QF` families with identifiers and availability versions.
- [Staticcheck: configuration](https://staticcheck.dev/docs/configuration/) — `staticcheck.conf` TOML, per-subtree merging, and the `"inherit"` value.
- [golangci-lint: linters configuration](https://golangci-lint.run/docs/linters/configuration/) and [formatters configuration](https://golangci-lint.run/docs/formatters/configuration/) — the v2 `linters.default` set and the relocated formatter keys.
- [golangci-lint: configuration file](https://golangci-lint.run/docs/configuration/) — `linters.exclusions`, `issues.*`, and the migration from v1 keys.
- [Go 1.22 release notes](https://go.dev/doc/go1.22) — per-iteration loop variables and `for i := range n`.
- [Go 1.24 release notes](https://go.dev/doc/go1.24) — `testing.B.Loop`, `T.Context`, `T.Chdir`, `os.Root`, and `tool` directives in `go.mod`.
- [Go 1.25 release notes](https://go.dev/doc/go1.25) — `sync.WaitGroup.Go`, the `waitgroup` and `hostport` vet analyzers, `T.Attr`/`T.Output`, container-aware `GOMAXPROCS`.
- [Go 1.26 release notes](https://go.dev/doc/go1.26) — `errors.AsType`, the rewritten `go fix` modernizer suite, `new(expr)`, and the lowered `go` directive default.
- [Go Modules Reference](https://go.dev/ref/mod) — `go.mod` directives, including `tool` and `toolchain`.
- [Organizing a Go module](https://go.dev/doc/modules/layout) — `cmd/` and `internal/` placement rules.
