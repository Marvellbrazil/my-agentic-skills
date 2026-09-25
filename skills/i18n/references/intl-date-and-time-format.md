# Dates, Times, Time Zones, and Calendars

This module covers the gap between an instant on the UTC timeline and the wall-clock date a user reads. Getting it wrong
produces off-by-one-day values, meetings that shift by an hour twice a year, years rendered in the wrong era, and week
numbers that disagree between a US and a German office. Every failure here is silent: the string is well-formed and only
a human in the affected locale notices it is wrong.

## When This Applies

- Any timestamp is stored, transmitted, or rendered for a user.
- A date picker, calendar, scheduling, booking, expiry, trial, or billing-cycle feature is built.
- A "last updated", "posted on", "3 hours ago", or countdown label is produced.
- A duration, interval, or time span is displayed ("1 hr 30 min", "Mar 29 – 31").
- A non-Gregorian calendar is in play: Islamic, Hebrew, Buddhist, Japanese era, Persian, Indian, ROC, Chinese, Coptic, Ethiopic.
- Week numbers, fiscal weeks, or a first-day-of-week grid is rendered.
- Data crosses a DST transition, a zone rename, or a zone rule change.
- A date with no time component is stored or compared (birthdays, holidays, invoice dates), or a locale's default
  calendar, hour cycle, or digit system differs from the developer's own.

## Instants, Offsets, Time Zones, and Wall-Clock Time

Four different things get called "a date", and conflating them is the root cause of most date bugs.

| Concept         | What it is                                           | Example                | Stored as                    |
| --------------- | ---------------------------------------------------- | ---------------------- | ---------------------------- |
| Instant         | A point on the UTC timeline, independent of location | `2026-03-29T12:00:00Z` | epoch seconds, `timestamptz` |
| Offset          | A fixed distance from UTC, valid only at a moment    | `+05:45`               | never authoritative alone    |
| Time zone       | A region's rules mapping instants to offsets         | `Asia/Kathmandu`       | IANA ID string               |
| Wall-clock time | What a local clock reads, with no zone               | `2026-03-29 17:45`     | `timestamp`, `PlainDateTime` |

**Store instants in UTC; render in a zone.** The offset is an output of a zone at an instant, not an input. Persisting
`2026-03-29T12:00:00+05:45` discards the zone, so a later rule change cannot be applied. Persist the IANA ID next to the
instant, or use a format that carries both.

