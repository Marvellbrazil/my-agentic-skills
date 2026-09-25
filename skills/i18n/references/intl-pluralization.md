# Pluralization, Gender, and ICU Message Format

This module covers how a message is chosen and assembled for a language: CLDR plural categories and the
operands that drive them, ICU MessageFormat syntax (`plural`, `select`, `selectordinal`, nesting,
offsets), grammatical gender and case agreement, the runtimes that implement each, and the catalog
workflow that lets translators do their job. Getting it wrong ships broken text: "1 items", "5 item", a
Russian counter that reads like machine output, or a gender branch rendering the wrong verb form.

## Contents

- [When This Applies](#when-this-applies)
- [CLDR Plural Categories and Operands](#cldr-plural-categories-and-operands)
- [ICU MessageFormat Syntax and Semantics](#icu-messageformat-syntax-and-semantics)
- [Grammar: Gender, Case, and Why Assembly Fails](#grammar-gender-case-and-why-assembly-fails)
- [Runtimes, Catalogs, and Translator Workflow](#runtimes-catalogs-and-translator-workflow)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- Any user-visible string containing a count, quantity, rank, ordinal, or measure.
- Code contains `count === 1`, `n == 1`, `length > 1`, `%d item(s)`, `item${n === 1 ? '' : 's'}`, or a
  hand-rolled ternary producing a suffix.
- A message interpolates a noun whose grammatical gender or case affects the surrounding words
  (Slavic, Baltic, Semitic, Romance, Celtic, Finno-Ugric languages).
- Introducing or reviewing ICU MessageFormat patterns, Fluent messages, or `gettext` `msgid_plural`
  entries, or choosing a runtime (ICU4J, ICU4C, `intl-messageformat`, Fluent, `gettext`, MF2).
- Building extraction, translation, or pseudolocalization tooling, or auditing why a translated plural
  form is unreachable, missing, or ignored at runtime.
- A locale needs `zero`, `two`, `few`, or `many` and the template only defines `one`/`other`.

## CLDR Plural Categories and Operands

Plural selection is a property of the **language**, not of the number. CLDR defines six categories —
`zero`, `one`, `two`, `few`, `many`, `other` — and each locale assigns every number to exactly one of
them. `one` does not mean "equals 1": in French it means `i = 0,1`, so `0` and `1.5` both select `one`.
`other` is mandatory in every message and is the fallback for anything the rules do not claim.

| Operand   | Definition                                                      | For `1 234.50` |
| --------- | --------------------------------------------------------------- | -------------- |
| `n`       | Absolute value (sign is never visible to a rule)                | `1234.5`       |
| `i`       | Integer digits of `n`                                           | `1234`         |
| `v`       | Count of visible fraction digits, including trailing zeros      | `2`            |
| `w`       | Count of visible fraction digits, excluding trailing zeros      | `1`            |
| `f`       | Visible fraction digits as an integer, including trailing zeros | `50`           |
| `t`       | Visible fraction digits as an integer, excluding trailing zeros | `5`            |
| `c` / `e` | Compact decimal exponent (CLDR 42+; `e` is the newer spelling)  | `0`            |

Rule syntax is a small DSL over those operands: `and`, `or`, parentheses, `mod`, and the relations
`is`/`=` (equality), `in` (integer range or list), `not in`, `within` (range allowing fractions), and
`not within`. Ranges use `..`. `in` matches integers only, which is how English excludes `1.5` from
`one` without an explicit `v` test. Rules as CLDR publishes them:

```
en cardinal  one: i = 1 and v = 0
ru cardinal  one:  v = 0 and i % 10 = 1 and i % 100 != 11
             few:  v = 0 and i % 10 = 2..4 and i % 100 != 12..14
             many: v = 0 and (i % 10 = 0 or i % 10 = 5..9 or i % 100 = 11..14)
ar cardinal  zero: n = 0   one: n = 1   two: n = 2
             few:  n % 100 = 3..10     many: n % 100 = 11..99
en ordinal   one: n % 10 = 1 and n % 100 != 11
             two: n % 10 = 2 and n % 100 != 12
             few: n % 10 = 3 and n % 100 != 13
```

Which categories a locale uses, and which counts land in them:

| Locale                             | Cardinal categories in use                   | Representative counts                                           |
| ---------------------------------- | -------------------------------------------- | --------------------------------------------------------------- |
| `en`                               | `one`, `other`                               | `1` → one; `0`, `2`, `1.0`, `1.5` → other                       |
| `fr`                               | `one`, `many`, `other`                       | `0`, `1`, `1.5` → one; `1000000` → many; `2` → other            |
| `ru`                               | `one`, `few`, `many`, `other`                | `1`, `21` → one; `2`–`4` → few; `0`, `5`–`20`, `11`–`14` → many |
| `sl`                               | `one`, `two`, `few`, `other`                 | `1` → one; `2` → two; `3`, `4` → few; `5` → other               |
| `ar`                               | `zero`, `one`, `two`, `few`, `many`, `other` | `0`–`2` exact; `3`–`10` → few; `11`–`99` → many; `100` → other  |
| `ja`, `zh`, `ko`, `th`, `vi`, `id` | `other` only                                 | every count takes one form; adding `one` is dead code           |

Cardinal and ordinal rules are independent sets over the same number. English `2` is cardinal `other`
but ordinal `two`; `3` is cardinal `other` but ordinal `few`; `11` is ordinal `other` while `21` is
ordinal `one`. Selecting with the wrong rule set produces "2th" and "21th".

`Intl.PluralRules` is the platform primitive; it is per-locale and exposes both rule sets, plus
`selectRange(start, end)` for range selection (ECMA-402 2023, feature-detect it). Its number options
change the operands, so `minimumFractionDigits` can move a value out of `one`:

```js
new Intl.PluralRules("en").select(1); // 'one'
new Intl.PluralRules("en").select(1.0); // 'other'  (v = 1)
new Intl.PluralRules("en", { minimumFractionDigits: 1 }).select(1);
new Intl.PluralRules("en", { type: "ordinal" }).select(2); // 'two'
new Intl.PluralRules("ru").select(5); // 'many'
new Intl.PluralRules("fr").select(0); // 'one'
new Intl.PluralRules("ja").select(5); // 'other'
```

ICU exposes the same data with an explicit type switch:

```java
import com.ibm.icu.text.PluralRules;
import com.ibm.icu.util.ULocale;

ULocale ru = new ULocale("ru");
PluralRules.forLocale(ru).select(5); // "many"
PluralRules.forLocale(ru, PluralRules.PluralType.ORDINAL).select(5);
```

## ICU MessageFormat Syntax and Semantics

ICU MessageFormat (MF1) is the interchange format nearly every runtime consumes, so one pattern can be
extracted and executed by Java, C/C++, PHP, JavaScript, and Python tooling. Its grammar:

| Construct    | Syntax                                      | Semantics                                                                                |
| ------------ | ------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Argument     | `{name}`                                    | Inserts the argument verbatim; no locale formatting                                      |
| Number       | `{n, number}` / `{n, number, ::percent}`    | Locale number formatting; see [intl-number-and-currency.md](intl-number-and-currency.md) |
| Date/time    | `{d, date, short}` / `{d, time, ::HHmm}`    | Locale formatting; see [intl-date-and-time-format.md](intl-date-and-time-format.md)      |
| Plural       | `{n, plural, one{…} other{…}}`              | Selects the CLDR **cardinal** category; `#` is the formatted number                      |
| Ordinal      | `{n, selectordinal, one{#st} other{#th}}`   | Selects the CLDR **ordinal** category                                                    |
| Select       | `{g, select, female{…} other{…}}`           | Exact string match, no plural logic                                                      |
| Exact number | `=0`, `=1`                                  | Matches the raw value, before any `offset` is applied                                    |
| Offset       | `{n, plural, offset:1 …}`                   | Subtracts the offset before category selection **and** before `#`                        |
| Nesting      | `{n, plural, one{{g, select, …}} other{…}}` | Arbitrary depth; `#` binds to the nearest enclosing plural                               |
| Quoting      | `'{'`, `''`, `'#'`                          | Literal brace, literal apostrophe, literal hash                                          |

`other` is required in both `plural` and `select`; omitting it is a parse error in strict parsers and a
silent fallback in lenient ones. `#` is only special inside a plural or selectordinal sub-message, and
ICU's default apostrophe mode is `DOUBLE_OPTIONAL`, so `it's` is literal while a literal `{` must be
written `'{'`.

A worked example. The offset removes the speaker from the count so the branch text reads naturally,
and `#` compensates in the branch that needs the remainder:

```
{count, plural, offset:1
    =0 {No one replied to {subject}}
    =1 {{author} replied to {subject}}
    one {{author} and one other replied to {subject}}
    other {{author} and # others replied to {subject}}}
```

`count = 0` → `=0`; `count = 1` → `=1`; `count = 2` → offset-adjusted `1` → `one`; `count = 5` →
`other` with `#` rendering `4`. Exact matches compare the original value; category selection and `#`
both see `count - offset`. The identical ICU string in three runtimes:

```js
const args = { count: 5, subject: "release" };
new IntlMessageFormat(pattern, "ru").format(args);
```

```java
Object[] args = { 5, "release" };
new MessageFormat(pattern, new ULocale("ru")).format(args);
```

```php
\MessageFormatter::formatMessage('ru', $pattern, $args);
```

FormatJS also returns structured parts, so a variable can be wrapped in a link without splitting the
translated string: `new IntlMessageFormat(p, "ru").formatToParts(args)`.

MessageFormat 2.0 (MF2) replaces positional brace syntax with declarations and `when` clauses, making
selectors and local variables explicit and removing the apostrophe-quoting hazard:

```
.input {$count :number}
.match $count
one {{You have {$count} item.}}
*   {{You have {$count} items.}}
```

`.local` declares reusable intermediate values; `*` marks the catch-all variant and is mandatory;
`{{…}}` is a quoted pattern, needed wherever a nested pattern appears inside a variant. MF2 also
defines a function registry (`:number`, `:string`, `:date`, `:time`, `:datetime`) that implementations
may extend, which is the intended extension point for the case and gender functions MF1 lacks. The
specification is Unicode TR35 Part 9; ICU4J ships `com.ibm.icu.message2.MessageFormatter`, built with
`MessageFormatter.builder().setLocale(...).setPattern(...).build()` and read with `formatToString()`.

`java.text.MessageFormat` from the JDK is **not** ICU MessageFormat: it has no `plural` and no
`selectordinal`, and its `{0, choice, 0#none|1#one|1<many}` form is a numeric-interval type with no
CLDR data behind it, so `1<many` fires for `1.5` and Russian's four cardinal forms are inexpressible.

## Grammar: Gender, Case, and Why Assembly Fails

Plural categories classify a _number_. Grammar needs agreement across the whole clause, and the words
that must change are frequently not adjacent to the number. Gender agreement: an adjective, article,
demonstrative, or past-tense verb may agree with a noun's grammatical gender, which is a lexical
property of the noun, not of the message.

| Language | `file` (masc.)     | `folder` (fem.)       | `letter` (neut.)     |
| -------- | ------------------ | --------------------- | -------------------- |
| Russian  | этот файл          | эта папка             | это письмо           |
| French   | ce fichier         | ce dossier            | cette lettre         |
| German   | diese Datei (fem.) | dieser Ordner (masc.) | dieses Blatt (neut.) |

So a message containing a noun needs that noun's gender as an operand, and the branch is `select`-ed on
a gender attribute carried in the data — never inferred from the person's gender or from the number.

Case agreement: the same noun changes form with the syntactic role the message gives it. Russian
`файл` is nominative, `файла` genitive, `файлу` dative, `файлом` instrumental, `файле` prepositional.
`{noun} не найден` requires nominative; `Ошибка в {noun}` requires prepositional. A noun therefore
cannot be stored once and substituted into arbitrary templates; either the declension lives in the
catalog (one entry per case, per noun) or the whole sentence is the message.

Number agreement is separate from plural category: Hungarian, Turkish, and the CJK/SEA languages above
keep the noun singular after any numeral — `5 alma`, not `5 almák` — yet Hungarian's CLDR rules still
distinguish `one` from `other`, so the category and the required noun form disagree. Slavic `few`
governs genitive singular and `many` genitive plural, so noun, adjective, and verb move with the
category, and the number must sit inside the translated unit.

This is why concatenation and `sprintf`-style assembly cannot work:

- Word order is not universal. Verb-final languages (Japanese, Korean, Turkish) and VSO languages
  (Welsh, Irish) reorder subject, verb, and object, so `"Delete " + name + "?"` is untranslatable.
- Agreement targets sit outside the variable. Appending a noun forces every agreeing word already
  fixed in the literal text to change.
- Translators cannot inflect text they cannot see. `"$n " + $noun + " added"` gives them nothing.
- Post-processing translated output (`split`, `replace`, regex on a separator) is unsafe: the
  translated string may not contain the separator, and bidi reordering makes visual order differ from
  logical order (see [intl-bidi.md](intl-bidi.md)).

Project Fluent takes the opposite position: whole clauses are the unit, variant lists carry the
selection, and terms give case and gender a place to live (`FluentBundle::new` / `add_resource` /
`format_pattern` in Rust; `@fluent/bundle` in JS).

```
emails = { $count ->
    [one] You have one email.
   *[other] You have { $count } emails.
}
```

Fluent selects variants on the numeric value while `{ $count }` renders it with the locale's number
formatter; `NUMBER($count)` makes that formatting explicit.

## Runtimes, Catalogs, and Translator Workflow

Runtime support is uneven, and the difference matters most for MF2, gender, and case:

| Runtime                         | MF1 `plural`/`select`                  | `selectordinal`      | MF2                          | Notes                                                                      |
| ------------------------------- | -------------------------------------- | -------------------- | ---------------------------- | -------------------------------------------------------------------------- |
| ICU4J                           | Yes (`com.ibm.icu.text.MessageFormat`) | Yes                  | Yes (`com.ibm.icu.message2`) | Reference implementation; `MessagePatternUtil` parses patterns for tooling |
| ICU4C                           | Yes (`icu::MessageFormat`)             | Yes                  | Recent releases, C++         | `icu::PluralRules` for direct category queries                             |
| ICU4X                           | Category lookup only                   | Category lookup only | Experimental                 | `icu::plurals`; formatting is left to the host                             |
| `intl-messageformat` (FormatJS) | Yes                                    | Yes                  | No                           | Most widely deployed JS runtime; `onError` reports missing arguments       |
| Project Fluent                  | Variant lists                          | Not built in         | No                           | `@fluent/bundle` and `fluent-bundle`; `NUMBER()` for formatting            |
| `gettext` / `ngettext`          | Two-plus forms via `Plural-Forms`      | No                   | No                           | No nesting, no `select`, no gender                                         |
| PHP `intl`                      | Yes (`MessageFormatter`)               | Yes                  | No                           | Symfony selects `IntlFormatter` for `+intl-icu` domains                    |
| Go `x/text`                     | No                                     | No                   | No                           | `message` and `feature/plural` cover formatting and category lookup only   |

The placeholder-vs-numbered-argument decision follows from the runtime:

- **Prefer named arguments** (`{count}`, `{author}`). They survive reordering, are self-documenting in
  the catalog, and adding an argument never renumbers anything.
- **Positional arguments** (`{0}`, `{1}`) are required only by `java.text.MessageFormat` and
  `printf`-family APIs. Inserting an argument mid-string renumbers every later index and invalidates
  existing translations.
- **`%1$s`-style positional printf specifiers** reorder arguments but cannot select a plural category
  or a gender form; they are a formatting mechanism, not a message mechanism.
- Never pass a pre-formatted string where the message expects a number or date. `{count, number}` must
  receive the numeric value so the message's locale controls grouping and fraction digits.

Variables belong inside the translatable unit. ICU MF1 skeletons make the required format explicit
(`{d, date, ::yyyyMMdd}` on ICU4J/ICU4C/PHP; `{d, date, short}` everywhere) so the translator sees one
unit and no caller pre-formats a value. One MF1 limitation: plural selection reads the **raw** value,
so a message displaying `1.2M` still selects its category from `1200000`; if compact formatting must
drive the category, use Fluent or MF2, or select explicitly on the compacted value.

Extraction moves messages out of source into a catalog; use the ecosystem's own tool so plural
metadata is emitted correctly:

```bash
pybabel extract -F babel.cfg -o messages.pot .
pybabel compile -d locale
```

```bash
formatjs extract 'src/**/*.{ts,tsx}' --out-file lang/en.json
formatjs compile lang/ru.json --ast --out-file compiled-lang/ru.json
```

`gettext` catalogs carry plural forms as a header plus parallel strings, which is what `ngettext`
consumes. Python's `gettext` compiles the `Plural-Forms` expression, so `nplurals` greater than 2
works for Russian and Arabic without a special API — `gettext.translation(...).ngettext(...)`:

```
"Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : "
"n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);\n"

msgid "%d file"
msgid_plural "%d files"
msgstr[0] "%d файл"
msgstr[1] "%d файла"
msgstr[2] "%d файлов"
```

A wrong `nplurals` or a copied English expression silently maps every count to the wrong form. Verify
the header against the locale, and verify `msgstr[i]` is non-empty for every `i < nplurals`; a missing
index falls back to the English `msgid_plural`.

Translators need context the format does not carry. `gettext` has `msgctxt` for disambiguation and
`#.` extracted comments but no screenshot field — screenshots live in the translation management
system (Crowdin, Weblate, Phrase, Lokalise), not in the PO file. FormatJS messages carry a
`description` alongside `defaultMessage` for the same purpose. For plural work specifically:

- Two identical English strings with different plural behavior (items versus seconds) must be distinct
  catalog entries, via `msgctxt` or a distinct message id.
- The translator must know what the number counts, and whether it is a total, remainder, or rank.
- Ordinals must be marked as ordinals in the source, not inferred from a comment.

Pseudolocalization of plural forms has a specific trap: a pseudo-locale derived from English (`en-XA`
on Android, or a generated accent locale) resolves its plural rules to English, so
`Intl.PluralRules('en-XA')` returns only `one`/`other` and any missing `few` or `many` branch stays
invisible. Pseudolocalization must therefore:

- Parse each message with a real ICU parser and transform only literal nodes, leaving arguments, plural
  selectors, `#`, and skeletons intact. A raw string-replacement pseudolocalizer corrupts the braces and
  the pattern stops parsing. FormatJS exposes `parse()` and the `TYPE.literal` element kind for this.
- Force values that hit every category of the _target_ locale, and add a stress locale whose rules
  exercise `zero`, `two`, `few`, and `many`. Expansion of ~30–40% exposes truncation, but the `#`
  substitution itself must not be expanded.

## Common Mistakes

| Mistake                                                       | Why It Breaks                                                                                                                                                                           | Correct Approach                                                                                              |
| ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `count === 1 ? singular : plural`                             | `one` is not "equals 1": French `0` and `1.5` are `one`; Russian `21` is `one` while `11` is `many`; English `1.0` is `other`. The branch is wrong in every language, including English | Select the CLDR category via `Intl.PluralRules`, ICU `plural`, or Fluent, and keep the wording in the catalog |
| Building the message with concatenation or `sprintf`          | Word order, noun gender, case, and number agreement all live outside the variable, so no translation can be grammatical                                                                 | Put the whole clause in the message with named arguments inside it                                            |
| Omitting `other` from a plural or select                      | Strict parsers reject the pattern; lenient ones fall back to nothing or throw at format time                                                                                            | Always define `other`; treat its absence as a build failure                                                   |
| Using `plural` for a rank (`1st`, `2nd`)                      | Cardinal rules assign English `2` to `other`, so the output is "2th"                                                                                                                    | Use `selectordinal`, or `Intl.PluralRules` with `{ type: 'ordinal' }`                                         |
| Reusing one plural message across sentence positions          | Case governs the noun form: `{noun} не найден` needs nominative, `Ошибка в {noun}` needs prepositional                                                                                  | Keep separate catalog entries per syntactic role, or never substitute a bare noun                             |
| Copying the English `Plural-Forms` header into a Russian file | The catalog exposes fewer forms than the locale has, so `ngettext` maps counts to the wrong strings                                                                                     | Set `nplurals` and the rule expression from CLDR for that locale, and verify every index is filled            |
| Passing a pre-formatted number into the message               | Plural selection needs the numeric value; a string like `"1,5"` either throws or selects the wrong category, and the message can no longer format it for its own locale                 | Pass the raw number and let `{n, number}` / `NUMBER()` format it                                              |
| Assuming `offset` shifts the exact matches                    | `=0` and `=1` compare the original value while category selection and `#` use the offset value; conflating them produces off-by-one counts                                              | Test the pattern at the offset boundary, e.g. `count = offset + 1`                                            |
| Pseudolocalizing a pattern with plain string replacement      | Braces, selectors, and skeletons get mangled and the pattern stops parsing                                                                                                              | Parse to an AST and transform only literal nodes                                                              |
| Treating `java.text.MessageFormat` as ICU MessageFormat       | The JDK class has no CLDR plural data; `{0, choice, 1<many}` fires for `1.5` and cannot express four Russian forms                                                                      | Use `com.ibm.icu.text.MessageFormat` when ICU semantics are required                                          |

## Checklist

1. Grep the tree for `=== 1`, `== 1`, `> 1`, `%d`, `(s)`, and ternary suffix logic in any file that
   produces user-visible text, and replace each with a catalog-driven selection.
2. Confirm every `plural`, `selectordinal`, and `select` pattern defines `other`, and fail the build if
   one does not.
3. Confirm the plural selector receives a numeric value at every call site; reject pre-formatted
   strings, `null`, and `undefined` before they reach the formatter.
4. Verify `Intl.PluralRules` (or the ICU equivalent) is constructed per locale rather than per rendered
   number, and that ordinal text uses `{ type: 'ordinal' }` or `selectordinal`.
5. For each locale in the catalog, diff the defined plural branches against that locale's CLDR
   categories and flag any locale whose `few`, `many`, `two`, or `zero` branch is a copy of `other`.
6. Validate the `Plural-Forms` header of every `gettext` catalog against CLDR, and assert that
   `msgstr[i]` is non-empty for every `i < nplurals`.
7. Check every message containing a substituted noun for gender and case agreement, and confirm the
   message carries a gender or case selector where the target language requires one.
8. Trace each message's variables to confirm they are arguments inside the message and not values
   assembled by the caller before translation.
9. Verify exact-match branches (`=0`, `=1`) and `offset` values against test cases at the boundary
   counts, and assert the rendered `#` for a non-exact branch.
10. Run the pseudolocalization pass through an ICU parser, transform only literal nodes, and confirm
    the pseudo-locale renders every category the target locale defines.
11. Inspect the catalog for duplicated source strings with different plural behavior and require
    distinct ids or `msgctxt` values, plus a description and screenshot for every plural message and
    ordinals marked as ordinals in the source.
12. Reject any path that lets untrusted input become the message pattern rather than an argument, and
    confirm the formatter's error hook reports a missing argument instead of rendering literal braces.
13. Run the extraction tool after adding a plural message, confirm the catalog diff contains the new
    forms for every target locale, then re-run the compile step the runtime consumes.

## References

- Unicode CLDR, _Language Plural Rules_ (categories, operands, rule syntax): https://unicode.org/reports/tr35/tr35-numbers.html#Language_Plural_Rules
- Unicode CLDR, _Plural rules syntax_: https://unicode.org/reports/tr35/tr35-numbers.html#Plural_rules_syntax
- CLDR plural rule charts, cardinal and ordinal, all locales: https://www.unicode.org/cldr/charts/latest/supplemental/language_plural_rules.html
- Unicode TR35 Part 9, _MessageFormat 2.0_: https://unicode.org/reports/tr35/tr35-messageFormat.html
- MessageFormat 2.0 documentation: https://messageformat.unicode.org/
- ICU User Guide, _Formatting Messages_: https://unicode-org.github.io/icu/userguide/format_parse/messages/
- ICU4J `MessageFormat` API: https://unicode-org.github.io/icu-docs/apidoc/released/icu4j/com/ibm/icu/text/MessageFormat.html
- ICU4J `PluralRules` API: https://unicode-org.github.io/icu-docs/apidoc/released/icu4j/com/ibm/icu/text/PluralRules.html
- ICU4J `com.ibm.icu.message2.MessageFormatter` API: https://unicode-org.github.io/icu-docs/apidoc/released/icu4j/com/ibm/icu/message2/MessageFormatter.html
- FormatJS `intl-messageformat`: https://formatjs.github.io/docs/intl-messageformat/
- FormatJS ICU MessageFormat parser (AST node kinds for tooling): https://formatjs.github.io/docs/icu-messageformat-parser/
- FormatJS CLI, `extract` and `compile`: https://formatjs.github.io/docs/tooling/cli/
- ECMA-402, PluralRules objects: https://tc39.es/ecma402/#pluralrules-objects
- GNU gettext manual, _Plural forms_: https://www.gnu.org/software/gettext/manual/html_node/Plural-forms.html
- GNU gettext manual, _PO Files_ (`msgid_plural`, `msgstr[n]`, `msgctxt`): https://www.gnu.org/software/gettext/manual/html_node/PO-Files.html
- Babel message catalogs and extraction: https://babel.pocoo.org/en/latest/messages.html
- Symfony translation component, ICU format and `+intl-icu` domains: https://symfony.com/doc/current/components/translation.html
- Project Fluent syntax guide, selectors and variant lists: https://projectfluent.org/fluent/guide/selectors.html
- `fluent-bundle` Rust API: https://docs.rs/fluent-bundle/latest/fluent_bundle/struct.FluentBundle.html
- ICU4X `PluralRules` API: https://docs.rs/icu/latest/icu/plurals/struct.PluralRules.html
- Android pseudolocales (`en-XA`, `ar-XB`): https://developer.android.com/guide/topics/resources/pseudolocales
- Sibling modules: [intl-language.md](intl-language.md), [intl-number-and-currency.md](intl-number-and-currency.md),
  [intl-date-and-time-format.md](intl-date-and-time-format.md), [intl-bidi.md](intl-bidi.md), [intl-collation-and-
  sorting.md](intl-collation-and-sorting.md), [intl-text-processing.md](intl-text-processing.md), [intl-content-and-
  assets.md](intl-content-and-assets.md), [intl-testing-and-qa.md](intl-testing-and-qa.md)

