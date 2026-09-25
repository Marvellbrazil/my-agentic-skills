# YAML, JSON, and Configuration Standards

Configuration formats are the contract between an application and every environment it runs in. A trailing comma, an unquoted `no`, a tab character, or a silently-coerced string turns a deploy into an outage that no unit test catches. This module covers format selection, YAML's type-coercion traps, schema validation, layering and precedence, secret hygiene, and the tooling that enforces all of it in CI.

## Contents

- [When This Applies](#when-this-applies)
- [Format Selection and Consistency](#format-selection-and-consistency)
- [YAML Traps: Types, Quoting, and Anchors](#yaml-traps-types-quoting-and-anchors)
  - [Indentation](#indentation)
  - [Anchors, aliases, and merge keys](#anchors-aliases-and-merge-keys)
- [JSON Conventions and Schema Validation](#json-conventions-and-schema-validation)
  - [Versioning config schemas](#versioning-config-schemas)
- [Layering, Precedence, and Secrets](#layering-precedence-and-secrets)
  - [Layered configuration](#layered-configuration)
  - [Environment variables versus templating](#environment-variables-versus-templating)
  - [Secrets](#secrets)
- [Types, Validation, and Single Source of Truth](#types-validation-and-single-source-of-truth)
  - [Explicit types, no stringly-typed config](#explicit-types-no-stringly-typed-config)
  - [Validation error messages](#validation-error-messages)
  - [Single source of truth](#single-source-of-truth)
  - [Documenting every key](#documenting-every-key)
  - [Formatting and linting in CI](#formatting-and-linting-in-ci)
  - [Generated files](#generated-files)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- The repo contains more than one config format for the same concern (`app.yaml` and `app.json`, `.env` plus `settings.toml`) and no documented rule for which wins.
- A config value is parsed differently in two environments — `true` in dev, `"true"` in prod — or a port is a string in one service and an integer in another.
- A deploy fails at runtime, not at startup, because a required key is missing or misspelled.
- Secrets, tokens, or connection strings appear in a committed config file, or in a `values.yaml` checked into the repo.
- Configuration is hand-edited in production, or a generated file (`package-lock.json`, `compose.override.yaml`, Helm rendered output) is edited by hand.
- The project has no schema for its config, no lint step for YAML/TOML, or no CI check that config parses.
- The same literal (a queue name, a bucket, a timeout) is repeated across three or more config files with no single source of truth.

## Format Selection and Consistency

| Role                                                           | Format                | Rationale                                                                                    |
| -------------------------------------------------------------- | --------------------- | -------------------------------------------------------------------------------------------- |
| Machine-to-machine exchange, API payloads, lockfiles           | JSON                  | Unambiguous grammar, universal parsers, no type coercion beyond number/string/bool/null      |
| Human-edited application config, CI definitions, K8s manifests | YAML                  | Comments, multi-line strings, anchors; tolerable at human scale                              |
| Tooling and build config where the ecosystem dictates it       | TOML                  | Explicit types, no indentation sensitivity, spec'd datetime; the Rust/Python tooling default |
| Environment-specific overrides injected at runtime             | Environment variables | Not a file; twelve-factor delivery mechanism, not a config language                          |
| Schema-heavy config needing comments where a tool requires it  | JSON5 / JSONC / HCL   | VS Code `settings.json`, Terraform; never for files other tools must parse as strict JSON    |

The format a tool mandates is not negotiable — `Cargo.toml`, `pyproject.toml`, `go.mod`, and `package.json` are fixed. What is negotiable is the format you choose for your _own_ config surface; pick one and never add a second. A repository that ships `app.yaml` **and** `app.json` for the same settings has two truths, and the one that wins depends on load order.

## YAML Traps: Types, Quoting, and Anchors

YAML 1.1 — still implemented by PyYAML, Ruby's Psych, and many parsers — coerces unquoted scalars far more aggressively than authors expect.

| Written                  | Parsed as           | Why                                                                                                               |
| ------------------------ | ------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `country: NO`            | `false`             | YAML 1.1 booleans include `y`, `Y`, `yes`, `Yes`, `YES`, `n`, `N`, `no`, `No`, `NO`, `on`, `off`, `true`, `false` |
| `version: 1.10`          | `1.1` (float)       | Trailing zero dropped; version becomes a number, not a string                                                     |
| `port: 080`              | `80` or error       | Leading-zero integers are read as octal in some parsers                                                           |
| `time: 12:30`            | `750` (sexagesimal) | YAML 1.1 base-60 integers; `12:30:00` becomes `45000`                                                             |
| `value: ~`               | `null`              | `~` and `null`/`Null`/`NULL` are all null                                                                         |
| `id: 0x1F`               | `31`                | Hex integers are coerced                                                                                          |
| `duration: 1_000`        | `1000`              | Underscores are digit separators in YAML 1.1                                                                      |
| `key: value: with colon` | parse error         | A colon followed by a space inside an unquoted scalar starts a mapping                                            |

The rule that resolves all of these: **quote anything that is not unambiguously a string or a plain number you intend as a number.** Version strings, country codes, dates, and any scalar with a leading zero get double quotes.

```yaml
country: "NO" # bare NO parses as boolean false
version: "1.10" # bare 1.10 parses as the float 1.1
release: "2024-01-05" # bare form is a datetime in YAML 1.1, a string in 1.2
port: 80 # a real number, deliberately left bare
```

### Indentation

YAML forbids tabs for indentation, full stop, and the parser error on a tab is often reported at a misleading line. Standardize on two spaces (the de facto convention in Kubernetes, GitHub Actions, Ansible, and Prettier's default) and enforce it in a lint config rather than in review. Sequence items may be indented under their parent key or flush with it — both are legal, so mixed styles inside one file parse fine and read badly. Pick one; yamllint's `indentation.indent-sequences` is the switch.

### Anchors, aliases, and merge keys

Anchors (`&`) and aliases (`*`) deduplicate YAML content. They are resolved by the parser before your code sees the data, so an alias produces a shared _value_, not a reference. The `<<` merge key is **not in the YAML 1.2 spec**: it is a YAML 1.1 feature supported by PyYAML, Psych, and js-yaml, and unsupported by Go's `gopkg.in/yaml.v3`.

```yaml
defaults: &defaults
  retries: 3
  timeout_seconds: 30

service_a:
  <<: *defaults
  endpoint: "https://a.internal"
```

Anchors are per-document — there is no cross-file alias. When config is consumed by three or more tools, prefer an explicit template or generated file over merge keys, because a tool that cannot follow the alias reads a different config than the one you wrote.

Multi-document streams are a separate feature: `---` separates documents, and it belongs only where a consumer expects a stream (Kubernetes manifests, `kubectl apply -f`). A single-document config that uses `---` as a decorative header fails in `yaml.safe_load`, which raises `ComposerError: expected a single document` on multi-document input; `safe_load_all` is the reader for the streaming case.

## JSON Conventions and Schema Validation

JSON's grammar is stricter and its trap set is smaller, but the conventions differ per ecosystem.

| Ecosystem                            | Property casing                                                             | Evidence                                              |
| ------------------------------------ | --------------------------------------------------------------------------- | ----------------------------------------------------- |
| JavaScript / TypeScript, Node APIs   | `camelCase`                                                                 | `package.json`, ESLint config, npm registry responses |
| Python (FastAPI, Django REST, PEP 8) | `snake_case`                                                                | PEP 8 names, Pydantic field names                     |
| PHP / Laravel                        | `snake_case` in payloads                                                    | Eloquent attribute convention, `config/*.php` keys    |
| Java / Jackson                       | `camelCase` by default                                                      | Jackson `PropertyNamingStrategies.LOWER_CAMEL_CASE`   |
| Go                                   | `PascalCase` in structs, `snake_case` or `camelCase` in tags by team choice | `encoding/json` uses the tag verbatim                 |
| SQL / column names                   | `snake_case`                                                                | See [std-sql.md](std-sql.md)                          |

Rules that are not stylistic preferences:

- **No comments.** JSON has no comment syntax; a `//` in a `.json` file makes it invalid JSON even though VS Code's JSONC parser and `json5` accept it. If a config needs comments, use YAML or TOML.
- **No trailing commas.** `{"a": 1,}` is a parse error in every spec-compliant parser.
- **No `NaN`, `Infinity`, or `-Infinity`.** RFC 8259 permits only the JSON number grammar. `JSON.parse` rejects them; Python's `json.loads` accepts them by default and `json.dumps` emits them unless `allow_nan=False` is set, which raises `ValueError: Out of range float values are not JSON compliant`. Serialize as `null` or a sentinel string.
- **Numbers lose precision above 2^53.** A 64-bit integer ID serialized to JSON and parsed in JavaScript silently truncates. Send large IDs as strings.
- **Duplicate keys are undefined behavior.** RFC 8259 says names "SHOULD" be unique; parsers keep the last one (`JSON.parse`) or the first (`json.loads`). `uniqueItems` in a schema covers array elements, not object keys — only a linter rule (`no-duplicate-keys`) catches this.

### Versioning config schemas

Every config file gets a schema, and the schema gets a version when its shape is not additive. Store the schema next to the config, reference it by `$id`, and validate at startup — not at first use of the offending key.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.internal/schemas/app-config/v2.json",
  "type": "object",
  "required": ["server", "database"],
  "additionalProperties": false,
  "properties": {
    "server": {
      "type": "object",
      "required": ["port"],
      "additionalProperties": false,
      "properties": {
        "port": { "type": "integer", "minimum": 1, "maximum": 65535 },
        "host": { "type": "string", "format": "hostname", "default": "0.0.0.0" }
      }
    },
    "database": {
      "type": "object",
      "required": ["url"],
      "additionalProperties": false,
      "properties": {
        "url": { "type": "string", "pattern": "^postgres(ql)?://" },
        "pool_size": { "type": "integer", "minimum": 1, "default": 10 }
      }
    }
  }
}
```

`additionalProperties: false` is the highest-value setting in the file: it turns a typo'd key from a silent no-op into a startup failure. Note that `format: hostname` is annotation-only in draft 2020-12 — not asserted unless the validator enables format assertion.

Validation in three ecosystems:

```python
# Python — jsonschema; iter_errors yields every failure, FormatChecker asserts format
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

schema = json.loads(Path("config/app.schema.json").read_text())
config = yaml.safe_load(Path("config/app.yaml").read_text())
validator = Draft202012Validator(schema, format_checker=FormatChecker())

errors = sorted(validator.iter_errors(config), key=lambda e: list(e.absolute_path))
for error in errors:
    path = "/" + "/".join(str(part) for part in error.absolute_path)
    print(f"  {path}: {error.message}")
if errors:
    raise SystemExit(1)
```

```typescript
// TypeScript — Ajv 8 strict mode, all errors at once
import Ajv from "ajv";
import addFormats from "ajv-formats";

const ajv = new Ajv({ allErrors: true, strict: true });
addFormats(ajv);

const validate = ajv.compile(schema);
if (!validate(config)) {
  const detail = validate.errors
    ?.map((e) => `${e.instancePath || "/"} ${e.message}`)
    .join("; ");
  throw new Error(`Invalid configuration: ${detail}`);
}
```

PHP uses `opis/json-schema`: `(new Validator())->validate($configData, $schemaData)` returns a result whose `hasError()` and `(new ErrorFormatter())->format($result->error())` give the same per-key detail. In every language the shape is identical — validate the whole document, collect every error, name each failing key by its path, exit non-zero before serving traffic.

Schema evolution: additive optional fields are a minor bump and old configs stay valid. A renamed key, a changed type, or a new required field is a major bump — publish `v2.json`, keep `v1.json` resolvable, and support both for one deprecation window with an explicit migration path.

## Layering, Precedence, and Secrets

### Layered configuration

Configuration resolves from a stack, and the precedence must be written down. The conventional order, lowest to highest:

1. Hard-coded defaults in the schema or code (must be safe, must not be production credentials).
2. Committed base config (`app.yaml`).
3. Committed environment overlay (`app.prod.yaml`).
4. Mounted file config from the platform (K8s ConfigMap, container bind mount).
5. Environment variables.
6. Command-line flags.
7. Runtime overrides (feature flags, admin UI, database-backed settings).

Later layers win, and the merge must be **deep for maps, replace for arrays**. Arrays are the recurring bug: replacing `plugins: [a, b]` with `plugins: [c]` is correct, while a deep merge that appends produces a list no one authored. Decide explicitly, document it, and unit-test the merge function.

```python
def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = deep_merge(current, value)
        else:
            merged[key] = value
    return merged
```

Never read an environment variable inside the module that needs the value. Read all configuration once at the composition root, validate it, and pass typed values down — see [std-php.md](std-php.md) and [std-js.md](std-js.md) for the per-language dependency-injection shapes.

### Environment variables versus templating

Environment variables carry _scalar_ values. They cannot express nesting, lists, or types without a convention, and every convention is a parsing bug waiting to happen. Two defensible patterns:

- **One variable per scalar leaf**, with a documented mapping: `APP_DATABASE__POOL_SIZE=20` (double underscore for nesting, as in Spring Boot's relaxed binding and .NET's `__` separator).
- **One variable holding a document**, parsed by the app: `APP_CONFIG_JSON='{"database":{"pool_size":20}}'`. Only for small documents; multi-line values and shell quoting make it fragile.

Templating (Helm, `envsubst`, Jinja, `gomplate`) is a build-time transform, not a config format. Rendered output is a build artifact: not committed, not hand-edited, reproducible from template plus inputs. A committed rendered file is silently overwritten by the next `helm upgrade`.

Interpolation inside a config _file_ (`${VAR}` in YAML) works only if the loader implements it. Kubernetes does **not** expand `${VAR}` in ConfigMap values consumed as files, though the kubelet does expand `$(VAR)` inside `env`, `args`, and `command` in a Pod spec. Know which layer expands; never assume a format expands variables unless the tool documents it.

### Secrets

Secrets do not belong in config files, in images, in Helm values committed to git, or in CI logs.

- Local development: a gitignored `.env` loaded by the app or toolchain, plus a committed `.env.example` listing key _names_ and no values.
- Deployed: variables injected by the orchestrator from a secret store, or files mounted from that store.
- Stores: AWS Secrets Manager / SSM Parameter Store, GCP Secret Manager, Azure Key Vault, HashiCorp Vault, Kubernetes Secrets (base64 is _not_ encryption — enable etcd encryption at rest, and prefer External Secrets Operator or Sealed Secrets).
- Rotation must not require a rebuild. If rotating a credential needs a new image, the credential is baked in.

Scan for leaks in CI with `gitleaks` or `trufflehog` over the working tree **and** the full history; a secret removed in a later commit is still in `git log -p`.

## Types, Validation, and Single Source of Truth

### Explicit types, no stringly-typed config

Config arrives as strings from environment variables and as loosely-typed trees from YAML/JSON. Parse it once into a typed structure at startup, and fail loudly on failure.

```typescript
import { z } from "zod";

const Config = z.object({
  server: z.object({
    port: z.coerce.number().int().min(1).max(65535),
    tls: z
      .enum(["true", "false", "1", "0"])
      .transform((v) => v === "true" || v === "1"),
    allowedOrigins: z.array(z.string().url()).default([]),
  }),
  database: z.object({
    url: z.string().url(),
    poolSize: z.coerce.number().int().min(1),
  }),
});

export const config = Config.parse(rawConfig);
```

Do not reach for `z.coerce.boolean()` here: it applies JavaScript truthiness, so the string `"false"` coerces to `true`. Parse booleans through an explicit `enum` as above. The Python equivalent declares the same constraints on a Pydantic v2 `BaseSettings` with `env_prefix="APP_"` and `env_nested_delimiter="__"`, giving `APP_DATABASE__POOL_SIZE` and a `PostgresDsn`-typed `url` field.

Avoid stringly-typed values for enumerations. `mode: "prod"` with a typo becomes `mode: "prd"` and passes every check until a branch falls through to a default. Constrain it in the schema (`enum: ["development", "staging", "production"]`) or the model (`Literal["development", "staging", "production"]`).

### Validation error messages

A validation failure must name the offending key, the file, and the expectation. `KeyError: 'port'` is a stack trace, not an error message.

```
Invalid configuration in config/app.yaml:
  /server/port: must be integer, got string "8080"
  /database/pool_size: must be >= 1, got 0
  /cache/ttl_second: unknown property (did you mean "ttl_seconds"?)
```

The "did you mean" hint comes free from `additionalProperties: false` plus a nearest-key match; Ajv exposes `e.params.additionalProperty`. Emit all errors at once (`allErrors: true` in Ajv, `iter_errors` in jsonschema), not the first — an operator fixing five typos should not need five deploys.

### Single source of truth

Any value that appears in two config files will drift. Collapse it:

- Define it once and reference it: a shared `constants.yaml` included by the template, a JSON Schema `$ref`, a generated file, or one environment variable consumed by both readers.
- For values shared across services, publish from one place — a config service, a Terraform output consumed by every module, or a versioned artifact — and consume, never copy.
- When two tools genuinely cannot share a file (a port in `docker-compose.yaml` and in `app.yaml`), generate one from the other, or add a CI assertion that the two agree. A test that greps for the literal is inelegant but it fails fast, which is the point.

### Documenting every key

Every key carries a doc comment: what it does, its unit, its default, its valid range. YAML and TOML have `#`; JSON does not, which is one reason JSON is a poor choice for human-edited config.

```yaml
server:
  # TCP port the HTTP server binds to. Default: 8080. Range: 1-65535.
  port: 8080
  # Seconds to wait for in-flight requests during shutdown. Default: 30.
  graceful_shutdown_seconds: 30
```

For config consumed by other teams, generate the reference doc from the schema's `description` fields (`jsonschema2md`, `helm-docs`, or a short script) rather than maintaining prose that drifts.

### Formatting and linting in CI

| Tool                           | Target                        | Key settings                                                                                                                                                         |
| ------------------------------ | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Prettier                       | JSON, YAML, TOML, Markdown    | `"tabWidth": 2`, `"singleQuote": false`; run with `--check` in CI                                                                                                    |
| yamllint                       | YAML                          | `indentation: {spaces: 2, indent-sequences: true}`, `truthy: {allowed-values: ['true','false']}`, `key-duplicates: enable`, `comments: {min-spaces-from-content: 1}` |
| taplo                          | TOML                          | `taplo fmt --check`, `taplo lint`; schema validation via `#:schema` directives                                                                                       |
| `actionlint`                   | GitHub Actions workflows      | Catches expression and shellcheck errors YAML linting misses                                                                                                         |
| `gitleaks`                     | Any file, full history        | Blocks secrets at PR time                                                                                                                                            |
| `ajv-cli` / `check-jsonschema` | JSON/YAML against JSON Schema | `ajv validate -s schema.json -d config/*.yaml`                                                                                                                       |

```yaml
# .github/workflows/config-lint.yml
name: config-lint
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npx --yes prettier --check "**/*.{json,yaml,yml,toml}"
      - run: pipx run yamllint -c .yamllint.yaml .
      - run: npx --yes ajv-cli validate -s config/app.schema.json -d "config/app.yaml" --strict=true
      - uses: gitleaks/gitleaks-action@v2
```

### Generated files

Lockfiles, rendered manifests, and code-generated config are outputs. They are committed when reproducibility requires it (`package-lock.json`, `Cargo.lock`, `go.sum`) and gitignored when the build regenerates them deterministically. Either way they carry a generated-file header where the format allows it — `# Code generated by scripts/render-config.ts. DO NOT EDIT.` in YAML and TOML, a top-level `"$comment"` in JSON — and they are never hand-edited. If one must change, change its source and re-run the generator. A generator lost from the repo makes its output unmaintainable, so keep generators next to their templates.

## Common Mistakes

| Mistake                                             | Why It Breaks                                                                                                       | Correct Approach                                                                                           |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Unquoted `no`, `on`, `yes`, `off` as values         | YAML 1.1 parses them as booleans; a country code `NO` becomes `false` and a feature flag `on` becomes `true`        | Quote any value matching a YAML boolean word; enable yamllint's `truthy: allowed-values: ['true','false']` |
| Unquoted `1.10` or a date-like `2024-01-05`         | Version becomes float `1.1`; date becomes a datetime object in YAML 1.1, string in 1.2 — behavior differs by parser | Quote versions, dates, and any scalar with leading zeros                                                   |
| Tab characters for indentation                      | YAML forbids tabs; the parser error points at a misleading line, and the file is unloadable in every strict parser  | Two spaces; enforce with yamllint and an `.editorconfig` `indent_style = space`                            |
| Trailing comma in JSON                              | `{"a":1,}` is a syntax error in every spec-compliant parser, including `JSON.parse`                                 | Fix the generator or editor; never hand-edit JSON without a linter                                         |
| `NaN`/`Infinity` in JSON                            | Not in RFC 8259; `JSON.parse` throws, Python accepts by default, so the bug appears only at the consumer            | Serialize as `null` or a sentinel string; set `allow_nan=False` in Python                                  |
| Duplicate keys in one mapping                       | Last-wins in JS, first-wins in Python; the config means two different things in two runtimes                        | Add a duplicate-key lint rule; JSON Schema alone does not catch this                                       |
| Secrets in a committed config or Helm values file   | Credential is in git history forever, readable by anyone with repo access, and rotation requires a rewrite          | Inject from a secret manager at deploy; keep a `.env.example` with names only; run gitleaks in CI          |
| Shallow merge where deep was needed (or vice versa) | Nested keys silently vanish, or arrays grow into a union no one authored                                            | Decide merge semantics explicitly, document them, and unit-test the merge function                         |
| Config read lazily at first use                     | Missing or invalid keys surface as a production error mid-request instead of at startup                             | Load and validate the whole config at the composition root; exit non-zero on failure                       |
| `additionalProperties` omitted in the schema        | A typo'd key (`ttl_second`) is accepted silently and the default applies — the setting appears to have no effect    | Set `additionalProperties: false` and surface `e.params.additionalProperty` in the error                   |
| Same literal copied into three config files         | One copy is updated, the others drift; behavior differs per service with no test failing                            | One source of truth: shared include, generated file, or a CI assertion that the copies agree               |
| Hand-editing a generated or lock file               | Next regeneration silently reverts the change; the fix is lost at the next build                                    | Change the template or the generator input; re-run the generator                                           |
| JSON used for human-edited config                   | No comments, so keys are undocumented and defaults are invisible; readers guess                                     | YAML or TOML for anything a human maintains by hand                                                        |
| `z.coerce.boolean()` on an env var                  | JavaScript truthiness makes the string `"false"` coerce to `true`                                                   | Parse with an explicit `enum(["true","false"])` and transform, or compare against the exact literal        |

## Checklist

1. Confirm every config file uses the format its role dictates, and that no concern is expressed in two formats without a documented precedence rule.
2. Enumerate every YAML scalar matching a YAML 1.1 boolean word (`y`, `yes`, `on`, `no`, `off`, `n`) and confirm each is quoted or is genuinely intended as a boolean.
3. Check every version string, date, time-like value, and zero-padded number for quoting; flag any unquoted value that could coerce to a number, date, or sexagesimal.
4. Verify no tab characters appear in any YAML file and that indentation width is uniform across the repo (two spaces by convention).
5. Confirm anchors and merge keys (`<<`) are used only where every consuming tool supports them; replace cross-file or cross-tool reliance with a template.
6. Confirm `---` multi-document separators appear only in files whose consumers expect a document stream.
7. Validate every JSON file for comments, trailing commas, `NaN`/`Infinity`, duplicate keys, and integer IDs above 2^53.
8. Verify each config file has a schema, that the schema sets `additionalProperties: false` where the shape is closed, and that validation runs at startup and exits non-zero on failure.
9. Confirm schema `$id` values are versioned and that a breaking shape change ships a new schema version with a documented migration window.
10. Trace the precedence order of layered config and confirm it is documented and unit-tested, with explicit merge semantics for maps and arrays.
11. Confirm all configuration is read once at the composition root and passed as typed values, with no `process.env` / `os.environ` reads inside domain modules.
12. Verify environment-variable parsing is explicit for booleans, integers, and lists, and that malformed values fail startup rather than defaulting silently.
13. Scan for secrets in config files, Helm values, and git history (`gitleaks detect --no-git=false`); confirm a gitignored local file plus a committed `.env.example` with names only.
14. Confirm every key has a doc comment stating unit, default, and valid range, or that a reference doc is generated from the schema's `description` fields.
15. Identify values duplicated across two or more config files and confirm each has a single source of truth or a CI assertion that the copies agree.
16. Confirm Prettier `--check`, yamllint, taplo, and schema validation all run in CI and fail the build on violation.
17. Confirm generated files and lockfiles are never hand-edited, carry a generated-file header where the format permits, and can be reproduced by a generator kept in the repo.

## References

- YAML 1.2.2 Specification — https://yaml.org/spec/1.2.2/
- YAML 1.1 Type Repository: boolean coercion rules — https://yaml.org/type/bool.html
- YAML 1.1 Integer Type (sexagesimal) — https://yaml.org/type/int.html
- YAML Merge Key Type (YAML 1.1 only, absent from 1.2) — https://yaml.org/type/merge.html
- RFC 8259 — The JavaScript Object Notation (JSON) Data Interchange Format — https://www.rfc-editor.org/rfc/rfc8259
- JSON Schema draft 2020-12 core and validation — https://json-schema.org/draft/2020-12/json-schema-core.html · https://json-schema.org/draft/2020-12/json-schema-validation.html
- TOML v1.0.0 Specification — https://toml.io/en/v1.0.0
- The Twelve-Factor App, III. Config — https://12factor.net/config
- yamllint documentation (rules and configuration) — https://yamllint.readthedocs.io/en/stable/rules.html
- Prettier options reference — https://prettier.io/docs/options
- Taplo TOML toolkit — https://taplo.tamasfe.dev/
- Ajv JSON Schema validator — https://ajv.js.org/
- Python jsonschema documentation — https://python-jsonschema.readthedocs.io/en/stable/
- Pydantic v2 settings management — https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Zod coercion and `z.coerce` — https://zod.dev/?id=coercion
- Kubernetes ConfigMap and Secrets — https://kubernetes.io/docs/concepts/configuration/configmap/ · https://kubernetes.io/docs/concepts/configuration/secret/
- External Secrets Operator — https://external-secrets.io/latest/
- gitleaks secret scanning — https://github.com/gitleaks/gitleaks
- actionlint for GitHub Actions workflows — https://github.com/rhysd/actionlint