```js
// RFC 9557 / IXDTF: instant + offset + zone + calendar in one string.
// Temporal parses this; Intl.DateTimeFormat cannot.
const meeting = Temporal.ZonedDateTime.from(
  "2026-03-29T12:00:00+05:45[Asia/Kathmandu]",
);
meeting.toInstant().toString(); // '2026-03-29T06:15:00Z'
```

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# aware and unambiguous — an instant
datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc).astimezone(
    ZoneInfo("Asia/Kathmandu")
).isoformat()  # '2026-03-29T17:45:00+05:45'
```

### IANA identifiers versus fixed offsets

- Use `Area/Location` IDs (`America/New_York`, `Asia/Kathmandu`), never abbreviations. `EST` is not an IANA ID; ICU 78.3
  resolves it to the unrelated `America/Panama`, and it cannot express DST.
- `Etc/GMT+5` means **UTC−05:00**. The sign is inverted against ISO 8601, a legacy POSIX convention. Prefer `Etc/UTC` or the zone you actually mean.
- Identifiers get renamed and merged. `Asia/Calcutta`/`Asia/Kolkata` and `Asia/Katmandu`/`Asia/Kathmandu` are equivalent
  pairs. ECMAScript treats equivalents as the same zone, so `id1 === id2` is the wrong equivalence test; engines
  canonicalize on output (`resolvedOptions().timeZone` rewrites `Asia/Kathmandu` to `Asia/Katmandu`).
- `Intl.supportedValuesOf('timeZone')` returns canonical IDs only (418 on ICU 78.3) and does **not** include `'UTC'`, so
  never validate user-supplied zones against that list. A fixed-offset string is accepted where a zone is expected
  (`timeZone: '+05:30'`), but a numeric offset is never equivalent to an IANA zone and carries no DST rules.

## Formatting with Intl and CLDR Skeletons

`Intl.DateTimeFormat` resolves patterns from CLDR. Its four named widths are not "short and long versions of the same
thing" — they select different field sets, and which fields appear differs per locale.

| Style    | Fields CLDR intends                 | Where it belongs                                     |
| -------- | ----------------------------------- | ---------------------------------------------------- |
| `full`   | weekday + month name + day + year   | Detail pages, receipts, anywhere the weekday matters |
| `long`   | month name + day + year, no weekday | Headings, prose, event titles                        |
| `medium` | abbreviated month + day + year      | Tables, cards, log rows — the default choice         |
| `short`  | all-numeric, year may be 2-digit    | Dense grids, mobile, calendars                       |

The same four styles, resolved from real CLDR data:

| Locale  | `full`                            | `long`         | `medium`      | `short`    |
| ------- | --------------------------------- | -------------- | ------------- | ---------- |
| `en-US` | Sunday, March 29, 2026            | March 29, 2026 | Mar 29, 2026  | 3/29/26    |
| `en-GB` | Sunday, 29 March 2026             | 29 March 2026  | 29 Mar 2026   | 29/03/2026 |
| `de-DE` | Sonntag, 29. März 2026            | 29. März 2026  | 29.03.2026    | 29.03.26   |
| `th-TH` | วันอาทิตย์ที่ 29 มีนาคม พ.ศ. 2569 | 29 มีนาคม 2569 | 29 มี.ค. 2569 | 29/3/69    |

`th-TH` renders the Buddhist year 2569 and `ar-EG` uses Arabic-Indic digits — both are CLDR defaults for the locale, not
opt-ins. `medium` and `long` are identical in some locales (`fr-FR`), so never infer the style from the output.

### Skeletons and why Intl has no skeleton option

A CLDR _skeleton_ names the fields you want in canonical order (`yMMMd`, `Hm`, `MMMMy`); CLDR returns the pattern that
expresses them in a locale. Skeletons carry no order or punctuation — the resolved pattern supplies both. Two special
letters: `j` resolves to the locale's preferred hour cycle, `C` to the preferred day-period style.

```js
const d = new Date("2026-03-29T12:00:00Z");
// Intl has NO skeleton option — `skeleton` is silently ignored and you
// get the default pattern ('3/29/2026'), not 'Mar 29, 2026'.
new Intl.DateTimeFormat("en", { skeleton: "yMMMd" }).format(d);
// Request fields instead; CLDR matches them to the closest pattern.
new Intl.DateTimeFormat("en", {
  year: "numeric",
  month: "short",
  day: "numeric",
}).format(d); // 'Mar 29, 2026'
```

Skeleton resolution exists only through ICU:

```php
// PHP 8.1+. Passing a skeleton where a PATTERN is expected produces
// garbage: IntlDateFormatter with "yMd" as the pattern renders '2026329'.
$pattern = (new IntlDatePatternGenerator('de_DE'))->getBestPattern('yMMMd'); // 'd. MMM y'
echo (new IntlDateFormatter('de_DE', IntlDateFormatter::NONE, IntlDateFormatter::NONE,
    'Europe/Berlin', IntlDateFormatter::GREGORIAN, $pattern
))->format(new DateTimeImmutable('2026-03-29T12:00:00Z')); // '29. März 2026'
```

Java reaches the same generator via `DateTimeFormatterBuilder.getLocalizedDateTimePattern(...)`; ICU4J exposes
`DateTimePatternGenerator.getBestPattern(String)`, ICU4C `udatpg_getBestPattern`. Java's pattern alphabet is separate
from CLDR skeletons (`yyyy` vs `y`, `XXX` for offset, `VV` for zone ID) and must not be mixed with them.

### Rules the constructor enforces

- `dateStyle`/`timeStyle` cannot combine with component options or with `timeZoneName` — mixing throws `TypeError`.
- `hour12` overrides `hourCycle`. `fractionalSecondDigits` accepts only `1`, `2`, `3`; `4` throws `RangeError`. `era`
  accepts `'long' | 'short' | 'narrow'`; `'numeric'` throws.
- An unknown _calendar_ is silently ignored and falls back to `gregory`; an unknown _time zone_ throws `RangeError`.
  Unknown option keys (`week`, `skeleton`, typos) are ignored silently, so verify with `resolvedOptions()`.
- `formatRange()` does not sort or validate: a reversed range prints reversed (`3/30/26 – 3/29/26`) and a non-Date
  argument is coerced through `Number`; `undefined` throws. `resolvedOptions()` omits the component styles `dateStyle`
  expands to, so its output can be fed back into the constructor.

## Calendars, Eras, and Week Numbering

### The calendar set

`Intl.supportedValuesOf('calendar')` on ICU 78.3 returns exactly: `buddhist`, `chinese`, `coptic`, `dangi`, `ethioaa`,
`ethiopic`, `gregory`, `hebrew`, `indian`, `islamic`, `islamic-civil`, `islamic-rgsa`, `islamic-tbla`, `islamic-
umalqura`, `iso8601`, `japanese`, `persian`, `roc`.

| Locale tag                    | Output for `2026-03-29T12:00:00Z` |
| ----------------------------- | --------------------------------- |
| `ar-SA-u-ca-islamic-umalqura` | الأحد، ١٠ شوال ١٤٤٧ هـ            |
| `he-IL-u-ca-hebrew`           | יום ראשון, י״א בניסן תשפ״ו        |
| `ja-JP-u-ca-japanese`         | 令和8年3月29日日曜日              |
| `th-TH-u-ca-buddhist`         | วันอาทิตย์ที่ 29 มีนาคม พ.ศ. 2569 |
| `hi-IN-u-ca-indian`           | रविवार, 8 चैत्र 1948 शक           |
| `zh-TW-u-ca-roc`              | 民國115年3月29日 星期日           |

Several calendars are the CLDR default for their locale and apply with no opt-in, and the mapping is not the one you
would guess: `th-TH` resolves to `buddhist` and `fa-IR` to `persian`, while `ja-JP`, `ar-SA`, and `he-IL` all resolve to
`gregory`. Never infer the calendar from the language subtag.

The four Islamic sub-calendars are not interchangeable — on one instant `islamic` and `islamic-civil` give Shawwal 10,
1447 while `islamic-tbla` gives Shawwal 11. Pick the market's variant (`islamic-umalqura` for Saudi Arabia) and never
let it default. The `iso8601` calendar is not "gregory with ISO formatting": it suppresses month names in some widths,
so `dateStyle: 'long'` yields `'2026  29'` with a double space where the month name would be.

### Eras

Eras are not a cosmetic suffix — they carry the year. Japanese era years restart at 1, so `year` alone is ambiguous across an era boundary.

```js
const eraFmt = (iso) =>
  new Intl.DateTimeFormat("en-US", {
    calendar: "japanese",
    year: "numeric",
    era: "long",
  }).format(new Date(iso));
