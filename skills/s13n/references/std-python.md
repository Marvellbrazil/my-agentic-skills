# Python Standards

Python's standard library and tooling let a dozen dialects coexist in one repository: `os.path` next to `pathlib`, `typing.List` next to `list`, `%`-formatting next to f-strings, `except:` next to `except ValueError`. Each dialect compiles, so nothing fails until a mutable default argument leaks state across requests, a bare `except` swallows `KeyboardInterrupt`, or a blocking `requests.get` stalls the whole event loop. This module defines the canonical choice for each and the tooling that enforces it mechanically.

## Contents

- [When This Applies](#when-this-applies)
- [Toolchain: Formatter, Linter, and Type Checker](#toolchain-formatter-linter-and-type-checker)
  - [Type checking](#type-checking)
- [Types, Data Modeling, and Errors](#types-data-modeling-and-errors)
  - [Data carriers](#data-carriers)
  - [Enums over magic strings](#enums-over-magic-strings)
  - [Exceptions](#exceptions)
  - [EAFP vs LBYL](#eafp-vs-lbyl)
- [Idioms That Break at Scale](#idioms-that-break-at-scale)
- [Testing, Logging, and Async](#testing-logging-and-async)
  - [pytest](#pytest)
  - [Docstrings and the public API](#docstrings-and-the-public-api)
  - [Logging](#logging)
  - [Async correctness](#async-correctness)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- The repository contains `.py` files, a `pyproject.toml`, `setup.py`, `requirements.txt`, or a `uv.lock` / `poetry.lock` / `Pipfile.lock`.
- An audit finds mixed path APIs (`os.path.join` vs `/`), mixed type-hint eras (`Optional[X]` vs `X | None`), or mixed string formatting across modules.
- Type checking is absent, or configured but defeated by unqualified `# type: ignore` comments.
- Dependencies are declared in more than one place, or a lockfile is committed but CI installs with an unpinned `pip install -r`.
- An `async def` function calls a synchronous blocking API, or `asyncio.gather` is used without `return_exceptions`.
- Exception handling uses bare `except`, catches `Exception` and continues, or loses the cause of a failure.

## Toolchain: Formatter, Linter, and Type Checker

PEP 8 is the baseline, not the arbiter. Its 79-character code limit and 72-character docstring limit predate autoformatters; the ecosystem settled on 88. Where a deterministic tool has an opinion, the tool wins.

| Concern       | Authority       | Canonical value                                                                                                                       |
| ------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Line length   | Formatter       | 88 (Ruff/Black default); PEP 8's 79 is legacy                                                                                         |
| Quote style   | Formatter       | Double quotes; `quote-style = "single"` is a per-repo override                                                                        |
| Import order  | Linter (`I001`) | isort-compatible sections: stdlib, third-party, first-party, local                                                                    |
| Naming        | PEP 8           | `snake_case` functions/vars, `CapWords` classes, `UPPER_CASE` module constants, `_leading_underscore` internal, `__dunder__` protocol |
| Anything else | Human review    | Only where no tool is deterministic                                                                                                   |

Ruff's formatter reproduces >99.9% of lines identically on Black-formatted codebases like Django and Zulip, so pick `ruff format` and delete Black rather than running both. `line-length` is not a hard upper bound — formatted lines may exceed it, and `E501` is configured separately via `lint.pycodestyle.max-line-length`. `E501` and `E402` are **not** in Ruff's default rule set (defaults include `E722`, `W605`, `F401`, `I001`, `B006`, `B008`, `B023`, `RUF012`, `DTZ005`, `UP006`, `UP007`, `UP035`, `RUF100`, `S110`), so line length only errors once you select it.

```toml
# pyproject.toml
[project]
name = "billing"
requires-python = ">=3.11"          # Ruff infers target-version from this
dependencies = ["httpx>=0.27,<1"]

[dependency-groups]                  # PEP 735; not [project.optional-dependencies]
dev = ["pytest>=8.1,<9", "mypy>=1.11,<2"]

[tool.uv]
default-groups = ["dev"]

[tool.ruff]
line-length = 88
src = ["src"]
required-version = ">=0.6"           # fail loudly instead of drifting across machines

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM", "C4", "PT", "RET", "RUF", "PTH", "ASYNC", "TRY", "LOG", "G", "S", "D", "ANN"]
ignore = [
  "D203",   # conflicts with D211; pick one blank-line-after-class-docstring rule
  "ANN101", # self/cls annotations add noise, not safety
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "ANN201", "D103"]   # asserts and short test names are the point

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.pylint]
max-args = 5              # PLR0913
max-branches = 12         # PLR0912
max-returns = 6           # PLR0911
max-nested-blocks = 5     # PLR1702

[tool.ruff.lint.flake8-bugbear]
extend-immutable-calls = ["fastapi.Depends", "fastapi.Query"]  # B008 is wrong for DI markers

[tool.ruff.format]
docstring-code-format = true
```

```bash
ruff check .                     # 1 = violations found
ruff check --fix .               # safe fixes only; --unsafe-fixes opts into risky rewrites
ruff check --statistics          # count by rule, to triage a large baseline
ruff check --add-noqa            # generate suppressions instead of hand-writing them
ruff format --check .            # 0 = clean, 1 = would reformat, 2 = internal/config error
ruff check --isolated .          # ignore all config, to see raw tool defaults
```

### Type checking

Every public signature carries PEP 484 annotations. Use PEP 604 unions (`int | None`) and PEP 585 generics (`list[str]`, `dict[str, int]`) — `typing.Optional`, `typing.List`, and `typing.Dict` are deprecated aliases (`UP007`, `UP006`, `UP035` rewrite them). `from __future__ import annotations` was scheduled to become mandatory in 3.10, that plan was cancelled, and PEP 649 (3.14) replaces it with deferred evaluation — do not build new code on it.

```toml
[tool.mypy]
python_version = "3.11"
strict = true                        # expands to the flags listed below
warn_unreachable = true              # NOT part of --strict; opt in explicitly
enable_error_code = ["ignore-without-code", "redundant-expr", "possibly-undefined"]
files = ["src", "tests"]

# --strict is exactly: --disallow-any-generics --disallow-subclassing-any
# --disallow-untyped-calls --disallow-untyped-defs --disallow-incomplete-defs
# --check-untyped-defs --disallow-untyped-decorators --warn-redundant-casts
# --warn-unused-ignores --warn-return-any --no-implicit-reexport
# --strict-equality --extra-checks

[tool.pyright]                       # pyrightconfig.json overrides this if both exist
include = ["src"]
pythonVersion = "3.11"
typeCheckingMode = "strict"          # off | basic | standard (default) | strict
reportUnnecessaryTypeIgnoreComment = "error"
reportImplicitOverride = "error"     # @override enforcement; "none" by default even in strict
reportUnusedCoroutine = "error"      # dropped create_task() results; "none" by default
```

Suppressions must name a code, so an unrelated error introduced later on the same line cannot hide behind them: `value = legacy_api()  # type: ignore[no-any-return]`. A bare `# type: ignore` is an error under `ignore-without-code`; an unused suppression is an error under `warn_unused_ignores` (mypy) and `reportUnnecessaryTypeIgnoreComment` (Pyright). If a whole module must be excluded, exclude it in config — never add a blanket suppression.

## Types, Data Modeling, and Errors

### Data carriers

`@dataclass` for records, `frozen=True` for value objects, `slots=True` for hot paths. `slots=True` returns a _new_ class and raises `TypeError` if the class already defines `__slots__`; `kw_only` and `match_args` landed in 3.10, `weakref_slot` in 3.11, and `frozen=True` raises `TypeError` if the class defines `__setattr__` or `__delattr__`. The generated `__eq__` requires both operands to be the _identical_ type and compares fields in order (individually, as of 3.13).

```python
from dataclasses import dataclass, field
from decimal import Decimal

@dataclass(frozen=True, slots=True, kw_only=True)
class LineItem:
    sku: str
    quantity: int
    unit_price: Decimal
    tags: tuple[str, ...] = ()          # immutable default: no field() needed

@dataclass(slots=True)
class Cart:
    items: list[LineItem] = field(default_factory=list)   # never `= []`
    coupon: str | None = None
```

Prefer a dataclass to a plain class or `NamedTuple` for anything with more than two fields: `__init__`, `__repr__`, `__eq__`, `fields()`, and `asdict()` come for free.

### Enums over magic strings

A string literal repeated across modules is unvalidated, uncompletable, and unrenamable. `StrEnum` (3.11) members are `str` subclasses and serialize as-is; `IntEnum` members are `int` subclasses, but arithmetic on them produces a bare `int`, and 3.11 changed `IntEnum.__str__` to `int.__str__`. `auto()` assigns the lowercased member name for `StrEnum` and 1, 2, 3 for plain `Enum` (highest-seen + 1 as of 3.13; previously last-seen + 1).

```python
from enum import StrEnum, auto, unique

@unique
class Channel(StrEnum):
    EMAIL = auto()      # "email"
    SMS = auto()        # "sms"
    PUSH = auto()       # "push"
```

`@unique` turns an accidental duplicate value into an import-time `ValueError` instead of a silent alias; `PIE796` catches non-unique enums statically. Use `Flag`/`IntFlag` only for genuine bitmask combination.

### Exceptions

Never `except:` or `except Exception:` and continue. Catch the narrowest type that can occur, chain with `raise ... from` so the original survives as `__cause__`, and use `raise ... from None` only when the original is genuinely noise (it sets `__suppress_context__`). Without `from`, Python still sets `__context__` and prints "During handling of the above exception, another exception occurred" — which is how a `KeyError` inside an error handler gets mistaken for the root cause. `B904` enforces `from` inside `except`.

```python
class BillingError(Exception):
    """Base for all errors this package raises."""

class PaymentDeclined(BillingError):       # N818: exception names end in Error/Exception
    def __init__(self, decline_code: str) -> None:
        super().__init__(f"payment declined: {decline_code}")
        self.decline_code = decline_code

def charge(order_id: str, amount: Decimal) -> Receipt:
    try:
        return gateway.charge(order_id, amount)
    except gateway.ConnectionError as exc:
        raise BillingError(f"gateway unreachable for {order_id}") from exc
    except gateway.Declined as exc:
        raise PaymentDeclined(exc.code) from exc
```

A package exports one base exception and derives every raised error from it, so callers can `except BillingError` without importing implementation modules. `TRY003` and `EM101`/`EM102` flag long inline messages and f-strings passed directly to `raise`; build the message in a variable or a custom `__init__`. For concurrent failures, `ExceptionGroup` and `except*` (3.11) exist — but a `try` takes either `except` or `except*` clauses, never both, the exception type is mandatory (`except*:` is a syntax error), and matching a subclass of `BaseExceptionGroup` raises `TypeError`.

### EAFP vs LBYL

The Python glossary defines EAFP — "easier to ask for forgiveness than permission" — as assuming valid keys/attributes and catching the failure, contrasting it with LBYL, "common to many other languages such as C". Use EAFP when the check and the use are the same operation (dict access, attribute access, `int()` parsing), because a pre-check doubles the work and races in concurrent code. Use LBYL when the operation is destructive or the failure is expensive: check before deleting a directory, and prefer `Path.is_relative_to()` over string prefix tests when validating that a user-supplied path stays inside a root.

## Idioms That Break at Scale

**Mutable default arguments** are evaluated once, at function definition. `def f(items: list[str] = [])` shares one list across every call. `B006` catches this; `RUF012` catches the class-scope equivalent, which needs `ClassVar` for immutable constants.

```python
def append_log(entry: str, log: list[str] | None = None) -> list[str]:
    log = [] if log is None else log
    log.append(entry)
    return log
```

**`pathlib` over `os.path`.** `Path` carries the operations, is typed, and behaves identically on Windows and POSIX. The `PTH` family rewrites the common cases (`PTH123` `open()` → `Path.open()`, `PTH118` `os.path.join` → `/`, `PTH111` `expanduser`, `PTH109` `getcwd`). `Path.walk()` (3.12) replaces `os.walk` and lets you prune in place by mutating `dirnames` when `top_down=True`; `glob`/`rglob` return results in no particular order and suppress `OSError` during scanning, so sort explicitly when order matters. `Path.suffix` treats a lone `.` as valid as of 3.14.

```python
from pathlib import Path

def load_config(root: Path) -> dict[str, str]:
    path = root.expanduser() / "config" / "app.toml"
    if not path.is_file():
        raise FileNotFoundError(path)
    return tomllib.loads(path.read_text(encoding="utf-8"))
```

**f-strings over `%` and `.format()`.** `UP031`/`UP032` convert them; `RUF010` prefers the `!r` conversion flag over `repr(...)` inside the braces. The exception is logging: `G004` bans f-strings in logging calls because the f-string is evaluated even when the level is disabled. Use `%`-style lazy formatting in log calls — no Ruff rule catches a `%`-format outside logging, so that part is a human convention.

**Comprehensions over `map`/`filter`, but not past readability.** `C417` flags `map()` with a lambda, `C416` flags a copy-comprehension (`[x for x in xs]`), `PERF401` suggests a comprehension where a loop had a single `.append`. A loop is clearer when the body has more than one statement, contains `try`/`except`, or mutates shared state.

**Generators for streaming.** `yield` keeps memory flat over a large file or response body; `itertools.batched(iterable, n, *, strict=False)` (3.12, `strict` added in 3.13) chunks without materializing. `zip(*iterables, strict=False)` gained `strict` in 3.10 and raises `ValueError` on length mismatch — pass `strict=True` for parallel collections that must align.

**No module-level side effects, no global mutable state.** Importing a module must not open sockets, read config, or mutate a registry. `PLW0603` (`global-statement`) and `PLW0602` flag the symptom; the fix is dependency injection through arguments or a `functools.cache`-decorated accessor called lazily. `functools.cache` is `lru_cache(maxsize=None)` — pure functions with hashable arguments only.

**Context managers, always.** `SIM115` flags `open()` without `with`. Use `contextlib.suppress(SpecificError)` instead of `try/except/pass` (`SIM105`), `ExitStack` when the number of resources is data-driven, `nullcontext` for an optional manager, and `@contextmanager` for a generator that must release in `finally`. A generator-based context manager must re-raise (or not catch) the exception, otherwise it silently marks the error handled.## Dependencies, Environments, and Lockfiles

`pyproject.toml` is the single source of dependency truth (PEP 621 `[project]` for runtime, PEP 735 `[dependency-groups]` for development). `requirements.txt` is a build artifact produced by `uv export`, not hand-edited. `uv.lock` is committed; `.venv` is not.

```bash
uv init --package billing
uv add "httpx>=0.27,<1"
uv add --dev pytest            # alias for --group dev
uv add --group lint ruff       # arbitrary PEP 735 group
uv lock                        # update uv.lock; existing lock is used as a preference
uv lock --check                # assert the lockfile is up to date; equivalent to --locked
uv sync --locked               # error if pyproject.toml and uv.lock disagree
uv sync --frozen               # use the lockfile as-is, skip the freshness check
uv run --locked pytest         # CI: fail instead of silently re-resolving
uv export --format requirements.txt --no-emit-project --no-hashes > requirements.txt
uv python pin 3.11             # writes .python-version
uv venv --seed                 # .venv with pip/setuptools/wheel for tooling that needs them
```

Three details matter. `uv lock` will **not** consider the lockfile stale when a newer package version is published — upgrading is always an explicit `uv lock --upgrade`. `uv sync` is exact by default (it removes extraneous packages) while `uv run` is inexact (it only adds); pass `--exact` to `uv run` for the stricter behavior. `tool.uv.default-groups` controls which groups install by default — set it explicitly rather than relying on the `dev` special case.

The lockfile discipline is universal, but the flag names are not:

| Ecosystem    | Lock file           | CI-strict command      | Semantics                                                             |
| ------------ | ------------------- | ---------------------- | --------------------------------------------------------------------- |
| Python (uv)  | `uv.lock`           | `uv sync --locked`     | Error if `pyproject.toml` and lock disagree                           |
| Rust (Cargo) | `Cargo.lock`        | `cargo build --locked` | Error if the lock would change; `--frozen` = `--locked` + `--offline` |
| Node (npm)   | `package-lock.json` | `npm ci`               | Installs exactly the lock, never writes it                            |

Never install into a system interpreter; every project gets its own `.venv` (`requires-python` pins the floor, `.python-version` pins the exact interpreter). See [std-shell.md](std-shell.md) for activation patterns and [std-js.md](std-js.md) for the npm side.

## Testing, Logging, and Async

### pytest

Configuration belongs in `[tool.pytest.ini_options]` (since pytest 6.0); `pytest.ini` takes precedence over it, and `pytest.toml` (9.0) takes precedence over both.

```toml
[tool.pytest.ini_options]
minversion = "8.1"
testpaths = ["tests"]
addopts = ["-ra", "--strict-markers", "--strict-config"]
filterwarnings = ["error", "ignore::DeprecationWarning:legacy_pkg.*"]
xfail_strict = true
faulthandler_timeout = 30
```

`filterwarnings = ["error"]` promotes every warning to a failure; allowlist by module the specific ones you cannot fix, so new warnings still break the build. `--strict-markers` rejects typos in `@pytest.mark.*` names instead of silently passing. Fixtures use `yield` for teardown, scope narrowly (`function` is the default and the only safe default for stateful resources), and live in the nearest `conftest.py`. `tmp_path`, `capsys`, and `monkeypatch` are built in — do not reimplement them.

```python
import pytest
from decimal import Decimal

@pytest.mark.parametrize(
    ("quantity", "unit_price", "expected"),
    [(1, Decimal("10.00"), Decimal("10.00")), (3, Decimal("9.99"), Decimal("29.97"))],
    ids=["single", "bulk"],
)
def test_line_total(quantity: int, unit_price: Decimal, expected: Decimal) -> None:
    assert LineItem(sku="A1", quantity=quantity, unit_price=unit_price).total == expected

def test_declined_payment_raises() -> None:
    with pytest.raises(PaymentDeclined, match=r"payment declined: insufficient_funds"):
        charge("ord_1", Decimal("1"))
```

Test names state the behavior (`test_declined_payment_raises`), not the method under test (`test_charge_2`). `pytest.raises` requires an exception class — `pytest.raises(Exception)` is `PT011` and passes for the wrong error — and `match` is a regex searched against `str(exc)`, including PEP 678 `__notes__`.

### Docstrings and the public API

Docstrings go on public modules, classes, and functions (`D100`–`D107`); `D103` covers public functions, `D107` covers `__init__`. Choose one convention — Ruff supports `convention = "google"`, `"numpy"`, or `"pep257"` and disables the rules the chosen convention does not include. `D401` requires an imperative-mood summary ("Return the parsed config", not "Returns the parsed config").

`__all__` is the public interface contract. Type checkers treat underscore-prefixed and imported names as private unless `__all__` lists them, and only a statically resolvable `__all__` works — `__all__ = ["a", "b"]`, `__all__ += other.__all__`, and `__all__.extend(...)` are recognized; a computed list is not. `RUF022` sorts it. Ship a `py.typed` marker (PEP 561) if the package is a library, or downstream consumers get no type information at all.

### Logging

`print()` is for scripts a human runs; everything else uses `logging` (`T201` bans `print`). Get a module-level logger with `logging.getLogger(__name__)` and never reconfigure the root logger from a library. Configure once at the application entry point via `logging.config.dictConfig`.

```python
import logging

logger = logging.getLogger(__name__)

def process(order_id: str) -> None:
    logger.info("processing order %s", order_id)          # lazy %-style, not an f-string
    try:
        charge(order_id, Decimal("1"))
    except BillingError:
        logger.exception("charge failed for order %s", order_id)   # carries exc_info
        raise
```

`logger.exception` (or `exc_info=True`) records the traceback; `TRY400` flags `logger.error` inside an `except`, and `TRY401` flags a message that also interpolates the exception. `G004` bans f-strings in log calls, `G010` bans the deprecated `warn()`, and `B028` flags `warnings.warn` without `stacklevel=2`.

### Async correctness

An `async def` function runs on the event loop, so any synchronous blocking call inside it freezes every other task. Ruff's `ASYNC` rules catch the common cases: `ASYNC210`/`ASYNC212` blocking HTTP, `ASYNC221` subprocess, `ASYNC230` `open()`, `ASYNC240` path methods, `ASYNC251` `time.sleep`. Offload unavoidable blocking work with `asyncio.to_thread` (3.9) — it is a thread, not a process, so the GIL still serializes CPU-bound work.

```python
import asyncio
from pathlib import Path

async def fetch_all(urls: list[str]) -> list[str]:
    async with asyncio.TaskGroup() as tg:          # 3.11; structural concurrency
        tasks = [tg.create_task(fetch(url)) for url in urls]
    return [t.result() for t in tasks]

async def read_many(paths: list[Path]) -> list[bytes]:
    results = await asyncio.gather(
        *(asyncio.to_thread(p.read_bytes) for p in paths),
        return_exceptions=True,                    # one failure does not cancel the rest
    )
    return [r for r in results if isinstance(r, bytes)]

async def fetch(url: str) -> str:
    async with asyncio.timeout(5):                 # 3.11
        async with httpx.AsyncClient() as client:
            return (await client.get(url)).text
```

Two traps. `asyncio.gather(..., return_exceptions=False)` propagates the first exception **immediately** and leaves the other awaitables running — they are not cancelled, so their failures surface later as unretrieved-exception warnings. With `return_exceptions=True` the exceptions land in the result list and the caller must inspect types. Second, `asyncio.create_task` returns a task the loop only weakly references; save it or it can be garbage collected mid-flight. `TaskGroup` avoids both: the first non-`CancelledError` failure cancels the remaining tasks and the failures combine into an `ExceptionGroup`, except that `KeyboardInterrupt` and `SystemExit` are re-raised directly instead of grouped.

## Common Mistakes

| Mistake                                                          | Why It Breaks                                                                                                                             | Correct Approach                                                                                                             |
| ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `def f(x, cache={})`                                             | The default is created once at definition; every call mutates the same object and leaks state across requests                             | `cache: dict[str, int] \| None = None`, then `cache = {} if cache is None else cache` (`B006`)                               |
| `except:` / `except Exception: pass`                             | Swallows `KeyboardInterrupt`, `SystemExit`, and real bugs; failures become silent wrong answers                                           | Catch the narrowest type; `contextlib.suppress(SpecificError)` when silence is intended (`E722`, `BLE001`, `S110`, `SIM105`) |
| `raise ValueError("bad")` inside `except KeyError`               | Implicit chaining sets `__context__`, so the traceback says "During handling of the above exception" and the original cause is buried     | `raise ValueError("bad") from exc` (`B904`); `from None` only when the original is noise                                     |
| `# type: ignore` with no code                                    | Silences every diagnostic on the line, including ones introduced later by an unrelated edit                                               | `# type: ignore[attr-defined]` plus `enable_error_code = ["ignore-without-code"]`; enable `warn_unused_ignores`              |
| `Optional[X]`, `List[str]`, `Dict[str, int]`                     | Deprecated aliases since 3.9; they hide that `list[str]` works at runtime for annotations and add an import                               | `X \| None`, `list[str]`, `dict[str, int]` (`UP007`, `UP006`, `UP035`)                                                       |
| `os.path.join(root, "a", "b")` and `open(path)`                  | Loses the typed API, mishandles Windows separators in some compositions, and cannot use `Path` helpers                                    | `root / "a" / "b"` and `path.read_text(encoding="utf-8")` (`PTH118`, `PTH123`)                                               |
| `logger.info(f"order {order_id}")`                               | The f-string is evaluated before the level check, so disabled logging still costs formatting on every call                                | `logger.info("order %s", order_id)` (`G004`); `logger.exception(...)` inside `except`                                        |
| `asyncio.gather(*coros)` without `return_exceptions`             | The first failure propagates immediately while the remaining tasks keep running, producing unretrieved-exception warnings and leaked work | `return_exceptions=True` and filter the results, or `asyncio.TaskGroup` for cancellation semantics                           |
| `requests.get(...)` inside `async def`                           | Blocks the event loop for the whole request, stalling every other coroutine                                                               | `httpx.AsyncClient`, or `asyncio.to_thread` for genuinely sync APIs (`ASYNC210`)                                             |
| `[x for x in xs]`, `map(lambda x: ..., xs)`                      | Allocates a copy of the sequence and is slower than the alternatives the tools already prefer                                             | Pass `xs` directly, or use a generator; `list(map(...))` → comprehension (`C416`, `C417`)                                    |
| `pip install -r requirements.txt` in CI against a committed lock | Resolves fresh versions, so CI and production run different dependency graphs                                                             | `uv sync --locked` (or `npm ci`, `cargo build --locked`) so a stale lock fails the build                                     |
| Mutable class attribute `items: list[str] = []`                  | Shared across all instances, same root cause as the default-argument bug                                                                  | `field(default_factory=list)` on a dataclass, or `ClassVar` if it truly is shared (`RUF012`)                                 |

## Checklist

1. Confirm a single dependency source: `[project]` and `[dependency-groups]` in `pyproject.toml`, with no hand-maintained `requirements.txt` and no second declaration in `setup.py`.
2. Verify `requires-python` is set and matches the version Ruff, mypy, and pyright resolve; pin the exact interpreter in `.python-version`.
3. Run `ruff format --check .` and confirm exit code 0; if Black is also configured, delete one of them.
4. Run `ruff check .`, record the baseline with `--statistics`, and confirm `E501`, `E402`, and project-specific rules are explicitly in `select` rather than assumed to be default.
5. Inspect every `noqa` and `# type: ignore`; confirm each names a rule code and that unused suppressions fail the build.
6. Verify the type checker runs strict (`strict = true` for mypy, `typeCheckingMode = "strict"` for pyright) with `warn_unreachable` / `reportUnusedCoroutine` enabled explicitly, since neither is implied by strict.
7. Grep for `Optional[`, `List[`, `Dict[`, `Tuple[`, and `from typing import` aliases; replace with PEP 604/585 forms.
8. Grep for `os.path.`, `os.walk`, and bare `open(`; convert to `pathlib` and use `Path.walk` where directory recursion exists.
9. Grep for `except:`, `except Exception`, and `raise` inside `except` without `from`; confirm each handler catches a specific type and chains the cause.
10. Confirm every mutable default argument is `None`-sentineled, every dataclass collection field uses `default_factory`, and every module-level collection constant is `ClassVar`.
11. Check that each module gets its logger via `logging.getLogger(__name__)`, that no library configures the root logger, and that no `print()` remains outside CLI entry points.
12. Confirm `filterwarnings = ["error"]` (or equivalent) is set, `--strict-markers` is in `addopts`, and every `pytest.raises` names a specific exception with a `match` pattern.
13. Verify every `async def` body is free of blocking I/O and `time.sleep`, and that each `gather` either passes `return_exceptions=True` or is replaced by `TaskGroup`.
14. Confirm `__all__` exists on public modules, is statically resolvable, is sorted, and that a `py.typed` marker ships if the package is published.
15. Confirm lockfile-based CI: `uv sync --locked` (or `--frozen` where freshness must not be checked), with `uv lock --check` as a pre-commit gate.
16. Verify docstrings on all public modules, classes, and functions follow one convention (`convention = "google"` or `"numpy"`), with imperative-mood summaries.

## References

- [PEP 8](https://peps.python.org/pep-0008/) · [PEP 484 Type Hints](https://peps.python.org/pep-0484/) · [PEP 585 Generics in Standard Collections](https://peps.python.org/pep-0585/) · [PEP 604 Union types as `X | Y`](https://peps.python.org/pep-0604/) · [PEP 695 Type Parameter Syntax](https://peps.python.org/pep-0695/) · [PEP 673 Self Type](https://peps.python.org/pep-0673/) · [PEP 649 Deferred Evaluation of Annotations](https://peps.python.org/pep-0649/)
- [PEP 654 Exception Groups and `except*`](https://peps.python.org/pep-0654/) · [PEP 621 Project metadata](https://peps.python.org/pep-0621/) · [PEP 735 Dependency Groups](https://peps.python.org/pep-0735/) · [PEP 561 Packaging Type Information](https://peps.python.org/pep-0561/)
- [Python Glossary — EAFP and LBYL](https://docs.python.org/3/glossary.html#term-EAFP) · [Language Reference — `raise` and exception chaining](https://docs.python.org/3/reference/simple_stmts.html#the-raise-statement) · [`try` / `except*`](https://docs.python.org/3/reference/compound_stmts.html#the-try-statement)
- [`dataclasses`](https://docs.python.org/3/library/dataclasses.html) · [`enum`](https://docs.python.org/3/library/enum.html) · [`pathlib`](https://docs.python.org/3/library/pathlib.html) · [`contextlib`](https://docs.python.org/3/library/contextlib.html) · [`asyncio` Tasks](https://docs.python.org/3/library/asyncio-task.html)
- [`logging`](https://docs.python.org/3/library/logging.html) · [`logging.config.dictConfig`](https://docs.python.org/3/library/logging.config.html) · [`__future__.annotations` status](https://docs.python.org/3/library/__future__.html)
- [Ruff — Linter](https://docs.astral.sh/ruff/linter/) · [Default Rules](https://docs.astral.sh/ruff/default-rules/) · [Settings](https://docs.astral.sh/ruff/settings/) · [Formatter](https://docs.astral.sh/ruff/formatter/) · [Black usage](https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html)
- [mypy — CLI](https://mypy.readthedocs.io/en/stable/command_line.html) · [Config](https://mypy.readthedocs.io/en/stable/config_file.html) · [Error codes](https://mypy.readthedocs.io/en/stable/error_code_list.html) · [Pyright — Configuration](https://microsoft.github.io/pyright/#/configuration) · [Suppressions](https://microsoft.github.io/pyright/#/comments) · [Typing Guidance for Libraries](https://microsoft.github.io/pyright/#/typed-libraries)
- [pytest — Fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html) · [Configuration](https://docs.pytest.org/en/stable/reference/customize.html) · [API Reference](https://docs.pytest.org/en/stable/reference/reference.html)
- [uv — Locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/) · [Dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/) · [CLI reference](https://docs.astral.sh/uv/reference/cli/) · [Cargo `--locked`/`--frozen`](https://doc.rust-lang.org/cargo/commands/cargo-build.html)
