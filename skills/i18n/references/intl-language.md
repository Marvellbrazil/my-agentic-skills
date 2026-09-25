# Language Tags, Locales, and Language Negotiation

This module covers BCP 47 language tags: how to parse, validate, and canonicalize them; what each subtag position means;
how a server maps an `Accept-Language` header onto available content; and what to persist about a user's language.
Getting it wrong is not cosmetic. A bare `en` silently resolves to US conventions, a `zh-Hant` user is served Simplified
text, and an ICU Lookup that returns `""` instead of a match becomes a null dereference or a 500 because the caller
assumed a match always exists.

## When This Applies

- The codebase reads or writes `Accept-Language` or `Content-Language`, or accepts a per-request `locale`/`lang` parameter.
- A locale is stored per user (database column, cookie, `localStorage`, JWT claim, tenant config) or passed as `?lang=`.
- The application selects a translation bundle, message catalog, or template by tag.
- A library is called with a locale identifier: `Intl.*`, `babel`, ICU `Locale`/`ULocale`, Java `java.util.Locale`, PHP
  `Locale`, .NET `CultureInfo`, Go `golang.org/x/text/language`.
- Chinese, Serbian, Azerbaijani, Punjabi, Kurdish, Hausa, or any other multi-script language is in the supported set.
- The UI offers a language picker, or infers language from geo-IP or browser settings.
- A URL scheme, CDN cache key, or `Vary` header depends on the active language, or locale identifiers cross a boundary
  between systems that disagree on format (POSIX `en_US.UTF-8` vs BCP 47 `en-US` vs ICU `en_US`).

## Anatomy of a BCP 47 Language Tag

RFC 5646 defines the `langtag` production. Order is fixed; everything after `language` is optional.

```
 langtag    = language
              ["-" script]      ; 4ALPHA, ISO 15924
              ["-" region]      ; 2ALPHA / 3DIGIT (UN M.49)
              *("-" variant)    ; 5*8alphanum / (DIGIT 3alphanum)
              *("-" extension)  ; singleton 1*("-" (2*8alphanum))
              ["-" privateuse]  ; "x" 1*("-" (1*8alphanum))

 language   = 2*3ALPHA ["-" extlang] / 4ALPHA / 5*8ALPHA
 singleton  = DIGIT / A-W / Y-Z / a-w / y-z   ; "x" reserved
```

Position is inferred from length, not from a label: a 4-letter subtag right after the language is always a script, and a
2-letter or 3-digit subtag after that is always a region. This is why `en-Latn-US` and `en-US-Latn` are not equivalent —
the second is well-formed only because `Latn` can also occupy a variant position, and it means something different.

| Tag                          | Breakdown                         | Note                                |
| ---------------------------- | --------------------------------- | ----------------------------------- |
| `en`                         | language only                     | Maximizes to `en-Latn-US`           |
| `en-GB`                      | lang + region                     | CLDR parent is `en-001`, not `en`   |
| `en-001` / `en-150`          | lang + UN M.49 "World" / "Europe" | `en-150`'s parent is `en-001`       |
| `zh-Hant-TW`                 | lang + script + region            | Traditional, Taiwan                 |
| `sr-Latn-RS`                 | lang + script + region            | Serbian in Latin script             |
| `sl-rozaj-biske`             | lang + two variants               | Variants are semantically unordered |
| `de-1901`                    | lang + digit-led variant          | Orthography variant                 |
| `en-US-u-ca-gregory-nu-latn` | lang + region + `-u-` extension   | Calendar and numbering system       |

### Script subtags: why they are not optional

Script is the most damaging subtag to drop, because dropping it changes _which text_ a user reads, not merely how it is
formatted. `Latn` covers `en`, `de`, `sr` (alternate), `az` (default), `uz`; `Cyrl` covers `ru`, `sr` (default), `kk`
(default), `uk`, `bg`, `mn`; `Arab` covers `ar`, `fa`, `ur`, `ps`, `ckb` plus `az` and `pa` alternates; `Hans` covers
mainland `zh` and `zh-SG`; `Hant` covers `zh-TW`, `zh-HK`, `zh-MO`.

**Chinese.** `zh` is not a script-neutral default. CLDR `likelySubtags` maps `zh` → `zh-Hans-CN` and `und-Hant` → `zh-
Hant-TW`, so a `zh-Hant` user whose bundle key is `zh` receives Simplified text. Hong Kong and Macau differ from Taiwan
even within Traditional script, and CLDR encodes this: `zh-Hant-MO` → `zh-Hant-HK`.