eraFmt("2019-04-30T12:00:00Z"); // 'April 30, 31 Heisei'
eraFmt("2019-05-01T12:00:00Z"); // 'May 1, 1 Reiwa'
```

Read the era back with `formatToParts()` (part type `era`) rather than string-matching the output. Java separates era
from year-of-era: `JapaneseDate.get(ChronoField.YEAR_OF_ERA)` is `8` while `ChronoField.YEAR` is `2026`. In Temporal,
`date.era`/`date.eraYear` are `undefined` for the ISO calendar and populated for `japanese` (`'reiwa'`, `8`).

### Week numbering and the first-day-of-week problem

There is no universal week. ISO 8601 defines week 1 as the week containing the year's first Thursday, with weeks
starting Monday. CLDR stores per-territory `firstDay` and `minDays`, and the web API that exposes it changed.

```js
new Intl.Locale("en-US").getWeekInfo(); // { firstDay: 7, weekend: [6, 7] }
new Intl.Locale("de-DE").getWeekInfo(); // { firstDay: 1, weekend: [6, 7] }
new Intl.Locale("fa-IR").getWeekInfo(); // { firstDay: 6, weekend: [5] }
new Intl.Locale("hi-IN").getWeekInfo(); // { firstDay: 7, weekend: [7] }
```

`firstDay` is 1 = Monday through 7 = Sunday. `weekend` is an array and is not always two contiguous days. `minimalDays`
was **removed** from this object (tc39/proposal-intl-locale-info PR #99, shipped from Chrome 136), so reading it now
yields `undefined` — do not assume `1`. Firefox does not implement `getWeekInfo()` at all, so feature-detect it, and
fall back to the older accessor spelling `weekInfo` where only that exists. Java still exposes the value the web API
dropped:

```java
WeekFields.of(Locale.forLanguageTag("de-DE")).getMinimalDaysInFirstWeek(); // 4
WeekFields.of(Locale.US).getMinimalDaysInFirstWeek();                      // 1
WeekFields.ISO.getMinimalDaysInFirstWeek();                                // 4
```

The ISO week _year_ is not the calendar year, and this is where week numbers break:

| Gregorian date   | ISO week   | ISO week-year |
| ---------------- | ---------- | ------------- |
| 2025-12-29 (Mon) | 2026-W01-1 | 2026          |
| 2026-01-01 (Thu) | 2026-W01-4 | 2026          |
| 2026-12-31 (Thu) | 2026-W53-4 | 2026          |
| 2027-01-01 (Fri) | 2026-W53-5 | 2026          |
| 2027-01-04 (Mon) | 2027-W01-1 | 2027          |

Always emit the week-year next to the week number (`2026-W53`), never the calendar year. Python's `date.isocalendar()`
returns `IsoCalendarDate(year=2026, week=53, weekday=5)` for `2027-01-01` — that `year` is the week-year. In Temporal,
`weekOfYear`/`yearOfWeek` follow ISO rules and are `undefined` for calendars without a defined week system (verified for
`hebrew` and `japanese`). `Intl.DateTimeFormat` has a `week` option in the specification but no engine implements it: it
is silently ignored and the formatter renders as if it were absent.

## Relative Time, Durations, and Intervals

Relative formatting must be computed against the _user's_ zone, not the server's, or "today" is wrong for a third of the world at any moment.

```js
const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
rtf.format(-1, "day"); // 'yesterday'
rtf.format(0, "day"); // 'today'
rtf.format(2, "week"); // 'in 2 weeks'
rtf.format(-1, "quarter"); // 'last quarter'
new Intl.RelativeTimeFormat("en", { numeric: "auto", style: "narrow" }).format(
  -2,
  "day",
); // '2d ago'
```

- Valid units are `year`, `quarter`, `month`, `week`, `day`, `hour`, `minute`, `second` (plural forms accepted). `'fortnight'` throws `RangeError`.
- `numeric: 'auto'` substitutes idiomatic words, and only for the units that have them: `format(0, 'day')` is `'today'`
  but `format(0, 'second')` is `'now'`. With `numeric: 'always'` both become `'in 0 …'`.
- Pluralization is CLDR-driven across languages with three or more forms: `ru` gives `2 недели назад` and `5 недель
  назад`; `pl` gives `2 tygodnie temu` and `5 tygodni temu`. Never build the unit string yourself — see [intl-
  pluralization.md](intl-pluralization.md).

Durations are a different type from relative time and get their own formatter. `Intl.DurationFormat` is Baseline Newly
available since 2025-03-04 (Chrome/Edge 129, Firefox 136, Safari 16.4).

```js
const df = (style, v) => new Intl.DurationFormat("en", { style }).format(v);
df("long", { hours: 1, minutes: 30 }); // '1 hour, 30 minutes'
df("short", { hours: 1, minutes: 30 }); // '1 hr, 30 min'
df("narrow", { hours: 1, minutes: 30 }); // '1h 30m'
df("digital", { hours: 1, minutes: 2, seconds: 3 }); // '1:02:03'
new Intl.DurationFormat("en", { hoursDisplay: "always" }).format({
  minutes: 30,
}); // '0 hr, 30 min'
```

Per-unit options are
`years`/`months`/`weeks`/`days`/`hours`/`minutes`/`seconds`/`milliseconds`/`microseconds`/`nanoseconds`, each accepting
`'long' | 'short' | 'narrow' | 'numeric' | '2-digit'`, plus a matching `…Display` of `'auto' | 'always'`. `hoursDisplay:
'always'` is what turns a partial duration into a clock readout, and `style: 'digital'` is the only style that produces
a clock string. Feature-detect with `typeof Intl.DurationFormat !== 'undefined'` and fall back to extracting balanced
unit fields.

Intervals use `formatRange()`, which elides fields the endpoints share, and `formatRangeToParts()` labels each part
`shared`, `startRange`, or `endRange` for styling and truncation:

```js
const range = new Intl.DateTimeFormat("en-US", { dateStyle: "medium" });
range.formatRange(
  new Date("2026-03-29T12:00:00Z"),
  new Date("2026-03-31T12:00:00Z"),
); // 'Mar 29 – 31, 2026'
```

## DST Transitions, Ambiguity, and Date-Only Values

### Offset transitions make local-to-instant conversion a partial function

Exact → local is always 1:1. Local → exact is not: during a spring-forward transition some local times do not exist, and
during a fall-back transition some occur twice. `America/New_York` 2026: `2026-03-08 02:00–02:59` does not exist;
`2026-11-01 01:00–01:59` occurs twice. `Australia/Lord_Howe` shifts by 30 minutes, not 60, so never hardcode a one-hour
assumption. Worse, the runtimes disagree about a nonexistent local time — and two of them disagree about the _instant_,
not just the label:

| Runtime                                 | `2026-03-08 02:30 America/New_York` becomes   | Instant  |
| --------------------------------------- | --------------------------------------------- | -------- |
| JS `new Date(2026, 2, 8, 2, 30)`        | `03:30 −04:00` (normalized forward)           | `07:30Z` |
| Java `LocalDateTime.atZone`             | `03:30 −04:00` (normalized forward)           | `07:30Z` |
| Python `zoneinfo`                       | `02:30 −05:00` (label kept, offset imaginary) | `07:30Z` |
| Go `time.Date`                          | `01:30 −05:00`                                | `06:30Z` |
| Temporal `disambiguation: 'compatible'` | `03:30 −04:00`                                | `07:30Z` |
| Temporal `disambiguation: 'earlier'`    | `01:30 −05:00`                                | `06:30Z` |

Go's `time.Date` documentation is explicit that it "returns a time that is correct in one of the two zones involved in
the transition, but it does not guarantee which". Java's `atZone` normalizes forward; Python's `zoneinfo` keeps the
wall-clock label and assigns an offset, producing the same instant as Java but a different string. For repeated hours
Python needs `fold`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

ny = ZoneInfo("America/New_York")
a = datetime(2026, 11, 1, 1, 30, tzinfo=ny, fold=0)  # -04:00
b = datetime(2026, 11, 1, 1, 30, tzinfo=ny, fold=1)  # -05:00
a == b                        # True  — PEP 495 keeps them equal
a.astimezone(ZoneInfo("UTC")) # 05:30Z
b.astimezone(ZoneInfo("UTC")) # 06:30Z — an hour apart
```

