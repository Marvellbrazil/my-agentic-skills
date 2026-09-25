# Java Standards

Java's guarantees are enforced by the compiler only where the source is shaped to let it. A codebase that declares types but passes `null` through them, uses `List` fields that callers mutate, catches `Exception` and logs it, or shares a `SimpleDateFormat` between threads compiles cleanly and fails in production. This module covers the conventions the compiler cannot see: immutability by default, exhaustive domain modeling, checked-versus-unchecked exception boundaries, resource discipline, and the concurrency rules that virtual threads changed.

## Contents

- [When This Applies](#when-this-applies)
- [Formatting and Build Enforcement](#formatting-and-build-enforcement)
  - [Google Java Style, enforced by Spotless](#google-java-style-enforced-by-spotless)
  - [Build tooling and dependency management](#build-tooling-and-dependency-management)
  - [Module and package structure](#module-and-package-structure)
- [Immutability, Records, and Domain Modeling](#immutability-records-and-domain-modeling)
  - [Records for data carriers](#records-for-data-carriers)
  - [Sealed hierarchies and pattern matching](#sealed-hierarchies-and-pattern-matching)
  - [`var`, `Optional`, and null policy](#var-optional-and-null-policy)
- [Exceptions, Resources, and Logging](#exceptions-resources-and-logging)
  - [Checked versus unchecked](#checked-versus-unchecked)
  - [Resources](#resources)
  - [Logging](#logging)
- [Concurrency and Threading](#concurrency-and-threading)
  - [Immutability and safe publication](#immutability-and-safe-publication)
  - [Executors, virtual threads, and structured concurrency](#executors-virtual-threads-and-structured-concurrency)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- A repository contains `src/main/java/`, `pom.xml`, `build.gradle`, or `build.gradle.kts`.
- The audit finds both `com.google.googlejavaformat` and Eclipse JDT formatter settings, or a `.editorconfig` that disagrees with `google-java-format`'s 2-space indent.
- Fields are injected (`@Autowired`, `@Inject` on a field) instead of constructor-injected.
- `Optional` appears as a field type, a method parameter, or inside a collection.
- `null` is returned from a method whose callers must check for it, or a `List` return is nullable where empty would do.
- `try` blocks call `close()` manually, or a `Connection`/`InputStream`/`ExecutorService` is never closed.
- An exception is caught, wrapped in a new exception without the cause, or logged and rethrown.
- Mutable static fields exist outside of `static final` constants.
- Tests use JUnit 4 (`org.junit.Test`), `@RunWith`, or `Assert.assertEquals` static imports.
- Logging calls use string concatenation (`"x=" + x`) or `System.out.println`.
- A `record` is absent where a class holds only final data, or Lombok `@Data`/`@Value` is used to generate what a record already provides.

## Formatting and Build Enforcement

### Google Java Style, enforced by Spotless

Style is not a review topic; it is a build step. Configure Spotless with `googleJavaFormat`, which defaults to 2-space block indent, +4-space continuation indent, and a 100-character column limit. `--aosp` switches to 4-space indent. Never mix formatters — an Eclipse formatter profile and `google-java-format` produce divergent diffs on every commit.

Gradle (`build.gradle.kts`), with the plugin marker `com.diffplug.spotless`:

```kotlin
plugins {
    id("com.diffplug.spotless") version "8.10.2"
}

spotless {
    ratchetFrom("origin/main")
    java {
        target("src/main/java/**/*.java", "src/test/java/**/*.java")
        googleJavaFormat("1.27.0")
        removeUnusedImports()
        forbidWildcardImports()
        formatAnnotations()
        importOrder()
    }
    kotlinGradle { ktlint() }
}
```

Maven (`pom.xml`), plugin `com.diffplug.spotless:spotless-maven-plugin:3.10.2`:

```xml
<plugin>
  <groupId>com.diffplug.spotless</groupId>
  <artifactId>spotless-maven-plugin</artifactId>
  <version>3.10.2</version>
  <configuration>
    <ratchetFrom>origin/main</ratchetFrom>
    <java>
      <googleJavaFormat><version>1.27.0</version></googleJavaFormat>
      <removeUnusedImports/>
      <forbidWildcardImports/>
      <importOrder/>
    </java>
  </configuration>
  <executions>
    <execution>
      <goals><goal>check</goal></goals>
    </execution>
  </executions>
</plugin>
```

`ratchetFrom` limits enforcement to files changed since the ref, which lets a legacy codebase adopt the standard without a 40,000-line reformat commit. Import order follows Google style: all static imports in one group, all non-static in another, one blank line between, ASCII sort order within each group, no wildcards. Note that Google style sorts by the imported _name_, not the import line — `.` sorts before `;`, so `java.util.List` precedes `java.util.Map` in a way line-sorting would not produce.

`forbidWildcardImports` and `forbidModuleImports` (Spotless supports the latter for Java 25+ module imports) both exist; module imports (`import module java.base;`) are disallowed by Google style.

### Build tooling and dependency management

| Concern             | Maven                                                 | Gradle                                                                                   |
| ------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Wrapper             | `mvnw` / `mvnw.cmd` from `maven-wrapper-plugin` 3.3.4 | `gradlew` / `gradlew.bat`                                                                |
| Version declaration | `<dependencyManagement>` + `import` scope BOM         | version catalog `gradle/libs.versions.toml`                                              |
| Conflict failure    | `maven-enforcer-plugin` rule `dependencyConvergence`  | `resolutionStrategy.failOnVersionConflict()`                                             |
| Locking             | BOM pinning is the mechanism                          | `dependencyLocking { lockAllConfigurations() }` + `./gradlew dependencies --write-locks` |
| JDK selection       | `<maven.compiler.release>`                            | `java { toolchain { languageVersion = JavaLanguageVersion.of(25) } }`                    |

Pin `maven-enforcer-plugin` rules `requireJavaVersion`, `requireMavenVersion`, `dependencyConvergence`, `requireUpperBoundDeps`, and `banDuplicatePomDependencyVersions`. `requireUpperBoundDeps` is the one that catches the diamond where two transitive paths resolve to different versions of the same artifact — Maven's nearest-wins rule silently picks one.

The Gradle toolchain block is not decoration: it decouples the JDK running Gradle from the JDK compiling the code, so a developer on JDK 21 still produces release-25 bytecode. Gradle 9.x requires a JVM between 17 and 27 to run.

### Module and package structure

- Package names are all-lowercase, no underscores, matching the directory path exactly.
- One top-level class per file; the file name matches the public type.
- `package-info.java` carries package-level Javadoc and, if used, `@NullMarked`.
- `module-info.java` declares `requires`/`exports`; prefer JPMS for libraries, classpath for applications that cannot tolerate split packages.
- Organize by feature, not by layer, once a package exceeds roughly a dozen types: `com.acme.orders` containing `Order`, `OrderRepository`, `OrderService` beats `com.acme.model`, `com.acme.dao`, `com.acme.service`.
- Never put mutable static state in a package-private "utility" class to avoid passing a dependency — that is a hidden global, and it breaks test isolation and parallel test execution.

## Immutability, Records, and Domain Modeling

### Records for data carriers

A `record` gives you a canonical constructor, accessors named after components, and derived `equals`/`hashCode`/`toString`. The derived `equals` compares each component with `Objects.equals` for reference types and `PW.compare` for primitives — which means an array component compares by identity, because arrays inherit `Object.equals`. Records with array components need explicit `equals`/`hashCode`, or a `List` component instead.

```java
public record Money(BigDecimal amount, Currency currency) {
    public Money {
        Objects.requireNonNull(amount, "amount");
        Objects.requireNonNull(currency, "currency");
        amount = amount.setScale(currency.getDefaultFractionDigits(), RoundingMode.HALF_EVEN);
    }
}
```

The compact constructor validates and normalizes; it does not reassign the parameter list into fields (that happens implicitly). Use records wherever the type is a value: DTOs, command/query objects, configuration snapshots, event payloads, map keys, and test fixtures. Use a class when the type has identity, mutable state, or lifecycle.

Do not reach for Lombok `@Data`/`@Value`/`@Builder` on a type that is a plain data carrier — the record is shorter, has no annotation processor in the build, and cannot drift out of sync with its fields. Lombok remains reasonable for `@Builder` on a constructor with 12 parameters, `@Slf4j`, or `@Cleanup`; it is not a substitute for language features that now exist.

Defensive copies matter on any record component that is itself mutable:

```java
public record Interval(Instant start, Instant end, List<String> tags) {
    public Interval {
        tags = List.copyOf(tags);
        if (start.isAfter(end)) {
            throw new IllegalArgumentException("start must not be after end");
        }
    }
}
```

`List.copyOf` rejects null elements with `NullPointerException` and returns an unmodifiable list; `List.of` does the same. Both are preferable to `Collections.unmodifiableList`, which is a _view_ — mutations to the backing list remain visible through it. `Stream.toList()` returns an unmodifiable list but _permits_ null elements, unlike `List.copyOf` and `Collectors.toUnmodifiableList`, which throw. Pick deliberately: `toList()` for nullable-tolerant pipelines, `Collectors.toUnmodifiableList()` when a null element is a bug.

### Sealed hierarchies and pattern matching

Sealed interfaces make the set of subtypes a compile-time fact, which is what makes an exhaustive `switch` checkable.

```java
public sealed interface Payment permits Card, BankTransfer, StoreCredit {}

record Card(String last4, Instant authorizedAt) implements Payment {}
record BankTransfer(String iban, String reference) implements Payment {}
record StoreCredit(String accountId, BigDecimal balance) implements Payment {}

static String describe(Payment payment) {
    return switch (payment) {
        case Card(String last4, var at) -> "card ending " + last4;
        case BankTransfer(var iban, _) -> "transfer to " + iban;
        case StoreCredit credit when credit.balance().signum() == 0 -> "exhausted credit";
        case StoreCredit credit -> "credit " + credit.accountId();
    };
}
```

Points that are easy to get wrong:

- A `switch` _expression_ must be exhaustive. A `switch` _statement_ must also be exhaustive as soon as it uses a pattern label, a `null` label, or a selector whose type is not one of the legacy types (`char`, `byte`, `short`, `int`, `Character`, `Byte`, `Short`, `Integer`, `String`, or an enum). Adding a subtype to a sealed hierarchy then breaks the build at every switch that did not handle it — that is the feature, not a nuisance.
- Record patterns (`case Card(String last4, var at)`) destructure; a nested record pattern can go arbitrarily deep.
- Without a `case null` label, a `switch` on a pattern throws `NullPointerException`. Write `case null ->` explicitly, or `case null, default ->` to combine.
- A guarded pattern (`when`) does not contribute to exhaustiveness; you still need an unguarded case for the same type.
- An unnamed pattern `_` (Java 22+) discards a component without naming it.

The same exhaustiveness argument applies at the type level: if the domain has three states and the code has two `boolean` fields representing them, no compiler will tell you the fourth combination is impossible. Model the states as the sealed hierarchy and delete the booleans.

### `var`, `Optional`, and null policy

`var` is restricted to local variables with initializers, enhanced-for indexes, and traditional-for index variables. It is forbidden for fields, method and constructor parameters, method return types, and catch formals, and it is rejected when the initializer is `null` or has no initializer. Use it when the right-hand side names the type (`var orders = new ArrayList<Order>();`, `var entry = map.entrySet().iterator().next();`) and write the type out when it does not (`var result = service.process(input);` tells a reader nothing).

`Optional` is a return type. The class Javadoc is explicit that it is "primarily intended for use as a method return type where there is a clear need to represent 'no result'". It must never be a field, a parameter, or an element of a collection: `Optional` is not `Serializable`, so an `Optional` field breaks any DTO that crosses a serialization boundary, and an `Optional` parameter forces every caller to wrap. On a field, the alternatives are a nullable field with `@Nullable` and a null check at the boundary, or a sealed type modeling presence. `Optional.get()` is deprecated in favor of `orElseThrow()`; prefer `orElseThrow(Supplier)` with a domain exception, `orElseThrow()` for the no-arg form, or `map`/`flatMap`/`ifPresentOrElse`/`stream` for composition.

Never return `null` from a method that returns a collection, array, or `Stream` — return `List.of()`, `new Order[0]`, or `Stream.empty()`. A caller that must null-check a collection will eventually forget. For a single value, return `Optional<T>` when absence is a normal outcome; throw when absence is a programming error.

Annotate nullability with JSpecify: `@NullMarked` on a package or module makes unannotated types non-null by default, and `@Nullable` marks the exceptions. Static analysis (NullAway 0.14.2, or Error Prone 2.50.0) can then enforce it. Helpful NullPointerExceptions (JEP 358, JDK 14+) name the null expression in the message, which makes the `-XX:-ShowCodeDetailsInExceptionMessages` diagnostic worth knowing about when a stack trace is opaque.

## Exceptions, Resources, and Logging

### Checked versus unchecked

Checked exceptions are for conditions the caller can _recover_ from and must decide on: a failed I/O read where a retry or a fallback path exists, a parse failure where the caller supplies a default. Unchecked exceptions are for programming errors and domain violations the caller cannot fix: a null argument, an invariant breach, an entity that does not exist.

Define a small unchecked hierarchy at the domain boundary rather than throwing `IllegalStateException` with a string from every layer:

```java
public class OrderException extends RuntimeException {
    public OrderException(String message) { super(message); }
    public OrderException(String message, Throwable cause) { super(message, cause); }
}

public final class OrderNotFoundException extends OrderException {
    public OrderNotFoundException(OrderId id) { super("order not found: " + id); }
}
```

Wrapping is mandatory when converting a checked exception to unchecked, and the cause must be passed: `throw new OrderException("failed to load " + id, e);`. Dropping the cause destroys the stack trace that would have explained the failure. `Throwable.getSuppressed()` and `addSuppressed` exist for try-with-resources and multi-failure aggregation; `initCause` is the fallback for exceptions constructed before their cause is known.

Never catch `Exception` (or `Throwable`) and swallow it. Never `catch (Exception e) {}` with an empty body. Never log-and-rethrow at the same layer — it duplicates the log line at every level. Log once, at the boundary that decides the outcome, and let the exception propagate.

### Resources

Every `Closeable`/`AutoCloseable` is acquired in a try-with-resources header. `ExecutorService` implements `AutoCloseable` (since Java 19) and its `close()` performs an orderly shutdown, waits for submitted tasks, and blocks new submissions — so a scope-scoped executor belongs in a try-with-resources too.

```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor();
     var connection = dataSource.getConnection();
     var statement = connection.prepareStatement(SQL)) {
    statement.setString(1, orderId.value());
    try (var rows = statement.executeQuery()) {
        return map(rows);
    }
}
```

Catch `IOException` around a resource operation, not around the whole block, so that a failure inside `map(rows)` is not misattributed to I/O. Suppressed exceptions from `close()` are attached automatically; do not hand-roll `close()` in a `finally` with a null check.

### Logging

Use SLF4J as the API and exactly one backend on the classpath (Logback 1.6.x, or Log4j2). Two backends produce a "multiple SLF4J providers" warning and unpredictable routing; the `log4j-slf4j2-impl`/`slf4j-simple` combination on a production classpath is a defect.

Always use parameterized messages; never string concatenation, and never a `String.format` argument.

```java
logger.debug("Temperature set to {}. Old value was {}.", newT, oldT);
logger.atWarn().setMessage("retry {} for order {}").addArgument(attempt).addArgument(orderId).log();
```

The fluent API (SLF4J 2.0+) supports `setMessage`, `addArgument`, and a `Supplier` argument, so an expensive argument is only evaluated when the level is enabled. Two rules that are easy to violate:

- The last argument of `debug(String, Object...)` is treated as the `Throwable` if it is one. Put the exception _last_: `logger.error("failed to load order {}", orderId, e)`. If it is not last, SLF4J treats it as an ordinary parameter and the stack trace is silently lost.
- Never log credentials, tokens, full request bodies, or personal data. Use MDC for correlation IDs (`MDC.put("traceId", id)` inside the request scope, `MDC.clear()` on exit), and prefer `ScopedValue` (final in JDK 25) over `ThreadLocal` for per-request context that must be inherited by child threads.

## Concurrency and Threading

### Immutability and safe publication

The default is no shared mutable state. A field that is only written in the constructor and then never again is safely publishable if it is `final`; a field written later needs `volatile`, a lock, or an `Atomic*` type. `HashMap` is not synchronized and can corrupt under concurrent writes; use `ConcurrentHashMap`, whose retrieval operations do not lock but which rejects null keys and values. `SimpleDateFormat` is not thread-safe — use `DateTimeFormatter`, which is immutable and thread-safe.

`static` mutable state is the most common cause of tests that pass alone and fail in a suite. If a counter, cache, or registry must be static, make it a `static final` immutable snapshot, or back it with a concurrent collection and a documented lifecycle.

```java
private static final Map<String, Strategy> STRATEGIES = Map.of(
    "card", new CardStrategy(),
    "transfer", new TransferStrategy());
```

### Executors, virtual threads, and structured concurrency

| Tool                                              | Use when                                                       |
| ------------------------------------------------- | -------------------------------------------------------------- |
| `Executors.newVirtualThreadPerTaskExecutor()`     | Task-per-request I/O; unbounded concurrency, no pooling needed |
| `Executors.newFixedThreadPool(n)`                 | CPU-bound work bounded to `availableProcessors()`              |
| `Thread.ofVirtual().name("worker-", 0).factory()` | Naming virtual threads for thread dumps and JFR                |
| `CompletableFuture`                               | Composing independent async stages with explicit failure paths |
| `StructuredTaskScope`                             | Fan-out where all subtasks must return to one lexical scope    |

Virtual threads (final in JDK 21, JEP 444) are cheap enough that pooling them is an anti-pattern: pool the scarce resource (connections, file handles), not the thread. Pinning — a virtual thread unable to unmount from its carrier — was largely eliminated for `synchronized` in JDK 24 (JEP 491); before that, `ReentrantLock` was required around blocking sections.

`StructuredTaskScope` remains a **preview** API as of JDK 25 (JEP 505, fifth preview; re-previewed in JDK 26 and 27). Using it requires `--enable-preview` at both compile and run time, which also pins the class-file version to that exact JDK release — a deployment constraint, not a formatting choice. A codebase on a preview API needs an explicit decision recorded, because a JDK upgrade can change the API.

```java
try (var scope = StructuredTaskScope.open()) {
    var user = scope.fork(() -> findUser(userId));
    var order = scope.fork(() -> fetchOrder(orderId));
    scope.join();
    return new Response(user.get(), order.get());
}
```

`open()` uses the default joiner, which fails if any subtask fails; `open(Joiner.allSuccessfulOrThrow())` collects all successful results; `open(Joiner.anySuccessfulResultOrThrow())` returns the first success. A `Joiner` must never be reused across scopes or after a scope closes. Subtasks run on virtual threads by default. Calling `fork` from a thread that is not the scope owner throws, and using a scope outside its try-with-resources block can raise `StructureViolationException` — the structure is enforced, not advisory.

`CompletableFuture` pitfalls that a review should catch: `allOf` completes exceptionally as soon as _any_ future fails, so `thenApply` on the result never runs and the partial results are lost; `orTimeout` and `completeOnTimeout` schedule on a shared delayed executor; `exceptionally` swallows the failure unless the function rethrows; and a `CompletableFuture` created with `new` (rather than `supplyAsync`/`runAsync`) needs `join()` for completion visibility.

## Common Mistakes

| Mistake                                                      | Why It Breaks                                                                                              | Correct Approach                                                                                         |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `Optional` as a field or parameter                           | `Optional` is not `Serializable`; breaks serialization, Jackson defaults, and forces every caller to wrap  | Nullable field with `@Nullable`, checked at the boundary; `Optional` only as a return type               |
| `Optional.get()` without a presence check                    | Throws `NoSuchElementException`; `get()` is deprecated in favor of `orElseThrow()`                         | `orElseThrow(Supplier)` with a domain exception, or compose with `map`/`ifPresentOrElse`                 |
| Returning `null` for an empty collection                     | Every caller must null-check; one that forgets gets an NPE far from the cause                              | Return `List.of()`, `Map.of()`, `new T[0]`, or `Stream.empty()`                                          |
| `record` with an array component and no explicit `equals`    | Derived `equals` uses `Objects.equals` on the array reference, so two equal-content records are unequal    | Use a `List` component, or override `equals`/`hashCode` with `Arrays.equals`/`Arrays.hashCode`           |
| Lombok `@Data` on a value type                               | Generated `equals`/`hashCode`/`toString` drift as fields change; adds an annotation processor to the build | Use a `record`; reserve Lombok for `@Builder` and `@Slf4j`                                               |
| `Collections.unmodifiableList(list)` for immutability        | It is a view — later mutations to the backing list remain visible to holders                               | `List.copyOf`, `List.of`, or `Collectors.toUnmodifiableList` for a real copy                             |
| `catch (Exception e) { log.error("failed"); }`               | Swallows the failure, loses the stack trace, and makes the caller believe the operation succeeded          | Catch the specific type, log with the exception as the last argument, rethrow or map to a domain error   |
| `throw new OrderException("failed")` inside a catch          | The original cause and its stack trace are discarded                                                       | `throw new OrderException("failed to load " + id, e)` — always pass the cause                            |
| `logger.error("order " + id + " failed: " + e.getMessage())` | Eager concatenation costs on every call, and the stack trace is lost entirely                              | `logger.error("order {} failed", id, e)` with the `Throwable` last                                       |
| `SimpleDateFormat` as a `static final` field                 | Not thread-safe; concurrent `format`/`parse` corrupts internal calendar state                              | `DateTimeFormatter` (immutable, thread-safe), or `ThreadLocal<SimpleDateFormat>` if stuck on the old API |
| Sharing a `HashMap` across threads                           | Unsynchronized writes can loop forever or lose entries; no visibility guarantee                            | `ConcurrentHashMap`, or confine the map to one thread; note it rejects null keys/values                  |
| `var` where the initializer hides the type                   | `var result = service.process(x);` forces the reader to open another file                                  | Spell out the type when the right-hand side does not name it                                             |
| Field injection (`@Autowired` on a field)                    | Hides required dependencies, prevents `final` fields, and makes the class untestable without a container   | Constructor injection with `final` fields; annotate the constructor when there is more than one          |
| Pattern `switch` without a `case null`                       | Throws `NullPointerException` for a null selector instead of handling it                                   | Add `case null ->` explicitly, or `case null, default ->`                                                |
| `--enable-preview` on a production build                     | Ties the artifact to one exact JDK release; the API can change on upgrade                                  | Use finalized features, or record the preview dependency and pin the JDK                                 |

## Checklist

1. Confirm a single formatter owns Java style — `googleJavaFormat` via Spotless in the Gradle or Maven build — and that no Eclipse JDT profile or `.editorconfig` overrides it; verify the plugin runs in `check` and fails the build.
2. Confirm `spotlessCheck` (Gradle) or `spotless:check` (Maven) executes in CI, and that `ratchetFrom` names the repository's actual default branch if it is used.
3. Confirm import ordering matches Google style: static group, blank line, non-static group, ASCII sort by imported name, no wildcards, no `import module`.
4. Replace every `Optional` field, parameter, and collection element with a nullable type plus `@Nullable`, or a sealed presence type; list each replacement and the callers updated.
5. Replace every `Optional.get()` with `orElseThrow(Supplier)`, `orElseThrow()`, or a composition method; verify no `get()` remains.
6. Replace every method that returns `null` for an empty collection with `List.of()`, `Map.of()`, `Set.of()`, `new T[0]`, or `Stream.empty()`.
7. Convert every Lombok `@Data`/`@Value` data carrier with no builder usage into a `record`; keep Lombok only where `@Builder` or a non-record feature is genuinely used, and state which.
8. For every `record` with an array component, add explicit `equals`/`hashCode` using `Arrays.equals`/`Arrays.hashCode`, or convert the component to an unmodifiable `List`.
9. Add compact constructors to records whose components need validation or defensive copies; confirm every mutable component is wrapped in `List.copyOf`/`Map.copyOf`/`Set.copyOf` or copied explicitly.
10. Confirm `equals`/`hashCode`/`toString` are generated by `record` where the type is a value, and hand-written with `Objects.equals`/`Objects.hash` where a class must implement them.
11. Convert every sealed-hierarchy `switch` to an exhaustive `switch` expression with record patterns, add `case null` where a null selector is possible, and remove any `default` clause that a sealed hierarchy makes unreachable.
12. Replace every `Collections.unmodifiableList`/`unmodifiableMap`/`unmodifiableSet` used for immutability with `List.copyOf`/`Map.copyOf`/`Set.copyOf`, and every `Stream.collect(Collectors.toList())` with `toList()` or `Collectors.toUnmodifiableList()` according to null tolerance.
13. Convert every resource acquisition to try-with-resources, including `ExecutorService`, and confirm no `close()` call appears in a `finally` block.
14. For each `catch` block: narrow to a specific exception type, pass the original exception as the `cause` when wrapping, and confirm no empty catch body or log-and-rethrow at the same layer remains.
15. Introduce or verify a domain exception hierarchy extending `RuntimeException`, and replace generic `IllegalStateException`/`RuntimeException` throws in service layers with the domain type.
16. Replace every `logger.x("..." + value)` and `String.format` log argument with `{}` placeholders, and confirm each logged `Throwable` is the last argument.
17. Confirm exactly one SLF4J backend is on the runtime classpath and that no `System.out.println` remains in `src/main/java`.
18. Replace every field-injected dependency with constructor injection and `final` fields; confirm JSR-330 `@Inject`/`@Singleton` or Jakarta `jakarta.inject` annotations are used consistently, with no `javax.inject` remnant.
19. Convert every JUnit 4 test to JUnit 5: `org.junit.jupiter.api.Test`, `@DisplayName`, `@Nested` inner classes for grouping, `@ParameterizedTest` with `@CsvSource`/`@MethodSource`, and AssertJ `assertThat`/`assertThatThrownBy` in place of `Assert.*`.
20. Audit static mutable state: convert to `static final` immutable values or a concurrent collection with a documented lifecycle, and confirm tests can run in parallel without cross-test interference.
21. For concurrency: confirm virtual threads are not pooled, `ExecutorService` instances are closed, `CompletableFuture` chains handle `allOf` partial failure, and `StructuredTaskScope` usage is either absent or has a recorded decision about `--enable-preview`.
22. Confirm the build declares a JDK via toolchain (Gradle) or `maven.compiler.release` (Maven), and that `maven-enforcer-plugin` rules `dependencyConvergence`, `requireUpperBoundDeps`, `requireJavaVersion`, and `requireMavenVersion` are configured.

## References

- [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html) — column limit 100, +2 block indent, +4 continuation indent, import grouping, and the no-wildcard/no-module-import rules.
- [google-java-format](https://github.com/google/google-java-format) — `--aosp` 4-space style, `--fix-imports-only`, and the formatter's release notes.
- [Spotless: Gradle plugin README](https://github.com/diffplug/spotless/blob/main/plugin-gradle/README.md) — `googleJavaFormat`, `importOrder`, `removeUnusedImports`, `forbidWildcardImports`, `ratchetFrom`, `enforceCheck`.
- [Spotless: Maven plugin README](https://github.com/diffplug/spotless/blob/main/plugin-maven/README.md) — the `<java>` step list and goal/phase binding.
- [JEP 395: Records](https://openjdk.org/jeps/395) — final in JDK 16; derived `equals`/`hashCode`/`toString` and the copy-equality invariant.
- [java.lang.Record](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Record.html) — the exact `Objects.equals`/`PW.compare` semantics behind derived equality, including the array-component trap.
- [JEP 409: Sealed Classes](https://openjdk.org/jeps/409) — final in JDK 17; `permits`, implicit finality of records implementing a sealed interface.
- [JEP 441: Pattern Matching for switch](https://openjdk.org/jeps/441) — final in JDK 21; exhaustiveness rules, `case null`, dominated patterns, guarded patterns.
- [JEP 440: Record Patterns](https://openjdk.org/jeps/440) — nested destructuring in `switch` and `instanceof`.
- [JEP 456: Unnamed Variables & Patterns](https://openjdk.org/jeps/456) — final in JDK 22; the `_` pattern and unnamed variable.
- [JEP 286: Local-Variable Type Inference](https://openjdk.org/jeps/286) — the exact set of places `var` is legal, and why `null` initializers are rejected.
- [java.util.Optional](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Optional.html) — "primarily intended for use as a method return type", `get()` deprecation, `orElseThrow`/`ifPresentOrElse`/`stream`.
- [java.util.List](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html) — `List.of`/`List.copyOf` null rejection, value-based identity, and `reversed()` from Sequenced Collections.
- [java.util.stream.Stream#toList](<https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/Stream.html#toList()>) — unmodifiable but null-permitting, unlike `Collectors.toUnmodifiableList`.
- [java.util.Collections](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Collections.html) — the unmodifiable-_view_ semantics that make it unsuitable as an immutability guarantee.
- [JSpecify](https://jspecify.dev/docs/api/org/jspecify/annotations/package-summary.html) — `@NullMarked`, `@NullUnmarked`, `@Nullable` and the nullness model.
- [NullAway](https://github.com/uber/NullAway) and [Error Prone](https://errorprone.info/) — static enforcement of nullness and common Java defects.
- [JEP 358: Helpful NullPointerExceptions](https://openjdk.org/jeps/358) — JDK 14+ NPE messages naming the null expression.
- [SLF4J FAQ](https://www.slf4j.org/faq.html) — the last-argument `Throwable` rule and the SLF4J 1.6 change that introduced it.
- [SLF4J Manual: Fluent Logging API](https://www.slf4j.org/manual.html) — `atDebug()`, `setMessage`, `addArgument`, and supplier arguments (SLF4J 2.0+).
- [java.lang.Thread.Builder](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Thread.Builder.html) — `name(String, long)`, `unstarted(Runnable)`, `factory()`.
- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444) — final in JDK 21; `Executors.newVirtualThreadPerTaskExecutor`, why pooling virtual threads is wrong.
- [JEP 491: Synchronize Virtual Threads without Pinning](https://openjdk.org/jeps/491) — JDK 24; removal of `synchronized` pinning.
- [JEP 505: Structured Concurrency (Fifth Preview)](https://openjdk.org/jeps/505) — JDK 25; `StructuredTaskScope.open()`, `Joiner.allSuccessfulOrThrow`/`anySuccessfulResultOrThrow`, `Subtask`, `StructureViolationException`, and the `--enable-preview` requirement.
- [JEP 506: Scoped Values](https://openjdk.org/jeps/506) — final in JDK 25; `ScopedValue.newInstance()`, `ScopedValue.where(...).run(...)` as the inheritable replacement for `ThreadLocal`.
- [java.util.concurrent.CompletableFuture](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html) — `allOf`, `orTimeout`, `completeOnTimeout`, `failedFuture`, `exceptionallyAsync`.
- [java.util.concurrent.ExecutorService](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ExecutorService.html) — `AutoCloseable` since Java 19 and the `close()` shutdown semantics.
- [java.util.concurrent.ConcurrentHashMap](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html) — lock-free retrieval and the null-key/null-value prohibition.
- [JUnit 5 User Guide](https://docs.junit.org/current/user-guide/index.html) — `@Nested`, `@ParameterizedTest` with `@CsvSource`/`@MethodSource`/`@CsvFileSource`, `useHeadersInDisplayName`, `assertAll`, `assertThrows`/`assertThrowsExactly`.
- [AssertJ](https://joel-costigliola.github.io/assertj/) — `assertThat`, `assertThatThrownBy`, `assertThatExceptionOfType`, `extracting`, `satisfies`.
- [Maven Enforcer Plugin rules](https://maven.apache.org/enforcer/enforcer-rules/index.html) — `dependencyConvergence`, `requireUpperBoundDeps`, `banDuplicatePomDependencyVersions`, `requireJavaVersion`.
- [Gradle: Toolchains for JVM projects](https://docs.gradle.org/current/userguide/toolchains.html) and [Dependency Locking](https://docs.gradle.org/current/userguide/dependency_locking.html) — `JavaLanguageVersion.of`, `lockAllConfigurations`, `--write-locks`.
- [Gradle: Compatibility Matrix](https://docs.gradle.org/current/userguide/compatibility.html) — the JVM range (17–27) required to run current Gradle.