**Serbian.** `sr` defaults to `sr-Cyrl-RS`; `sr-Latn` defaults to `sr-Latn-RS`. Same language, two alphabets. Note that
`sr-ME` maximizes to `sr-Latn-ME` — the script flips relative to `sr`, so region alone is insufficient information.
Serbian is not RTL in either script; do not infer direction from its `Arab`-script relatives.

```js
new Intl.Locale("zh").maximize().baseName; // zh-Hans-CN
new Intl.Locale("zh-Hant").maximize().baseName; // zh-Hant-TW
new Intl.Locale("sr").maximize().baseName; // sr-Cyrl-RS
new Intl.Locale("sr-ME").maximize().baseName; // sr-Latn-ME
new Intl.Locale("und-Hant").maximize().baseName; // zh-Hant-TW
```

### Language vs locale vs region vs market

Four different things; conflating them causes both bugs and compliance problems.

- **Language** (`en`, `zh`, `pt`) selects the message catalog. It answers "which words?"
- **Locale** (language + script + region + variants + extensions) selects formatting behavior and usually also the
  catalog. It answers "which words, in which conventions?"
- **Region** (`US`, `GB`, `419`, `001`) is a geographic or macro-geographic area driving currency, measurement system,
  date order, and week start. `419` (UN M.49 Latin America and the Caribbean) is a real usable code, not a placeholder.
- **Market** is commercial: a country or group where you sell. It is not a BCP 47 subtag. A market may imply a default
  locale (`es-419`), but never store a market as if it were a locale. `en-001` and `en-150` are regions, not markets.

`en` vs `en-US` vs `en-GB` is the canonical proof that a language tag alone is insufficient. All three are English; the conventions differ:

| Locale  | `dateStyle:"short"` | `timeStyle:"short"` | Week starts            | `getHourCycles()` |
| ------- | ------------------- | ------------------- | ---------------------- | ----------------- |
| `en-US` | `3/5/24`            | `2:30 PM`           | Sunday (`firstDay: 7`) | `["h12"]`         |
| `en-GB` | `05/03/2024`        | `14:30`             | Monday (`firstDay: 1`) | `["h23"]`         |
| `en-IN` | `05/03/24`          | `2:30 pm`           | Sunday                 | `["h12"]`         |

`en-GB` groups numbers identically to `en-US` (`1,234,567.89`) but renders `USD` as `US$1,234.50` rather than
`$1,234.50` — the currency _symbol_ is locale-dependent even when the currency code is fixed. Conversely `en-US` renders
`GBP` as `£1,234.50`. Number and currency mechanics belong to [intl-number-and-currency.md](intl-number-and-
currency.md); the region subtag is what carries them.

```js
const d = new Date(Date.UTC(2024, 2, 5, 14, 30));
const o = { dateStyle: "short", timeZone: "UTC" };
new Intl.DateTimeFormat("en-US", o).format(d); // 3/5/24
new Intl.DateTimeFormat("en-GB", o).format(d); // 05/03/2024
new Intl.Locale("en-GB").getWeekInfo(); // firstDay 1, weekend [6,7]
```

## Parsing, Validating, and Canonicalizing

Three distinct operations; production code needs all three.

1. **Structural validation** — does the string match the BCP 47 grammar? `en_US` fails (underscore); `en-US` passes.
2. **Registry validation** — are the subtags in the IANA Language Subtag Registry? `xx-YY` is structurally valid but semantically meaningless.
3. **Canonicalization** — replace deprecated subtags with preferred values, fix case, drop redundant subtags.

Most libraries do (1) and (3) but skip (2), or vice versa. Know which one you are calling.

### JavaScript / TypeScript

`Intl.getCanonicalLocales()` throws `RangeError` on a structurally invalid tag; `Intl.Locale` additionally exposes parsed subtags.

```js
Intl.getCanonicalLocales("EN-US"); // ["en-US"]
Intl.getCanonicalLocales("iw"); // ["he"]  — alias resolved
Intl.getCanonicalLocales("en_US"); // throws RangeError
Intl.getCanonicalLocales("en-GB-oed"); // throws (grandfathered)
new Intl.Locale("zh-Hant-TW").minimize().baseName; // zh-TW
```

`-u-` extension keywords become typed properties and re-emit in canonical key order. Locale data accessors were migrated
to methods because a fresh object per access made `locale.weekInfo === locale.weekInfo` false — both spellings exist in
the wild, and `minimalDays` may be absent even where specified:

```js
const u = new Intl.Locale("en-US-u-nu-latn-ca-gregory");
u.calendar; // gregory
u.numberingSystem; // latn
u.toString(); // en-US-u-ca-gregory-nu-latn
new Intl.Locale("ar").getTextInfo(); // { direction: "rtl" }
new Intl.Locale("ar").textInfo; // legacy accessor, same value
new Intl.Locale("en-GB").getWeekInfo(); // firstDay 1
new Intl.Locale("en-GB").getHourCycles(); // ["h23"]
new Intl.Locale("ar-EG").getNumberingSystems(); // ["arab"]
```

Do not expect variant order to round-trip: `new Intl.Locale("sl-rozaj-biske").toString()` yields `"sl-biske-rozaj"`, and
`l.variants` returned `undefined` on Node 24 (V8 13.6) despite being specified. Treat variants as a set and compare
canonical forms.

### Python, PHP, Java, Go

**Python (`babel`)** uses underscore identifiers and exposes direction directly. `Locale.parse` defaults
`resolve_likely_subtags=True`, so an unrecognized-but-parseable tag is silently filled in from CLDR:
`Locale.parse('und', sep='-')` returns `Locale('en', territory='US')`. With `resolve_likely_subtags=False` that same
call raises `UnknownLocaleError`. `babel` exposes no `maximize()` method; read the likely-subtags table directly via
`babel.core.get_global('likely_subtags')`, which maps `zh` → `zh_Hans_CN`, `sr` → `sr_Cyrl_RS`, and `und_Hant` →
`zh_Hant_TW`.

```python
from babel import Locale
from babel.core import get_global, negotiate_locale

Locale.parse('ar-SA', sep='-').text_direction  # 'rtl'
Locale.parse('ar-SA', sep='-').character_order  # 'right-to-left'
Locale.parse('und', sep='-')  # Locale('en', territory='US')
get_global('likely_subtags')['sr']  # 'sr_Cyrl_RS'
negotiate_locale(['de_DE', 'en_US'], ['de_DE', 'de_AT'])  # 'de_DE'
```

**PHP (`Locale`)** wraps ICU with underscore identifiers, and `canonicalize()` does **not** resolve aliases — the most surprising divergence from JavaScript.

```php
Locale::canonicalize("EN-us");   // "en_US"
Locale::canonicalize("iw");      // "iw"   — NOT "he"
Locale::canonicalize("sh");      // "sh"   — NOT "sr-Latn"
Locale::isRightToLeft("ar");     // true
Locale::addLikelySubtags("zh");  // "zh_Hans_CN"
Locale::minimizeSubtags("zh-Hant-TW"); // "zh_TW"
```

ICU documents the superseded identifiers it deliberately does **not** remap: `no => nb`, `iw => he`, `id => in`.
JavaScript's `Intl.getCanonicalLocales("iw")` returns `["he"]`; PHP's returns `"iw"`. Normalize at your own boundary
rather than trusting either.

**Java (`java.util.Locale`)** is deliberately lenient: `forLanguageTag` parses well-formed tags without registry
validation and silently drops malformed input instead of throwing. Use `Locale.Builder` when you need a hard failure.

```java
Locale.forLanguageTag("EN-us").toLanguageTag(); // "en-US"
Locale.forLanguageTag("iw").toLanguageTag(); // "he"
Locale.forLanguageTag("EN_US").toLanguageTag(); // "und"
Locale.forLanguageTag("xx-YY").toLanguageTag(); // "xx-YY"
new Locale.Builder().setLanguageTag("EN_US"); // throws
```

Java also synthesizes Unicode extensions for two legacy cases: `ja-JP-x-lvariant-JP` becomes `ja-JP-u-ca-japanese-x-
lvariant-JP`, and `th-TH-x-lvariant-TH` becomes `th-TH-u-nu-thai-x-lvariant-TH`.

**Go (`golang.org/x/text/language`)** canonicalizes on `Parse`; `Make` never fails while `Parse` does, so use `Parse` at
trust boundaries. `language.Parse("zh-Hant-TW")` then `t.Raw()` yields `"zh"`, `"Hant"`, `"TW"`;
`language.Parse("en_US")` accepts the underscore and returns `en-US`; `language.Parse("iw")` returns `he`;
`language.Make("zh").Script()` returns `Hans` with `language.Low` confidence, because the script was inferred rather
than explicit.

## Language Negotiation

Negotiation maps a _language priority list_ (what the client wants) onto _available tags_ (what you have). RFC 4647
defines the matching schemes; RFC 9110 §12.5.4 defines the HTTP carrier.

### Accept-Language grammar and q-factors