That `==` returning `True` for two instants an hour apart is the trap: `fold` changes the offset but not the comparison,
so sorting or de-duplicating these silently drops a distinct instant. Java resolves the same ambiguity through the
offset argument, and rejects an impossible one:

```java
ZoneId ny = ZoneId.of("America/New_York");
ZonedDateTime.ofLocal(LocalDateTime.of(2026, 11, 1, 1, 30), ny, ZoneOffset.ofHours(-4)); // earlier
ZonedDateTime.ofLocal(LocalDateTime.of(2026, 11, 1, 1, 30), ny, ZoneOffset.ofHours(-5)); // later
ZonedDateTime.ofStrict(LocalDateTime.of(2026, 11, 1, 1, 30), ZoneOffset.ofHours(-6), ny);
// DateTimeException: ZoneOffset '-06:00' is not valid for LocalDateTime ...
```

Temporal makes the choice an explicit option. `ZonedDateTime.from` takes `disambiguation: 'compatible' | 'earlier' |
'later' | 'reject'` (default `'compatible'` — `'earlier'` for a repeated hour, `'later'` for a gap) and `offset: 'use' |
'ignore' | 'prefer' | 'reject'` (default `'reject'` on `from()`, `'prefer'` on `with()`). DST-safe arithmetic is the
reason to prefer a zone-aware type: adding a _day_ keeps the wall-clock time, adding _hours_ keeps the elapsed duration.

