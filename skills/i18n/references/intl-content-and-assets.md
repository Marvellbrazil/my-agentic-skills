# Content, Assets, and Cultural Adaptation

This module covers the content layer of internationalization: how translatable strings are keyed, stored, composed, and
round-tripped through a TMS, and how layout, imagery, and regional data survive translation into scripts and cultures
the source locale never anticipated. Getting it wrong is not cosmetic — concatenated strings produce ungrammatical
output in languages with different word order, US-shaped address and phone validation rejects legitimate users outright,
and machine-translated regulatory disclosures create legal exposure. These defects are invisible in the source locale
and appear only after a locale you do not read reaches production.

## Contents

- [When This Applies](#when-this-applies)
- [Message Catalogs, Key Strategy, and Version Control](#message-catalogs-key-strategy-and-version-control)
- [Message Composition, Placeholders, and Translator Context](#message-composition-placeholders-and-translator-context)
  - [Never concatenate or fragment sentences](#never-concatenate-or-fragment-sentences)
  - [Named versus positional arguments](#named-versus-positional-arguments)
  - [Escaping](#escaping)
  - [Translator context](#translator-context)
- [Layout Resilience and Text Expansion](#layout-resilience-and-text-expansion)
- [Cultural Adaptation and Regional Data](#cultural-adaptation-and-regional-data)
  - [Imagery, color, and examples](#imagery-color-and-examples)
  - [The flag-for-language anti-pattern](#the-flag-for-language-anti-pattern)
  - [Right-to-left assets](#right-to-left-assets)
  - [Names, addresses, phones, and national identifiers](#names-addresses-phones-and-national-identifiers)
  - [Forms and validation that assume US formats](#forms-and-validation-that-assume-us-formats)
- [Scripts, Fonts, and Regulated Copy](#scripts-fonts-and-regulated-copy)
  - [Font fallback per script](#font-fallback-per-script)
  - [Plural-sensitive copy](#plural-sensitive-copy)
  - [Legal, regulatory, and safety copy](#legal-regulatory-and-safety-copy)
  - [Sample, demo, and fixture content](#sample-demo-and-fixture-content)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- A user-visible string is added, moved, or refactored in any UI, email, notification, PDF, or CLI output.
- A message catalog is introduced, migrated between formats, or moved behind a TMS.
- A layout uses fixed widths or heights, `white-space: nowrap`, `text-overflow`, or line clamping on translated text.
- A form collects names, addresses, phone numbers, national identifiers, or dates from a global audience.
- Screenshots, illustrations, icons, or raster images containing text are produced for more than one market.
- Fonts, webfont subsets, or fallback stacks are chosen, or a non-Latin script is rendered.
- Marketing, legal, medical, or safety copy is localized, or machine translation is proposed for it.
- Sample, demo, seed, or fixture content is authored (test users, addresses, currencies, units, dates), or a language or region picker is built.

## Message Catalogs, Key Strategy, and Version Control

Source-string keys (`msgid` = the English text) are the gettext default, but they couple the catalog to copy edits:
renaming "Sign in" to "Log in" orphans every existing translation unless the tool fuzzy-matches it. Symbolic IDs
decouple them.

| Approach                     | Example                                               | Failure mode                                                                                  |
| ---------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Source string as key         | `msgid "Sign in"`                                     | Any copy edit orphans translations; identical English with different meanings needs `msgctxt` |
| Symbolic ID, value is source | `checkout-submit = Sign in` (Fluent)                  | Missing IDs fail silently at runtime                                                          |
| Symbolic ID, value elsewhere | `t("checkout.submit")`                                | Source text invisible in review; translators need the default supplied separately             |
| Symbolic ID + inline default | `defineMessages({ id, defaultMessage, description })` | Defaults drift from the catalog unless extraction is enforced in CI                           |

Prefer "symbolic ID, value is source" (Fluent, ARB, Apple String Catalogs) or "symbolic ID + inline default" (react-intl, vue-i18n). Both survive copy churn.

| Format                      | Ecosystem                      | Plural mechanism                            | Translator metadata                                                                 |
| --------------------------- | ------------------------------ | ------------------------------------------- | ----------------------------------------------------------------------------------- |
| PO / POT                    | gettext (C, PHP, Python, Rust) | `msgid_plural` + `msgstr[0..n]`             | `#.` extracted, `#:` source ref, `# ` translator note                               |
| XLIFF 1.2 / 2.x             | TMS interchange                | ICU nested in `<source>`/`<target>`         | `<note from="...">` + `<context-group>` (1.2); `<notes><note category="...">` (2.x) |
| ARB                         | Flutter / Dart `intl`          | ICU in the value; `@@plural` in `@@context` | `@key.description`, `@key.placeholders`, `@key.context`                             |
| JSON (ICU)                  | i18next, FormatJS, ICU4X       | ICU inline                                  | FormatJS: `description` beside `defaultMessage`                                     |
| `.strings` / `.stringsdict` | Apple platforms                | `%#@var@` with `NSStringFormatRuleType`     | `NSLocalizedString(_:comment:)`; String Catalog `comment`                           |
| `strings.xml`               | Android                        | `<plurals>` with `<item quantity="...">`    | `xliff:g` with `id` and `example`                                                   |

Commit the source-locale catalog (the canonical copy), TMS project config (`crowdin.yml`, `lokalise.conf`,
`phrase.yml`), the glossary and style guide, and the extraction and validation scripts. Commit approved legal or medical
translations with the review record naming the reviewer and the source revision.

Do not commit per-round-trip bilingual XLIFF working files, exported TMX/TM dumps, vendor API tokens, unreviewed
machine-translation output, or artifacts a pinned toolchain rebuilds (`messages.mo` from `.po`,
`app_localizations*.dart` from ARB). Mark catalogs `linguist-generated=true` in `.gitattributes` and never use
`merge=union` on them: it concatenates both sides of a conflict into duplicate keys and invalid JSON.

```bash
pybabel extract -F babel.cfg -o locales/messages.pot .
msgmerge --update --backup=none locales/de/LC_MESSAGES/messages.po locales/messages.pot
msgattrib --translated --no-fuzzy --no-obsolete locales/de/LC_MESSAGES/messages.po -o -
msgfmt --check --check-format --statistics -o /dev/null locales/de/LC_MESSAGES/messages.po
```

`msgfmt --check` fails on malformed entries; `--check-format` verifies that `printf` conversions in the translation
match the source. `msgattrib --no-fuzzy` matters because gettext discards `#, fuzzy` entries at runtime — a stale
machine-translated string marked fuzzy is replaced by the untranslated source anyway, so shipping it only hides the gap.

Translation state is not free-form. XLIFF 1.2 puts `state` on `<target>` with values including `new`, `translated`,
`needs-translation`, `needs-review-translation`, `final`, and `signed-off`. XLIFF 2.x moved it to `<segment
state="...">` with the reduced set `initial`, `translated`, `reviewed`, `final`. Tooling that reads a 2.x `state` from
`<target>` sees nothing.

## Message Composition, Placeholders, and Translator Context

### Never concatenate or fragment sentences

```ts
const msg = `You have ${n} new ` + (n === 1 ? "message" : "messages");
const banner =
  t("read") + " <a>" + t("terms") + "</a> " + t("before_continuing");
```

The first fails for languages with more than two plural categories (Arabic has six: `zero`, `one`, `two`, `few`, `many`,
`other`) and for languages with none (Japanese, Korean, Chinese, Vietnamese, Thai, Indonesian). The second is unfixable:
link position, the case of the noun it governs, and surrounding punctuation all vary, and no translator can repair a
fragment.

```json
{
  "inboxUnread": "{count, plural, =0 {No unread messages} one {# unread message} other {# unread messages}}",
  "termsConsent": "You must accept the <terms>Terms of Service</terms> before continuing."
}
```

```ts
intl.formatMessage(messages.termsConsent, {
  terms: (chunks) => <a href="/terms">{chunks}</a>,
});
```

The equivalents are Fluent's `<a data-l10n-name="terms">` plus a `data-l10n-id` element, and vue-i18n's `<i18n-t
keypath="termsConsent">` with a named `#terms` slot. Also banned: `(s)` suffixes (`1 item(s)`), `he/she`, `his/her`, and
slash-joined alternatives (`Save / Save as`). Slash constructs assume a Latin slash and read as one unknown token to
screen readers; CJK typography uses `／` or `・`.

### Named versus positional arguments

Named placeholders let the translator reorder the sentence; positional ones do not. When a language requires the object
before the subject, only named placeholders survive.

| Platform              | Named    | Positional       | Note                                                           |
| --------------------- | -------- | ---------------- | -------------------------------------------------------------- |
| ICU / FormatJS        | `{name}` | `{0}`            | Named and positional cannot be mixed in one pattern            |
| Android `strings.xml` | No       | `%1$s`, `%2$d`   | Explicit index required; bare `%s` breaks reordering           |
| Apple `.strings`      | No       | `%1$@`, `%2$d`   | Bare `%@` is a reordering bug                                  |
| Java `MessageFormat`  | No       | `{0}`, `{1}`     | ICU4J `MessageFormat` has no named-argument form               |
| Go `fmt`              | No       | `%[1]s`, `%[2]d` | Explicit argument index requires `[n]`                         |
| PHP `sprintf`         | No       | `%1$s`           | `%s` alone is order-dependent                                  |
| Python `str.format`   | `{name}` | `{0}`            | f-strings cannot be externalized; they bake text into bytecode |

Go has no compile-time-checked localization path: `golang.org/x/text/message` with a `catalog` gives a runtime
`Printer`, but `go vet` printf checks apply only to `fmt` functions with literal formats.

### Escaping

| Context               | Escape                                                           | Trap                                                                                                                                                                                   |
| --------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ICU MessageFormat     | `'{'` / `'}'` for literal braces, `''` for a literal apostrophe  | ICU4J's `MessagePattern.ApostropheMode` defaults to `DOUBLE_OPTIONAL`, where an apostrophe before a non-syntax character is literal. Escape explicitly instead of relying on the mode. |
| Android `strings.xml` | `\'`, `\"`, `%%` when `formatted="true"`                         | A string starting with `@` or `?` must be escaped `\@` / `\?` or it is read as a resource reference                                                                                    |
| Apple `.strings`      | `\"`, `%%`                                                       | A `%@` in a translation with no matching argument crashes at runtime                                                                                                                   |
| gettext PO            | `\n`, `\"`, `\\`; continuation lines are adjacent quoted strings | With `#, c-format`, the `%` conversions must match the source count                                                                                                                    |
| HTML injection        | Escape `<`, `&`, `"` on output                                   | Never assign translator text through `innerHTML`; use `textContent` or framework escaping                                                                                              |
| Fluent                | `{"literal braces"}`                                             | A stray `{` opens a placeable and fails the whole message                                                                                                                              |

### Translator context

A string without context is translated by guessing. Every catalog has a place to record it: PO's `#.` extracted comment,
`#:` source reference, `# ` translator note, and `#|` previous `msgid`; XLIFF 1.2's `<note from="...">` plus `<context-
group context-type="sourcefile|linenumber">`; XLIFF 2.x's `<notes><note category="...">`; ARB's `@key.description`,
`@key.placeholders.<name>.description`, and `@key.context` for `@@plural` and `@@select`; the Apple String Catalog
`comment` field, whose `extractionState` (`manual`, `extracted_with_value`, `migrated`, `stale`) controls whether a
manual entry survives the next export; and Android's `<xliff:g id="..." example="...">`.

There is no spec-mandated XLIFF field for a length limit, but the honored conventions are a `#. maxlength: 20` extracted
comment in PO, `<note from="maxlength" priority="1">20</note>` in XLIFF, and the TMS's own `maxLength` attribute. State
whether the limit is characters or pixels: 20 characters is a different constraint in CJK than in German. When enforcing
a limit in code, count grapheme clusters, not UTF-16 code units — `"👨‍👩‍👧‍👦".length` is `11` in JavaScript and renders
as one character.

## Layout Resilience and Text Expansion

The source locale is the shortest case, not the baseline.

| Target                                      | Typical length vs. `en-US`               | Cause                                                                                             |
| ------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------- |
| German, Finnish                             | +30% to +40%                             | Compounding and agglutination                                                                     |
| French, Portuguese, Spanish, Italian, Dutch | +15% to +30%                             | Longer function words and morphology                                                              |
| Russian, Polish, Czech                      | +10% to +20%                             | Case endings and aspect                                                                           |
| Chinese, Japanese, Korean                   | −40% to −60% in characters               | Higher density per glyph, but full-width glyphs need more `line-height` and a larger optical size |
| Arabic, Hebrew                              | Shorter in characters, wider in practice | Cursive joining and no traditional hyphenation reduce break opportunities                         |

Treat these as directional and measure against your own corpus with a pseudo-locale: Android ships `en-XA` (accented,
~30% expansion) and `ar-XB` (RTL pseudo), and Xcode's scheme editor offers Accented, Bounded, and Right-to-Left
pseudolanguages.

```css
.badge {
  min-inline-size: 6rem;
  max-inline-size: 100%;
  padding-inline: 0.5rem;
  overflow-wrap: anywhere;
}
```

- Never fix `width` or `height` on a text container; use `min-inline-size`, `min-block-size`, and padding.
- Flex children do not shrink below their min-content size unless you set `min-width: 0` (or `min-inline-size: 0`) — the
  most common cause of a translated label pushing a row off-screen. In grid, use `minmax(0, 1fr)` rather than `1fr` for
  the same reason.
- Use `aspect-ratio` for media instead of a fixed height, so a re-localized image with a different aspect fits.
- The `ch` unit is the width of the `0` glyph, a Latin metric; `60ch` of CJK is far wider than `60ch` of English.
- `hyphens: auto` only works when the element has a correct `lang`; otherwise the browser has no hyphenation dictionary and silently does nothing.
- `overflow-wrap: anywhere` also affects intrinsic min-content size; `break-word` does not. Use `anywhere` when the shrink must propagate.
- For Korean, `word-break: keep-all` prevents breaking inside an eojeol. For Thai, `word-break: break-all` is wrong: Thai
  has no inter-word spaces, so line breaking needs a dictionary-based breaker (ICU `LineBreak`, Java
  `BreakIterator.getLineInstance(locale)`).

```css
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-inline-size: 0;
}

.clamp-3 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
}
```

`-webkit-line-clamp` remains the interoperable spelling; the unprefixed `line-clamp` is not yet reliable across engines.
Never clamp or truncate a required legal disclosure or an error message — that is a compliance problem, not a layout
one. Truncate on grapheme clusters, or you will split an emoji ZWJ sequence, a Devanagari conjunct, or a Thai vowel mark
off its base consonant.

```ts
const segmenter = new Intl.Segmenter(locale, { granularity: "grapheme" });

export function truncate(text: string, maxGraphemes: number): string {
  const clusters = [...segmenter.segment(text)].map((entry) => entry.segment);
  return clusters.length <= maxGraphemes
    ? text
    : clusters.slice(0, maxGraphemes - 1).join("") + "…";
}
```

The Python equivalent is `grapheme.slice(text, 0, max_graphemes - 1)` from the `grapheme` package; Java uses
`BreakIterator.getCharacterInstance(locale)`. Both count the same clusters `Intl.Segmenter` does, so a string truncated
in one runtime stays truncatable in the other.

## Cultural Adaptation and Regional Data

### Imagery, color, and examples

| Element                        | Risk                                                                                                                                              | Practice                                                           |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Hand gestures                  | Thumbs-up, the "OK" ring, and palm-up beckoning are obscene or hostile in parts of the Middle East and West Africa                                | Ship gesture-neutral photography or per-market art                 |
| Color semantics                | Red means danger in Western finance but a price **rise** in mainland China, where green means a fall                                              | Do not encode gain/loss by hue alone; add an arrow, sign, or label |
| Mourning colors                | White in parts of East Asia and India; purple in Brazil and Thailand; yellow in Egypt; blue in Iran                                               | Audit celebratory and status palettes per market                   |
| Religious and seasonal imagery | Christmas trees and Halloween assume a Christian calendar, while Ramadan, Lunar New Year, and Diwali are peak commercial moments in large markets | Make seasonal art a per-market content pack                        |
| Maps and borders               | Crimea, Kashmir, Taiwan, and Western Sahara are drawn differently by jurisdiction, and some markets legally mandate a depiction                   | Source map assets per region; never ship one global raster         |
| Emergency and civic examples   | Screenshots showing `911`, `$`, `ZIP`, or a Social Security number teach a US-only world                                                          | Use neutral sample data or per-locale fixture sets                 |

### The flag-for-language anti-pattern

Flags denote countries, not languages: `en` covers the UK, US, Australia, Ireland, and dozens more; `es` and `ar` cover
twenty-plus countries each; `pt` covers Portugal and Brazil. A flag beside a language asserts a national claim that is
often politically contested, and `en` with a US flag promises American spelling to an `en-GB` user. Use the localized
language name, sorted by the _displayed_ string, not the code:

```ts
const display = new Intl.DisplayNames([uiLocale], {
  type: "language",
  languageDisplay: "dialect",
});

display.of("pt-BR");
```

`languageDisplay: "dialect"` yields "Brazilian Portuguese" where `"standard"` yields "Portuguese (Brazil)". Select
Chinese by script (`zh-Hans`, `zh-Hant`), never by country. Use `zxx` for "no linguistic content" and `und` for
undetermined rather than guessing from location.

### Right-to-left assets

Direction itself is covered in [intl-bidi.md](intl-bidi.md); this is the asset layer.

- **Mirror**: back/forward arrows, chevrons, breadcrumb separators, progress and step indicators, undo/redo, list bullets
  and indentation, sliders, timeline direction.
- **Do not mirror**: clocks, calendar grids, mathematical notation, logos, checkmarks, phone numbers, QR codes, media play
  buttons. A mirrored calendar grid reads backwards and is unusable.
- **Never bake text into raster art.** Text in a PNG cannot be re-translated, reflowed, or resized for expansion. Use SVG
  with `<text>` or overlay real DOM text, and re-shoot screenshots per locale: a localized UI with English chrome is an
  immediate visible defect.
- **Flip directional icons with a token** so the flip can be disabled per asset: `.icon-directional { transform:
  scaleX(var(--icon-flip, 1)); }` with `:root[dir="rtl"] { --icon-flip: -1; }`.
- **Use logical properties**: `inset-inline-start`, `margin-inline-end`, `padding-inline`, `border-start-start-radius`,
  `text-align: start`. `border-radius: 8px 8px 0 0` becomes `border-start-start-radius` and `border-start-end-radius`, and
  `background-position: left center` and `transform: translateX(-8px)` are physical and must be replaced.

### Names, addresses, phones, and national identifiers

Address field order is not universal. CLDR / libaddressinput tokens (`%N` name, `%O` organization, `%A` street address,
`%D` dependent locality, `%C` locality, `%S` administrative area, `%Z` postal code, `%R` country, `%n` line break)
encode it:

| Locale  | Format pattern           | Rendered shape                                                   |
| ------- | ------------------------ | ---------------------------------------------------------------- |
| `en-US` | `%N%n%O%n%A%n%C, %S %Z`  | Alice Chen / Acme / 123 Main St / Springfield, IL 62704          |
| `de-DE` | `%N%n%O%n%A%n%Z %C`      | Hauptstraße 5 before 10115 Berlin; the number follows the street |
| `ja-JP` | `%Z%n%S%C%A%n%O%n%N`     | Postal code first, then prefecture, city, address, then name     |
| `zh-CN` | `%Z%n%S%C%D%A%n%O%n%N`   | Largest-to-smallest, postal code first                           |
| `en-GB` | `%N%n%O%n%A%n%C%n%Z`     | Postcode on its own final line                                   |
| `ru-RU` | `%Z%n%S%n%C%n%A%n%O%n%N` | Postal code, then region, city, street                           |

A form with separate "House number" then "Street name" fields in that order is wrong for Germany, which writes
`Hauptstraße 5`, and wrong for the US and France, which write the number first. Japanese addresses are a descending
hierarchy, not an `%A` + `%C` split. Label fields with the localized role: `Postal code` not `ZIP`; `State / Province /
Region` not `State`; `Address line 2` not `Apt / Suite`.

Phone numbers: store E.164 (`+`, country calling code, at most 15 digits per ITU-T E.164) plus the region used to parse
the input, and format for display. Never length-check. `+39 06 6982` keeps its leading zero because Italy's national
significant number includes it; Argentina's mobiles carry a `9` after the country code (`+54 9 11 2345-6789`); Japan
drops the leading `0` internationally (`03-1234-5678` becomes `+81 3 1234 5678`).

```ts
import { parsePhoneNumberFromString } from "libphonenumber-js";

const parsed = parsePhoneNumberFromString(input, region);
if (parsed?.isValid()) {
  await save({ e164: parsed.number, country: parsed.country });
}
```

The Java equivalent is `PhoneNumberUtil.getInstance()` with `util.parse(input, region)`, gated on
`util.isValidNumber(number)` and stored via `util.format(number, PhoneNumberFormat.E164)`.

National identifiers are per-country and often legally restricted. `\d{3}-\d{2}-\d{4}` is a US SSN; India's Aadhaar is
12 digits starting 2–9 with a Verhoeff check digit; Brazil's CPF is 11 digits with two mod-11 check digits; the UK's
NINO has the shape `QQ 12 34 56 C`; EU VAT numbers are a country prefix plus a national body validated against VIES.
Collect them only where local law permits, always optionally, and never with a global pattern.

Names: a required family-name field is a hard block for Indonesian mononyms, Afghan and South Indian single names, and
Icelandic patronymics. Spanish and Hispanic-American names carry two family names; Portuguese and Brazilian names carry
`de`/`da`/`dos` particles; Arabic names carry `bin`, `bint`, and `Al-` with up to five parts; Chinese, Korean, Japanese,
Vietnamese, and Hungarian order the family name first.

- Label fields `Given name` and `Family name`, not `First name` and `Last name`, and state the expected order. Offer a
  single `Full name` field as an alternative rather than forcing a split.
- Do not `text-transform: capitalize` names; it corrupts `van der Berg`, `McDonald`, and `Ó Súilleabháin`. Do not
  uppercase them either: German `ß` uppercases to `SS`, and Turkish dotless `ı` casing is covered in [intl-text-
  processing.md](intl-text-processing.md).
- Allow at least 50 characters per name field; a 20-character limit rejects much of the world.
- Honorifics are not a fixed prefix list. German `Herr`/`Frau` doubles as direct address, Japanese `様` is a suffix,
  Spanish adds `Don`/`Doña`. Model prefix and suffix separately, include an explicit "none", and never infer gender from a
  title.

### Forms and validation that assume US formats

| Assumption                           | Fails for                                                                                                        | Fix                                                                                       |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `^\d{5}(-\d{4})?$` for postal code   | UK `SW1A 1AA`, Canada `K1A 0B1`, Netherlands `1011 AB`, Japan `100-0001`, Brazil `01310-100`, Ireland `D02 AF30` | Per-country patterns from CLDR/libaddressinput, or no client-side postal validation       |
| `\d{10}` for phone                   | Every country except NANP                                                                                        | `libphonenumber` parsing and validity                                                     |
| A `<select>` of 50 US states         | Every other country                                                                                              | Free text or a country-driven list; `address-level1`                                      |
| `MM/DD/YYYY` input                   | Most of the world                                                                                                | `<input type="date">` (the value is always ISO `YYYY-MM-DD`; never display the raw value) |
| `<input type="number">` for decimals | Locales using `,` as the decimal separator; the control rejects it                                               | `type="text"` with `inputmode="decimal"`, displayed via `Intl.NumberFormat`               |
| Uppercasing input on blur            | Names with case-sensitive particles; Turkish `i`/`ı`                                                             | Never mutate the case of user-entered names                                               |

Use WHATWG autofill tokens so browsers and password managers fill a localized form correctly: `honorific-prefix`,
`given-name`, `additional-name`, `family-name`, `honorific-suffix`, `organization`, `street-address`, `address-
line1`–`address-line3`, `address-level1`–`address-level4`, `postal-code`, `country`, `country-name`, `tel`, `tel-
country-code`, `tel-national`, `email`, `bday`. Set `inputmode="numeric"` only when the value is genuinely numeric;
Netherlands and UK postal codes need `inputmode="text"`. Put a correct `lang` on the form.

## Scripts, Fonts, and Regulated Copy

### Font fallback per script

| Script                       | Reference family                                | Rendering constraint                                                                                                                                                                                                                                                                                                                     |
| ---------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Latin / Cyrillic / Greek     | Noto Sans                                       | Watch Cyrillic `locl` variants (Serbian, Bulgarian), which follow the element's `lang`                                                                                                                                                                                                                                                   |
| Arabic                       | Noto Naskh Arabic (text), Noto Sans Arabic (UI) | Cursive joining: `letter-spacing` inserts gaps between joined letters and must not be used. Synthetic bold degrades shaping — set `font-synthesis: none` and load a real bold. Digits may be Arabic-Indic (U+0660–0669) or Extended Arabic-Indic (U+06F0–06F9).                                                                          |
| Hebrew                       | Noto Sans Hebrew / Noto Serif Hebrew            | No case, so `text-transform: uppercase` and `font-variant: small-caps` are silent no-ops. Verify a true italic exists before using `font-style: italic`.                                                                                                                                                                                 |
| Han (SC/TC/JP/KR)            | Noto Sans SC / TC / JP / KR                     | Han unification: one codepoint has region-specific glyphs (U+9AA8 骨). The engine picks the variant from the element's `lang`, so a missing `lang` renders Japanese text with Chinese glyphs. No true italic — italics are synthesized obliques. Needs `line-height` near 1.6–1.8 and a larger optical size than Latin at the same `px`. |
| Devanagari                   | Noto Sans Devanagari                            | Conjuncts and matra reordering need a shaping engine (HarfBuzz). The headline stroke and above/below marks need vertical room; a fixed-height container clips them. `text-transform` is a no-op, and truncating mid-cluster detaches a matra from its consonant.                                                                         |
| Thai / Lao / Khmer / Myanmar | Noto Sans Thai, Noto Sans Lao                   | No inter-word spaces, so line breaking needs a dictionary-based breaker. Stacked vowels and tone marks need extra `line-height`.                                                                                                                                                                                                         |
| Korean                       | Noto Sans KR                                    | Use `word-break: keep-all`; the default breaks inside an eojeol.                                                                                                                                                                                                                                                                         |

Load script-specific subsets with `unicode-range` and matching fallback metrics, or the fallback font's line box shifts
layout on swap. A `@font-face` for `"Noto Sans Arabic"` declares `unicode-range: U+0600-06FF, U+0750-077F, U+FB50-FDFF,
U+FE70-FEFF` alongside `size-adjust`, `ascent-override`, `descent-override`, and `line-gap-override` so the swap does
not reflow the page.

On native platforms, iOS resolves fallbacks through `UIFontDescriptor.AttributeName.cascadeList`, and Android chains
`res/font/` with the system `fonts.xml` — but Android resource qualifiers must use the BCP 47 form when script matters:
`res/values-b+zh+Hans/` and `res/values-b+zh+Hant/`, not `values-zh-rCN` alone. Java logical fonts (`Dialog`,
`SansSerif`, `Serif`, `Monospaced`) map to physical fonts per locale, so specify a logical family and verify coverage
with `Font.canDisplayUpTo`.

### Plural-sensitive copy

Which plural categories exist is a CLDR question, covered in [intl-pluralization.md](intl-pluralization.md). The content consequences:

- Never ship a two-branch `count === 1` check. Arabic and Welsh need six categories; Irish five; Russian, Polish, Czech,
  and Lithuanian four; Latvian and Romanian three; Japanese, Korean, Chinese, Vietnamese, Thai, Indonesian, and Turkish
  only `other`.
- `zero` is not `=0`. Use the exact-value selector `=0` for "exactly zero" (an empty-inbox message) and the `zero`
  category only for languages that grammatically distinguish it.
- Ordinals are separate from cardinals (`1st` vs `1`) and have their own rule sets; use `Intl.PluralRules` with `type: "ordinal"`.
- A Russian plural count selects among three genitive forms of the following noun, so the noun must live inside the same
  message, not be concatenated. Keep the count and its noun in one message even when the layout separates them visually;
  pass the count in and let CSS position the pieces.

### Legal, regulatory, and safety copy

Machine translation is not acceptable for text carrying legal, medical, financial, or safety consequence. Route it to a
qualified human translator with domain expertise and record a reviewer sign-off.

- **GDPR Article 12(1)** requires privacy information in a "concise, transparent, intelligible and easily accessible form,
  using clear and plain language"; a machine-translated notice does not satisfy this.
- **EU Directive 2011/83/EU** requires pre-contractual information and the 14-day withdrawal notice in the language of the
  member state, using the model withdrawal form in Annex I(B). **EU Regulation 2017/745 (MDR)** requires medical device
  instructions for use in the official language(s) of the member state where the device is made available.
- **France's Loi Toubon** mandates French for consumer information, product descriptions, and advertising, with the French
  term at least as prominent as any foreign term. **Quebec's Charter of the French Language** requires French to be
  markedly predominant in commercial signage, and **Canada's Official Languages Act** obliges federal institutions to
  serve the public in both official languages.
- **California Civil Code §1632** requires a translated copy of a consumer contract before signing when it was negotiated
  primarily in Spanish, Chinese, Tagalog, Vietnamese, or Korean. **China's PIPL** requires a Chinese-language privacy
  policy for domestic users, and maps must comply with Chinese mapping regulations.

Flag these strings so the pipeline cannot send them to a machine-translation queue: a dedicated namespace or file, a
`legal` flag in the TMS, and a CI check that rejects a diff touching them without a recorded reviewer.

### Sample, demo, and fixture content

Sample content teaches your team what "normal" looks like, so US-only fixtures propagate US-only assumptions into the
product. Replace `John Smith, 123 Main St, New York, NY 10001, (555) 123-4567, $1,234.56, 12/31/2025, 180 lb` with per-
locale fixtures, and include one deliberately long value per locale to stress layout — a Welsh `Llanfairpwllgwyngyll`, a
German `Donaudampfschifffahrtsgesellschaft`, an Arabic or Hebrew name with particles. Cover the units inside sample
content too: distance, temperature, body weight, recipe measures, clothing and shoe sizes (US 8 vs. EU 38 vs. UK 12 vs.
JP 24.5), paper size (US Letter vs. A4), blood glucose (mg/dL vs. mmol/L), fuel economy (mpg vs. L/100km), and date
conventions. Localize demo seeds, invoices, and PDF templates per market — an invoice heading, tax identifier, and
currency format are regulated artifacts, not decoration.

## Common Mistakes

| Mistake                                                 | Why It Breaks                                                                                                           | Correct Approach                                                                                |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `"You have " + n + " messages"`                         | Word order, plural category count, and gender agreement are all English-specific                                        | One ICU `plural` message with the count as an argument                                          |
| Splitting a sentence around an inline link or `<b>`     | Translators cannot reorder or inflect a fragment; the result is ungrammatical                                           | Rich-text placeholders: FormatJS function values, Fluent `data-l10n-name`, vue-i18n named slots |
| Keying catalogs by source string                        | Every copy edit orphans all translations                                                                                | Symbolic IDs with the source string as the value                                                |
| Bare `%s` / `%@` in a translatable string               | Positional placeholders cannot be reordered into a different word order                                                 | Explicit indexes: `%1$s`, `%1$@`, `%[1]s`                                                       |
| Fixed `width`/`height` on buttons, tabs, or table cells | German and Finnish run 30–40% longer; text clips or overflows                                                           | `min-inline-size` + padding; `min-width: 0` on flex children; `minmax(0, 1fr)` in grid          |
| Truncating with `slice()` on UTF-16 code units          | Splits emoji ZWJ sequences, Devanagari conjuncts, and Thai vowel marks                                                  | `Intl.Segmenter` with `granularity: "grapheme"`, Python `grapheme`                              |
| `white-space: nowrap` on a translated label             | Silently overflows in every longer locale                                                                               | Allow wrapping; reserve `nowrap` for numeric and code content                                   |
| Flag emoji as the language selector                     | Flags denote countries; `en`, `es`, `ar`, and `pt` each map to many, and `en` with a US flag promises American spelling | `Intl.DisplayNames` language names sorted by the displayed string                               |
| `^\d{5}(-\d{4})?$` postal validation                    | Rejects UK, Canadian, Dutch, Japanese, Brazilian, and Irish codes                                                       | Per-country patterns from CLDR/libaddressinput, or omit client-side validation                  |
| Required `First name` and `Last name` fields            | Mononyms and Icelandic patronymics have no family name; East Asian and Hungarian names order family first               | Optional family name, `Given`/`Family` labels, a `Full name` alternative                        |
| `text-transform: capitalize` on names                   | Corrupts `van der Berg`, `McDonald`, `Ó Súilleabháin`                                                                   | Never transform user-entered names                                                              |
| `letter-spacing` on Arabic or Hebrew                    | Inserts gaps between cursively joined Arabic letters                                                                    | Remove `letter-spacing` for cursive scripts                                                     |
| A single global map raster in marketing art             | Border depictions are legally contested and sometimes mandated per market                                               | Region-specific map assets from a compliant source                                              |
| Committing per-round-trip XLIFF and TM exports          | Merge conflicts on every translation cycle; bloats the repository                                                       | Commit source catalogs and TMS config; keep working files in the TMS                            |
| `merge=union` on catalog files                          | Concatenates both sides of a conflict, producing duplicate keys and invalid JSON                                        | Mark catalogs `linguist-generated=true`; regenerate from the TMS on conflict                    |
| Machine-translating legal, medical, or safety copy      | Fails GDPR Art. 12, Directive 2011/83/EU, and MDR language requirements                                                 | Human domain-expert translation with a recorded reviewer sign-off                               |
| Shipping a US-only default screenshot set               | Localized UI with English chrome reads as unfinished, and screenshots carry examples users trust                        | Re-shoot per locale; keep text out of raster art                                                |

## Checklist

1. Confirm every new user-visible string exists in the source-locale catalog and is not inlined in a template, a `console` call, or an exception message.
2. Verify no string is built by concatenation, `+`, template literal, or `sprintf` joining a fragment to a variable, and
   that every translatable string uses named placeholders where the platform supports them and explicit positional indexes
   (`%1$s`, `%1$@`, `%[1]s`) where it does not.
3. Run the catalog parser (`msgfmt --check --check-format`, `@formatjs/icu-messageformat-parser`, `pybabel compile`) in
CI and fail on malformed ICU, mismatched conversions, or unescaped braces.
4. Diff placeholder sets between the source and each target catalog; fail when a target introduces, drops, or renames an
argument, when a target is missing a source key, or when the source contains an untranslated `#, fuzzy` entry.
5. Check that every string with a count uses plural categories rather than a two-branch comparison, and that `=0` is distinguished from the `zero` category.
6. Verify no message composes a sentence around an inline link, bold run, or variable noun; convert to rich-text placeholders.
7. Confirm each string carries translator context — a description, screenshot, source reference, and a character or pixel limit where one exists.
8. Grep templates and stylesheets for fixed `width`, `height`, `nowrap`, and `text-overflow` on translated text; replace
with `min-inline-size`, `min-width: 0`, and `minmax(0, 1fr)`.
9. Render the UI in a pseudo-locale (`en-XA`, Xcode Accented) and confirm no clipping, overlap, or horizontal scroll.
10. Verify `lang` is set on the document and on any element whose language differs, so hyphenation, CJK glyph selection, and screen readers work.
11. Confirm truncation operates on grapheme clusters, and that no required disclosure, error message, or legal notice is truncated.
12. Verify the language picker lists language names rather than flags, sorts by the displayed name, and offers script-based options for Chinese.
13. Audit forms for US-shaped validation — postal code, phone, state list, date format, and `<input type="number">` for
decimals — and replace with per-country rules.
14. Verify names allow a single name, do not require a family name, are never case-transformed, and accept at least 50 characters.
15. Confirm phone numbers are stored in E.164 with the parse region and displayed through a formatting library, and
check the address form against the target locale's CLDR field order and label wording.
16. Confirm every font in the stack covers the scripts you ship, that subsets declare `unicode-range`, and that fallback
metrics (`size-adjust`, `ascent-override`) limit layout shift.
17. Verify directional icons flip with direction while clocks, calendars, logos, phone numbers, and QR codes do not.
18. Confirm no raster asset contains baked-in text, and that screenshots and seasonal art are per-market content packs.
19. Confirm legal, medical, and safety strings are flagged, excluded from machine translation, and shipped with a recorded reviewer sign-off.
20. Replace US-only sample data in fixtures, seeds, demos, and marketing with per-locale values that include a deliberately long string.
21. Confirm generated catalogs and per-round-trip XLIFF files are excluded from version control, and that TMS config and the glossary are committed.

## References

- W3C Internationalization Activity — https://www.w3.org/International/
- RFC 5646, Tags for Identifying Languages (BCP 47) — https://www.rfc-editor.org/rfc/rfc5646.html
- Unicode CLDR Project — https://cldr.unicode.org/
- Google libaddressinput (address format metadata and field tokens) — https://github.com/google/libaddressinput
- ICU User Guide, MessageFormat and quoting/apostrophes — https://unicode-org.github.io/icu/userguide/format_parse/messages/
- ICU User Guide, Boundary Analysis (grapheme and line breaking) — https://unicode-org.github.io/icu/userguide/boundaryanalysis/
- ICU4J `MessagePattern.ApostropheMode` — https://unicode-org.github.io/icu-docs/apidoc/released/icu4j/com/ibm/icu/text/MessagePattern.ApostropheMode.html
- Fluent Syntax Guide — https://projectfluent.org/fluent/guide/
- GNU gettext Manual — https://www.gnu.org/software/gettext/manual/gettext.html
- OASIS XLIFF 1.2 Core — https://docs.oasis-open.org/xliff/v1.2/os/xliff-core.html
- OASIS XLIFF 2.1 Core — https://docs.oasis-open.org/xliff/xliff-core/v2.1/os/xliff-core-v2.1-os.html
- Flutter internationalization and ARB files — https://docs.flutter.dev/ui/accessibility-and-internationalization/internationalization
- Apple, "Localizing and varying text with a string catalog" — https://developer.apple.com/documentation/xcode/localizing-and-varying-text-with-a-string-catalog
- Android string resources (plurals, `xliff:g`) — https://developer.android.com/guide/topics/resources/string-resource
- Android pseudolocales — https://developer.android.com/guide/topics/resources/pseudolocales
- ECMA-402, `Intl.Segmenter` — https://tc39.es/ecma402/#segmenter-objects
- ECMA-402, `Intl.DisplayNames` — https://tc39.es/ecma402/#intl-displaynames-objects
- Google libphonenumber — https://github.com/google/libphonenumber
- ITU-T Recommendation E.164 — https://www.itu.int/rec/T-REC-E.164/
- WHATWG HTML, Autofill field names — https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#autofill
- CSS Fonts Module Level 5 (`size-adjust`, metric overrides) — https://www.w3.org/TR/css-fonts-5/
- Unicode UAX #29, Text Segmentation (grapheme clusters) — https://www.unicode.org/reports/tr29/
- Noto Fonts (script coverage and family index) — https://notofonts.github.io/
- GDPR Article 12 — https://gdpr-info.eu/art-12-gdpr/
- Directive 2011/83/EU on consumer rights — https://eur-lex.europa.eu/eli/dir/2011/83/oj
- Regulation (EU) 2017/745 on medical devices — https://eur-lex.europa.eu/eli/reg/2017/745/oj
- California Civil Code §1632 — https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=1632

