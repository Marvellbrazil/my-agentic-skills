# Collation, Sorting, and String Comparison

Collation is the mapping from strings to a total order for a given locale: which characters are primary-equal (base
letters), secondary-equal (accents), tertiary-equal (case), and which sequences are contractions (`ch`, `ll`, `dzs`) or
expansions (`ä` → `a` + combining diaeresis). Getting it wrong is not cosmetic: an unlocalized `sort()` puts every non-
ASCII name at the end of a picker, a `WHERE name = @name` lookup misses an existing user and creates a duplicate, and a
`Set`-based dedupe silently merges two distinct records. The failure mode is always the same — code compares code units,
while users compare letters.

## Contents

- [When This Applies](#when-this-applies)
- [Codepoint order, the UCA, and DUCET](#codepoint-order-the-uca-and-ducet)
  - [The Unicode Collation Algorithm and DUCET](#the-unicode-collation-algorithm-and-ducet)
- [Comparison in the application layer](#comparison-in-the-application-layer)
  - [Intl.Collator and its options](#intlcollator-and-its-options)
  - [Searching and substring matching](#searching-and-substring-matching)
  - [Normalized comparison vs locale comparison](#normalized-comparison-vs-locale-comparison)
- [Database collations and the app/DB mismatch](#database-collations-and-the-appdb-mismatch)
- [Sorting numbers stored as strings, and tie-breaking](#sorting-numbers-stored-as-strings-and-tie-breaking)
- [Locale-aware equality for deduplication](#locale-aware-equality-for-deduplication)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- Any user-visible ordering: name and title lists, product catalogs, alphabetical index bars, "group by first letter" navigation, leaderboards.
- Any equality test used for lookup, uniqueness, deduplication, or upsert keys on human-entered text (names, cities, tags, company names).
- Search, autocomplete, typeahead, and filter boxes that match substrings rather than whole values.
- `ORDER BY` on a text column in any relational database, and any query whose sort order must agree with what the application renders.
- Sorting or comparing keys derived from user input with `toLowerCase()` / `toUpperCase()`, or with bare `<`, `>`, `===`,
  or `String.prototype.localeCompare` without arguments.
- Sorting values stored as strings that look numeric ("item 2" vs "item 10", "v1.9" vs "v1.10", sizes, prices with grouping separators).
- Migrating a database to a different collation, or comparing data across a database and a service that each collate differently.

## Codepoint order, the UCA, and DUCET

Every language runtime's default comparison is a code-unit (or code-point) comparison, and the order it produces is
_codepoint order_, not alphabetical order. The concrete consequences:

| Fact                                 | Consequence                                                                                                                                               |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `"Z"` is U+005A, `"a"` is U+0061     | In codepoint order all uppercase letters precede all lowercase ones: `["a","B"].sort()` yields `["B","a"]`                                                |
| `"é"` is U+00E9, beyond `"z"` U+007A | `["éclair","zebra"].sort()` yields `["zebra","éclair"]`                                                                                                   |
| `"Å"` is U+00C5, beyond `"z"`        | Swedish `["Åland","Zebra"]` sorts wrong; Norwegian and Danish `"Æ"`/`"Ø"` do too                                                                          |
| UTF-16 code units, not code points   | Any BMP character sorts before any astral character, so every CJK Extension B ideograph, emoji, and rare Han character lands after all Latin and most CJK |
| Canonical equivalence is invisible   | `"é"` as U+00E9 and as U+0065 U+0301 are different code-unit sequences that users read as identical                                                       |

The fix is never a hand-rolled `charCodeAt` offset. It is to route every comparison through a collator that knows the locale.

```javascript
["Zebra", "ähnlich", "Apple", "Åland"].sort();
// ["Apple", "Zebra", "Åland", "ähnlich"] — codepoint order, wrong in de and sv

const de = new Intl.Collator("de", { sensitivity: "variant" });
["Zebra", "ähnlich", "Apple", "Åland"].sort(de.compare);
// ["ähnlich", "Åland", "Apple", "Zebra"] — German: ä sorts with a
```

### The Unicode Collation Algorithm and DUCET

The Unicode Collation Algorithm (UCA, UTS #10) defines how two strings are compared, in three stages:

1. **Normalize** each string to NFD (canonical decomposition), so U+00E9 and `e` + U+0301 become the same sequence.
2. **Map** each character to one or more collation elements — typically three weights: primary (base letter), secondary
   (accent/diacritic), tertiary (case, and some script variants). Contractions consume several characters at once;
   expansions emit several collation elements for one character.
3. **Compare** weight by weight, primary first, then secondary, then tertiary.

The `sensitivity` option is exactly a choice of how many weight levels participate:

| `sensitivity` | Levels compared     | `"a"` vs `"á"` | `"a"` vs `"A"` | `"a"` vs `"b"` |
| ------------- | ------------------- | -------------- | -------------- | -------------- |
| `"base"`      | primary             | equal          | equal          | different      |
| `"accent"`    | primary + secondary | different      | equal          | different      |
| `"case"`      | primary + tertiary  | equal          | different      | different      |
| `"variant"`   | all                 | different      | different      | different      |

**DUCET** (Default Unicode Collation Element Table) is the locale-neutral table the UCA is defined against. It is a
starting point, not a shipping default: it puts `å` next to `a`, which is correct for German and wrong for Swedish. Real
locales are DUCET plus **tailorings** — ordered rules that reweight or reorder characters. The CLDR root locale defines
the default tailoring set, and each locale's `collation` data holds its own. The three behaviors a sorting
implementation must not guess at:

| Locale                      | `å` position          | `ö` position          | `ü` position |
| --------------------------- | --------------------- | --------------------- | ------------ |
| `de` (standard, DIN 5007-1) | with `a`              | with `o`              | with `u`     |
| `sv`                        | after `z`             | after `z` (after `å`) | with `y`     |
| `da`                        | after `z` (after `æ`) | after `z` (after `ø`) | with `y`     |

So `"Ö"` sorts into the `o` run in German, at the very end of the alphabet in Swedish, and near the end in Danish —
three different answers from one character, decided entirely by the collator's locale. A fourth axis is **phonebook vs
dictionary** tailoring: `de-u-co-phonebk` folds `ä` to `ae` so that `Müller` and `Mueller` interleave, while the default
dictionary tailoring keeps them apart. German phonebook collation is what a customer-facing directory usually wants;
German dictionary collation is what a code-signing key listing usually wants. They are not interchangeable.

The collation-specific subtag is passed with the `-u-co-` Unicode extension on the locale tag: `"de-u-co-phonebk"`,
`"sv-u-co-trad"`, `"zh-u-co-pinyin"`, `"ja-u-co-stroke"`. This is how you select a non-default collation for the same
language — `zh` offers `pinyin`, `stroke`, `zhuyin`, and others, and they produce completely different orders for the
same Han data.

## Comparison in the application layer

### Intl.Collator and its options

`Intl.Collator` is the platform primitive; every higher-level API (`localeCompare`, `Intl.ListFormat`, ICU-backed DB collations) either is it or mirrors it.

| Option              | Values                                             | Default                                                        | Effect                                                                                            |
| ------------------- | -------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `usage`             | `"sort"`, `"search"`                               | `"sort"`                                                       | Optimizes for a total order or for substring matching; changes which strings are considered equal |
| `sensitivity`       | `"base"`, `"accent"`, `"case"`, `"variant"`        | locale-dependent (`"variant"` for most)                        | Which weight levels count, per the table above                                                    |
| `ignorePunctuation` | `true`, `false`                                    | `false`                                                        | Ignore punctuation and whitespace at primary level, so `"e.g."` sorts with `"eg"`                 |
| `numeric`           | `true`, `false`                                    | `false`                                                        | Compare embedded digit runs by numeric value, so `"2"` < `"10"`                                   |
| `caseFirst`         | `"upper"`, `"lower"`, `"false"`                    | locale-dependent (`"false"` = use the locale's tertiary order) | Controls upper-vs-lower ordering when case is a tiebreaker                                        |
| `collation`         | e.g. `"phonebk"`, `"pinyin"`, `"stroke"`, `"trad"` | locale default                                                 | Selects a named tailoring                                                                         |

Two of these are load-bearing and easy to miss.

**`usage` is not a hint, it is a different equivalence relation.** With `usage: "search"`, strings that differ only in a
secondary or tertiary way can compare equal, so a comparison loop that uses `!== 0` to mean "not found" works while one
that uses `=== 0` to mean "same string" breaks. Use `"search"` for substring/prefix matching and `"sort"` for ordering
and for equality of identifiers.

**`caseFirst` interacts with `sensitivity`.** It is only observable at the tertiary level, so `caseFirst: "upper"` is a
no-op under `sensitivity: "base"` or `"accent"`. If you want `["a","B","b"]` to sort as `["B","a","b"]` you need
`sensitivity` at `"case"` or `"variant"` _and_ `caseFirst: "upper"`.

```javascript
const numeric = new Intl.Collator("en", { numeric: true });
["file10", "file2", "file1"].sort(numeric.compare);
// ["file1", "file2", "file10"]

const ignorePunct = new Intl.Collator("en", { ignorePunctuation: true });
ignorePunct.compare("e.g.", "eg"); // 0

const search = new Intl.Collator("de", {
  usage: "search",
  sensitivity: "base",
});
search.compare("Straße", "strasse"); // 0
const sortDe = new Intl.Collator("de", { sensitivity: "base" });
sortDe.compare("Straße", "strasse"); // non-zero: ß is not primary-equal to ss under sort usage
```

`Collator.prototype.resolvedOptions()` reports the options the engine actually applied, which is the only reliable way
to detect that a requested `collation` was unavailable and silently fell back. Assert on it in tests rather than
assuming.

Equivalent primitives elsewhere:

```python
import locale
locale.setlocale(locale.LC_COLLATE, "de_DE.UTF-8")
sorted(["Zebra", "ähnlich", "Apple"], key=locale.strxfrm)
# ['ähnlich', 'Apple', 'Zebra'] — ä sorts with a

import icu  # PyICU, backed by the same ICU data as Intl.Collator
coll = icu.Collator.createInstance(icu.Locale("sv_SE"))
coll.setStrength(icu.Collator.SECONDARY)  # accent-sensitive, case-insensitive
sorted(["Åland", "Zebra", "Öland"], key=coll.getSortKey)
# ['Zebra', 'Åland', 'Öland'] — Swedish: å and ö after z
```

```php
<?php
$c = new Collator('de_DE');
$c->setStrength(Collator::PRIMARY);
$c->setAttribute(Collator::NUMERIC_COLLATION, Collator::ON);
$c->compare('ähnlich', 'ahnlich'); // 0
$c->compare('Datei10', 'Datei2');  // 1 — numeric ordering, 10 > 2
```

`locale.strxfrm` is correct only after `setlocale` succeeds — it raises or silently keeps `C` collation when the locale
is not installed on the host, which is the single most common way Python i18n sorting breaks in containers. PyICU does
not depend on system locales and carries its own ICU data, which is why it is the safer choice for server code.

Java and Rust:

```java
import java.text.Collator;
import java.util.Locale;

Collator sv = Collator.getInstance(Locale.forLanguageTag("sv"));
sv.setStrength(Collator.SECONDARY);
// Swedish: Åland sorts after Zebra
```

`java.text.Collator.getInstance` honors the same locale and strength model but is **not** guaranteed to match ICU
weight-for-weight unless the JDK is configured with CLDR data and a matching ICU version. Cross-runtime agreement
requires pinning the same CLDR version, not just the same locale tag.

### Searching and substring matching

`usage: "search"` exists because ordering and matching have different equivalence needs. Matching a query against a
corpus should treat `"Muller"`, `"Müller"`, and `"MUELLER"` as hits for the same intent; ordering them should not.

```javascript
const matcher = new Intl.Collator("en", {
  usage: "search",
  sensitivity: "base",
});

function includesLocale(haystack, needle) {
  const h = Array.from(haystack);
  const n = Array.from(needle);
  if (n.length === 0) return true;
  outer: for (let i = 0; i + n.length <= h.length; i++) {
    for (let j = 0; j < n.length; j++) {
      if (matcher.compare(h[i + j], n[j]) !== 0) continue outer;
    }
    return true;
  }
  return false;
}

includesLocale("Café Zürich", "zurich"); // true
```

Two constraints on that pattern. First, it must iterate code points (`Array.from`) rather than code units, or surrogate
pairs get split and the comparison degenerates. Second, it is quadratic: O(n·m) collator calls. For real corpora,
precompute a folded search key and use a normal index.

`Intl.Collator.prototype.compare` is not a sort key. It is a comparison function, and calling it O(n log n) times per
sort is the expected cost. Where the same values are compared repeatedly, a **sort key** is a byte string whose byte
order equals collation order, so it can be compared with plain `memcmp` and, critically, stored in a database index:

JavaScript's `Intl` does not expose sort keys, so the key trick is available only through a database collation, an ICU
binding with `getSortKey` (PyICU, `RuleBasedCollator` in Java), or the folding approach below.

```python
import unicodedata

def search_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))

search_key("Café Zürich")  # 'cafe zurich'
```

### Normalized comparison vs locale comparison

These answer different questions and are routinely confused.

| Question                                                   | Correct tool                                                 | Why                                                                                                                                                              |
| ---------------------------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Are these the same identifier/email/hostname/slug?         | Normalize (NFKC or NFC) + casefold, then compare code points | Identifiers are machine tokens; two spellings that differ only by compatibility characters are the same token, and locale tailoring must not merge distinct ones |
| Do these two display names look the same to a German user? | `Intl.Collator("de", { sensitivity: "base" })`               | Correctness is defined by the reader's expectations, not by bytes                                                                                                |
| Will these two strings sort into the same place?           | Collator with `usage: "sort"` and an explicit `sensitivity`  | Only a sort-usage collator gives a total order                                                                                                                   |
| Does this query match this text?                           | Collator with `usage: "search"`                              | Search equivalence is broader than sort equivalence                                                                                                              |

The rule: **normalize for identity, collate for presentation.** Storing a locale-folded value as a primary key is a bug,
because the fold is locale-dependent — the same input folds differently under `de` and `tr`, so the key changes when the
locale changes. Store the canonical form (NFC or NFKC, per your identifier rules) plus, if you need fast locale-aware
lookup, a _separate_ derived column for the folded search key. Normalization rules themselves, and the grapheme/word
segmentation this section assumes, are covered in [intl-text-processing.md](intl-text-processing.md).

**Use normalization, not `toLowerCase()`, for identifiers.** `toLowerCase()` and `toUpperCase()` are locale-independent
in JavaScript (`toLocaleLowerCase` takes the locale), and both are lossy in ways that break identity:

- They are not inverse operations. `"İ".toLowerCase()` is `"i̇"` (two code points), and `"ß".toUpperCase()` is `"SS"` (two characters). Neither round-trips.
- `toLowerCase` changes string length for some inputs, so any code that indexes by position after folding is wrong.
- Case folding is not lowercasing. Unicode case folding (`casefold()`, `toCaseFold`) is the identity-preserving operation
  for caseless comparison; Turkish `I`/`ı` and German `ß` are handled by the fold, not by a naive lower.
- For caseless _identity_, apply NFKC **then** casefold: `str.casefold()` after `unicodedata.normalize("NFKC", s)`. The
  order matters because NFKC can introduce new cased characters.

The Turkish dotless i is the canonical trap. In `tr` and `az`, `"I"` lowercases to `"ı"` (U+0131, dotless) and `"i"`
uppercases to `"İ"` (U+0130, dotted). A locale-independent `toLowerCase()` therefore produces a string that Turkish
users consider wrong, and a comparison of `"Istanbul"` against a user-typed `"istanbul"` behaves differently under `tr`
than under `en`. For identifiers, do not use locale-sensitive casing at all — use `toLowerCase()` (locale-independent)
plus NFKC, and document that Turkish `I` folds to `i` in your identifier space even though it does not in Turkish text.

## Database collations and the app/DB mismatch

A database collation governs `ORDER BY`, `=`, `LIKE`, `GROUP BY`, `DISTINCT`, unique indexes, and range predicates on
text. It is chosen at column, table, database, or cluster level, and it is frequently not the collation your application
runtime uses. The mismatch shows up as three specific bugs: rows that the DB considers duplicates but the app considers
distinct (or vice versa), a page of results whose order does not match the sort indicator, and pagination that skips or
repeats rows because the two orderings disagree about ties.

| System     | Setting                                                                                                | Notes                                                                                                                                                                                                      |
| ---------- | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PostgreSQL | `lc_collate` / `lc_ctype` at `initdb`/database level; `COLLATE "de-DE-x-icu"` per column/expression    | The legacy `libc` provider's ordering changes with the host's glibc version, so the same query returns a different order after an OS upgrade; the `icu` provider (`provider = icu`) is stable across hosts |
| PostgreSQL | `CREATE COLLATION german (provider = icu, locale = 'de-u-co-phonebk')`                                 | Locale tags carry the same `-u-co-` collation extension as `Intl.Collator`                                                                                                                                 |
| MySQL 8.0  | `utf8mb4_0900_ai_ci` — accent-insensitive, case-insensitive                                            | `ai`/`ci` is why `WHERE name = 'Jose'` matches `'José'`; `_bin` and `_as_cs` variants do not                                                                                                               |
| MySQL 8.0  | `utf8mb4_0900_as_cs`                                                                                   | Accent-sensitive, case-sensitive — the choice for identifier columns                                                                                                                                       |
| SQL Server | `COLLATE Latin1_General_100_CI_AS` on the column; `SQL_Latin1_General_CP1_CI_AS` is the legacy default | SQL Server's `_CI_AS` default also affects `=` and unique indexes, not just ordering                                                                                                                       |
| MongoDB    | `db.createCollection(..., { collation: { locale: "de", strength: 2 } })`, per-query `collation` option | `strength` is the ICU strength level: 1 = primary (base), 2 = secondary (accent), 3 = tertiary (case/variant)                                                                                              |

The `ai_ci` default in MySQL 8.0 is the highest-traffic source of accidental merges: an email or username column created
without an explicit collation will treat `user@example.com` and `USER@example.com` as the same value in a unique index,
which may be what you want for email and is almost never what you want for a case-sensitive token. Audit every text
column that carries a unique constraint and set its collation deliberately.

Conversely, `_bin`/`_as_cs` on a display-name column produces the reverse bug: a search box that uses the app's accent-
insensitive collator matches more rows than the database index can serve, so the query falls back to a scan, or worse,
the app filters in memory and the pagination count is computed from the wrong set.

The durable rule: **decide which layer owns ordering, and make the other layer defer.** If the database owns it, use a
database collation that matches the locale the UI displays and never re-sort in the application. If the application owns
it, fetch the full set (or use a stored, folded sort key column), sort once in the application with an explicit
collator, and paginate after sorting. Mixing the two — `ORDER BY name LIMIT 20 OFFSET 40` followed by an in-app
`sort(collator.compare)` — produces pages that overlap and rows that never appear.

## Sorting numbers stored as strings, and tie-breaking

Numeric text sorts lexicographically by default, which is wrong for versions, sizes, durations, and any "item N" label.
Fixes, in order of preference: store a real numeric type; store a zero-padded sort key; or use `numeric: true` on the
collator / `NUMERIC_COLLATION` in PHP / `utf8mb4_0900_...` numeric-aware DB collations. Note that `numeric: true`
compares _runs of digits_ numerically, so `"v1.9"` and `"v1.10"` compare correctly as version strings, but `"1,000"` and
`"1000"` do not compare equal because the separator is punctuation — combine with `ignorePunctuation` if that is the
intent, and be aware that doing so also merges genuinely different values.

Sorting must also be **stable**, or equal elements reorder unpredictably and pagination breaks. ECMAScript
`Array.prototype.sort` is stable as of ES2019, and Python's `sorted`/`list.sort` are stable; the SQL standard is not,
and no database guarantees the relative order of rows that compare equal. Always add a unique tiebreaker to every
ordered query and every in-app sort of display data:

```sql
SELECT id, name FROM users ORDER BY name COLLATE "de-DE-x-icu", id;
```

```javascript
const coll = new Intl.Collator("sv");
rows.sort((a, b) => coll.compare(a.name, b.name) || a.id - b.id);
```

Without the tiebreaker, two rows with the same name can swap between the first and second page of results, so a user
scrolling a list sees one item twice and never sees another. This is a pagination bug that looks like a caching bug and
is neither.

## Locale-aware equality for deduplication

Deduplication needs a decision about what "same" means, made explicitly and applied consistently at both the app and the storage layer.

| Intent            | Key function                                                      | Collapses                                          | Keeps distinct         |
| ----------------- | ----------------------------------------------------------------- | -------------------------------------------------- | ---------------------- |
| Exact token       | `normalize("NFKC", s)`                                            | Compatibility variants, e.g. fullwidth `Ａ` vs `A` | `a` vs `A`, `e` vs `é` |
| Caseless token    | NFKC + casefold                                                   | `a` vs `A`, `ß` vs `ss`                            | `e` vs `é`             |
| Reader-equivalent | `Intl.Collator(locale, { sensitivity: "base" })`                  | `e` vs `é`, `a` vs `A`                             | `a` vs `b`             |
| Search-equivalent | `Intl.Collator(locale, { usage: "search", sensitivity: "base" })` | Also `Straße` vs `Strasse` in `de`                 | Script-distinct values |

```javascript
function dedupeByName(rows, locale) {
  const coll = new Intl.Collator(locale, { sensitivity: "base" });
  const seen = new Map();
  for (const row of rows) {
    const key = row.name.normalize("NFC");
    let bucket = null;
    for (const k of seen.keys()) {
      if (coll.compare(k, key) === 0) {
        bucket = k;
        break;
      }
    }
    if (bucket === null) seen.set(key, [row]);
    else seen.get(bucket).push(row);
  }
  return seen;
}
```

That linear scan is correct but O(n²); for real volumes, bucket by a folded key first, then resolve within the bucket.
And never use `Object`/`Map` keyed by the raw string as the dedupe key if the intent is reader-equivalence — the map's
equality is code-unit equality, which is exactly the thing that is wrong.

## Common Mistakes

| Mistake                                                          | Why It Breaks                                                                                                                                             | Correct Approach                                                                                          |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `arr.sort()` with no comparator on display text                  | Code-unit order puts `"Z"` before `"a"` and all non-ASCII after all ASCII                                                                                 | `arr.sort(new Intl.Collator(locale).compare)`                                                             |
| `a.name.localeCompare(b.name)` with no locale or options         | Uses the runtime default locale, which differs between the server's `LANG`, the browser, and CI; also defaults to a sensitivity that may not match intent | Pass locale and options explicitly: `new Intl.Collator(locale, { sensitivity, numeric })`                 |
| Constructing a collator inside the comparator or inside a loop   | Each construction reparses locale data; a sort of 10k rows constructs the collator 10k+ times                                                             | Hoist the collator out of the comparator, once per locale                                                 |
| `ORDER BY name` without a tiebreaker                             | Rows that compare equal have unspecified relative order, so pages overlap and rows go missing                                                             | `ORDER BY name <collation>, id`                                                                           |
| Assuming `ORDER BY` agrees with the app's sort                   | The DB collation and the runtime collator are independent settings; ties and accents resolve differently                                                  | Pick one owner for ordering; if the DB owns it, do not re-sort in the app                                 |
| Using `toLowerCase()` for case-insensitive identity              | Not inverse-safe (`ß` → `SS`), changes length, and is not case folding                                                                                    | `unicode.normalize("NFKC", s).casefold()` in Python; NFKC + `toLowerCase()` in JS                         |
| `new Set(names)` or a `Map` keyed by raw strings for "same name" | Code-unit equality: `"José"` and `"JOSÉ"` are distinct keys                                                                                               | Normalize, then compare with a collator at the intended sensitivity                                       |
| Assuming `ignorePunctuation` is on                               | It defaults to `false`, so `"e.g."` sorts far from `"eg"`                                                                                                 | Set `ignorePunctuation: true` explicitly when punctuation should not affect order                         |
| Expecting `caseFirst: "upper"` to work with default sensitivity  | `caseFirst` acts at the tertiary level; `sensitivity: "base"`/`"accent"` discards it                                                                      | Pair `caseFirst` with `sensitivity: "case"` or `"variant"`                                                |
| Sorting numeric-looking strings lexicographically                | `"item10"` sorts before `"item2"`                                                                                                                         | `numeric: true`, a zero-padded key column, or a numeric type                                              |
| Treating `Intl.Collator.compare` as producing a sort key         | It is a comparator; there is no key to store or index                                                                                                     | Use a DB/ICU collation or a stored folded key column for indexed ordering                                 |
| Trusting `libc` collation to be stable across hosts              | Ordering changes with the glibc version, so the same query reorders after an OS upgrade                                                                   | Use ICU-provider collations in Postgres, or pin the OS image                                              |
| Storing a locale-folded value as a primary key                   | The fold is locale-dependent, so the key changes if the locale changes                                                                                    | Store the canonical (NFC/NFKC) form as the key; keep the folded form in a derived column                  |
| Locale-independent `toLowerCase()` on Turkish data               | `"I"` does not fold to `"ı"`, and `"i"` does not uppercase to `"İ"` under `tr`                                                                            | For identifiers use locale-independent folding and document it; for display use `toLocaleLowerCase("tr")` |
| Using `usage: "search"` for equality of identifiers              | Search equivalence is broader, so distinct tokens can compare equal                                                                                       | `usage: "sort"` (the default) for equality and ordering                                                   |

## Checklist

1. Locate every `sort()`, `sorted()`, `usort`, `ORDER BY`, and comparator in the codebase and classify each as ordering
   display text, ordering machine tokens, or ordering numbers — then confirm each has a collator or a numeric type
   appropriate to that class.
2. Verify every user-visible sort passes an explicit locale and an explicit `sensitivity`; flag any call site relying on
   the runtime default locale or on `localeCompare` with no arguments.
3. Confirm no `Intl.Collator` (or `Collator`, `icu.Collator`, `RuleBasedCollator`) is constructed inside a comparator, a
loop body, or a per-row function; each should be hoisted and reused.
4. For each locale the product claims to support, assert the expected order of a fixture containing that locale's
special letters — `å`/`ä`/`ö` for `sv` and `de`, `æ`/`ø` for `da`/`no`, `ß` for `de`, `ı`/`İ` for `tr` — against a
hardcoded expected array, not against another collator.
5. Check every `ORDER BY` on a text column for a unique tiebreaker column, and confirm the tiebreaker is unique (not merely indexed).
6. Determine whether the application or the database owns ordering for each list, and verify the other layer does not
re-sort; flag any `ORDER BY ... LIMIT/OFFSET` followed by an in-app sort.
7. Read the effective collation of every text column carrying a `UNIQUE` constraint or used as a lookup key, and confirm
it is the intended sensitivity (`_bin`/`_as_cs`/ICU locale) rather than an inherited default such as
`utf8mb4_0900_ai_ci`.
8. Verify that any per-query `COLLATE` clause names a collation that exists in the target server version, and that
Postgres collations are ICU-provider or otherwise pinned to a host-independent definition.
9. Search for `toLowerCase()`, `toUpperCase()`, `toLocaleLowerCase`, and `lower()` applied to values used in
comparisons, keys, or uniqueness checks, and replace each with normalization plus case folding.
10. Check that numeric-looking string columns (versions, sizes, "item N" labels, prices with separators) are ordered
with `numeric: true`, a padded sort key, or a real numeric type — and confirm the three agree.
11. Confirm deduplication uses an explicit equivalence choice: a normalized-and-folded key for tokens, or a collator
bucket at a stated sensitivity for reader-equivalence; flag any `Set`/`Map`/`distinct` over raw strings whose intent is
"same name".
12. Verify substring and prefix search uses `usage: "search"` with `sensitivity: "base"`, iterates code points rather
than code units, and does not run an O(n·m) collator loop over a large corpus.
13. Test with a locale whose host data may be absent (`locale -a` in the container), and confirm the code fails loudly
or falls back to a documented behavior rather than silently collating as `C`/`POSIX`.
14. Assert on `resolvedOptions()` for each requested collator, so a silently ignored `collation` (for example `phonebk`
on an engine that lacks it) surfaces in tests rather than in production output.
15. Add a regression fixture of the locale's special characters to the test suite and run it under the same runtime and
CLDR/ICU version as production; record the versions alongside the expected order.
16. Verify any stored derived sort or search key is regenerated when its source column changes, and that its generating
function is versioned so a fold-rule change can be detected and backfilled.

## References

- Unicode Standard Annex #10, Unicode Collation Algorithm — https://www.unicode.org/reports/tr10/
- Unicode Technical Standard #35, LDML, Part 5: Collation (locale tailorings and options) — https://www.unicode.org/reports/tr35/tr35-collation.html
- Unicode Technical Standard #35, Part 3: Unicode Language and Locale Identifiers (`-u-co-` extension) — https://www.unicode.org/reports/tr35/tr35.html
- Unicode Standard Annex #15, Unicode Normalization Forms — https://www.unicode.org/reports/tr15/
- Unicode Default Collation Element Table (DUCET) — https://www.unicode.org/Public/UCA/latest/allkeys.txt
- CLDR collation data per locale — https://github.com/unicode-org/cldr/tree/main/common/collation
- ECMA-402, `Intl.Collator` — https://tc39.es/ecma402/#collator-objects
- MDN, `Intl.Collator` — https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/Collator
- MDN, `String.prototype.localeCompare` — https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/localeCompare
- ICU Collation Service API — https://unicode-org.github.io/icu/userguide/collation/
- PostgreSQL, Collation (ICU and libc providers) — https://www.postgresql.org/docs/current/collation.html
- MySQL, Unicode Character Sets and `utf8mb4_0900_ai_ci` — https://dev.mysql.com/doc/refman/8.0/en/charset-unicode-sets.html
- Microsoft SQL Server, Collation and Unicode Support — https://learn.microsoft.com/en-us/sql/relational-databases/collations/collation-and-unicode-support
- MongoDB, Collation — https://www.mongodb.com/docs/manual/reference/collation/
- Python `locale.strxfrm` and `locale.setlocale` — https://docs.python.org/3/library/locale.html
- Python `str.casefold` — https://docs.python.org/3/library/stdtypes.html#str.casefold
- PyICU (ICU bindings, `Collator.getSortKey`) — https://pyicu-docs.readthedocs.io/
- PHP `Collator` — https://www.php.net/manual/en/class.collator.php
- Java `java.text.Collator` — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/text/Collator.html