```js
Temporal.ZonedDateTime.from("2026-03-08T02:30[America/New_York]").toString();
// '2026-03-08T03:30:00-04:00[America/New_York]'  (compatible → later)
Temporal.ZonedDateTime.from("2026-03-08T02:30[America/New_York]", {
  disambiguation: "earlier",
}).toString();
// '2026-03-08T01:30:00-05:00[America/New_York]'

const base = Temporal.ZonedDateTime.from("2026-03-07T12:00[America/New_York]");
base.add({ days: 1 }).toString(); // '2026-03-08T12:00:00-04:00[...]'
base.add({ hours: 24 }).toString(); // '2026-03-08T13:00:00-04:00[...]'
base.until(base.add({ days: 1 }), { largestUnit: "hours" }).toString(); // 'PT23H'
```

Temporal is Stage 4 and part of ES2026. Firefox 139 (2025-05-27), Chrome/Edge 144 (2026-01), and Node 26 (2026-05-05)
ship it; **Safari stable has not**. Feature-detect `typeof Temporal !== 'undefined'` and load `@js-temporal/polyfill`
when absent.

### Date-only values and the off-by-one-day bug

A date with no time is not an instant. `birth_date`, `invoice_date`, and `holiday` must be stored as a date type, not as
midnight UTC, or every render west of UTC loses a day.

```js
// Date-only strings parse as UTC midnight; date-time strings without a
// zone parse in the host zone. The asymmetry is a spec quirk, not a bug.
Date.parse("2026-03-29"); // 1774742400000 → 2026-03-29T00:00:00Z
Date.parse("2026-03-29T00:00:00"); // parsed in the host zone

// With the host zone at UTC−07:00 the same value is "yesterday" locally:
new Date("2026-03-29").getDate(); // 28
new Date("2026-03-29").toLocaleDateString(); // '3/28/2026'
```