```
Accept-Language = #( language-range [ weight ] )
language-range  = <language-range, see RFC 4647 §2.1>
weight          = OWS ";" OWS "q=" qvalue
qvalue          = ( "0" [ "." 0*3DIGIT ] )
                / ( "1" [ "." 0*3("0") ] )
```

Consequences that matter in code:

- At most three digits after the decimal point. `q=0.3333` is invalid.
- An absent `q` defaults to `1`. It does not mean "unspecified" and not "lowest".
- `q=0` means **not acceptable**, not "least preferred". `en;q=0, fr` rejects English outright. Filter `q=0` out; do not rank it last or coerce it to `0.0001`.
- RFC 9110 states recipients "cannot be relied upon" to treat listing order as priority when `q` values tie. Many agents
  assign distinct `q` values _and_ list descending. Sort by `q` descending and use original order only as a stable
  tiebreak.
- `*` matches any tag not explicitly named by another range in the same list. It is not "anything at all" when a specific range is also present.

For `Accept-Language: da, en-gb;q=0.8, en;q=0.7`: Danish `1.0`, British English `0.8`, any other English `0.7`.

```js
function parseAcceptLanguage(header) {
  const out = [];
  for (const entry of header.split(",")) {
    const [range, ...params] = entry.trim().split(";");
    const qp = params.find((p) => p.trim().startsWith("q="));
    const q = qp ? Number.parseFloat(qp.split("=")[1]) : 1;
    if (q > 0) out.push({ range: range.toLowerCase(), q });
  }
  return out.sort((a, b) => b.q - a.q);
}
parseAcceptLanguage("en;q=0, fr"); // [{ range: "fr", q: 1 }]
```

### Lookup vs Basic Filtering, and why ICU Lookup returns ""

RFC 4647 §3.4 Lookup truncates **the range**, not the tag, and returns the first available tag the range is a prefix of.
The RFC's worked example for `zh-Hant-CN-x-private1-private2`:

```
1. zh-Hant-CN-x-private1-private2     4. zh-Hant
2. zh-Hant-CN-x-private1              5. zh
3. zh-Hant-CN                         6. (default)
```

The consequence is counter-intuitive and causes real outages: **a bare `en` range does not match an `en-US` tag**,
because truncating `en` further yields nothing. Basic Filtering (§3.3.1) has the opposite asymmetry — the range prefix-
matches the tag, so `en` matches `en-US`. Verified on two ICU-backed runtimes:

| Range (client) | Available    | Lookup                       | Basic Filter |
| -------------- | ------------ | ---------------------------- | ------------ |
| `en`           | `en-US`      | `""` / `null` — **no match** | `en-US`      |
| `en-US`        | `en`         | `en`                         | none         |
| `de`           | `de-CH`      | `""` / `null`                | `de-CH`      |
| `zh-Hant`      | `zh-Hant-TW` | `""` / `null`                | `zh-Hant-TW` |

```php
Locale::lookup(["en-US"], "en", false);  // ""  — no match
Locale::lookup(["en"], "en-US", false);  // "en"
Locale::lookup(["de-DE"], "de-AT", false); // ""
```

```java
var r = Locale.LanguageRange.parse("en");
var avail = List.of(Locale.forLanguageTag("en-US"));
Locale.lookup(r, avail);  // null
Locale.filter(r, avail);  // [en_US]
```

Because Lookup can miss, `Locale.lookup` is nullable in Java and returns `""` in PHP/ICU. Every call site must handle
the miss and supply a default. RFC 4647 §3.4.1 _requires_ the protocol to define that default and lists the legitimate
options: an untagged item, a null/empty tag where permitted, a designated default tag, `i-default`, an error, or a list
of available languages for the user to choose from.

This is the concrete reason a server calling only ICU Lookup on `Accept-Language: en` against an `en-US`-only catalog
serves untranslated content or crashes: **the range is narrower than the tag**. Either expand the range into its
prefixes before matching, or use Basic Filtering semantics. Expanding means dropping subtags from the end, removing any
singleton together with the subtag it introduces: `zh-Hant-CN-x-private1-private2` → `zh-Hant-CN-x-private1` → `zh-Hant-
CN` → `zh-Hant` → `zh`, exactly the RFC's sequence above.

### Fallback chains and the pseudo-locale trap

