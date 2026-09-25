# C# and .NET Standards

Covers the conventions the C# compiler and the .NET SDK can be made to enforce — nullable flow analysis, analyzer severities, asynchrony, resource lifetime, allocation discipline, DI and configuration — plus the ones only a reviewer catches. Getting these wrong fails in ways tests rarely surface: a `Task.Result` that deadlocks only under a synchronization context, an `IEnumerable` enumerated twice that hits the database twice, a `required` member silently bypassed by `[SetsRequiredMembers]`, a `Span<T>` that will not compile once someone wraps the method in `async`.

## Contents

- [When This Applies](#when-this-applies)
- [Enforcement: Compiler Flags, Analyzers, and EditorConfig](#enforcement-compiler-flags-analyzers-and-editorconfig)
  - [The project-file surface that does the enforcing](#the-project-file-surface-that-does-the-enforcing)
  - [Severities, naming, and per-rule scoping](#severities-naming-and-per-rule-scoping)
  - [Keeping it applied](#keeping-it-applied)
- [Type Design: Nullability, Records, and Required Members](#type-design-nullability-records-and-required-members)
  - [Nullability is a flow contract, not a syntax flag](#nullability-is-a-flow-contract-not-a-syntax-flag)
  - [Records, `init`, and `required`](#records-init-and-required)
  - [Exhaustiveness](#exhaustiveness)
- [Asynchrony and Resource Lifetime](#asynchrony-and-resource-lifetime)
  - [Never block on a task](#never-block-on-a-task)
  - [ConfigureAwait: a library concern only](#configureawait-a-library-concern-only)
  - [Streaming with `IAsyncEnumerable<T>`](#streaming-with-iasyncenumerablet)
  - [Disposal](#disposal)
- [Allocation, Collections, and Exceptions](#allocation-collections-and-exceptions)
  - [`Span<T>` and the `ref struct` boundary](#spant-and-the-ref-struct-boundary)
  - [LINQ, deferred execution, and multiple enumeration](#linq-deferred-execution-and-multiple-enumeration)
  - [Exceptions are not control flow](#exceptions-are-not-control-flow)
- [Project Structure, DI, Configuration, and Tests](#project-structure-di-configuration-and-tests)
  - [`Directory.Build.props` and central package management](#directorybuildprops-and-central-package-management)
  - [Dependency injection and the options pattern](#dependency-injection-and-the-options-pattern)
  - [Logging and tests](#logging-and-tests)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- The repository contains `.cs`, `.csproj`, `.sln`, `.props`, or `.editorconfig` files, or a `Directory.Build.props`.
- Nullable reference types are absent from the project file, or `<Nullable>` is set on some projects and not others.
- `AnalysisMode`, `EnforceCodeStyleInBuild`, or `TreatWarningsAsErrors` differ between projects in one solution.
- `.Result`, `.Wait()`, `.GetAwaiter().GetResult()`, or `async void` appear anywhere outside an event handler.
- `IEnumerable<T>` values are enumerated more than once, or LINQ chains materialize into `List<T>` defensively "just in case".
- The codebase mixes `var` and explicit types for the same category of declaration, or mixes block-scoped and file-scoped namespaces.
- Services are resolved with `IServiceProvider.GetService` outside a composition root, or `BuildServiceProvider()` is called during registration.
- Test projects use bare `Assert.Equal`, or FluentAssertions is pinned at v8+ in a commercial repository.

## Enforcement: Compiler Flags, Analyzers, and EditorConfig

### The project-file surface that does the enforcing

These belong in `Directory.Build.props`, not repeated per project. Their defaults are permissive; the standard is to make them strict and let projects opt out explicitly.

```xml
<Project>
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <WarningsAsErrors>nullable</WarningsAsErrors>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
    <AnalysisLevel>latest-recommended</AnalysisLevel>
    <GenerateDocumentationFile>true</GenerateDocumentationFile>
  </PropertyGroup>
</Project>
```

| Property                            | Allowed values                                                                | Notes                                                                                                             |
| ----------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `Nullable`                          | `enable`, `disable`, `warnings`, `annotations`                                | Default is `disable`; .NET 6+ templates set `enable`. The `warnings`/`annotations` split is useful mid-migration. |
| `AnalysisMode`                      | `None`, `Default`, `Minimum`, `Recommended`, `All`                            | `Default` ships only a small rule set as build warnings.                                                          |
| `AnalysisLevel`                     | `latest`, `preview`, `latest-<mode>`, `preview-<mode>`, or a version like `9` | Compound form `preview-recommended` is valid. Defaults to `latest` when targeting .NET 5+.                        |
| `WarningsAsErrors`                  | `CS` IDs, bare numbers, or the literal `nullable`                             | `nullable` promotes every nullability warning at once.                                                            |
| `CodeAnalysisTreatWarningsAsErrors` | `true`, `false`                                                               | Set `false` to keep CA rules as warnings while `-warnaserror` is on for compiler warnings.                        |

`AnalysisMode` = `All` does **not** enable every rule. CA1017, CA1045, CA1005, CA1014, CA1060, CA1021, and the code-metrics rules CA1501, CA1502, CA1505, CA1506, CA1509 stay off; enable them individually via `dotnet_diagnostic.CAxxxx.severity`. `AnalysisMode` also causes bulk `dotnet_analyzer_diagnostic.*` entries in `.editorconfig` to be ignored.

Generated code is exempt from the global nullable context regardless of `<Nullable>`: a file counts as generated when `.editorconfig` sets `generated_code = true`, the first comment contains `<auto-generated>`, the name starts with `TemporaryGeneratedFile_`, or it ends in `.designer.cs`, `.generated.cs`, `.g.cs`, or `.g.i.cs`. A generator opts back in with `#nullable enable`.

### Severities, naming, and per-rule scoping

Severity values are `error`, `warning`, `suggestion`, `silent`, `none`, and `default`. Only `error` and `warning` are enforced on build; `suggestion` becomes a build _message_.

```ini
[*.cs]
dotnet_diagnostic.CA1031.severity = error
dotnet_diagnostic.IDE0005.severity = warning
dotnet_diagnostic.CA1707.api_surface = public
csharp_style_namespace_declarations = file_scoped
csharp_style_var_for_built_in_types = false
csharp_style_var_when_type_is_apparent = true
csharp_style_var_elsewhere = false
dotnet_style_require_accessibility_modifiers = always
dotnet_style_prefer_collection_expression = when_types_loosely_match
dotnet_naming_symbols.private_fields.applicable_kinds = field
dotnet_naming_symbols.private_fields.applicable_accessibilities = private
dotnet_naming_style.underscored.capitalization = camel_case
dotnet_naming_style.underscored.required_prefix = _
dotnet_naming_rule.private_fields_underscored.symbols = private_fields
dotnet_naming_rule.private_fields_underscored.style = underscored
dotnet_naming_rule.private_fields_underscored.severity = error
```

Four facts about this file that are easy to get wrong:

- **Naming-rule `severity` is IDE-only.** The compiler ignores it, so `severity = error` inside a `dotnet_naming_rule.*` block does not fail the build. Enforce on build with `dotnet_diagnostic.IDE1006.severity = error`; the symbol-group/style/rule triples still declare the convention.
- **`required_modifiers` cannot express absence.** There is no "instance only" modifier, so exempting `static` fields from the `_camelCase` rule needs a second symbol group (`required_modifiers = static`) with its own rule. A `static` group also matches `const`, since `const` is implicitly `static`.
- **`applicable_kinds = class` includes records**, and tuple members are not supported by `applicable_kinds` at all.
- **IDE0005 (unnecessary usings) only runs on build when XML documentation is generated** — hence `GenerateDocumentationFile` above. Without it the rule is IDE-only.

CA1707 checks namespaces, types, members, _and parameters_ for underscores, which conflicts with `_camelCase` private fields; scope it with `api_surface` or suppress it (Microsoft's guidance says suppressing it for test code is safe). CA1062 (validate arguments of public methods) is not enabled by default in .NET 10, so argument validation is a review rule, not a build rule.

### Keeping it applied

```bash
dotnet format --verify-no-changes              # non-zero exit if anything would change
dotnet format analyzers --diagnostics CA1851 --severity warn
```

`dotnet format` subcommands are `whitespace`, `style`, and `analyzers`; `--severity` accepts `info`, `warn`, `error` and defaults to `warn`. StyleCop is a separate package (`StyleCop.Analyzers`); its ordering rules are the ones that matter — SA1200 (using directives outside a namespace) and SA1201 (elements in the correct order). For hard prohibitions, `Microsoft.CodeAnalysis.BannedApiAnalyzers` reads a `BannedSymbols.txt` registered as `AdditionalFiles`, using documentation-comment IDs (`M:System.Threading.Tasks.Task.Wait`), and reports RS0030 for a banned use and RS0031 for a duplicate entry.

## Type Design: Nullability, Records, and Required Members

### Nullability is a flow contract, not a syntax flag

`<Nullable>enable</Nullable>` makes the compiler track null state and emit CS8602 (dereference of a possibly null reference), CS8603, CS8604, CS8618 (non-nullable field must contain a non-null value when exiting constructor), and the rest. The compiler trusts annotations, so they are the API contract: `[AllowNull]`/`[DisallowNull]` are preconditions; `[MaybeNull]`/`[NotNull]` are postconditions on returns and `out`/`ref`; `[MaybeNullWhen(bool)]`/`[NotNullWhen(bool)]` tie a postcondition to a return value as in `TryParse`; `[NotNullIfNotNull]` makes the output non-null exactly when the named input is; `[MemberNotNull]`/`[MemberNotNullWhen]` guarantee named members after the call; `[DoesNotReturn]`/`[DoesNotReturnIf(bool)]` mark methods that never return. The same contract exists elsewhere in the type system: TypeScript's `strictNullChecks` with `x is T` predicates, or Rust's `Option<T>` with no nullable escape hatch. C#'s difference is that annotations are advisory metadata the compiler consumes but that survive erasure — so a mis-annotated library lies to every consumer's flow analysis.

### Records, `init`, and `required`

| Construct                                | Introduced | Semantics                                                                                   |
| ---------------------------------------- | ---------- | ------------------------------------------------------------------------------------------- |
| `record` / `record class`                | C# 9       | Reference type, value equality, positional properties immutable.                            |
| `init` accessor                          | C# 9       | Settable only during object initialization; enables `with` expressions.                     |
| `record struct`                          | C# 10      | Value type; positional properties are **mutable** unless declared `readonly record struct`. |
| `required`                               | C# 11      | Member must be set by an object initializer.                                                |
| Primary constructors on any class/struct | C# 12      | Parameters in scope for the type body; no synthesized properties outside records.           |
| `field` keyword in an accessor           | C# 14      | Compiler-synthesized backing field, no explicit private field.                              |

```csharp
public sealed record Money
{
    public required decimal Amount { get; init; }
    public required string Currency { get; init; }

    public Money Add(Money other) => Currency == other.Currency
        ? this with { Amount = Amount + other.Amount }
        : throw new InvalidOperationException($"Cannot add {other.Currency} to {Currency}.");
}
```

`required` rules the compiler enforces, each with its own error code: a required member and its setter must be at least as visible as the containing type (CS9032, CS9034); a required member cannot be hidden by a derived member, and an override of a required property must repeat `required` (CS9031); a type with required members cannot be a type argument where the constraint includes `new()` (CS9040); a constructor annotated `[SetsRequiredMembers]` **disables the check**, and one that chains to such a constructor must carry the attribute too (CS9039). `required` cannot be applied to interface members, to explicit interface implementations, or directly to record positional parameters. `[SetsRequiredMembers]` asserts rather than verifies, so prefer a factory method or a primary constructor that genuinely assigns every required member, and reserve it for `record` copy constructors and source-generated interop.

### Exhaustiveness

`switch` expressions warn when a case is missing: CS8509 when the input is an enum or a closed set, CS8524 when an unnamed enum value is the gap, CS8655 when the gap is `null`. Treat those as errors and close the final arm explicitly rather than defaulting to a silent value — `_ => throw new UnreachableException($"Unhandled {nameof(PaymentMethod)}: {method}.")`. `UnreachableException` (`System.Diagnostics`, .NET 7+) exists for exactly this arm: unlike `InvalidOperationException` it will not be mistaken for ordinary control flow, and it distinguishes "the compiler cannot prove this is unreachable" from "the program is in an impossible state". When a switch expression is genuinely total, omit the arm and let the compiler prove it.

## Asynchrony and Resource Lifetime

### Never block on a task

`Task<T>.Result`, `Task.Wait()`, `Task.GetAwaiter().GetResult()`, and any `Async`-suffixed method's synchronous twin are flagged by CA1849 ("Call async methods when in an async method") when called from a `Task`-returning method. The failure they cause is a deadlock, not a slowdown: in a context with a `SynchronizationContext` or a bounded thread pool, the blocked thread is the one the continuation needs.

`async void` is worse — exceptions thrown after the first `await` cannot be caught by the caller and crash the process. Return `async void` only from event handlers. xUnit's analyzers enforce the test-side equivalents: xUnit1031 ("Do not use blocking task operations in test method"), and for v3 xUnit1049 ("Do not use 'async void' for test methods as it is no longer supported") with xUnit1048 warning during migration. xUnit1031 explains the mechanism: tests run on a user-bounded pool of threads, so blocking work forces continuations onto other threads and can exhaust the pool into a deadlock. The same shape exists elsewhere: in Python, a blocking `requests.get` inside `async def` stalls the entire event loop and the fix is an async client, not a thread; in Go, a synchronous channel receive where a `select` with `ctx.Done()` belongs produces a goroutine that never exits.

### ConfigureAwait: a library concern only

CA2007 ("Do not directly await a Task") is off by default and is **intended for libraries**. Microsoft's guidance is unambiguous: application code should generally suppress it, and running it on application code "is likely to lead to the wrong actions being taken". ASP.NET Core has no `SynchronizationContext` or non-default `TaskScheduler`, so `ConfigureAwait` changes nothing there.

| Context                             | Guidance                                                                                    |
| ----------------------------------- | ------------------------------------------------------------------------------------------- |
| NuGet library / reusable component  | `ConfigureAwait(false)` on every await — the code runs in environments it does not control. |
| ASP.NET Core app                    | Neither needed nor harmful; the context is absent.                                          |
| WinForms / WPF / MAUI event handler | Keep the default (`ConfigureAwait(true)`) — the continuation must return to the UI thread.  |
| Test method                         | Do **not** call it (xUnit1030).                                                             |

Scope CA2007 rather than suppressing per-file: `dotnet_code_quality.CA2007.output_kind = ConsoleApplication, DynamicallyLinkedLibrary` applies it to non-UI output kinds only, and `dotnet_code_quality.CA2007.exclude_async_void_methods = true` skips handlers. Return the task rather than awaiting and returning it only when there is no work after the await; `return _client.GetStringAsync(url);` skips a state machine but also skips any `try`/`catch` added later, so a method that validates arguments or wraps exceptions must `await`.

### Streaming with `IAsyncEnumerable<T>`

```csharp
public async IAsyncEnumerable<Reading> ReadAsync(
    string deviceId,
    [EnumeratorCancellation] CancellationToken cancellationToken = default)
{
    await foreach (Reading reading in _source.StreamAsync(deviceId, cancellationToken))
    {
        yield return reading;
    }
}

await foreach (Reading reading in service.ReadAsync("d1").WithCancellation(ct))
{
    Process(reading);
}
```

`[EnumeratorCancellation]` marks the parameter that receives the token passed to `GetAsyncEnumerator`. `WithCancellation` does exactly one thing: it sets the token handed to `GetAsyncEnumerator`; the compiler combines it with any token passed to the iterator entry point and routes the result into the marked parameter. It does **not** poll the token or inject checks into the body — cancellation only takes effect where your code observes it. `IAsyncEnumerable<T>` also has `ConfigureAwait(bool)` and `WithCancellation` extension methods returning `ConfiguredCancelableAsyncEnumerable<T>`, so library streaming code writes `.ConfigureAwait(false)` after the enumerable, not after each `await foreach`. Forward tokens with CA2016 ("Forward the CancellationToken parameter to methods that take one") and place the token last per CA1068 ("CancellationToken parameters must come last"). For concurrency, `Parallel.ForEachAsync` is the built-in bounded-parallelism primitive; do not launch an unbounded `Task.WhenAll` over an `IAsyncEnumerable<T>`.

### Disposal

A `using` declaration disposes at end of scope; `await using` is the `IAsyncDisposable` form (`using HttpClient client = new();`, `await using FileStream stream = File.OpenRead(path);`). Both replace the brace form except when the scope must end early.

- Types that own disposable fields must implement `IDisposable` (CA1001); `Dispose` should be idempotent and call `GC.SuppressFinalize(this)` in unsealed types (CA1816).
- Objects the DI container creates are disposed by the container — transient and scoped at the end of their scope, singletons when the provider is disposed. Never dispose a resolved service yourself.
- CA2000 ("Dispose objects before losing scope") catches the object created, never disposed, and dropped.
- `ValueTask` may be awaited only once and must not be stored or consumed concurrently (CA2012); if the result may be awaited twice, use `Task`.

## Allocation, Collections, and Exceptions

### `Span<T>` and the `ref struct` boundary

`Span<T>` and `ReadOnlySpan<T>` are `ref struct` types: they live only on the stack, so they cannot be a field of a class, a generic type argument without `allows ref struct`, or a local in an `async` method or iterator (CS4013). C# 14 adds first-class span conversions, so `T[]` and `Span<T>` compose implicitly and extension methods accept spans naturally.

```csharp
static bool TryParseHeader(ReadOnlySpan<char> line, out ReadOnlySpan<char> value)
{
    int separator = line.IndexOf(':');
    if (separator < 0) { value = default; return false; }
    value = line[(separator + 1)..].Trim();
    return true;
}
```

Accept `ReadOnlySpan<char>` instead of `string` where you only slice, return spans only when the backing memory outlives the call, and keep the parse synchronous — the moment the caller needs `await`, the span must become a `string` or an array anyway. `stackalloc` is safe only when the size is bounded by a small constant.

### LINQ, deferred execution, and multiple enumeration

```csharp
IEnumerable<Order> orders = _repository.Query(customerId);

int count = orders.Count();
Order? latest = orders.OrderByDescending(o => o.PlacedAt).FirstOrDefault();
```

That is two round trips. CA1851 ("Possible multiple enumerations of `IEnumerable` collection") exists for exactly this, and its own note is that a repeated enumeration is a _correctness_ bug when the source has side effects, not merely a performance one. Materialize once — `Order[] orders = [.. _repository.Query(customerId)];` — or pass the result through a single chain.

The identical failure mode appears in Python, where a generator is consumed by the first loop and silently yields nothing to the second; in Java, where a `Stream` throws `IllegalStateException` on reuse instead. C#'s version is the quiet one: the second enumeration re-runs the query. Related rules worth enforcing: CA1860 (avoid `Enumerable.Any()` where `Count`/`Length` is O(1)), CA1861 (avoid constant arrays as arguments — they allocate per call), CA1859 (use concrete types when the abstraction is never substituted), CA1002 (do not expose `List<T>` from a public API; expose `IReadOnlyList<T>`).

### Exceptions are not control flow

```csharp
public Order GetOrder(OrderId id)
{
    ArgumentNullException.ThrowIfNull(id);
    return _orders.TryGetValue(id, out Order? order)
        ? order
        : throw new OrderNotFoundException(id);
}

public sealed class OrderNotFoundException(OrderId id)
    : Exception($"Order '{id}' was not found.")
{
    public OrderId OrderId { get; } = id;
}
```

- Use `TryGetValue`/`TryParse` for expected absence; reserve exceptions for the exceptional.
- Throw helpers replace the null-check block and are cheaper: `ArgumentNullException.ThrowIfNull`, `ArgumentException.ThrowIfNullOrEmpty`, `ArgumentException.ThrowIfNullOrWhiteSpace`, `ArgumentOutOfRangeException.ThrowIfNegative`, `.ThrowIfNegativeOrZero`, `.ThrowIfZero`, `.ThrowIfGreaterThan`, `.ThrowIfLessThan`, and `ObjectDisposedException.ThrowIf`. CA1510 flags the hand-written null-check-plus-throw form.
- A custom exception type that may be serialized or remoted needs the standard constructors (parameterless, message, message + inner); always pass `inner` so the causal chain survives.
- Never catch `Exception` to swallow (CA1031), never throw reserved types like `Exception` or `ApplicationException` (CA2201), and never log-and-rethrow — that duplicates the log entry at every frame. Prefer a domain error result over an exception when the caller is expected to branch on the outcome; an exception crossing a layer boundary should be translated at that boundary.

## Project Structure, DI, Configuration, and Tests

### `Directory.Build.props` and central package management

MSBuild searches **upward** from `$(MSBuildProjectFullPath)` for `Directory.Build.props` and stops at the first file it finds — the solution's location is irrelevant. A nested file does not merge automatically; it must chain explicitly:

```xml
<Import Project="$([MSBuild]::GetPathOfFileAbove('Directory.Build.props', '$(MSBuildThisFileDirectory)../'))"
        Condition="'' != $([MSBuild]::GetPathOfFileAbove('Directory.Build.props', '$(MSBuildThisFileDirectory)../'))" />
```

`Directory.Build.props` is imported early, so a property it sets can be overwritten by the project; properties that must win belong in `Directory.Build.targets`, imported late (after NuGet `.targets`). Use `msbuild /pp:preprocessed.xml MyProject.csproj` to see the actual evaluation order when a property "does not take effect".

Package versions belong in `Directory.Packages.props` with central package management: set `<ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>`, declare `<PackageVersion Include="..." Version="..." />` there, and reference `<PackageReference Include="..." />` with no `Version` in each project. Setting `CentralPackageVersionOverrideEnabled` to `false` makes `VersionOverride` a restore error rather than an invisible exception to the standard — the point of centralizing. Transitive pinning (`CentralPackageTransitivePinningEnabled`) cannot downgrade; a lower pin fails restore with NU1109. `GlobalPackageReference` (SDK 7.0.100+ / NuGet 6.4+) applies a build-only package to every project.

### Dependency injection and the options pattern

Register services in a composition root and inject them through constructors. The rules the docs call out, and the reasons:

- **No service locator.** `IServiceProvider.GetService` and injected factories that resolve at runtime invert nothing; they hide dependencies from the constructor signature and from the container's validation.
- **No `BuildServiceProvider()` during registration.** Use the `IServiceProvider` overload of the registration method; building an intermediate provider creates a second container with its own singletons.
- **Validate scopes.** Scope validation catches a singleton capturing a scoped service — the "captive dependency", where a longer-lived service promotes a shorter-lived one to application lifetime, including its `DbContext`.
- **Singleton means thread-safe**, and cannot react to configuration reload. Transient and scoped services are disposed at the end of their scope, singletons at provider disposal — never dispose a resolved service yourself.
- **No async construction.** C# has no asynchronous constructor; resolve synchronously and expose an `InitializeAsync`, or use an async factory consumed at startup.

Configuration binds through the options pattern, never through `IConfiguration` injected into business logic:

```csharp
public sealed class RetryOptions
{
    [Range(0, 10)] public int MaxAttempts { get; set; } = 3;
    [Required] public string[] Endpoints { get; set; } = [];
}

builder.Services
    .AddOptions<RetryOptions>()
    .Bind(builder.Configuration.GetSection("Retry"))
    .ValidateDataAnnotations()
    .ValidateOnStart();
```

`IOptions<T>` is a singleton snapshot; `IOptionsSnapshot<T>` recomputes per scope; `IOptionsMonitor<T>` supports change notification and is the only one safe to hold in a singleton. `ValidateDataAnnotations` needs the `Microsoft.Extensions.Options.DataAnnotations` package; `ValidateOnStart` turns bad configuration into a startup failure instead of a request-time exception.

### Logging and tests

Use `ILogger<T>` injected via constructor, with structured named placeholders — never string interpolation, which destroys the structured fields:

```csharp
public sealed partial class OrderProcessor(ILogger<OrderProcessor> logger)
{
    public void Process(Order order)
    {
        LogProcessed(order.Id, order.Lines.Count);
        logger.LogInformation("Order {OrderId} queued", order.Id);
    }

    [LoggerMessage(Level = LogLevel.Information, Message = "Processed order {OrderId} with {LineCount} lines")]
    private partial void LogProcessed(OrderId orderId, int lineCount);
}
```

The source-generated `[LoggerMessage]` partial method is what CA1848 ("Use the LoggerMessage delegates") asks for, and the reason is mechanical: the extension methods box value types into `object` and re-parse the template on every call, while the generated method caches the template and takes strongly typed parameters. `Microsoft.Extensions.Logging.Abstractions` alone is enough for a library; a library should never configure providers or call `AddConsole`.| Concern | Rule |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Test project | Reference `Microsoft.NET.Test.Sdk`, set `IsPackable=false`, disable `GenerateDocumentationFile` (CS1591). |
| Blocking | Never `.Result`/`.Wait()` in a test (xUnit1031); make the test `async Task` and `await`. |
| `async void` | Not allowed (xUnit1049 in v3; xUnit1048 warns during migration). |
| Cancellation | Use `TestContext.Current.CancellationToken` rather than `CancellationToken.None` (xUnit1051). |
| Naming | `MethodName_Scenario_ExpectedOutcome`; exclude test projects from the production naming rules. |
| Assertions | Constraint model or FluentAssertions, not bare equality with no message. |
| FluentAssertions | v8+ is free only for non-commercial use and needs a paid Xceed license commercially; v7 remains Apache-2.0 and is the safe commercial pin. |

For NUnit the analyzers push the same way: NUnit2005 ("Consider using Assert.That(actual, Is.EqualTo(expected)) instead of ClassicAssert.AreEqual") and NUnit2010 ("Use EqualConstraint for better assertion messages in case of failure"). Assertions exist to produce a _diagnosis_; `Assert.True(x == y)` produces only `Expected: True, Actual: False`. Time-dependent tests should inject `TimeProvider` (`System.TimeProvider` on .NET 8+, `Microsoft.Bcl.TimeProvider` below) rather than calling `DateTimeOffset.UtcNow`, so a `FakeTimeProvider` can advance the clock. From .NET 10, `dotnet test` can run a Microsoft.Testing.Platform runner configured in `global.json` as `{"test": {"runner": "Microsoft.Testing.Platform"}}`.

## Common Mistakes

| Mistake                                                                      | Why It Breaks                                                                                                                     | Correct Approach                                                                                        |
| ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Blocking on a task with `.Result` / `.Wait()`                                | Deadlocks where a synchronization context or bounded pool exists; exceptions arrive wrapped in `AggregateException`               | `await` the task; make the whole call path async; CA1849 catches it                                     |
| `async void` outside an event handler                                        | Exceptions after the first `await` are unobservable and crash the process; the method cannot be awaited or tested                 | Return `Task`/`Task<T>`; xUnit1049 for tests                                                            |
| `ConfigureAwait(false)` applied to application or test code                  | Wrong in UI handlers (the continuation must return to the UI thread) and meaningless in ASP.NET Core (no context)                 | Scope CA2007 to library output kinds; never call it in a test (xUnit1030)                               |
| Marking a constructor `[SetsRequiredMembers]` without assigning every member | The attribute _disables_ the compiler's check, so the required-member guarantee silently disappears                               | Assign all required members and omit the attribute, or keep it only on a compiler-generated constructor |
| `Count()` / repeated loops over an `IEnumerable<T>`                          | Deferred LINQ re-executes the query on every enumeration; two round trips, or a side-effecting source applied twice               | Materialize once with a collection expression, or keep one chain; CA1851 detects it                     |
| Catching `Exception` at a boundary to log and rethrow                        | Duplicated log entries at every frame; swallows `OperationCanceledException` and turns cancellation into an error                 | Catch what you can handle; translate at the boundary; let cancellation propagate; CA1031                |
| `_camelCase` private fields with CA1707 enabled unscoped                     | The rule flags underscores in members and parameters, so the convention fails the build                                           | Scope it with `dotnet_code_quality.CA1707.api_surface = public`; suppress it in test projects           |
| Singleton service holding a scoped `DbContext`                               | Captive dependency: the context lives for the application lifetime, sharing state across requests and never releasing connections | Enable scope validation; inject `IServiceScopeFactory` or make the lifetime scoped                      |
| `IConfiguration` injected into business logic and read by string key         | No validation, no strong typing, no startup failure, no reload semantics                                                          | Bind to an options class with `ValidateDataAnnotations().ValidateOnStart()`                             |
| `<Nullable>enable</Nullable>` added without fixing CS8618 in constructors    | Warnings become errors under `TreatWarningsAsErrors`, or worse, are suppressed wholesale                                          | Use `required`, `init`, or a constructor that assigns; migrate per-project, not per-file                |
| `AnalysisMode` set to `All` and assumed exhaustive                           | CA1017, CA1045, CA1005, CA1014, CA1060, CA1021 and the code-metrics rules stay disabled regardless                                | Enable those individually with `dotnet_diagnostic.CAxxxx.severity`                                      |
| `Span<T>` passed across an `await`                                           | CS4013 — `ref struct` locals cannot exist in an async method or iterator                                                          | Keep the span work in a synchronous method and convert at the boundary                                  |

## Checklist

1. Verify `Directory.Build.props` exists at the repository root and that nested props files import their parent via `$([MSBuild]::GetPathOfFileAbove(...))` rather than relying on implicit merging.
2. Confirm `<Nullable>enable</Nullable>` is set once in `Directory.Build.props` and not overridden per project without a recorded reason.
3. Confirm `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>` is present and that `<WarningsAsErrors>` includes `nullable` or the specific nullable codes.
4. Check `<EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>`; if style rules must fail the build, confirm `IDE0005` is not the only one relied upon and that `GenerateDocumentationFile` is enabled for it.
5. Read the `<AnalysisMode>` and `<AnalysisLevel>` values and confirm they are consistent across every project in the solution.
6. Search for `.Result`, `.Wait()`, `.GetAwaiter().GetResult()`, and `async void`; every hit outside an event handler is a defect.
7. Determine whether the project ships as a library; if so, confirm `ConfigureAwait(false)` is applied on awaits and that CA2007 is scoped with `output_kind` rather than suppressed.
8. Grep for `IEnumerable<` locals enumerated twice, and for `.Count()` / `.Any()` on a non-materialized query; replace with a single materialization.
9. Verify every `IDisposable`/`IAsyncDisposable` local uses a `using` declaration or `await using`, and that owning types implement `IDisposable` (CA1001).
10. Confirm `Directory.Packages.props` sets `ManagePackageVersionsCentrally` and that no `PackageReference` carries a `Version` attribute.
11. Inspect the composition root for `BuildServiceProvider()`, `GetService`, or injected resolving factories; confirm scope validation is on and no singleton holds a scoped dependency.
12. Confirm configuration is bound to options classes with `ValidateDataAnnotations()` and `ValidateOnStart()` rather than read from `IConfiguration` by string key.
13. Check that logging uses `ILogger<T>` with named placeholders or `[LoggerMessage]` source generation, and that no library configures logging providers.
14. Run `dotnet format --verify-no-changes` and confirm a zero exit code; if it fails, the drift is real and not a formatter disagreement.
15. Confirm test projects set `IsPackable=false`, use `async Task` test methods with `await`, and that the FluentAssertions pin matches the license the repository actually holds.

## References

- [Framework Design Guidelines](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/) — the naming, type-design, and member-design conventions the analyzers encode.
- [MSBuild properties for Microsoft.NET.Sdk](https://learn.microsoft.com/en-us/dotnet/core/project-sdk/msbuild-props) — `AnalysisMode`, `AnalysisLevel`, `EnforceCodeStyleInBuild`, `EnableNETAnalyzers`, `ImplicitUsings`, `GenerateDocumentationFile`.
- [Code analysis in .NET](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/overview), [configuration options](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/configuration-options), and [configuration files](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/configuration-files) — the analysis-mode table, the rules excluded from `All`, severity values, `dotnet_diagnostic.<id>.severity`, and `.editorconfig` versus `.globalconfig`.
- [Code-style naming rules](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/style-rules/naming-rules) — `dotnet_naming_symbols` / `dotnet_naming_style` / `dotnet_naming_rule`, allowed values, and the IDE-only severity caveat.
- [C# compiler options: language features](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-options/language) and [errors and warnings](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-options/errors-warnings) — `Nullable` values, the generated-code exemption, `WarningsAsErrors`, the `nullable` token.
- [`required` modifier](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/keywords/required) and [`SetsRequiredMembers`](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.codeanalysis.setsrequiredmembersattribute) — the visibility, hiding, and `new()` constraints.
- [Records](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/builtin-types/record) and [What's new in C# 14](https://learn.microsoft.com/en-us/dotnet/csharp/whats-new/csharp-14) — `record struct` mutability, the `field` keyword, first-class span conversions.
- [ConfigureAwait FAQ](https://devblogs.microsoft.com/dotnet/configureawait-faq/), [CA2007](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/quality-rules/ca2007), and [CA1849](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/quality-rules/ca1849) — the library-versus-application split, and the `output_kind` / `exclude_async_void_methods` options.
- [Task-based Asynchronous Pattern](https://learn.microsoft.com/en-us/dotnet/standard/asynchronous-programming-patterns/task-based-asynchronous-pattern-tap), [`TaskAsyncEnumerableExtensions`](https://learn.microsoft.com/en-us/dotnet/api/system.threading.tasks.taskasyncenumerableextensions.withcancellation), and [`EnumeratorCancellationAttribute`](https://learn.microsoft.com/en-us/dotnet/api/system.runtime.compilerservices.enumeratorcancellationattribute) — the `Async` suffix rule, the `TaskAsync` fallback, and what `WithCancellation` does and does not do.
- [CA1851](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/quality-rules/ca1851), [CA2000](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/quality-rules/ca2000), [CA2012](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/quality-rules/ca2012), [CA1031](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/quality-rules/ca1031), [CA1510](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/quality-rules/ca1510) — enumeration, disposal, `ValueTask`, exception scope, and throw helpers.
- [`TimeProvider` overview](https://learn.microsoft.com/en-us/dotnet/standard/datetime/timeprovider-overview) — framework versus `Microsoft.Bcl.TimeProvider` availability and the async extensions.
- [Customize the build by folder](https://learn.microsoft.com/en-us/visualstudio/msbuild/customize-by-directory) and [Central Package Management](https://learn.microsoft.com/en-us/nuget/consume-packages/central-package-management) — the upward search and manual import chain; `ManagePackageVersionsCentrally`, `VersionOverride`, NU1109, NU1507.
- [Dependency injection guidelines](https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection/guidelines) and [Options pattern](https://learn.microsoft.com/en-us/dotnet/core/extensions/options) — disposal ownership, scope validation, captive dependencies, and the `IOptions<T>` family.
- [CA1848](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/quality-rules/ca1848) — why `[LoggerMessage]` avoids boxing and template re-parsing.
- [xUnit.net Roslyn analyzer rules](https://xunit.net/xunit.analyzers/rules/) and [NUnit analyzers](https://github.com/nunit/nunit.analyzers/blob/master/documentation/index.md) — xUnit1031, xUnit1049, xUnit1051, NUnit2005, NUnit2010.
- [Fluent Assertions licensing](https://xceed.com/fluent-assertions-faq/) — v7 remains Apache-2.0; v8+ is free for non-commercial use only.
- [BannedApiAnalyzers](https://github.com/dotnet/roslyn/blob/main/src/RoslynAnalyzers/Microsoft.CodeAnalysis.BannedApiAnalyzers/BannedApiAnalyzers.Help.md) and [`dotnet format`](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-format) — `BannedSymbols.txt` with RS0030/RS0031, and the `whitespace`/`style`/`analyzers` subcommands with `--verify-no-changes`.