The fix is to keep the value out of the instant pipeline entirely: store a date type, compare date-to-date, and when a
`Date` object is unavoidable format it with explicit fields plus `timeZone: 'UTC'`. The SQL types encode exactly this
distinction:

```sql
-- `date` has no time and no zone; `timestamptz` is an instant.
SELECT DATE '2026-03-29' AS date_only,
       TIMESTAMPTZ '2026-03-29 12:00:00+00' AT TIME ZONE 'America/New_York' AS local_wall;
-- 2026-03-29 | 2026-03-29 08:00:00
```

PostgreSQL `timestamp with time zone` stores UTC and converts on output while `timestamp without time zone` does not;
MySQL converts `TIMESTAMP` between the session `time_zone` and UTC on write and read but never touches `DATETIME`; SQL
Server `datetimeoffset` stores UTC and preserves the offset while `datetime`/`datetime2` carry no offset and `datetime`
is DST-unaware. Choosing the wrong column is the same bug one layer down.

### ISO 8601 versus locale-formatted output

Keep the two apart; mixing them is how `2026-03-29` ends up in a UI and `03/29/2026` ends up in a log parser.

| Use ISO 8601 / RFC 3339                         | Use locale formatting              |
| ----------------------------------------------- | ---------------------------------- |
| API request and response bodies                 | Anything a human reads             |
| Logs, traces, filenames, cache keys, sort keys  | Tables, cards, labels, tooltips    |
| Database columns, message payloads, interchange | Emails, PDFs, screenshots, exports |

ISO 8601 output is a fixed string needing no CLDR data: `toISOString()`, Python `datetime.isoformat()`, Go
`time.RFC3339`, Java `DateTimeFormatter.ISO_INSTANT`, `AT TIME ZONE 'UTC'` in SQL. Locale output must go through CLDR:
`Intl.DateTimeFormat`, Python `babel.dates.format_skeleton`, PHP `IntlDateFormatter`, Java
`DateTimeFormatter.ofLocalizedDate(...)`. Note that `Intl`'s `iso8601` _calendar_ is not an ISO 8601 _serializer_ — it
is a CLDR calendar whose year aligns with Gregorian but which may omit month names.

## Common Mistakes

| Mistake                                                                                                               | Why It Breaks                                                                                                                  | Correct Approach                                                                                         |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| Storing `timestamp without time zone` for events                                                                      | It is a wall-clock reading with no zone, so after a DST or rule change it denotes a different instant                          | Store UTC (`timestamptz`, epoch, `Instant`) plus the IANA zone ID                                        |
| Storing a fixed offset like `+05:45` as "the time zone"                                                               | Offsets have no rules; future DST or zone changes cannot be applied, and two zones sharing an offset become indistinguishable  | Store the IANA ID; treat the offset as derived output                                                    |
| Using `EST`/`PST`/`CET` as a zone                                                                                     | Not IANA IDs; ICU resolves `EST` to `America/Panama` and DST is lost                                                           | Use `America/New_York`, `Europe/Berlin`, or `Etc/GMT±N` with the sign inversion in mind                  |
| Hand-rolling a format string like `DD/MM/YYYY`                                                                        | Field order, separators, month names, year length, and digit system are all locale data                                        | Request CLDR fields or a named style; resolve skeletons with ICU when a combination is needed            |
| Storing a birthday as midnight UTC and rendering it in the user's zone                                                | The instant lands on the previous calendar day west of UTC (`new Date('2026-03-29').getDate()` is `28` at UTC−07:00)           | Store a date-only type and format with `timeZone: 'UTC'` or `Temporal.PlainDate`                         |
| Passing a CLDR skeleton where a format _pattern_ is expected                                                          | Skeletons carry no order or punctuation, so `yMd` is emitted literally as `2026329`                                            | Run it through `DateTimePatternGenerator.getBestPattern` (PHP `IntlDatePatternGenerator`, ICU4J/C) first |
| Assuming `Intl.DateTimeFormat` has a `skeleton` or `week` option                                                      | Neither is implemented; unknown keys are ignored silently and you get the default pattern                                      | Request explicit fields; compute weeks from `getWeekInfo()` plus ISO week rules                          |
| Emitting the ISO week number next to the calendar year                                                                | ISO week-years diverge at both ends: `2027-01-01` is `2026-W53-5`                                                              | Print `weekOfYear` with `yearOfWeek` (`2026-W53`), never with `year`                                     |
| Reading `getWeekInfo().minimalDays`                                                                                   | Removed from the spec (Chrome 136+); the field is `undefined`, and `getWeekInfo` is absent in Firefox                          | Use `firstDay` only; get `minimalDays` from `WeekFields` (Java) or CLDR data                             |
| Treating a repeated local hour as one instant                                                                         | In `2026-11-01 01:30 America/New_York` two instants exist an hour apart, and Python's `fold=0`/`fold=1` datetimes compare `==` | Resolve explicitly (`fold`, `disambiguation`, `ofLocal`) and compare instants in UTC                     |
| Assuming a DST shift is always one hour                                                                               | `Australia/Lord_Howe` shifts 30 minutes; zones have shifted 2 hours or changed offset permanently                              | Derive the offset from the zone at that instant; never use a constant                                    |
| Letting Go's `time.Date` resolve a user-entered local time                                                            | For nonexistent times it returns whichever zone it happens to pick — a different instant than Java, Python, or Temporal        | Validate the local time against the zone's transitions before converting                                 |
| Formatting the year without the era for `japanese`                                                                    | Era years restart at 1, so `2019-04-30` is Heisei 31 and `2019-05-01` is Reiwa 1                                               | Emit `era` with `year` and read it from `formatToParts()`, not by string matching                        |
| Letting the calendar default from the language subtag                                                                 | `ja-JP` resolves to `gregory` while `th-TH` resolves to `buddhist`; `islamic` and `islamic-tbla` disagree by a day             | Pass the calendar explicitly (`u-ca-…` or `calendar:`) and pick the market's variant                     |
| Computing relative labels from the server's zone                                                                      | "Today" and "yesterday" are user-relative; a UTC server is a day off for much of the world                                     | Compare the instant against the user's zone before choosing the unit                                     |
| Building "3 days ago" or "1 hr 30 min" by concatenation                                                               | Word choice and plural forms are CLDR data spanning many plural categories                                                     | Use `Intl.RelativeTimeFormat` and `Intl.DurationFormat`, with feature detection for the latter           |
| Trusting `formatRange(a, b)` argument order, or calling `toLocaleDateString()` with no arguments on a date-only value | The formatter neither sorts nor validates its arguments, and the no-argument call applies the host zone                        | Validate `a <= b` before formatting; always pass `timeZone: 'UTC'` or the user's zone explicitly         |