CLDR defines an explicit parent chain that is not subtag truncation: `en-GB` → `en-001` → `en`, `es-AR` → `es-419` →
`es`, and `zh-Hant-MO` → `zh-Hant-HK`. `en-150` (Europe) parents to `en-001` (World), not to `en`. Neither intermediate
is reachable by stripping subtags. `zh-Hant` and `sr-Latn` both parent to `und`, the root — not to `zh` or `sr`, which
is why a `zh-Hant` lookup that falls back by language alone lands on Simplified. Query the real chain
(`babel.core.get_global('parent_exceptions')` exposes it, and `babel`'s display-name fallback respects it) rather than
hand-rolling one.

**The pseudo-locale trap.** Pseudo-locales are structurally valid tags that pass every BCP 47 validator and have no real
users. CLDR's generator emits `en_XA` (accented, bracketed, expanded text for spotting hard-coded strings) and `ar_XB`
(BiDi-hostile text for spotting RTL breakage); `ar_XB` wraps LTR runs in `U+202E RIGHT-TO-LEFT OVERRIDE` and `U+200F
RIGHT-TO-LEFT MARK`. All of these are accepted by every runtime tested: `Intl.getCanonicalLocales("en-XA")` returns
`["en-XA"]`, `new Intl.Locale("qps-ploc")` maximizes to `qps-Ploc`, and `new Intl.Locale("ar-XB").getTextInfo()` reports
`{ direction: "rtl" }`.

Three parts to the trap:

1. `XA` and `XB` are **private-use region codes**, and `qps-*` sits in the IANA `qaa..qtz` private-use language range, so
   all of them validate and pass through any structure-only check.
2. They leak. A pseudo-locale written into a user record, cache key, or bundle name survives into production. `ar-XB` is
   the worst case: it looks RTL and formats "correctly" while every string is deliberately corrupted.
3. `ar-XB` is `ar` plus a private-use region, so `getTextInfo().direction === "rtl"` and any negotiation that treats
`ar` as acceptable with prefix matching will select it.

```js
const PSEUDO_REGIONS = new Set(["XA", "XB"]);
const SPECIAL_CODES = new Set(["und", "mul", "zxx"]);
function isServableLocale(tag) {
  const { language, region } = new Intl.Locale(tag);
  if (PSEUDO_REGIONS.has(region)) return false;
  if (SPECIAL_CODES.has(language)) return false;
  return !/^qps$/i.test(language);
}
```

`SPECIAL_CODES` covers IANA `Scope: special` entries — `und` (undetermined), `mul` (multiple languages), `zxx` (no
linguistic content) — which mean "not a language" and must never be stored as a preference.

### ECMA-402 matching: `lookup` vs `best fit`

`Intl` constructors accept `localeMatcher`, whose only valid values are `"lookup"` and `"best fit"`, defaulting to
`"best fit"`. "Best fit" is implementation-defined and may select a locale you did not expect; pass `"lookup"` when
selection must be reproducible across engines. An invalid value throws `RangeError`.

```js
new Intl.DateTimeFormat("en-US", { localeMatcher: "lookup" }); // ok
new Intl.DateTimeFormat("en-US", { localeMatcher: "bogus" }); // throws
new Intl.DateTimeFormat(navigator.languages).format(new Date());
```

The constructors accept an _array_ of tags and use the first supported entry — the portable way to express a priority
list. `navigator.languages` is the browser's ordered preference list, and `Accept-Language` generally mirrors it with
decreasing `q` values, but Chrome and Safari inject language-only fallback tags, so `navigator.languages === ["en-US",
"zh-CN"]` can produce `Accept-Language: en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7`. For anti-fingerprinting, Safari (always)
and Chrome incognito may send only one language. Treat neither as complete.

## Language Selection UI and What to Persist

Four signals, four trust levels. Use them in this order and persist only what the user chose.

| Signal            | Trust   | Scope             | Note                                                                           |
| ----------------- | ------- | ----------------- | ------------------------------------------------------------------------------ |
| Explicit picker   | Highest | Account or device | The only signal reflecting intent; never override it                           |
| Stored preference | Highest | Account           | Persists across sessions and devices when authenticated                        |
| `Accept-Language` | Medium  | Request           | A language preference, not a regional setting; often an unratified default     |
| Geo-IP            | Lowest  | Request           | Infers location, not language; wrong for travelers, VPNs, multilingual regions |

- **The picker always wins.** W3C: "The server should never override an explicit user language choice." Do not re-
  negotiate on every request after a choice has been made.
- **Store the choice as a full tag.** Persisting `en` destroys the `en-US`/`en-GB` distinction permanently — the next
  request's `Accept-Language` is a fresh guess, not a recovery.
- **Mark inferred values as inferred.** If you seed from `Accept-Language` or geo-IP, store `locale_source: "inferred" |
  "explicit"` so a later better signal can supersede it. An inferred value indistinguishable from a chosen one is a
  permanent bug.
- **Separate UI language from formatting locale.** A user may want English UI with German date and number formats. One
  `locale` column cannot express both; use `ui_language` and `formatting_locale`.
- **`Accept-Language` is a language hint, not a locale.** W3C notes it "was originally only intended to specify the user's
  language" and that using it alone "may handcuff the user into a set of choices not to his liking." A header carrying
  only `de` gives no region, so `de-DE` vs `de-AT` vs `de-CH` currency and date conventions are unresolvable from it.
- **Geo-IP yields a region, not a language.** Belgium, Switzerland, Canada, India, and South Africa are multilingual;
  inferring `fr` from a French IP is wrong for a meaningful share of users. Use it only as a last-resort formatting-region
  fallback.

Cache correctness depends on this. Any response whose body varies by language must send `Vary: Accept-Language`, or a
shared cache serves the first visitor's language to everyone. If language comes from geo-IP or a cookie instead of the
header, `Vary: Accept-Language` alone is insufficient — the cache key must include whatever actually drove the decision,
or the response must not be publicly cached.

## RTL Language Inventory

Derive direction from the resolved locale, not from a hard-coded language list. CLDR's `scriptMetadata.txt` marks a
script `RTL=YES` when its letters carry an RTL `Bidi_Class`; ICU surfaces it as `getTextInfo().direction` and `babel` as
`character_order`/`text_direction`.

Direction is a property of the **script**, and script is optional in the tag, so it resolves from the maximized tag.
Languages whose direction flips with the script subtag:

| Language         | Default script     | RTL variant                 |
| ---------------- | ------------------ | --------------------------- |
| `az` Azerbaijani | `az-Latn-AZ` → ltr | `az-Arab` → rtl             |
| `pa` Punjabi     | `pa-Guru-IN` → ltr | `pa-Arab` → rtl (Shahmukhi) |
| `ku` Kurdish     | `ku-Latn-TR` → ltr | `ku-Arab` → rtl (Sorani)    |
| `ha` Hausa       | `ha-Latn-NG` → ltr | `ha-Arab` → rtl (Ajami)     |
| `ms` Malay       | `ms-Latn-MY` → ltr | `ms-Arab` → rtl (Jawi)      |
| `ur` Urdu        | `ur-Arab-PK` → rtl | `ur-Latn` → ltr             |
| `sd` Sindhi      | `sd-Arab-PK` → rtl | `sd-Deva` → ltr             |

```js
new Intl.Locale("az").getTextInfo().direction; // "ltr"
new Intl.Locale("az-Arab").getTextInfo().direction; // "rtl"
```

RTL scripts and the languages commonly written in them: **`Arab`** — `ar`, `fa`, `ur`, `ps`, `ckb`, `sd`, `ug`, `ks`,
`bal`, `mzn`, `lrc`, `glk`, `arz`, `apc`, `ary`, `acm`, `aeb`, `ajp`, `apd`, `ars`, `aii`; **`Hebr`** — `he`, `yi`;
**`Thaa`** — `dv`; **`Nkoo`** — `nqo`; **`Syrc`** — `syr`, `syc`; **`Adlm`** — `ff-Adlm`; **`Rohg`** — `rhg`; **`Mand`**
— `mid`; **`Samr`** — `sam`; **`Mend`** — `men`; **`Khar`** — `khar`. CLDR also marks the historical and liturgical
scripts `Armi`, `Avst`, `Chrs`, `Cprt`, `Elym`, `Gara`, `Hatr`, `Hung`, `Lydi`, `Mani`, `Merc`, `Mero`, `Narb`, `Nbat`,
`Orkh`, `Ougr`, `Palm`, `Phli`, `Phlp`, `Phnx`, `Prti`, `Sarb`, `Sidt`, `Sogd`, `Sogo`, `Yezi` RTL.

Notably **`Mong` is `RTL=NO`** in CLDR's metadata even though traditional Mongolian is written vertically: `new
Intl.Locale("mn-Mong").getTextInfo().direction` returns `"ltr"`. Do not assume vertical implies RTL. Rendering, BiDi
isolation, and mirroring mechanics belong to [intl-bidi.md](intl-bidi.md).

## Common Mistakes

| Mistake                                                                | Why It Breaks                                                                                                              | Correct Approach                                                                                             |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Storing `en` when the user picked `en-GB`                              | The region is unrecoverable; dates, currency symbols, and week start silently revert to US conventions                     | Persist the full canonical tag at the specificity the picker offered                                         |
| Matching with ICU Lookup and assuming a hit                            | Lookup truncates the _range_, so range `en` returns `""`/`null` against an `en-US`-only catalog                            | Expand the range into prefixes, or use Basic Filtering; define the miss behavior per RFC 4647 §3.4.1         |
| Treating `q=0` as "lowest priority"                                    | `q=0` means _not acceptable_; ranking it last still selects it when nothing else matches                                   | Filter `q === 0` out before sorting; treat absent `q` as `1.0`                                               |
| Assuming `zh` means Chinese-in-general                                 | `zh` maximizes to `zh-Hans-CN`, so a `zh-Hant` user receives Simplified text                                               | Carry the script subtag through storage, matching, and bundle lookup                                         |
| Dropping the script subtag from `sr-Latn`                              | `sr` is Cyrillic; stripping the script flips the alphabet for the user                                                     | Treat `sr-Cyrl` and `sr-Latn` as distinct supported locales                                                  |
| Letting `en-XA` / `ar-XB` / `qps-ploc` into production                 | Private-use tags that pass every structural validator, so they reach real users and corrupt all strings                    | Reject `XA`/`XB` regions and `qps-*` languages at ingestion and at negotiation                               |
| Treating `und`, `mul`, `zxx` as ordinary codes                         | They mean "undetermined", "multiple languages", "no linguistic content"; storing one destroys the preference               | Reject them, or map to your default before persisting                                                        |
| Using `forLanguageTag` or `new Intl.Locale` as the validator           | `forLanguageTag("EN_US")` returns `und` silently while `Intl.getCanonicalLocales("en_US")` throws — opposite failure modes | Pick the validator whose failure mode you handle: `Locale.Builder` in Java, `Intl.getCanonicalLocales` in JS |
| Assuming ICU canonicalization resolves deprecated subtags              | ICU documents that `no => nb`, `iw => he`, `id => in` are _not_ performed; PHP returns `"iw"` for `canonicalize("iw")`     | Normalize aliases yourself from CLDR `languageAlias`, or accept both spellings                               |
| Serving a language-varying response without `Vary: Accept-Language`    | A shared cache serves the first visitor's language to every later user                                                     | Send `Vary: Accept-Language`, and include any non-header signal in the cache key                             |
| Deriving text direction from the language code                         | `az`, `pa`, `ku`, `ha`, `ms`, `ur`, `sd` flip direction with the script subtag                                             | Resolve direction from the maximized locale's script via CLDR/ICU                                            |
| Using geo-IP as the primary language signal                            | Location is not language; multilingual countries and travelers/VPNs break the inference                                    | Use geo-IP only as a last-resort formatting-region fallback, below explicit choice and `Accept-Language`     |
| Hand-rolling a fallback chain by stripping subtags                     | CLDR parents are not truncations: `en-GB` → `en-001` → `en`, `es-AR` → `es-419` → `es`                                     | Query the CLDR parent chain, or rely on the library's own fallback                                           |
| Relying on the default `localeMatcher: "best fit"` for reproducibility | "Best fit" is implementation-defined; engines may select different locales for identical input                             | Pass `localeMatcher: "lookup"` when selection must be reproducible                                           |

## Checklist

1. Verify every locale identifier at the BCP 47 boundary uses hyphens, not underscores, and convert ICU/POSIX `_` forms at the edge.
2. Confirm the stored language field holds a full canonicalized tag with script and region, not a bare language code.
3. Trace each `Intl.getCanonicalLocales`, `Locale.canonicalize`, `Locale.forLanguageTag`, and `language.Parse` call and
confirm the caller handles that library's specific failure mode (throw vs silent `und` vs empty result).
4. Grep for hand-written fallback chains and replace them with the CLDR parent chain (`en-GB` → `en-001` → `en`; `es-AR` → `es-419` → `es`).
5. Confirm every negotiation call site defines explicit behavior for the no-match case, since Lookup can return `""`/`null` (RFC 4647 §3.4.1).
6. Check the `Accept-Language` parser: absent `q` defaults to `1.0`, `q=0` entries are dropped rather than ranked last,
and no more than three decimal digits are accepted.
7. Verify the matching scheme is chosen deliberately — Lookup truncates the range and will not match a bare `en` against `en-US`; Basic Filtering will.
8. Add a guard rejecting `XA`/`XB` private-use regions, `qps-*` languages, and the special codes `und`, `mul`, `zxx` before any locale is persisted or served.
9. Confirm `zh`, `sr`, `az`, `pa`, `ku`, `ha`, `ms`, `ur`, and `sd` all appear with explicit script subtags in the supported-locale list.
10. Verify the explicit user choice is never overwritten by `Accept-Language` or geo-IP on a later request, and that inferred values carry a provenance flag.
11. Check that `ui_language` and `formatting_locale` are separate fields, so English UI with German formatting is representable.
12. Confirm every language-varying response sends `Vary: Accept-Language`, and that any non-header signal is part of the cache key.
13. Verify text direction is resolved from the maximized locale's script, not from a hard-coded language list.
14. Confirm `localeMatcher: "lookup"` is passed wherever locale selection must be reproducible across JavaScript engines.
15. Cross-check canonicalization of deprecated subtags (`iw`, `in`, `ji`, `tl`, `sh`, `mo`) in each runtime you deploy, since ICU and ECMA-402 disagree.

## References

- [RFC 5646 — Tags for Identifying Languages (BCP 47)](https://www.rfc-editor.org/rfc/rfc5646.txt) — the `langtag` ABNF,
  subtag semantics, grandfathered tags, private use.
- [RFC 4647 — Matching of Language Tags](https://www.rfc-editor.org/rfc/rfc4647.txt) — Basic/Extended Filtering, Lookup,
  fallback patterns, default values (§3.4.1).
- [RFC 9110 §12.5.4 — Accept-Language](https://www.rfc-editor.org/rfc/rfc9110.txt) — header grammar, quality values (§12.4.2), wildcard (§12.4.3).
- [IANA Language Subtag Registry](https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry) —
  authoritative subtags, `Preferred-Value`, `Deprecated`, `Suppress-Script`, `Scope`.
- [Unicode UTS #35 (LDML) Part 1](https://www.unicode.org/reports/tr35/tr35.html) — canonical Unicode locale identifiers, likely subtags, locale inheritance.
- [CLDR `likelySubtags.json`](https://github.com/unicode-org/cldr-json/blob/main/cldr-json/cldr-
  core/supplemental/likelySubtags.json) — maximize data (`zh` → `zh-Hans-CN`, `sr` → `sr-Cyrl-RS`).
- [CLDR `parentLocales.json`](https://github.com/unicode-org/cldr-json/blob/main/cldr-json/cldr-
  core/supplemental/parentLocales.json) — real fallback chains (`en-GB` → `en-001`, `es-AR` → `es-419`).
- [CLDR `aliases.json`](https://github.com/unicode-org/cldr-json/blob/main/cldr-json/cldr-core/supplemental/aliases.json)
  — deprecated-subtag replacements used for canonicalization.
- [CLDR `scriptMetadata.txt`](https://github.com/unicode-org/cldr/blob/main/common/properties/scriptMetadata.txt) — the
  `RTL=YES` field defining the RTL script inventory.
- [CLDR `CLDRFilePseudolocalizer.java`](https://github.com/unicode-org/cldr/blob/main/tools/cldr-
  code/src/main/java/org/unicode/cldr/tool/CLDRFilePseudolocalizer.java) — how `en_XA` and `ar_XB` are generated,
  including `U+202E`/`U+200F` injection.
- [ICU User Guide — Locales](https://unicode-org.github.io/icu/userguide/locale/) — ICU locale IDs, level 1 vs level 2
  canonicalization, fallback, and the superseded identifiers ICU deliberately does not remap.
- [MDN — `Intl.Locale`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/Locale) —
  subtag properties, `maximize`/`minimize`, accessor-to-method migration.
- [MDN — `Intl.getCanonicalLocales()`](https://developer.mozilla.org/en-
  US/docs/Web/JavaScript/Reference/Global_Objects/Intl/getCanonicalLocales) — structural validation and canonicalization
  in ECMAScript.
- [MDN — `Accept-Language` header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Accept-Language) —
  browser fallback-tag injection and anti-fingerprinting reduction.
- [W3C i18n — Accept-Language used for locale setting](https://www.w3.org/International/questions/qa-accept-lang-locales)
  — why the header is a language hint, not a locale.
- [Babel core API](https://babel.pocoo.org/en/latest/api/core.html) — `Locale.parse`, `negotiate_locale`, `character_order`, `text_direction`.
- [PHP `Locale` class](https://www.php.net/manual/en/class.locale.php) — `canonicalize`, `acceptFromHttp`, `lookup`, `filterMatches`, `addLikelySubtags`.
- [Java `java.util.Locale`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Locale.html) —
  `forLanguageTag` leniency, `Builder` strictness, `lookup`/`filter`.
- [Go `golang.org/x/text/language`](https://pkg.go.dev/golang.org/x/text/language) — `Parse`, `ParseAcceptLanguage`, `Matcher`, `Confidence`.

