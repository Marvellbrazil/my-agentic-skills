# PHP Standards

Covers the conventions PHP's runtime and tooling leave open: which coding standard the repository actually enforces, where types are declared versus inferred, how errors cross module boundaries, and how dependencies are wired and locked. PHP's permissiveness is the failure mode — a file with no `declare(strict_types=1)` silently coerces `"5"` into `5` at the call site, `@` hides a failure that a throwing error handler turns into a fatal anyway, and `composer update` without a committed lockfile ships a different dependency graph to production than to CI.

## Contents

- [When This Applies](#when-this-applies)
- [Coding Standard, Autoloading, and File Layout](#coding-standard-autoloading-and-file-layout)
- [Types, Immutability, and Value Objects](#types-immutability-and-value-objects)
- [Errors, Exceptions, and Logging](#errors-exceptions-and-logging)
- [Composer, Static Analysis, and Composition](#composer-static-analysis-and-composition)
- [Tests](#tests)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- The repository contains `composer.json`, `composer.lock`, or any `.php` file.
- A formatter or linter config is missing, or two coexist with different rulesets (`pint.json` alongside `.php-cs-fixer.dist.php`).
- Files disagree on `declare(strict_types=1)`, on import style, or on class-per-file layout.
- Types are being added or tightened: native parameter and return types, union/intersection/DNF forms, `readonly`, promoted constructor properties.
- `class` constants or `switch` statements are being replaced with enums and `match`.
- Error handling is under review: `@` usage, `catch (\Exception)`, `false`/`-1` sentinel returns, ad-hoc `\RuntimeException` throws.
- Static analysis is absent, or PHPStan/Psalm runs at a level far below the codebase's actual type coverage.
- Test layout, naming, or the annotation-versus-attribute question comes up, or coverage is not attributed to a class.
- Composer `require` constraints are being widened, `platform` is unset, or `vendor/` is committed.

## Coding Standard, Autoloading, and File Layout

PSR-2 is deprecated and PSR-12 is superseded. PER Coding Style 3.1 extends, expands, and replaces PSR-12 and requires adherence to PSR-1; declare it as the target and configure the formatter to match. PER-CS keeps PSR-12's rules where they agree, makes PSR-12's errata binding, and specifies modern syntax PSR-12 predates — the 120-character _soft_ line limit with no hard limit, 4-space indentation, and `declare(strict_types=1)` written with no spaces inside the parentheses. In a file that mixes markup and PHP, the strict-types declaration goes on the first line, opening tag, declaration, closing tag.

| Standard             | Status          | Binds what                                                                                                                                                                      |
| -------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PSR-1                | Accepted        | Base: `<?php` only, UTF-8 without BOM, `StudlyCaps` classes, `camelCase` methods, `UPPER_SNAKE` class constants, one symbol set per file, no side effects in a declaration file |
| PSR-2                | Deprecated      | Superseded by PSR-12 — do not configure it                                                                                                                                      |
| PSR-12               | Accepted (2019) | Extended style; superseded by PER-CS                                                                                                                                            |
| PSR-4                | Accepted        | Autoloading: case-sensitive FQCN to path mapping                                                                                                                                |
| PER Coding Style 3.1 | Current         | Replaces PSR-12; adds rules for enums, attributes, match, promoted properties, hooks                                                                                            |

PSR-4 maps a namespace prefix to a base directory and the remaining namespace segments to subdirectories whose case must match the namespace exactly; the terminating class name must match the file name's case. Prefix `Acme\Log\Writer` with base `./acme-log-writer/lib/` resolves `\Acme\Log\Writer\File_Writer` to `./acme-log-writer/lib/File_Writer.php`. Autoloaders MUST NOT throw exceptions, so a missing class surfaces as a class-not-found error at first use, not at boot — which is why `composer dump-autoload --optimize --strict-psr` is worth running in CI: it fails the build on PSR-4 mapping errors before a request does.

```json
{
  "autoload": {
    "psr-4": { "App\\": "src/" },
    "exclude-from-classmap": ["/Tests/", "/tests/"]
  },
  "autoload-dev": {
    "psr-4": { "App\\Tests\\": "tests/" }
  }
}
```

`require` resolves to the nearest symbol; a fully-qualified name inline bypasses that and silently ignores any import alias the file already declares. Import every class, function, or constant with a top-level `use` statement and reference the short name in the body.

```php
use App\Domain\Order\OrderId;
use App\Domain\Order\OrderRepository;
use Psr\Log\LoggerInterface;

final class PlaceOrder
{
    public function __construct(
        private readonly OrderRepository $orders,
        private readonly LoggerInterface $logger,
    ) {}
}
```

## Types, Immutability, and Value Objects

`declare(strict_types=1)` governs **calls made from within the file that enables it**, not the functions declared in it: a coercive file calling a function defined in a strict file still coerces, and calls into internal functions are never affected. Strict typing is defined only for scalar declarations, so it never governs class types, arrays, or `null`. This is why the declaration belongs in every file rather than at the entry point — coverage is a property of each call site, not of the application.

| Concept             | PHP                                    | TypeScript                     | Rust                 | Python                         |
| ------------------- | -------------------------------------- | ------------------------------ | -------------------- | ------------------------------ |
| Nullable            | `?T`, or `T\|null` in a union          | `T \| null` (strict mode)      | `Option<T>`          | `T \| None`                    |
| Intersection        | `A&B` (8.1)                            | `A & B`                        | trait bounds         | `Protocol` composition         |
| DNF                 | `(A&B)\|(A&C)` (8.2)                   | n/a                            | n/a                  | n/a                            |
| Immutable value     | `readonly` property / `readonly class` | `readonly` (erased at runtime) | ownership + no `mut` | `@dataclass(frozen=True)`      |
| Exhaustive dispatch | `match` throws `UnhandledMatchError`   | union + `never` guard          | `match` on enum      | `match` (3.10, not exhaustive) |

The nullable shorthand cannot appear inside a union: `?int|string` is a parse error, while `int|string|null` is valid. DNF types are unions whose members may be parenthesised intersections, and the engine rejects a redundant member — `A|(A&B)` is a fatal "more restrictive than type" error, so write `(A&B)|(A&C)` only when neither intersection is subsumed by another union member.

```php
interface HasId { public function id(): string; }
interface Timestamped { public function at(): int; }
interface Archivable { public function archivedAt(): ?int; }

function describe((HasId&Timestamped)|(HasId&Archivable) $row): string
{
    return $row->id();
}
```

Constructor property promotion removes the declare-then-assign boilerplate, and combining it with `readonly` produces a value object whose invariants are enforced once. A `readonly` property can only be initialised by a direct assignment from the declaring class scope, cannot be `static`, must have a type, and cannot carry a default — a defaulted readonly property is a constant wearing a property's clothes. As of PHP 8.3 a readonly property may be reinitialised inside `__clone()`; as of 8.5 `clone($obj, ['prop' => $value])` returns a modified copy, applies overrides after `__clone()` has run, and honours visibility — so a `private(set)` property cannot be overridden from outside the class.

```php
final readonly class Money
{
    public function __construct(
        public int $amount,
        public string $currency,
    ) {
        if ($amount < 0) {
            throw new \InvalidArgumentException('amount must be non-negative');
        }
    }

    public function plus(self $other): self
    {
        if ($this->currency !== $other->currency) {
            throw new \InvalidArgumentException('currency mismatch');
        }

        return new self($this->amount + $other->amount, $this->currency);
    }
}
```

A `readonly class` (8.2) makes every declared property readonly and forbids static properties. Property hooks (8.4) attach `get`/`set` bodies to a property and are incompatible with `readonly`; asymmetric visibility (8.4) writes `public private(set)` and is only legal on typed properties, with the `set` visibility equal to or more restrictive than `get`. Prefer the narrower modifier to a getter/setter pair — `private(set)` expresses "readable everywhere, writable here" in one declaration that static analysis can verify.

Enums replace class constants as soon as the value set is closed and the values need behaviour. A pure enum's cases are singleton objects with no scalar backing; a backed enum implements `BackedEnum`, exposes `->value`, and provides `from()` (throws `ValueError` on a miss) and `tryFrom()` (returns `null`). Enums cannot declare properties — carrying state means you wanted a class. They may implement interfaces, hold constants, and define methods, and `match ($this)` inside a method is exhaustive with no `default` arm, so adding a case produces an `UnhandledMatchError` at the first uncovered path instead of silently falling through.

```php
enum Status: string
{
    case Active = 'active';
    case Suspended = 'suspended';
    case Closed = 'closed';

    public function allowsLogin(): bool
    {
        return match ($this) {
            self::Active => true,
            self::Suspended, self::Closed => false,
        };
    }

    public static function fromDatabase(string $raw): self
    {
        return self::tryFrom($raw) ?? throw new \ValueError("unknown status: {$raw}");
    }
}
```

`match` compares with `===`, unlike `switch`'s loose comparison, and throws `UnhandledMatchError` when no arm matches — that strictness is the point, so do not add a `default` arm to silence it over a closed type. Named arguments make call sites order-independent and let a call skip defaults, but they must follow positional arguments and they couple the caller to the parameter name, so reserve them for booleans and optional flags where the meaning is otherwise invisible. First-class callable syntax (`strlen(...)`, `$this->handle(...)`) produces a `Closure` from any callable and replaces `Closure::fromCallable()` and string callables, which the engine resolves at call time.

## Errors, Exceptions, and Logging

`@` suppresses the diagnostic message but not the failure. The operator still invokes a custom error handler, and inside that handler `error_reporting()` in PHP 8 returns `E_ALL & (E_ERROR | E_CORE_ERROR | E_COMPILE_ERROR | E_USER_ERROR | E_RECOVERABLE_ERROR | E_PARSE)` rather than `0`, so the pre-8.0 idiom `if (!(error_reporting() & $errno)) { return; }` no longer detects suppression. Worse, an application that installs a throwing error handler — the correct way to make warnings fatal — converts `@file_get_contents($path)` into an `ErrorException` that the `@` did nothing to prevent. And `@` cannot suppress engine `Error` subclasses at all: `@undefined_function()` still throws.

```php
try {
    $contents = file_get_contents($path);
} catch (\ErrorException $e) {
    throw new ConfigUnreadable($path, previous: $e);
}
```

Model failure as exceptions, not sentinel returns. `Throwable` is implemented by both `Exception` and `Error`, so catching `\Throwable` swallows programming errors; catch the narrowest type you can act on and let the rest propagate. Define one marker interface per domain and have every domain exception implement it, so a caller can catch the domain's failures without catching the framework's.

```php
namespace App\Domain\Payment;

interface PaymentFailure extends \Throwable {}

final class CardDeclined extends \RuntimeException implements PaymentFailure
{
    public static function forCard(string $last4): self
    {
        return new self("card ending {$last4} was declined", 402);
    }
}
```

Order catch blocks from most specific to most general, because the first match wins. Several names are already taken by the engine — `ParseError`, `ValueError`, `DomainException`, `TypeError`, `ArithmeticError` — and redeclaring one in the global namespace is a fatal "cannot redeclare class" at load, so namespace every domain exception and never extend `\Error`. Pass the original exception through `previous:` so the chain survives; discarding it destroys the only record of where the failure started.

Logging goes through PSR-3, never through `error_log()` scattered in domain code. `LoggerInterface` exposes eight level methods — `debug`, `info`, `notice`, `warning`, `error`, `critical`, `alert`, `emergency` — plus `log($level, string|\Stringable $message, array $context = [])`, and `Psr\Log\LogLevel` holds the eight level constants. Placeholder names in the message MUST correspond to keys in the context array, MUST be delimited by a single brace pair with no surrounding whitespace, and are only interpolated by implementations that choose to. If an exception is in the context it MUST be under the `'exception'` key; implementations MUST verify the value is actually an `Exception` before using it, and MUST treat every other context value with lenience — a context value MUST NOT throw or raise.

```php
$this->logger->warning('charge declined', [
    'order_id' => $orderId->value,
    'last4' => $last4,
    'exception' => $e,
]);
```

Inject `LoggerInterface`, not a concrete logger, and do not call a static `Log::channel()` accessor from inside a service — that is service location, it makes the dependency invisible to static analysis, and it cannot be replaced in a test. Constructor injection of every collaborator is the default; a static singleton is acceptable only for genuinely process-global state (a clock the test can freeze via an injected interface, not a static property).

## Composer, Static Analysis, and Composition

`composer install` installs exactly what `composer.lock` pins; `composer update` re-resolves and rewrites the lock. Commit the lockfile for applications and services, and omit it for libraries — a library's consumers resolve their own graph, and a committed lock there conflicts with the consuming application's. CI must run `composer install` (never `update`) and fail if the lock is stale: `composer validate --strict` reports both a `composer.json` that is invalid and a `composer.lock` out of date with it, and `composer audit --locked` checks the pinned set for advisories rather than whatever is currently in `vendor/`.

| Constraint | Expands to       | Use                                           |
| ---------- | ---------------- | --------------------------------------------- |
| `^1.2.3`   | `>=1.2.3 <2.0.0` | Libraries; the recommended operator           |
| `^0.3`     | `>=0.3.0 <0.4.0` | Pre-1.0, where the minor is the breaking axis |
| `^0.0.3`   | `>=0.0.3 <0.0.4` | Pre-1.0 patch-only                            |
| `~1.2`     | `>=1.2 <2.0.0`   | Minimum minor, allows the last digit to rise  |
| `~1.2.3`   | `>=1.2.3 <1.3.0` | Patch-only                                    |

`config.platform` fakes platform packages so resolution targets the deployment runtime rather than the developer's machine — without it, a laptop on PHP 8.5 resolves a graph that the production PHP 8.3 cannot install. `config.allow-plugins` (required to be explicit since Composer 2.2) names the plugins permitted to execute; leaving it open lets any transitive dependency run code at install time. `optimize-autoloader` converts PSR-4 to a classmap, `classmap-authoritative` goes further and refuses to fall back to the filesystem, and `apcu-autoloader` caches lookups — the last two are mutually exclusive choices, and `classmap-authoritative` requires a full `dump-autoload` on every deploy or new classes will not resolve.

```json
{
  "config": {
    "platform": { "php": "8.3.14" },
    "allow-plugins": { "phpstan/extension-installer": true },
    "sort-packages": true,
    "optimize-autoloader": true,
    "classmap-authoritative": true
  }
}
```

PHPStan's eleven levels are cumulative and start at 0; `-l|--level max` tracks the highest so upgrades never silently lower the bar. Level 5 reports argument types at call sites, level 6 reports missing typehints, level 7 reports partially-wrong union calls, level 8 reports calls on nullable types, level 9 permits only passing `mixed` to `mixed`, and level 10 (new in PHPStan 2.0) applies the same rule to implicit `mixed` — a missing type declaration. Run level 6 or higher on `src` only: analysing `vendor/` produces findings you cannot fix. When a config file is used, the level must be set in it or passed on the command line, because the default-0 fallback does not apply. Adopt with `--generate-baseline` and commit `phpstan-baseline.neon`, then ratchet: `reportUnmatchedIgnoredErrors` (on by default) fails the build when a baseline entry no longer matches, which is what stops the baseline from becoming permanent debt.

Psalm runs error levels 1 (strictest) through 8 (most lenient), default 2; issues reported at level 1 — `UndefinedClass`, `UndefinedVariable` — cannot be suppressed by raising the level, and lowering the number turns more issues into blocking errors. `findUnusedCode` defaults to `true` and resolves reachability from the public API and entry points, so a symbol referenced only by other unused code is reported; a `@psalm-suppress UnusedClass` silences the symbol but does not make it an entry point. Use `--set-baseline=psalm-baseline.xml` to adopt and `--update-baseline` to remove fixed entries without adding new ones.

PHP-CS-Fixer defaults to `@PSR12` when no config file exists, which is the wrong default for a modern codebase. Write `.php-cs-fixer.dist.php` returning a `PhpCsFixer\ConfigInterface`, target `@PER-CS` (an alias for the newest PER-CS revision, so it moves with the standard), and enable the migration set matching your minimum PHP. Risky rules are off by default and must be opted into with `setRiskyAllowed(true)` — `declare_strict_types` is one of them, and it is risky precisely because it changes runtime behaviour. CI runs `--dry-run --diff` so a violation fails the build instead of being rewritten under review.

```php
$finder = (new PhpCsFixer\Finder())->in(__DIR__)->exclude(['vendor', 'var']);

return (new PhpCsFixer\Config())
    ->setRiskyAllowed(true)
    ->setRules([
        '@PER-CS' => true,
        '@PHP8x3Migration' => true,
        'declare_strict_types' => true,
        'ordered_imports' => ['sort_algorithm' => 'alpha'],
        'global_namespace_import' => ['import_classes' => true, 'import_functions' => true],
        'fully_qualified_strict_types' => true,
        'void_return' => true,
        'no_unused_imports' => true,
        'nullable_type_declaration_for_default_null_value' => true,
    ])
    ->setFinder($finder);
```

Pint wraps PHP-CS-Fixer with five presets: `laravel` (the default), `per`, `psr12`, `symfony`, and `empty`. Configure `preset` and `rules` in `pint.json`; run `--test` in CI to fail without writing, `--dirty` to touch only files with uncommitted changes, and `--repair` to fix and still exit non-zero. Pick one formatter per repository — Pint and PHP-CS-Fixer disagreeing on the same file makes every commit a fight.

Deep inheritance hierarchies and premature abstraction are the recurring structural failures: a base class with eight protected hooks, or an interface extracted for a single implementation, is harder to change than the concrete class it replaced. Extract an abstraction at the second or third real caller, and prefer composition — an injected collaborator — over an abstract base class. Prefer `final` classes with constructor-injected dependencies; a class that cannot be extended cannot be broken by a subclass, and static analysis can then reason about every call site.

## Tests

PHPUnit 12 requires PHP 8.3 and PHPUnit 13 requires PHP 8.4.1, so the test runner's floor constrains the runtime floor. Doc-comment metadata (`@test`, `@dataProvider`, `@covers`) was deprecated in PHPUnit 11 and removed in PHPUnit 12 — the replacement is attributes from `PHPUnit\Framework\Attributes`: `#[Test]`, `#[DataProvider('methodName')]`, `#[TestWith([...])]`, `#[CoversClass(Foo::class)]`, `#[Group('slow')]`, `#[Depends('otherTest')]`, `#[RequiresPhp('8.3')]`. A `DataProvider` must name a static method declared in the same class. Test methods are public, and either carry the `test` prefix or the `#[Test]` attribute — pick one convention repository-wide, since a method that is neither is silently not run.

```php
namespace App\Tests\Domain\Payment;

use App\Domain\Payment\CardDeclined;
use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

#[CoversClass(CardDeclined::class)]
final class CardDeclinedTest extends TestCase
{
    #[DataProvider('last4Provider')]
    public function testMessageNamesTheCard(string $last4): void
    {
        self::assertStringContainsString($last4, CardDeclined::forCard($last4)->getMessage());
    }

    public static function last4Provider(): array
    {
        return [['4242'], ['0005']];
    }
}
```

Attribute coverage to a class with `#[CoversClass]` and turn on `requireCoverageMetadata` plus `beStrictAboutCoverageMetadata` in `phpunit.xml` — coverage collected without an explicit target measures whichever file the autoloader happened to load. Configure `failOnWarning`, `failOnRisky`, `failOnDeprecation`, and `failOnNotice` so a deprecation is a build failure rather than a line nobody reads, and set `beStrictAboutTestsThatDoNotTestAnything` so a test with no assertions is reported instead of passing. Under PHPUnit 12 the `<source>` element with `<include>`/`<exclude>` defines what counts as first-party code for coverage; excluding `vendor` there is what keeps the percentage meaningful.

Pest 5 requires PHP 8.4 and expresses the same runner through `test()`/`it()` with `expect($value)->toBe(...)`, `describe()` for grouping, and a `tests/Pest.php` that applies shared base classes and traits via `uses(...)->in(...)`. Choose PHPUnit or Pest per repository and do not mix them within a suite; the underlying assertions are the same, but two idioms in one test tree makes the suite unsearchable.

## Common Mistakes

| Mistake                                                                    | Why It Breaks                                                                                                                                     | Correct Approach                                                                  |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `@file_get_contents($path)` to hide a warning                              | The warning is suppressed, the failure is not; with a throwing error handler the call still throws, and `@` cannot suppress engine `Error` at all | Handle the return value and wrap the failure in a domain exception                |
| Relying on `error_reporting() === 0` to detect suppression                 | In PHP 8 the handler sees `E_ALL & (fatal mask)`, not `0`, so the guard never fires                                                               | Never write suppression-aware handlers; make warnings throw and fix the call site |
| `?int\|string` in a signature                                              | Parse error — the nullable shorthand cannot be combined with a union                                                                              | Write `int\|string\|null`                                                         |
| `A\|(A&B)` as a DNF type                                                   | Fatal "more restrictive than type" error: the intersection is subsumed by the union member                                                        | Use intersections that are not subsumed, e.g. `(A&B)\|(A&C)`                      |
| `catch (\Exception $e)` around a whole method                              | Also swallows logic errors and bugs, turning a crash into a silent wrong answer                                                                   | Catch the narrowest exception type the code can act on                            |
| `final class ParseError extends \RuntimeException` in the global namespace | Fatal "cannot redeclare class" — `ParseError`, `ValueError`, and `DomainException` are engine names                                               | Namespace domain exceptions and extend `\RuntimeException`                        |
| `catch (PaymentFailure)` listed after `catch (\RuntimeException)`          | First matching block wins; the general arm swallows the domain failure                                                                            | Order catch blocks most-specific first                                            |
| `readonly` property with a default value                                   | Fatal: a defaulted readonly property is a constant, and the engine rejects it                                                                     | Assign in the constructor, or make it a class constant                            |
| `public readonly static int $n`                                            | Fatal: static properties cannot be readonly, and `readonly class` forbids them entirely                                                           | Keep static state out of readonly classes                                         |
| `public int $x { get => ... }` on a readonly property                      | Property hooks are incompatible with `readonly`                                                                                                   | Drop one: hooks with a normal property, or `readonly` with a getter method        |
| `public protected(set) int $x`                                             | Only typed properties may carry a separate `set` visibility, and it must be equal to or narrower than `get`                                       | Type the property and keep `set` at least as restrictive as `get`                 |
| Enum with a property to carry state                                        | Fatal: enums cannot include properties                                                                                                            | Move the state to the class that holds the enum case                              |
| `switch` over an enum with `default`                                       | A new case takes the default arm silently — no error, wrong behaviour                                                                             | `match ($this)` with every case listed; let `UnhandledMatchError` fire            |
| `composer update` in a deploy pipeline                                     | Re-resolves the graph, shipping versions nobody tested                                                                                            | `composer install` against a committed `composer.lock`                            |
| `composer install --ignore-platform-reqs` to get past a version check      | Installs a graph the runtime cannot execute; the failure moves to first request                                                                   | Set `config.platform.php` to the deployment version and resolve against it        |
| `classmap-authoritative` without a full dump on deploy                     | New classes are not in the classmap and the autoloader refuses to fall back to disk                                                               | Run `composer dump-autoload --classmap-authoritative --no-dev` in the deploy step |
| `@dataProvider` doc-comment in PHPUnit 12                                  | Metadata in doc-comments was removed in 12.0; the provider is never called                                                                        | `#[DataProvider('methodName')]` with a static provider method                     |
| Coverage enabled with no `#[CoversClass]`                                  | Coverage is attributed to whatever loaded, so the number measures the autoloader                                                                  | Attribute each test and enable `requireCoverageMetadata`                          |
| Static `Log::channel()->info(...)` inside a service                        | Hides the dependency from static analysis and cannot be substituted in a test                                                                     | Inject `LoggerInterface` through the constructor                                  |
| Abstract base class extracted for one implementation                       | Every future change must satisfy an interface with no second consumer, and subclasses can violate the base's invariants                           | Keep the concrete `final` class; extract at the second real caller                |

## Checklist

1. Confirm exactly one formatter config exists (`pint.json` or `.php-cs-fixer.dist.php`, not both) and its ruleset is `@PER-CS` or the `per` preset rather than `@PSR12`.
2. Run the formatter in check mode (`--dry-run --diff`, or `pint --test`) and record the violation count.
3. Grep for `@` before a function call and for `error_reporting()` inside an error handler; every hit is a finding.
4. Verify `declare(strict_types=1)` is the first statement of every PHP file, and that the repository does not rely on a single entry-point declaration to cover call sites.
5. List every function and method signature lacking a parameter or return type, and every `mixed` that is implicit rather than declared.
6. Confirm no `?T` appears inside a union type and no DNF type contains a member subsumed by another.
7. Confirm no `readonly` property has a default, no `readonly static` exists, and no property hook is attached to a `readonly` property.
8. Confirm every `readonly class` declares no static properties and every asymmetric `set` visibility is at least as restrictive as its `get`.
9. Confirm closed value sets are enums with no properties, and that no `match` over an in-repository enum has a `default` arm.
10. Confirm each catch block names a specific type, is ordered most-specific-first, and passes `previous:` when wrapping.
11. Confirm every domain exception implements a namespace-level marker interface and that no class name collides with an engine exception.
12. Confirm log calls go through an injected `LoggerInterface`, use `{}` placeholders matching context keys, and put exceptions under the `'exception'` key.
13. Run `composer validate --strict` and `composer audit --locked`; both must pass.
14. Confirm `config.platform.php` matches the deployment runtime and `config.allow-plugins` lists only required plugins.
15. Run PHPStan at level 6 or higher (or Psalm at level 4 or lower) over first-party paths only, and confirm the baseline is committed with `reportUnmatchedIgnoredErrors` enabled.
16. Confirm the runner's PHP floor matches the project's minimum: PHPUnit 12 needs 8.3, PHPUnit 13 and Pest 5 need 8.4.
17. Confirm no doc-comment metadata remains, every `DataProvider` names a static same-class method, and every test either carries `#[Test]` or the `test` prefix.
18. Confirm `requireCoverageMetadata` and `beStrictAboutCoverageMetadata` are enabled and each test class carries `#[CoversClass]`.
19. Confirm `composer.lock` is committed for applications and absent for libraries, and that CI runs `composer install` rather than `update`.
20. Confirm no service locator or static singleton appears in domain code, and no abstract base class has exactly one subclass.

## References

- PER Coding Style 3.1 — https://www.php-fig.org/per/coding-style/
- PSR-1: Basic Coding Standard — https://www.php-fig.org/psr/psr-1/
- PSR-4: Autoloader — https://www.php-fig.org/psr/psr-4/
- PSR-12: Extended Coding Style — https://www.php-fig.org/psr/psr-12/
- PSR-3: Logger Interface — https://www.php-fig.org/psr/psr-3/
- PHP manual, type declarations and `strict_types` — https://www.php.net/manual/en/language.types.declarations.php
- PHP manual, `declare` and strict-types placement — https://www.php.net/manual/en/control-structures.declare.php
- PHP manual, backed enumerations — https://www.php.net/manual/en/language.enumerations.backed.php
- PHP manual, enumeration constants — https://www.php.net/manual/en/language.enumerations.constants.php
- PHP manual, `match` expressions and `UnhandledMatchError` — https://www.php.net/manual/en/control-structures.match.php
- PHP manual, named arguments — https://www.php.net/manual/en/functions.arguments.php
- PHP manual, first-class callable syntax — https://www.php.net/manual/en/functions.first_class_callable_syntax.php
- PHP manual, readonly properties — https://www.php.net/manual/en/language.oop5.properties.php
- PHP manual, property hooks — https://www.php.net/manual/en/language.oop5.property-hooks.php
- PHP manual, asymmetric visibility — https://www.php.net/manual/en/language.oop5.visibility.php
- PHP manual, cloning and `clone($object, $withProperties)` — https://www.php.net/manual/en/language.oop5.cloning.php
- PHP manual, `#[\Override]` — https://www.php.net/manual/en/class.override.php
- PHP manual, `#[\Deprecated]` — https://www.php.net/manual/en/class.deprecated.php
- PHP manual, error control operator — https://www.php.net/manual/en/language.operators.errorcontrol.php
- PHP manual, exceptions and `Throwable` — https://www.php.net/manual/en/language.exceptions.php
- PHP manual, migration to 8.5 (pipe operator, `array_first`/`array_last`) — https://www.php.net/manual/en/migration85.new-features.php
- RFC: `#[\NoDiscard]` — https://wiki.php.net/rfc/marking_return_value_as_important
- PHP.Watch, PHP 8.5 pipe operator — https://php.watch/versions/8.5/pipe-operator
- PHPStan rule levels — https://phpstan.org/user-guide/rule-levels
- PHPStan config reference — https://phpstan.org/config-reference
- PHPStan baseline — https://phpstan.org/user-guide/baseline
- Psalm error levels — https://psalm.dev/docs/running_psalm/error_levels/
- Psalm configuration — https://psalm.dev/docs/running_psalm/configuration/
- PHP-CS-Fixer rule sets — https://cs.symfony.com/doc/ruleSets/index.html
- PHP-CS-Fixer usage and CLI options — https://cs.symfony.com/doc/usage.html
- Laravel Pint presets and `pint.json` — https://laravel.com/docs/12.x/pint
- PHPUnit attributes — https://docs.phpunit.de/en/12.0/attributes.html
- PHPUnit XML configuration reference — https://docs.phpunit.de/en/12.0/configuration.html
- Pest, writing tests — https://pestphp.com/docs/writing-tests
- Composer autoloader optimization — https://getcomposer.org/doc/articles/autoloader-optimization.md
- Composer version constraints — https://getcomposer.org/doc/articles/versions.md
- Composer CLI (`validate`, `audit`, `dump-autoload`) — https://getcomposer.org/doc/03-cli.md
- Composer config (`platform`, `allow-plugins`, `classmap-authoritative`) — https://getcomposer.org/doc/06-config.md
- Related modules: [std-structure.md](std-structure.md), [std-docs.md](std-docs.md), [std-sql.md](std-sql.md), [std-git.md](std-git.md)