## Checklist

1. Confirm every stored temporal value is classified as exactly one of instant, wall-clock time, or date-only, that the
   column type matches (`timestamptz`/`Instant`, `timestamp`/`PlainDateTime`, `date`/`PlainDate`), and that each event
   carries an IANA zone ID next to the instant.
2. Grep for zone abbreviations (`EST`, `PST`, `CET`, `GMT+`, `UTC+`) and replace each with an IANA ID or an explicit `Etc/GMT±N`.
3. Grep for hand-written display format strings (`DD/MM/YYYY`, `%d/%m/%Y`, `yyyy-MM-dd` outside interchange paths) and
replace them with CLDR field requests or named styles.
4. Verify no code passes a CLDR skeleton where a format pattern is expected, and that every skeleton goes through ICU's best-pattern generator.
5. Confirm ISO 8601 / RFC 3339 is used only for interchange, logs, keys, and sort order, and that all human-facing output goes through a locale formatter.
6. Check that date-only values are stored as a date type and formatted with `timeZone: 'UTC'` or as a `PlainDate`.
7. Verify the calendar is set explicitly wherever the market is not Gregorian, and that Islamic sub-calendars (`islamic-
umalqura` vs `islamic-tbla`) are chosen deliberately.
8. Confirm era and year are emitted together for any calendar whose era resets the year, and that the era is read from structured parts.
9. Verify week numbers are emitted with the ISO week-year and that `getWeekInfo()` is feature-detected rather than assumed.
10. Confirm first-day-of-week and weekend days come from locale data rather than a hardcoded Monday or Sunday.
11. Verify DST ambiguity is resolved explicitly (`fold`, `disambiguation`, `ofLocal`) and that comparisons happen on instants in UTC.
12. Check that no code relies on a runtime's unspecified handling of nonexistent local times, in particular Go's `time.Date`.
13. Confirm duration and relative-time strings are produced by `Intl.DurationFormat` / `Intl.RelativeTimeFormat` (with
feature detection) rather than by concatenation, and that relative labels are computed against the user's zone.
14. Verify `formatRange` arguments are ordered before formatting, and that interval output is never parsed for meaning.
15. Freeze the time zone and the ICU/CLDR data in tests and assert expected strings for at least one positive and one
negative offset — see [intl-testing-and-qa.md](intl-testing-and-qa.md).
16. Verify RTL date rendering and any Arabic-Indic or other numbering-system digits the locale produces by default — see
[intl-bidi.md](intl-bidi.md) and [intl-number-and-currency.md](intl-number-and-currency.md).
17. Confirm sorting and grouping by date uses the instant or the date-only value, not a locale-formatted string — see
[intl-collation-and-sorting.md](intl-collation-and-sorting.md).

