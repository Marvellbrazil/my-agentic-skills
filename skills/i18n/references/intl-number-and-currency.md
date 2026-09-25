# Numbers, Currency, Units, and Measurement

Every locale defines its own decimal separator, grouping pattern, digit shapes, currency symbol placement, and rounding
convention, so a number becomes a locale-specific string the moment it is rendered. Parsing that string with
`parseFloat` or `Number()` silently truncates at the first separator, formatting money through a binary float loses
cents, and assuming every currency has two decimal places prints `¥1,234.50` where the business wrote `¥1,235`. These
failures are quiet: no exception, no log line, just a wrong amount on an invoice.

## Contents

- [When This Applies](#when-this-applies)
- [Separators, Digit Shapes, and Parsing](#separators-digit-shapes-and-parsing)
  - [Digit shapes are a separate axis from language](#digit-shapes-are-a-separate-axis-from-language)
  - [Why `parseFloat` is always wrong](#why-parsefloat-is-always-wrong)
- [`Intl.NumberFormat`: The Options That Change Output](#intlnumberformat-the-options-that-change-output)
  - [The default rounding mode is not universal](#the-default-rounding-mode-is-not-universal)
- [Currency: Codes, Minor Units, Symbols, and Cash](#currency-codes-minor-units-symbols-and-cash)
  - [`$` is not a currency](#is-not-a-currency)
  - [Accounting format and negative money](#accounting-format-and-negative-money)
  - [Cash rounding is a separate axis from display rounding](#cash-rounding-is-a-separate-axis-from-display-rounding)
- [Rounding, Storage, and Money Arithmetic](#rounding-storage-and-money-arithmetic)
  - [Never store money as a binary float](#never-store-money-as-a-binary-float)
  - [Rounding modes are not interchangeable](#rounding-modes-are-not-interchangeable)
- [Compact Notation, Units, and Measurement](#compact-notation-units-and-measurement)
  - [Units and measurement](#units-and-measurement)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- Any code that renders an amount, count, percentage, ratio, score, or measurement to a user-facing surface.
- Any code that reads a number a user typed, pasted, or uploaded (form field, CSV, spreadsheet, invoice, OCR output).
- Introducing a currency, price, salary, tax rate, FX rate, budget, or financial report.
- Adding a locale beyond `en-US`, or resolving a locale from `Accept-Language` or a user profile.
- Choosing a storage type for money across `float`, `double`, `Decimal`, `numeric`, and integer minor units.
- Showing abbreviated counts (`1.2K`, `1,2 rb`, `1.2万`) or physical quantities (distance, mass, temperature, volume, file size, elapsed time).
- Auditing an app for `toFixed`, `parseFloat`, `parseInt`, `Math.round`, or hand-rolled separator regexes.

## Separators, Digit Shapes, and Parsing

Grouping and decimal separators are locale data, and several locales use a non-ASCII space that survives copy-paste and breaks naive splitting:

| Locale                             | `1234.56`  | Decimal sep | Group sep (code point)         |
| ---------------------------------- | ---------- | ----------- | ------------------------------ |
| `en-US`, `ja-JP`, `zh-CN`          | `1,234.56` | `.`         | `,` U+002C                     |
| `de-DE`, `id-ID`, `tr-TR`          | `1.234,56` | `,`         | `.` U+002E                     |
| `fr-FR`                            | `1 234,56` | `,`         | U+202F NO-BREAK SPACE (narrow) |
| `sv-SE`, `nb-NO`, `ru-RU`, `cs-CZ` | `1 234,56` | `,`         | U+00A0 NO-BREAK SPACE          |
| `ar-EG` (`arab`)                   | `١٬٢٣٤٫٥٦` | `٫` U+066B  | `٬` U+066C                     |
| `fa-IR` (`arabext`)                | `۱٬۲۳۴٫۵۶` | `٫`         | `٬`                            |

`fr-FR`'s separator is `U+202F`, not `U+00A0` and not a plain space. A `replace(/\s/g, '')` cleanup changes the string's
meaning under other locales, and `split(',')` produces the wrong field count.

`en-IN`, `hi-IN`, `ta-IN`, `mr-IN`, `bn-IN`, and `ur-IN` group the last three digits, then in pairs — `1,23,45,678.9`.
Secondary grouping is the most commonly unimplemented feature:

- **.NET** models it: `new CultureInfo("en-IN").NumberFormat.NumberGroupSizes` is `[3, 2]`, and `12345678.9m.ToString("N2", inr)` yields `1,23,45,678.90`.
- **Java** does not. `DecimalFormat` exposes one grouping size, and in JDK 24 both the default and `CLDR` providers render
  `en-IN` as `12,345,678.9`; even the explicit pattern `#,##,##0.00` produces `12,345,678.90`.
- **ICU** (Node, PHP, Swift, Flutter, most native stacks) models it as primary size 3 plus secondary size 2, exposed in
  PHP as `NumberFormatter::GROUPING_SIZE` / `SECONDARY_GROUPING_SIZE`.

Grouping is also suppressed below a locale-specific digit count (CLDR `minimumGroupingDigits`), which is `2` for `pl`,
`es`, `it`, `hu`, `bg`, `sl`, `lv`, `et`, `sq`, and `be`, so `Intl.NumberFormat("pl").format(1234)` is `"1234"` while
`format(12345)` is `"12 345"` and `de` gives `"1.234"`. `resolvedOptions().useGrouping` reports `"auto"` by default;
`"min2"` forces the later threshold everywhere and `"always"` forces grouping at four digits.

### Digit shapes are a separate axis from language

The numbering system is independent of the language and is not uniform across a script's languages. These values are resolved, not assumed:

| Locale                                      | `numberingSystem` | `1234.56`              |
| ------------------------------------------- | ----------------- | ---------------------- |
| `ar-EG`, `ar-SA`, `ar-IQ`, `ar-LB`, `ar-SY` | `arab`            | `١٬٢٣٤٫٥٦`             |
| `ar-AE`, `ar-DZ`, `ar-MA`, `ar-TN`          | `latn`            | `1,234.56` / `1.234,5` |
| `fa-IR`, `ur-IN`                            | `arabext`         | `۱٬۲۳۴٫۵۶`             |
| `bn-BD`                                     | `beng`            | `১,২৩৪.৫৬`             |
| `mr-IN`, `ne-NP`                            | `deva`            | `१,२३४.५६`             |
| `my-MM`                                     | `mymr`            | `၁,၂၃၄.၅၆`             |
| `ur-PK`                                     | `latn`            | `1,234.56`             |

Four common Arabic locales render Latin digits. Do not branch on "language starts with `ar`" to pick a digit table; read
the resolved value or set `numberingSystem` explicitly.

```js
new Intl.NumberFormat("ar-EG").resolvedOptions().numberingSystem; // "arab"
new Intl.NumberFormat("ar-AE").resolvedOptions().numberingSystem; // "latn"
new Intl.NumberFormat("en-u-nu-arab").format(1234.56); // "١٬٢٣٤٫٥٦"
// an explicit option wins over the -u-nu- extension:
new Intl.NumberFormat("en-u-nu-arab", { numberingSystem: "latn" }).format(
  1234.56,
); // "1,234.56"
```

`Intl.supportedValuesOf("numberingSystem")` lists 78 accepted values (`latn`, `arab`, `arabext`, `deva`, `beng`,
`fullwide`, `hanidec`, `thai`, `khmr`, `mymr`, …). `hanidec` is not a positional-digit table: `numberingSystem:
"hanidec"` on `zh` renders `1234.5` as `一,二三四.五`, a curiosity rather than something to ship.

### Why `parseFloat` is always wrong

There is no `Intl` parser — `Intl.NumberFormat` has no `parse` method — so applications reach for `parseFloat`, which
stops at the first character it cannot use:

```js
parseFloat("1.234,56"); // 1.234  (de-DE 1,234.56)
Number("1.234,56"); // NaN
parseFloat("1,234.56"); // 1      (en-US 1,234.56)
Number("1,234.56"); // NaN
parseFloat("1 234,56"); // 1      (fr-FR, U+202F)
parseFloat("١٢٣٤"); // NaN
parseFloat("1.234,56abc"); // 1.234  (no validation, no error)
```

Every one is a silent wrong answer rather than a rejection. A correct parse needs the locale, and it must validate the
whole string: read `formatToParts` for the `group` and `decimal` tokens, build a digit map from `useGrouping: false`
output for non-Latin numerals, strip grouping, normalize the decimal to `.`, then match `/^[+-]?\d*\.?\d+$/` and reject
on failure. Parsers that ship locale data are safer and should be the first choice:

| Ecosystem         | API                                                            | Notes                                                                                                    |
| ----------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Python + Babel    | `babel.numbers.parse_decimal(s, locale="de_DE")`               | `1.234,56` → `Decimal("1234.56")`; `strict=True` rejects malformed grouping                              |
| Python + Babel    | `parse_decimal(s, locale="ar_EG", numbering_system="default")` | Required for Arabic-Indic input; the default `numbering_system="latn"` raises `NumberFormatError`        |
| PHP intl          | `NumberFormatter::parse()`, `parseCurrency()`                  | `parseCurrency("$1,234.56", $cur)` returns `1234.56` and sets `$cur` to `"USD"`                          |
| Java              | `NumberFormat.getNumberInstance(locale).parse()`               | Partial by default: `"12abc"` → `12`, `"1,2,3"` → `123`; use `ParsePosition` to check the consumed index |
| .NET              | `decimal.Parse(s, NumberStyles.Currency, culture)`             | Accepts the symbol and accounting parentheses                                                            |
| ICU (C/C++/Swift) | `unum_parse`, `unum_parseDouble`                               | Locale-aware; returns the parse position                                                                 |

`parseFloat` on a canonical machine string is fine; the rule is that the string must never have been through a formatter.

## `Intl.NumberFormat`: The Options That Change Output

| Option                                                  | Values                                              | What it changes                                         |
| ------------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------- |
| `style`                                                 | `decimal`, `percent`, `currency`, `unit`            | `percent` multiplies by 100; `unit` does not            |
| `minimumFractionDigits` / `maximumFractionDigits`       | 0–100                                               | Pad vs truncate; a conflicting pair throws `RangeError` |
| `minimumSignificantDigits` / `maximumSignificantDigits` | 1–21                                                | Round by precision rather than decimal place            |
| `roundingPriority`                                      | `auto`, `morePrecision`, `lessPrecision`            | Which digit set wins when both are set                  |
| `useGrouping`                                           | `true`, `false`, `"always"`, `"auto"`, `"min2"`     | Whether and when separators appear                      |
| `notation`                                              | `standard`, `scientific`, `engineering`, `compact`  | Magnitude abbreviation                                  |
| `compactDisplay`                                        | `short`, `long`                                     | `1.2M` vs `1 million`                                   |
| `signDisplay`                                           | `auto`, `always`, `exceptZero`, `negative`, `never` | Plus sign, zero handling, suppressing `-`               |
| `currencySign`                                          | `standard`, `accounting`                            | Parentheses vs minus for negatives                      |
| `roundingMode`                                          | 9 values, default `halfExpand`                      | Tie-breaking                                            |
| `roundingIncrement`                                     | 14 values, default 1                                | Cash rounding; forces `minFrac === maxFrac`             |
| `trailingZeroDisplay`                                   | `auto`, `stripIfInteger`                            | `1.00` → `1` when the fraction is zero                  |
| `numberingSystem`                                       | `latn`, `arab`, `deva`, …                           | Digit shapes                                            |

`style: "percent"` and `style: "unit", unit: "percent"` are not interchangeable: `format(0.45)` gives `"45%"` for the
former and `"0.45%"` for the latter. Pick whichever matches whether the stored value is a ratio or already a percentage.
`signDisplay: "negative"` is the option for a negative that must not show a sign — `format(-12.3)` returns `"12.3"` and
on currency returns `"$12.30"`; `"never"` behaves the same for negatives, while `"exceptZero"` adds `+` for positives
but not zero.

Symbol position is locale data, not a formatting choice: `en-US` + `USD` gives `$1,234.50`, `de-DE` + `EUR` gives
`1.234,50 €`, `tr-TR` + `percent` gives `%45`, and `ar-EG` + `percent` gives `٤٥٪؜` — which contains U+061C ARABIC
LETTER MARK. Layouts that reserve space based on `en-US` order clip or misalign these; see [intl-bidi.md](intl-bidi.md)
for the marks themselves.

### The default rounding mode is not universal

`Intl.NumberFormat` defaults to `roundingMode: "halfExpand"` (ties away from zero). Most server-side stacks default to
half-even, so the same stored value renders differently on the client and in the ledger:

| Stack                               | Default tie rule     | `2.5` → int | `0.125` → 2 dp                                                   |
| ----------------------------------- | -------------------- | ----------- | ---------------------------------------------------------------- |
| JS `Intl.NumberFormat`              | `halfExpand`         | `3`         | `0.13`                                                           |
| JS `toFixed`                        | float artifact       | —           | `(1.005).toFixed(2)` → `"1.00"`, `(2.675).toFixed(2)` → `"2.67"` |
| Java `DecimalFormat`                | `HALF_EVEN`          | `2`         | `0.12`                                                           |
| PHP `NumberFormatter`               | `ROUND_HALFEVEN` (4) | `2`         | `0.12`                                                           |
| Python `round()`, `decimal` context | half-even            | `2`         | `0.12`                                                           |
| Go `golang.org/x/text/number`       | half-even            | `2`         | `0.12`                                                           |
| .NET `Math.Round`                   | `ToEven`             | `2`         | `0.12`                                                           |
| PostgreSQL `round(numeric)`         | away from zero       | `3`         | `0.13`                                                           |
| MySQL / MariaDB `ROUND()`           | away from zero       | `3`         | `0.13`                                                           |
| SQLite `round()`                    | away from zero       | `3`         | `1.005` → `1.0`                                                  |

A report generated in Java and a chart rendered in the browser disagree on `2.5` unless one side sets `roundingMode:
"halfEven"` or the other switches to `HALF_UP`. `toFixed` is a float-formatting operation, not a rounding contract:
`(1.005).toFixed(2)` is `"1.00"` because the stored double is `1.00499999999999989...`.

`roundingIncrement` has a hard precondition in ECMA-402 `SetNumberFormatDigitOptions`: the value must be one of `1, 2,
5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000`, the rounding type must be `fraction-digits` (so it
cannot combine with `maximumSignificantDigits`), and `minimumFractionDigits` must equal `maximumFractionDigits`.

```js
const cash = { minimumFractionDigits: 2, maximumFractionDigits: 2 };
new Intl.NumberFormat("en", { ...cash, roundingIncrement: 5 }).format(1.23);
// "1.25"
new Intl.NumberFormat("en", { maximumFractionDigits: 2, roundingIncrement: 5 });
// RangeError: maximumFractionDigits value is out of range.
new Intl.NumberFormat("en", {
  maximumSignificantDigits: 3,
  roundingIncrement: 25,
});
// TypeError: RoundingType is not fractionDigits
new Intl.NumberFormat("en", { ...cash, roundingIncrement: 4 });
// RangeError: roundingIncrement value is out of range.
```

## Currency: Codes, Minor Units, Symbols, and Cash

ISO 4217 `CcyMnrUnts` states the decimal relationship; CLDR `currencyData/fractions` states what applications should
print. They diverge for a real set of currencies, and formatting libraries follow CLDR:

| Code                                     | ISO minor units | CLDR `digits` | `1234.567` renders as                                  |
| ---------------------------------------- | --------------- | ------------- | ------------------------------------------------------ |
| `JPY`, `KRW`, `VND`, `CLP`, `ISK`        | 0               | 0             | `¥1,235`, `₩1,235`, `₫1,235`, `CLP 1,235`, `ISK 1,235` |
| `IQD`, `IDR`, `COP`, `HUF`               | 3, 2, 2, 2      | 0             | `IQD 1,235`, `IDR 1,235`, `COP 1,235`, `HUF 1,235`     |
| `KWD`, `BHD`, `OMR`, `TND`, `LYD`, `JOD` | 3               | 3             | `KWD 1,234.567`                                        |
| `CLF`, `UYW`                             | 4               | 4             | `CLF 1,234.5670`                                       |
| `MGA`                                    | 2               | 0             | `MGA 1,235`                                            |
| `MRU`                                    | 2               | 2             | `MRU 1,234.57`                                         |
| `CRC`, `CZK`, `NOK`, `SEK`, `TWD`        | 2               | 2             | `CRC 1,234.57`                                         |
| `XXX`, `XTS`, `XAU`                      | N.A.            | —             | `XXX` renders `¤1.00`; `XTS` renders `XTS 1.00`        |

`IQD` is the sharpest case: ISO says three decimals, CLDR says zero, ICU prints `IQD 1,235`. `HUF` has an ISO minor unit
of 2 but prints with none. `MGA` and `MRU` are non-decimal (1 ariary = 5 iraimbilanja, 1 ouguiya = 5 khoums), yet ISO
records both as 2 and CLDR prints `MGA` with 0 digits and `MRU` with 2 — neither library can represent `1 ariary 2
iraimbilanja` as a decimal string. If you handle those two, store an integer count of minor units.

Never hardcode a decimal count; read it from the formatter. In JS, `new Intl.NumberFormat("en", { style: "currency",
currency: code }).resolvedOptions().maximumFractionDigits` gives `0` for `JPY`, `3` for `KWD`, and `4` for `CLF`. In
Java, `Currency.getInstance("JPY").getDefaultFractionDigits()` is `0`, `KWD` is `3`, `MGA` is `2` (the ISO value, not
the printing value), and `Currency.getInstance("UYW")` throws `IllegalArgumentException` because the JDK table omits it.
.NET is worse — `NumberFormatInfo.CurrencyDecimalDigits` is one value per culture, so `CurrencySymbol = "JPY"` on `en-
US` yields `JPY1,234.50`, and `KWD` under `en-US` yields `KWD1,234.57`. Babel gets it right per currency:
`format_currency(Decimal("1234.5"), "JPY", locale="en_US")` → `'¥1,234'`, `"KWD"` → `'KWD1,234.500'`, `"CLF"` →
`'CLF1,234.5000'`, and `get_currency_precision("MGA")` → `0`.

### `$` is not a currency

`currencyDisplay: "symbol"` (the default) renders whatever CLDR associates with the code in that locale: `CAD` under
`en-US` is `CA$1,234.50`, but under `en-CA` it is `$1,234.50`, identical to `USD` under `en-CA`. At least a dozen
currencies use `$` — `AUD`, `CAD`, `HKD`, `SGD`, `NZD`, `MXN`, `BRL`, `ARS`, `CLP`, `COP`, `TWD`, `USD`.

| `currencyDisplay`  | `en-US` / `CAD`             | `en-US` / `CNY`         | `ja-JP` / `JPY` |
| ------------------ | --------------------------- | ----------------------- | --------------- |
| `symbol` (default) | `CA$1,234.50`               | `CN¥1,234.50`           | `￥1,235`       |
| `narrowSymbol`     | `$1,234.50`                 | `¥1,234.50`             | `¥1,235`        |
| `code`             | `CAD 1,234.50`              | `CNY 1,234.50`          | `JPY 1,235`     |
| `name`             | `1,234.50 Canadian dollars` | `1,234.50 Chinese yuan` | `1,234 円`      |

Use `code` whenever a symbol would be ambiguous — multi-currency ledgers, FX tables, machine-readable invoices — and
`narrowSymbol` only when the currency is unambiguous from context, because it collapses `CA$` and `$` into the same
string. `currencyDisplay: "name"` is pluralized through CLDR plural rules, so it needs a plural-category lookup rather
than concatenation; ICU 78 always emits the plural form (`format(1)` → `"1.00 US dollars"`). Unit long forms behave the
same way (`1 hour` vs `2 hours`, `5 godzin` in Polish) — see [intl-pluralization.md](intl-pluralization.md).

Currency codes are validated only as three ASCII letters, so unknown codes do not throw: `"ZZZ"` renders `"ZZZ 1.00"`,
lowercase `"usd"` renders `"$1.00"`, `"USDX"` throws `RangeError`, and `"XXX"` renders `"¤1.00"`.
`Intl.supportedValuesOf("currency")` returns 162 codes and omits `CLF`, `UYW`, and `XXX`, so it cannot validate
accounting inputs; validate against the ISO 4217 list from SIX instead.

### Accounting format and negative money

`currencySign: "accounting"` wraps negatives in parentheses only where the locale does. For `-1234.5`, `en-US` + `USD`
gives `"($1,234.50)"`, `nl-NL` + `EUR` gives `"(€ 1.234,50)"`, but `de-DE` + `EUR` gives `"-1.234,50 €"` and `it-IT` +
`EUR` gives `"-1234,50 €"`. German, Italian, and Danish do not use accounting parentheses, so a report that must be
parenthesized in German needs a manual wrapper. Combine with `signDisplay` only deliberately: `signDisplay: "always"`
turns a positive into `+$5.00`.

`formatToParts` is the supported way to restyle output, because it separates the currency token from the digits:

```js
const opts = { style: "currency", currency: "USD", currencySign: "accounting" };
new Intl.NumberFormat("en-US", opts).formatToParts(-1234.5);
// [{type:"literal",value:"("},{type:"currency",value:"$"},{type:"integer",value:"1"},
//  {type:"group",value:","},{type:"integer",value:"234"},{type:"decimal",value:"."},
//  {type:"fraction",value:"50"},{type:"literal",value:")"}]
```

It also emits `nan` and `infinity` tokens, and `format(NaN)` returns `"NaN"` while a currency format returns `"$NaN"`.
Validate finiteness at the boundary so neither reaches a user.

### Cash rounding is a separate axis from display rounding

CLDR records `cashDigits`/`cashRounding` per currency, and `Intl.NumberFormat` does not apply them. They describe
physical cash transactions, where the smallest coin makes a smaller unit impossible:

| Currency                          | `digits` | `cashDigits` | `cashRounding` | Effect                                            |
| --------------------------------- | -------- | ------------ | -------------- | ------------------------------------------------- |
| `CHF`, `CAD`                      | 2        | 2            | 5              | Nearest 0.05                                      |
| `DKK`                             | 2        | 2            | 50             | Nearest 0.50                                      |
| `HUF`                             | 0        | 0            | 5              | Nearest 5                                         |
| `MRU`                             | 2        | 2            | 20             | Nearest 0.20 (the khoums)                         |
| `CZK`, `NOK`, `SEK`, `TWD`, `CRC` | 2        | 0            | 0              | No cash rounding; smallest coin is the major unit |

A card payment of `CHF 1.23` is charged `1.23` while the same purchase in cash settles at `1.25`:

```js
new Intl.NumberFormat("de-CH", { style: "currency", currency: "CHF" }).format(
  1.23,
); // "CHF 1.23" — standard, what the card is charged
new Intl.NumberFormat("de-CH", {
  style: "currency",
  currency: "CHF",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  roundingIncrement: 5,
}).format(1.23); // "CHF 1.25" — cash
```

Go is the only mainstream stack that ships cash rounding as first-class data: `currency.Cash.Rounding(currency.CHF)`
returns scale 2 with increment 5, `currency.Standard.Rounding(currency.CHF)` returns scale 2 with increment 1, and
`currency.Cash.Rounding(currency.MustParseISO("DKK"))` returns increment 50, so
`currency.Symbol.Kind(currency.Cash)(currency.CHF.Amount(1.22))` under a German printer gives `"CHF 1,20"`. Its
`currency.Accounting` kind is an alias for `Standard` and does not produce parentheses, and its currency formatter
always inserts a space between symbol and number (`"$ 1,234.50"`), unlike ICU. Java has no cash-rounding API, so round
the `BigDecimal` first: `new BigDecimal("1.23").divide(new BigDecimal("0.05"), 0, RoundingMode.HALF_UP).multiply(new
BigDecimal("0.05"))` → `1.25`.

## Rounding, Storage, and Money Arithmetic

### Never store money as a binary float

`0.1 + 0.2` is `0.30000000000000004` in every IEEE-754 binary double, and cents accumulate the error across a ledger.
`1.005 * 100` is `100.49999999999999`, so `Math.round(1.005 * 100) / 100` yields `1` rather than `1.01`.
`JSON.parse("9007199254740993")` returns `9007199254740992` because the value exceeds `Number.MAX_SAFE_INTEGER`
(`9007199254740991`); `BigInt` handles it correctly (`format(9007199254740993n)` → `"9,007,199,254,740,993"`).

| Storage                                                      | Correct use                                            | Failure mode                                                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| Integer minor units (`BIGINT` cents, `long` fils)            | The default for money. Exact, comparable, sums exactly | You must track the currency's exponent per row; mixing exponents needs conversion             |
| `DECIMAL(p, s)` / `NUMERIC(p, s)` / `BigDecimal` / `Decimal` | Ledgers, tax math, FX, anything with division          | Scale must be pinned per currency; too small an `s` silently rounds on insert in some engines |
| `float` / `double` / `REAL`                                  | Never, for money                                       | Accumulating error; `SUM` of a float column is order-dependent                                |

Verified engine differences:

```sql
-- PostgreSQL: numeric ties go away from zero; float8 is platform-dependent
SELECT round(2.5::numeric);      -- 3
SELECT round(-2.5::numeric);     -- -3
SELECT round(1.005::numeric, 2); -- 1.01
SELECT round(1.005::float8, 2);  -- usually 1.00

-- MySQL / MariaDB: ties away from zero; DECIMAL(10,2) rounds on insert
SELECT ROUND(2.5), ROUND(-2.5), ROUND(1.005, 2); -- 3, -3, 1.01
SELECT CAST(2.675 AS DECIMAL(10,2));             -- 2.68
SELECT 0.1 + 0.2;                                -- 0.3
SELECT 0.1E0 + 0.2E0;                            -- 0.30000000000000004

-- SQLite: NUMERIC(10,2) is type affinity, not enforcement
CREATE TABLE t (amt DECIMAL(10,2));
INSERT INTO t VALUES (1.005);
SELECT amt FROM t;       -- 1.005, not 1.01
SELECT round(1.005, 2);  -- 1.0
```

The SQLite row is the trap: declaring `DECIMAL(10,2)` there buys nothing, and every stored amount must be rounded by the application before insert.

### Rounding modes are not interchangeable

The nine `roundingMode` values and their behavior on `2.5` / `-2.5` at zero fraction digits:

| `roundingMode` | `2.5` | `-2.5` | Meaning                           |
| -------------- | ----- | ------ | --------------------------------- |
| `ceil`         | `3`   | `-2`   | Toward +∞                         |
| `floor`        | `2`   | `-3`   | Toward −∞                         |
| `expand`       | `3`   | `-3`   | Away from zero                    |
| `trunc`        | `2`   | `-2`   | Toward zero                       |
| `halfCeil`     | `3`   | `-2`   | Ties toward +∞                    |
| `halfFloor`    | `2`   | `-3`   | Ties toward −∞                    |
| `halfExpand`   | `3`   | `-3`   | Ties away from zero (**default**) |
| `halfTrunc`    | `2`   | `-2`   | Ties toward zero                  |
| `halfEven`     | `2`   | `-2`   | Banker's rounding                 |

Banker's rounding exists because repeatedly rounding a half away from zero biases a large set of numbers upward; half-
even sends the tie to the even neighbor. It is the default in Java, PHP, Python, Go, and .NET, so an aggregate computed
server-side in half-even and rendered client-side with the JS default `halfExpand` will not reconcile. Pick one mode,
set it explicitly on both sides, and record it in the ledger schema.

Python's `round()` is half-even _and_ operates on the binary double: `round(2.5)` is `2`, `round(0.5)` is `0`, and
`round(2.675, 2)` is `2.67` — but `Decimal("2.675").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` is `2.68` while
`Decimal(1.005).quantize(...)` is `1.00` because the float was already inexact. Always construct `Decimal` from a
string; `Decimal(0.1)` is `0.1000000000000000055511151231257827021181583404541015625`. Java and .NET have the same trap
and the same fix:

```java
new BigDecimal("1234.565").setScale(2, RoundingMode.HALF_UP); // 1234.57
new BigDecimal(1234.565); // 1234.56500000000005456968210637569427490234375
Math.Round(2.5m);                                // C#: 2 (decimal, ToEven)
Math.Round(2.5m, MidpointRounding.AwayFromZero); // C#: 3
Math.Round(0.125m, 2);                           // C#: 0.12
```

## Compact Notation, Units, and Measurement

`notation: "compact"` picks its magnitude from CLDR compact patterns, which step in 10³ for `en`, 10⁴ for `ja` and `zh`, and lakh/crore for `hi` and `en-IN`:

| Value       | `en`   | `de`       | `ja`    | `zh`    | `hi`        | `en-IN` | `id`     |
| ----------- | ------ | ---------- | ------- | ------- | ----------- | ------- | -------- |
| `1234`      | `1.2K` | `1234`     | `1234`  | `1234`  | `1.2 हज़ार` | `1.2K`  | `1,2 rb` |
| `12345`     | `12K`  | `12.345`   | `1.2万` | `1.2万` | `12 हज़ार`  | `12K`   | `12 rb`  |
| `1234567`   | `1.2M` | `1,2 Mio.` | `123万` | `123万` | `12 लाख`    | `12L`   | `1,2 jt` |
| `100000000` | `100M` | `100 Mio.` | `1億`   | `1亿`   | `10 क॰`     | `10Cr`  | `100 jt` |

German does not abbreviate below one million, and `hi`/`en-IN` switch to lakh at 10⁵ and crore at 10⁷ — so a "K/M/B"
formatter hardcoded in the front end is wrong for most of the world. Compact output rounds before choosing the
magnitude: `999500` becomes `1M`, not `999.5K`.

`compactDisplay: "long"` gives words (`1 million`, `1,2 Millionen`), which suits prose but not axis labels. Compact
composes with `style`, but the result is not a hand-written abbreviation: `en` + `EUR` gives `€1.2M`, `de` + `EUR` gives
`1,2 Mio. €`. Avoid combining `notation: "compact"` with `roundingIncrement`, because compact selects significant-digit
rounding — the mode `roundingIncrement` rejects. `notation: "scientific"` and `"engineering"` produce `1.235E4` and
`12.345E3` in `en`, so do not parse either back.

### Units and measurement

`style: "unit"` is backed by a closed CLDR list — 45 values in ICU 78 — and there is no `permille` unit:
`Intl.supportedValuesOf("unit").includes("mile-scandinavian")` is `true` while `new Intl.NumberFormat("en", { style:
"unit", unit: "permille" })` throws `RangeError: Invalid unit argument for Intl.NumberFormat() 'permille'`. Compound
units use `-per-` (`kilometer-per-hour`, `mile-per-hour`), and there is no `unit: "currency"` — currency is a separate
`style`. Per-mille needs a manual pattern: Java's `new DecimalFormat("0.0‰").format(0.0123)` gives `"12,3‰"` under `de-
DE`, and PHP's `new NumberFormatter("en_US", NumberFormatter::PATTERN_DECIMAL, "0.0‰")` gives `"12.3‰"` because no
`PERMILL` constant exists.

`unitDisplay` selects register and decides whether plural forms apply at all:

| Unit                    | `long`                 | `short`             | `narrow`    |
| ----------------------- | ---------------------- | ------------------- | ----------- |
| `hour` (`1` / `2`)      | `1 hour` / `2 hours`   | `1 hr` / `2 hr`     | `1h` / `2h` |
| `byte` (`1` / `2`)      | `1 byte` / `2 bytes`   | `1 byte` / `2 byte` | `1B` / `2B` |
| `celsius` (`21.5`)      | `21.5 degrees Celsius` | `21.5°C`            | `21.5°C`    |
| `mile-per-hour` (`120`) | `120 miles per hour`   | `120 mph`           | `120mph`    |

Only `long` is reliably pluralized, and Polish and Russian pluralize across all forms (`1 godzina`, `2 godziny`, `5
godzin`), so `long` is the only form safe for text; `narrow` is for tables where the column header defines the unit.
Never concatenate a unit string — both `unitDisplay: "long"` and `currencyDisplay: "name"` need plural categories, which
is the domain of [intl-pluralization.md](intl-pluralization.md). `Intl.DisplayNames` does not cover units either: its
accepted types are `language`, `region`, `script`, `currency`, `calendar`, and `dateTimeField`, so `type: "measurement"`
throws a `RangeError`, while `new Intl.DisplayNames(["de"], { type: "currency" }).of("USD")` gives `"US-Dollar"` and
`type: "region"` on `"IN"` gives `"India"`. With `fallback: "none"`, an unknown code such as `"ZZZ"` returns `undefined`
instead of the code itself.

## Common Mistakes

| Mistake                                                  | Why It Breaks                                                                                                                              | Correct Approach                                                                                                                                                         |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `parseFloat` / `Number()` on a localized string          | `parseFloat("1.234,56")` → `1.234`, `Number("1,234.56")` → `NaN`, `parseFloat("1,234.56")` → `1`; all silent                               | Parse with the locale's own parser (`Intl` has none: use `parse_decimal`, `NumberFormatter::parse`, `NumberFormat.parse`, `decimal.Parse`) and validate the whole string |
| Hardcoding two decimal places for money                  | `JPY`, `KRW`, `VND`, `CLP`, `ISK`, `HUF`, `IDR`, `COP`, `IQD` have 0; `KWD`, `BHD`, `OMR`, `TND`, `JOD` have 3; `CLF`, `UYW` have 4        | Read `resolvedOptions().maximumFractionDigits`, `Currency.getDefaultFractionDigits()`, or `get_currency_precision(code)`                                                 |
| Treating ISO 4217's minor unit as the print format       | ISO says `IQD` = 3 and `HUF` = 2, but CLDR prints both with 0 digits and ICU follows CLDR                                                  | Take print digits from CLDR/ICU; use ISO minor units only for storage and validation                                                                                     |
| Storing money in `float` / `double` / `REAL`             | `0.1 + 0.2` = `0.30000000000000004`; `1.005 * 100` = `100.49999999999999`; `SUM` becomes order-dependent                                   | Integer minor units (`BIGINT` cents) or `DECIMAL`/`NUMERIC`/`BigDecimal`/`Decimal` constructed from strings                                                              |
| `toFixed()` or `Math.round(x * 100) / 100` for money     | `(1.005).toFixed(2)` → `"1.00"`; `(2.675).toFixed(2)` → `"2.67"`; float artifacts, not a rounding contract                                 | `Intl.NumberFormat` with an explicit `roundingMode`, or exact decimal arithmetic                                                                                         |
| Relying on the platform default rounding mode            | JS `Intl` defaults to `halfExpand`; Java, PHP, Python, Go, .NET default to half-even; PostgreSQL, MySQL, SQLite round ties away from zero  | Set `roundingMode` / `RoundingMode` / `rounding=` explicitly and assert the same mode in the ledger                                                                      |
| Assuming `$` identifies USD                              | `AUD`, `CAD`, `HKD`, `SGD`, `NZD`, `MXN`, `BRL`, `ARS`, `CLP`, `COP`, `TWD`, `USD` all use `$`, and `CAD` under `en-CA` prints as bare `$` | Use `currencyDisplay: "code"` for anything machine-read or multi-currency                                                                                                |
| Assuming `currencySign: "accounting"` yields parentheses | `en-US` and `ja-JP` parenthesize; `de-DE` and `it-IT` print a leading minus; `nl-NL` parenthesizes with the symbol inside                  | Read the rendered output per locale; never pattern-match `(` to detect negativity                                                                                        |
| Applying cash rounding to card and ledger amounts        | `CHF` cash rounds to 0.05 and `DKK` to 0.50, but the card is charged the exact amount                                                      | Keep cash and standard rounding as separate code paths; `roundingIncrement` only on the cash path                                                                        |
| Splitting a formatted number on `,` or `.`               | `fr-FR` uses U+202F, `sv-SE`/`ru-RU` use U+00A0, `ar-EG` uses `٬` U+066C                                                                   | Use `formatToParts` and read the `group` / `decimal` tokens                                                                                                              |
| Assuming a language implies its digit shapes             | `ar-AE`, `ar-DZ`, `ar-MA`, `ar-TN`, `ur-PK` resolve to `latn`, while `ar-EG`, `ar-SA`, `ar-IQ` resolve to `arab`                           | Read `resolvedOptions().numberingSystem` or set `numberingSystem` explicitly                                                                                             |
| Hardcoding `K` / `M` / `B` compact suffixes              | `de` does not abbreviate below 10⁶ (`1234` stays `1234`), `ja`/`zh` step at 10⁴, `hi`/`en-IN` use lakh and crore                           | Use `notation: "compact"` and let CLDR choose the magnitude and suffix                                                                                                   |
| Assuming `parseInt` / `Number` reject junk               | `parseFloat("1.234,56abc")` → `1.234`; Java `NumberFormat.parse("12abc")` → `12`; SQLite `DECIMAL(10,2)` stores `1.005` unchanged          | Validate with an anchored pattern and check the parse index or a `strict` flag                                                                                           |

## Checklist

1. Grep for `parseFloat`, `Number(`, `parseInt`, `toFixed`, `Math.round`, and hand-rolled separator regexes applied to
   user- or locale-derived numeric input, and replace each with a locale-aware parser or an explicit canonical-format
   contract.
2. Confirm every numeric input path parses with the request's resolved locale and rejects the whole string on failure — no
   prefix parsing, no `NaN` reaching storage.
3. Confirm every rendered number goes through `Intl.NumberFormat` (or the stack's equivalent) and that no output string
is assembled by concatenating digits with separators.
4. For each currency in the system, verify the printed fraction-digit count comes from CLDR/ICU and the storage scale
comes from the ISO 4217 minor unit, and document any divergence (`IQD`, `HUF`, `MGA`, `MRU`, `IDR`, `COP`, `CLP`,
`VND`).
5. Verify monetary storage is integer minor units or an exact decimal type, and that no `float`, `double`, `REAL`, or
untyped JSON number carries an amount end to end.
6. Confirm every `Decimal`/`BigDecimal` construction from a literal or payload uses a string, not a float, and that
`DECIMAL(p,s)` columns have a scale at least as large as the largest currency exponent they hold.
7. Pin the rounding mode explicitly at every rounding site (JS `roundingMode`, Java `RoundingMode`, .NET
`MidpointRounding`, Python `decimal` context, SQL `ROUND` semantics) and assert that client and server agree on a `2.5`
case.
8. Verify cash rounding exists as a separate path for `CHF`, `CAD`, `DKK`, `HUF`, and `MRU` if those currencies are
accepted, and that standard rounding is used for card, ledger, and API amounts.
9. Confirm `$`-ambiguous currencies (`CAD`, `AUD`, `HKD`, `SGD`, `NZD`, `MXN`, `BRL`, `ARS`, `CLP`, `COP`, `TWD`) render
with `currencyDisplay: "code"` wherever more than one currency can appear.
10. Verify negative amounts render per locale (`currencySign: "accounting"` only where the locale supports it) and that
no code branches on `(` to detect negativity.
11. Confirm percentage values are stored as ratios where `style: "percent"` is used and as percentages where `style:
"unit", unit: "percent"` is used, and that no value is multiplied by 100 twice.
12. Verify compact counts come from `notation: "compact"` rather than a hardcoded suffix table, and spot-check `1234`,
`12345`, `1234567`, and `100000000` in `en`, `de`, `ja`, `zh`, `hi`, and `en-IN`.
13. Confirm every unit string comes from `style: "unit"` with a `unitDisplay` chosen for its context, that no unit is
concatenated, and that no code depends on `permille` or a unit name outside `Intl.supportedValuesOf("unit")`.
14. Verify digit shapes are read from `resolvedOptions().numberingSystem` or set explicitly, and that the app does not
infer a digit table from the language subtag.
15. Confirm the number and currency test matrix covers `en-US`, `de-DE`, `fr-FR`, `en-IN`, `ja-JP`, `ar-EG`, and `fa-IR`
with both a zero-decimal and a three-decimal currency — see [intl-testing-and-qa.md](intl-testing-and-qa.md).

## References

- ECMA-402, `SetNumberFormatDigitOptions` — normative rules for `roundingIncrement`, `roundingMode`, `roundingPriority`,
  and `trailingZeroDisplay`: https://tc39.es/ecma402/#sec-setnumberformatdigitoptions
- ECMA-402, `NumberFormat` objects — the `style`/`notation`/`signDisplay`/`currencySign` option sets and their defaults:
  https://tc39.es/ecma402/#numberformat-objects
- Unicode TR35 Part 3 (Numbers) — `numberingSystems`, `minimumGroupingDigits`, and `currencyData/fractions` with `digits`,
  `rounding`, `cashDigits`, `cashRounding`:
  https://www.unicode.org/reports/tr35/tr35-numbers.html#Supplemental_Currency_Data
- ISO 4217 currency list one (XML) from SIX — authoritative `CcyMnrUnts`, including the `N.A.` entries for `XXX`, `XTS`,
  and metals: https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml
- Unicode CLDR `supplementalData.xml` — the `currencyData/fractions` source that ICU and every formatting library follow:
  https://github.com/unicode-org/cldr/blob/main/common/supplemental/supplementalData.xml
- MDN, `Intl.NumberFormat` — option reference and `formatToParts` token types: https://developer.mozilla.org/en-
  US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat
- MDN, `Intl.DisplayNames` — the accepted `type` values (`language`, `region`, `script`, `currency`, `calendar`,
  `dateTimeField`): https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DisplayNames
- Python `decimal` — rounding modes, context precision, and the float-construction warning: https://docs.python.org/3/library/decimal.html
- Babel numbers API — `format_currency`, `format_compact_decimal`, `parse_decimal` with `strict` and `numbering_system`:
  https://babel.pocoo.org/en/latest/api/numbers.html
- PHP intl `NumberFormatter` — `CURRENCY`, `CURRENCY_ACCOUNTING`, `CASH_CURRENCY`, `ROUNDING_INCREMENT`, `GROUPING_SIZE`,
  `SECONDARY_GROUPING_SIZE`: https://www.php.net/manual/en/class.numberformatter.php
- Java `DecimalFormat` — single grouping size, `setRoundingMode`, and `setParseBigDecimal`:
  https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/text/DecimalFormat.html
- Java `Currency` — `getDefaultFractionDigits` and the JDK's own ISO 4217 table:
  https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Currency.html
- Go `golang.org/x/text/currency` — `Standard`, `Cash`, and `Accounting` rounding kinds, `Symbol`/`NarrowSymbol`/`ISO`
  formatters, `FromRegion`, `Query`: https://pkg.go.dev/golang.org/x/text/currency
- Go `golang.org/x/text/number` — `Decimal`, `Percent`, `PerMille`, `Scientific`, `Engineering`, and
  `Scale`/`Precision`/`IncrementString`: https://pkg.go.dev/golang.org/x/text/number
- PostgreSQL math functions — `round(numeric)` ties away from zero vs platform-dependent `round(double precision)`:
  https://www.postgresql.org/docs/current/functions-math.html
- MySQL, precision math — `DECIMAL` exact arithmetic versus approximate floating-point literals:
  https://dev.mysql.com/doc/refman/8.4/en/precision-math-decimal-characteristics.html