## References

- ECMA-402, `Intl.DateTimeFormat` — options table, `formatRange`, `resolvedOptions`: https://tc39.es/ecma402/#datetimeformat-objects
- MDN, `Intl.DateTimeFormat`, `Intl.Locale.prototype.getWeekInfo()`, `Intl.DurationFormat`, `Intl.RelativeTimeFormat`:
  https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat ·
  https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/Locale/getWeekInfo ·
  https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DurationFormat ·
  https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/RelativeTimeFormat
- tc39/proposal-intl-locale-info — `minimalDays` removal (issue #86, PR #99): https://github.com/tc39/proposal-intl-locale-info/issues/86
- web.dev, `Intl.DurationFormat` becomes Baseline Newly available (2025-03-04): https://web.dev/blog/intl-durationformat-baseline
- CLDR / LDML Part 4, Dates — skeletons, `availableFormats`, `j`/`C` symbols, week data: https://unicode.org/reports/tr35/tr35-dates.html
- CLDR, Date/Time Patterns (skeleton-to-pattern examples per locale): https://cldr.unicode.org/translation/date-time/date-time-patterns
- ICU4J `DateTimePatternGenerator.getBestPattern` / ICU4C `udatpg_getBestPattern`: https://unicode-org.github.io/icu-
  docs/apidoc/released/icu4j/com/ibm/icu/text/DateTimePatternGenerator.html · https://unicode-org.github.io/icu-
  docs/apidoc/dev/icu4c/udatpg_8h.html
- PHP, `IntlDatePatternGenerator::getBestPattern` and the RFC that added it in 8.1:
  https://www.php.net/manual/en/intldatepatterngenerator.getbestpattern.php ·
  https://wiki.php.net/rfc/intldatetimepatterngenerator
- Java, `DateTimeFormatter`, `ZoneId`/`ZoneRules`, `WeekFields`:
  https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/time/format/DateTimeFormatter.html ·
  https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/time/ZoneId.html ·
  https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/time/temporal/WeekFields.html
- Python, `zoneinfo` and PEP 495 `fold`; `date.isocalendar`: https://docs.python.org/3/library/zoneinfo.html ·
  https://docs.python.org/3/library/datetime.html#datetime.date.isocalendar
- Go, `time` package (`time.Date` DST caveat, `LoadLocation`, `time/tzdata`) and issue #24551: https://pkg.go.dev/time ·
  https://github.com/golang/go/issues/24551
- IANA Time Zone Database: https://www.iana.org/time-zones
- RFC 3339 (timestamps) and RFC 9557 (IXDTF — `[America/New_York]`, `u-ca` suffix keys): https://www.rfc-
  editor.org/rfc/rfc3339.html · https://www.rfc-editor.org/rfc/rfc9557.html
- ISO 8601-1:2019 and ISO 8601-2:2019; ISO week date rule (week 1 contains the year's first Thursday):
  https://www.iso.org/standard/70907.html · https://www.iso.org/standard/70908.html ·
  https://en.wikipedia.org/wiki/ISO_week_date
- tc39/proposal-temporal (Stage 4, per-engine status) and its time-zone ambiguity docs: https://github.com/tc39/proposal-
  temporal · https://tc39.es/proposal-temporal/docs/ambiguity.html
- MDN, `Temporal.ZonedDateTime.from()` (`disambiguation`, `offset`) and `Temporal.PlainDate.prototype.weekOfYear`:
  https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Temporal/ZonedDateTime/from ·
  https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Temporal/PlainDate/weekOfYear
- PostgreSQL, Date/Time Types and `AT TIME ZONE`: https://www.postgresql.org/docs/current/datatype-datetime.html ·
  https://www.postgresql.org/docs/current/functions-datetime.html
- MySQL, DATE/DATETIME/TIMESTAMP types and session time zone support:
  https://dev.mysql.com/doc/refman/8.0/en/datetime.html · https://dev.mysql.com/doc/refman/8.0/en/time-zone-support.html
- SQL Server, `datetimeoffset` (UTC storage, offset preserved, `AT TIME ZONE`): https://learn.microsoft.com/en-
  us/sql/t-sql/data-types/datetimeoffset-transact-sql
- Babel, `babel.dates` (`format_skeleton`, `format_timedelta`, `get_timezone_name`): https://babel.pocoo.org/en/latest/dates.html

