# Unicode Text Processing and Segmentation

Text is a sequence of code points that users do not perceive as code points. Unicode defines several byte- and code-
point-level forms for the same visual character, and "one character" as perceived by a reader is a grapheme cluster that
may span many code points. Every operation built on `.length`, index arithmetic, or raw byte comparison — substring,
truncate, reverse, count, index, unique-constraint, password hash — silently corrupts or mis-compares non-ASCII text.
The failures are data-dependent and locale-dependent, so they pass English test suites and surface in production as
mojibake, split emoji, duplicate accounts, and spoofed identifiers.

## Contents

- [When This Applies](#when-this-applies)
- [Normalization Forms and Equality](#normalization-forms-and-equality)
- [Grapheme Clusters and Segmentation](#grapheme-clusters-and-segmentation)
- [Line Breaking and East Asian Wrapping](#line-breaking-and-east-asian-wrapping)
- [Case Folding and Locale-Sensitive Casing](#case-folding-and-locale-sensitive-casing)
- [Bytes, Encodings, and Confusables](#bytes-encodings-and-confusables)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- Any string comparison, equality check, dedupe, unique index, primary key, or lookup key over user-supplied text.
- Truncation, ellipsis, excerpting, "first N characters", table column clipping, or log-line capping.
- Character counters or length validators for form fields, bios, SMS segments, or tweet-like inputs.
- `substring`/`slice`/`substr`/`charAt`/`charCodeAt`/`[i]` indexing used to walk or edit text.
- Word wrapping, hyphenation, line breaking, or `white-space`/`overflow-wrap`/`word-break`/`line-break` tuning for CJK.
- Case conversion for search keys, emails, usernames, slugs, or sorting (especially Turkish, Azerbaijani, German, Greek).
- Parsing or emitting text from legacy encodings (Shift_JIS, EUC-JP, GB18030, Big5, EUC-KR, Windows-1252) or files with a BOM.
- Usernames, display names, domain names, file names, invite codes, or any identifier a human reads and trusts.
- Building search indexes, fuzzy match, autocomplete, or "did you mean" over multilingual content.

## Normalization Forms and Equality

Unicode assigns the same abstract character more than one code point sequence. `é` is U+00E9 (one code point) or U+0065
U+0301 (`e` + COMBINING ACUTE ACCENT, two code points). They render identically, compare unequal, have different
lengths, and hash differently. Normalization is the only fix.

| Form | Operation                                               | Preserves                  | Use for                                                                               |
| ---- | ------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------- |
| NFC  | Canonical decomposition, then canonical composition     | Canonical equivalence only | Storage, display, comparison, hashing, URLs, JSON, DB keys — the default              |
| NFD  | Canonical decomposition                                 | Canonical equivalence only | Text processing that must separate base + marks (accent stripping, per-mark analysis) |
| NFKC | Compatibility decomposition, then canonical composition | Nothing (lossy)            | Identifier comparison, search keys, security screening, legacy width folding          |
| NFKD | Compatibility decomposition                             | Nothing (lossy)            | Same as NFKC when you explicitly want the decomposed output                           |

NFC and NFD are information-preserving: `NFD(NFC(x))` returns a canonically equivalent string, so round-tripping is
safe. NFKC and NFKD are **lossy**: they fold compatibility distinctions that carry meaning in some scripts.

```javascript
const precomposed = "é"; // é  — 1 code unit
const decomposed = "é"; // é  — 2 code units
precomposed === decomposed; // false
precomposed.normalize("NFC") === decomposed.normalize("NFC"); // true
precomposed.normalize("NFD").length; // 2
"é".normalize("NFKD").length; // 2

"ﬁ".normalize("NFKC"); // "fi"   U+FB01 LATIN SMALL LIGATURE FI
"Ａ".normalize("NFKC"); // "A"    U+FF21 FULLWIDTH LATIN CAPITAL LETTER A
"①".normalize("NFKC"); // "1"    U+2460 CIRCLED DIGIT ONE
"µ".normalize("NFKC"); // "μ"    U+00B5 MICRO SIGN → U+03BC GREEK SMALL LETTER MU
"½".normalize("NFKC"); // "1⁄2"  U+00BD VULGAR FRACTION ONE HALF
```

NFKC is idempotent (`NFKC(NFKC(x)) === NFKC(x)`), so it is safe to apply repeatedly — but it is never safe to apply to
content whose compatibility distinctions matter: ligatures in typography, superscripts in chemistry, halfwidth katakana
in Japanese prose, and unit symbols such as U+3392 SQUARE MHZ (which folds to `MHz`). Normalize a _copy_ for the key;
store and render the original.

```python
import unicodedata

unicodedata.normalize("NFC", "é") == unicodedata.normalize("NFC", "é")  # True
unicodedata.is_normalized("NFC", "é")   # True   (Python 3.8+)
unicodedata.normalize("NFKC", "Ａ")      # 'A'
```

```php
<?php
Normalizer::normalize("e\u{0301}", Normalizer::FORM_C) === "\u{00E9}";  // true
Normalizer::isNormalized("\u{00E9}", Normalizer::NFC);                  // true
Normalizer::normalize("\u{FF21}", Normalizer::NFKC);                    // "A"
Normalizer::normalize("\u{FF21}", Normalizer::NFKC_CF);                 // "a" — NFKC + case fold
```

```sql
-- PostgreSQL 13+, UTF8 server encoding only. Form is an identifier, not a string.
SELECT normalize(U&'\0061\0308bc', NFC) = U&'\00E4bc' AS same;   -- true
SELECT U&'\0061\0308bc' IS NFC NORMALIZED;                       -- false
SELECT U&'\00E4bc'      IS NFKC NORMALIZED;                      -- true
```

```java
// Java
import java.text.Normalizer;
Normalizer.normalize("é", Normalizer.Form.NFC).equals("é");  // true
Normalizer.isNormalized("é", Normalizer.Form.NFC);                 // true
```

Normalize on the way in (before storing, indexing, hashing, or comparing) and normalize the query with the _same_ form.
A unique index on a column holding both NFC and NFD spellings of the same name permits two rows that a user cannot
distinguish.

## Grapheme Clusters and Segmentation

A grapheme cluster is what a reader calls one character. Unicode defines _extended_ grapheme clusters in UAX #29: base +
combining marks, Hangul syllable sequences, emoji modifier sequences, regional-indicator pairs (flags), and ZWJ
sequences all collapse to one cluster.

| String                | UTF-16 code units | Code points | Grapheme clusters |
| --------------------- | ----------------- | ----------- | ----------------- |
| `"é"` as U+00E9       | 1                 | 1           | 1                 |
| `"é"` as `e` + U+0301 | 2                 | 2           | 1                 |
| `"👨‍👩‍👧"`                | 8                 | 5           | 1                 |
| `"🇺🇳"` (flag)         | 4                 | 2           | 1                 |
| `"किंतु"` (Hindi)     | 5                 | 5           | 2                 |

Consequences of the three different "lengths":

| Ecosystem               | Code units / bytes       | Code points                       | Grapheme clusters                               |
| ----------------------- | ------------------------ | --------------------------------- | ----------------------------------------------- |
| JavaScript / TypeScript | `s.length` (UTF-16)      | `[...s].length`                   | `new Intl.Segmenter().segment(s)` count         |
| Python                  | `len(s.encode("utf-8"))` | `len(s)`                          | `regex.findall(r"\X", s)` (third-party `regex`) |
| PHP                     | `strlen($s)`             | `mb_strlen($s, "UTF-8")`          | `grapheme_strlen($s)`                           |
| Java                    | `s.length()`             | `s.codePointCount(0, s.length())` | `BreakIterator.getCharacterInstance()`          |
| Go                      | `len(s)`                 | `utf8.RuneCountInString(s)`       | `uniseg.GraphemeClusterCount(s)`                |
| Rust                    | `s.len()`                | `s.chars().count()`               | `s.graphemes(true).count()`                     |

`Intl.Segmenter` is the platform primitive for segmentation in JavaScript and Node:

```javascript
const seg = new Intl.Segmenter("en", { granularity: "grapheme" });
[...seg.segment("👨‍👩‍👧 a")].map((s) => s.segment); // ['👨‍👩‍👧', ' ', 'a']

const words = new Intl.Segmenter("ja", { granularity: "word" });
[...words.segment("吾輩は猫である。")]
  .filter((s) => s.isWordLike) // isWordLike is defined only for granularity: "word"
  .map((s) => s.segment); // ['吾輩', 'は', '猫', 'で', 'ある']

const sentences = new Intl.Segmenter("hi", { granularity: "sentence" });
[...sentences.segment("वाक्य एक। वाक्य दो।")].length; // 2 — splits on U+0964 danda
```

Segment objects expose `segment`, `index` (code-unit offset), `input`, and `isWordLike` (`undefined` unless granularity
is `"word"`). `segments.containing(index)` returns the segment covering a code-unit index, or `undefined` out of bounds.
Granularity defaults to `"grapheme"`. Word and sentence granularity are locale-sensitive; **grapheme** granularity is
not, because UAX #29 boundaries are locale-independent. Word segmentation for Japanese, Chinese, Thai, Lao, Khmer, and
Myanmar uses ICU dictionaries — `split(" ")` returns the whole string there, because those scripts do not delimit words
with spaces.

```python
import regex
regex.findall(r"\X", "👨‍👩‍👧 a")   # ['👨‍👩‍👧', ' ', 'a'] — `\X` is not in the stdlib `re` module
```

```php
<?php
grapheme_strlen("👨‍👩‍👧");                          // 1
$it = IntlBreakIterator::createCharacterInstance("en_US");
$it->setText("👨‍👩‍👧 a");
```

```rust
use unicode_segmentation::UnicodeSegmentation;
"👨‍👩‍👧 a".graphemes(true).collect::<Vec<_>>();   // ["👨‍👩‍👧", " ", "a"]
```

Extended grapheme clusters are still not universal. Indic conjuncts with a virama (क + ् + ष) are a single cluster only
under UAX #29 rule GB9c, added in Unicode 15.1, and CLDR's segmentation rules are broader than UAX #29's — so two
conforming libraries can disagree on Devanagari and other Indic text. Java's `BreakIterator.getCharacterInstance()`
documents conformance to extended grapheme cluster breaks. Do not hand-roll cluster logic from `\p{Mn}` and ZWJ checks;
the rule set has more than a dozen rules.

## Line Breaking and East Asian Wrapping

CJK text has no spaces, so line breaking cannot key on whitespace. UAX #14 defines break opportunities from character
classes, and kinsoku (禁則) rules — JLREQ in Japanese, CLREQ in Chinese — forbid breaking before certain characters (line-
head prohibition: `、。！？）」』】` and closing brackets) and after others (line-end prohibition: `（「『【` and opening brackets).
Browsers implement this through CSS, and the three properties are not interchangeable.

| Property        | Values                                                                                     | What it actually does                                                                                                                                                                                                                                                                                              |
| --------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `line-break`    | `auto`, `loose`, `normal`, `strict`, `anywhere`                                            | Selects the kinsoku strictness for CJK punctuation. `loose` permits breaks that `strict` forbids (small kana, prolonged sound mark, iteration marks). `anywhere` creates a soft wrap opportunity at every typographic character unit, ignoring prohibitions from the GL, WJ, and ZWJ classes and from `word-break` |
| `word-break`    | `normal`, `break-all`, `keep-all`, `auto-phrase` (experimental), `break-word` (deprecated) | `break-all` breaks between any two characters **but explicitly excludes CJK text**; `keep-all` forbids word breaks in CJK; `normal` uses the default rule                                                                                                                                                          |
| `overflow-wrap` | `normal`, `break-word`, `anywhere`                                                         | Emergency breaking inside a word that cannot fit. `anywhere` additionally makes those opportunities count toward `min-content` intrinsic size; `break-word` does not                                                                                                                                               |

That `word-break: break-all` excludes CJK is the trap: it is the wrong tool for Japanese or Chinese, where it is a no-
op, and the right tool for a long Latin URL in a narrow column. `word-break: keep-all` on a CJK paragraph produces
overflow instead of breaking — use it only when you intend to keep phrases intact and have another overflow strategy.

```css
.cjk-body {
  line-break: strict;
  word-break: normal;
  overflow-wrap: break-word;
}
.ja-newspaper {
  line-break: loose;
} /* short lines: permits more kinsoku breaks */
.latin-url {
  word-break: break-all;
} /* CJK is unaffected by break-all */
.no-cjk-break {
  word-break: keep-all;
} /* phrases stay whole; expect overflow */
```

`overflow-wrap: anywhere` and `break-word` render identically but differ in layout math: `anywhere` reduces the
element's `min-content` width, so a flex or grid track sized to `min-content` shrinks instead of overflowing. Choose
`anywhere` when the container should collapse around the long token.

```javascript
// Locale-aware word segmentation is a different operation from line breaking.
const wrap = (text, maxChars) => {
  const seg = new Intl.Segmenter("ja", { granularity: "word" });
  let line = "";
  const lines = [];
  for (const { segment, isWordLike } of seg.segment(text)) {
    if ((line + segment).length > maxChars && line) {
      lines.push(line);
      line = "";
    }
    line += segment;
    if (!isWordLike && line.length >= maxChars) {
      lines.push(line);
      line = "";
    }
  }
  return lines;
};
```

## Case Folding and Locale-Sensitive Casing

Case conversion is context- and language-sensitive. `toLowerCase()` and `toUpperCase()` are not inverses, and neither is
the right primitive for case-insensitive matching — case **folding** is.

- **Turkish and Azerbaijani.** `I` (U+0049) lowercases to `ı` (U+0131 LATIN SMALL LETTER DOTLESS I) in Turkish, not `i`;
  `i` uppercases to `İ` (U+0130 LATIN CAPITAL LETTER I WITH DOT ABOVE). Unicode's SpecialCasing.txt marks these with the
  `tr`/`az` locale tags and the `Not_Before_Dot` / `After_I` conditions.
- **German sharp s.** U+00DF `ß` uppercases to `SS`, so uppercase is length-expanding and lowercase is not its inverse.
  CaseFolding.txt gives `00DF; F; 0073 0073` — full case folding maps `ß` to `ss`, which is what makes `Fuß` and `FUSS`
  match.
- **Greek final sigma.** U+03A3 uppercases to itself but lowercases to U+03C2 `ς` at the end of a word and U+03C3 `σ`
  elsewhere. Context-dependent mappings cannot be expressed as a per-code-point table.
- **Default (non-Turkic) lowercase of U+0130** is the two-code-point sequence `i` + U+0307, because SpecialCasing.txt
  lists `0130; 0069 0307` as the default and `0130; 0069` only for `tr`/`az`.

| Ecosystem  | Locale-sensitive lower                             | Locale-sensitive upper                           | Case fold                                                                          |
| ---------- | -------------------------------------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------- |
| JavaScript | `s.toLocaleLowerCase("tr")`                        | `s.toLocaleUpperCase("tr")`                      | `s.toLowerCase().normalize("NFC")` is _not_ folding; use `Intl` + explicit compare |
| Python     | `s.lower()` (locale-independent)                   | `s.upper()`                                      | `s.casefold()` — full folding, `"ß".casefold() == "ss"`                            |
| Java       | `s.toLowerCase(Locale.forLanguageTag("tr"))`       | `s.toUpperCase(locale)`                          | `s.toLowerCase(Locale.ROOT)`                                                       |
| Go         | `strings.ToLowerSpecial(unicode.TurkishCase, s)`   | `strings.ToUpperSpecial(unicode.TurkishCase, s)` | `cases.Fold()` from `golang.org/x/text/cases`                                      |
| PHP        | `mb_strtolower($s, "UTF-8")` (no locale tailoring) | `mb_strtoupper($s, "UTF-8")`                     | compare with `Collator` at strength `PRIMARY`                                      |

```javascript
"I".toLowerCase(); // "i"     — wrong for Turkish
"I".toLocaleLowerCase("tr"); // "ı"     U+0131
"i".toLocaleUpperCase("tr"); // "İ"     U+0130
"İ".toLowerCase(); // "i̇"     U+0069 U+0307, length 2 — the non-Turkic default
"ß".toUpperCase(); // "SS"
"ß".toLowerCase(); // "ß"
"Straße".toLowerCase() === "STRASSE".toLowerCase(); // false — 6 vs 7 code units
"Straße".toUpperCase(); // "STRASSE"
```

```python
"ß".lower()       # 'ß'
"ß".casefold()    # 'ss'   — full folding, grows the string
"STRASSE".casefold() == "straße".casefold()   # True
"ΟΣ".lower()      # 'ος'   — final sigma applied
len("İ".lower())   # 2
```

`toLocaleLowerCase()` with no locale argument uses the host default locale, so the same code produces different keys on
different machines. Always pass the locale explicitly when it matters, and never use the host default for a value that
is persisted or compared across systems. For case-insensitive _matching_ rather than display, fold — do not lowercase —
and then compare bytewise. Cross-script comparison and ordering belong in [intl-collation-and-sorting.md](intl-
collation-and-sorting.md).

## Bytes, Encodings, and Confusables

Encoding and normalization are separate layers. A string can be perfectly valid UTF-8 and still be in a non-NFC form; a
byte stream can be valid in Shift_JIS and invalid in UTF-8. Both must be handled.

- **UTF-8** is a self-synchronizing variable-width encoding, 1–4 bytes per code point; ASCII bytes are unchanged, which
  makes it backward compatible with legacy ASCII tooling. U+FEFF encodes as `EF BB BF`.
- **UTF-16** is a code-unit encoding with surrogate pairs (U+D800–U+DFFF) for code points above U+FFFF. It is not a byte-
  oriented interchange encoding; never hash or compare UTF-16 bytes across platforms without fixing endianness. Lone
  surrogates are invalid scalar values: JavaScript's `TextEncoder` substitutes U+FFFD, while Python's
  `str.encode("utf-8")` raises `UnicodeEncodeError` unless you pass `errors="surrogatepass"`.
- **The BOM.** U+FEFF as `EF BB BF` is a _signature_ in UTF-8, not a byte-order indicator — UTF-8 has no byte order. In
  UTF-16 it does indicate byte order. `new TextDecoder("utf-8")` strips a leading BOM by default; `{ ignoreBOM: true }`
  keeps it in the output, which is the opposite of what the option name suggests. Python's `utf-8` codec leaves U+FEFF in
  the string; `utf-8-sig` strips it on decode and writes it on encode. A U+FEFF anywhere other than the start is ZERO
  WIDTH NO-BREAK SPACE and is a legitimate format character that normalization does not remove.
- **Legacy CJK encodings.** Shift_JIS, EUC-JP, EUC-KR, GB18030, and Big5 are the encodings you still meet in exported CSV,
  bank files, and government data. None are round-trip-safe for the full Unicode repertoire, and each has multiple vendor
  variants (CP932 vs Shift_JIS, CP949 vs EUC-KR).
- **WHATWG label aliasing.** The Encoding Standard maps the labels `iso-8859-1`, `latin1`, and `us-ascii` to
  **windows-1252**. So `new TextDecoder("iso-8859-1")` decodes byte `0x80` as U+20AC `€`, while Python's
  `b"\x80".decode("latin-1")` yields U+0080. Two "ISO-8859-1" decoders in the same stack can disagree on every byte from
  0x80 to 0x9F.
- **Invalid input.** `TextDecoder` substitutes U+FFFD for malformed sequences unless you pass `{ fatal: true }`, which
  throws `TypeError`. The labels `iso-2022-cn` and `iso-2022-cn-ext` map to the `replacement` encoding and make the
  constructor throw `RangeError`.

```javascript
new TextDecoder("utf-8").decode(new Uint8Array([0xef, 0xbb, 0xbf, 0x41])); // "A"
new TextDecoder("utf-8", { ignoreBOM: true }).decode(
  new Uint8Array([0xef, 0xbb, 0xbf, 0x41]),
); // "﻿A"
new TextDecoder("utf-8", { fatal: true }).decode(new Uint8Array([0xc3])); // throws TypeError
new TextDecoder("iso-8859-1").decode(new Uint8Array([0x80])); // "€" (windows-1252)
```

```python
b"\x80".decode("latin-1")                    # '\x80'   true ISO-8859-1
open("legacy.csv", encoding="utf-8-sig")     # strips a UTF-8 BOM if present
open("legacy.csv", encoding="shift_jis", errors="strict")
b"\xef\xbb\xbfA".decode("utf-8")             # '﻿A' — BOM kept
b"\xef\xbb\xbfA".decode("utf-8-sig")         # 'A'
```

```php
<?php
mb_detect_encoding($bytes, "UTF-8,SJIS,EUC-JP,GB18030,BIG-5", true);  // strict: returns false rather than guessing
```

Detection is a heuristic, never a guarantee: any byte sequence is valid in most single-byte encodings, so a detector can
only rule encodings _out_. Prefer an explicit encoding from the transport (HTTP `Content-Type`, DB connection charset,
file metadata) and use detection only as a fallback, always in strict mode. In MySQL, `utf8` is an alias for the 3-byte
`utf8mb3` and cannot store characters above U+FFFF — most emoji — so use `utf8mb4` for any column that accepts user
text.

**Confusables.** Unicode contains characters that render near-identically across scripts: Latin `a` (U+0061) vs Cyrillic
`а` (U+0430), Latin `o` (U+006F) vs Greek `ο` (U+03BF), Latin `e` (U+0065) vs Cyrillic `е` (U+0435). UTS #39 defines
single-script, mixed-script, and whole-script confusables and ships `confusables.txt`. The "Сirсlе" example has script
set `{ {Latn}, {Cyrl} }` — no single script covers it. Restriction levels, from most to least restrictive: ASCII-Only,
Single Script, Highly Restrictive (`Latn + Jpan`, `Latn + Hanb`, `Latn + Kore` are the only permitted multi-script
mixes), Moderately Restrictive (Latin plus exactly one other Recommended script, excluding Cyrillic and Greek),
Minimally Restrictive, Unrestricted. Restriction-level and confusable checks belong on any identifier a human will read
and trust — usernames, display names, tenant slugs, invite codes, file names, and domain labels. A confusable skeleton
is computed by decomposing, applying the `confusables.txt` mapping, then recomposing; two strings are confusable when
their skeletons match. ICU exposes this as `SpoofChecker`; most standard libraries do not, so plan on the Unicode data
files or a dedicated library.

## Common Mistakes

| Mistake                                                                                 | Why It Breaks                                                                                                                                                   | Correct Approach                                                                                                                                                                   |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Comparing strings with `===`, `==`, or `strcmp` without normalizing                     | NFC and NFD spellings of `é` are different byte sequences; logins, dedupe, and unique indexes fail                                                              | Normalize both sides to the same form (usually NFC) at the boundary, before storing, hashing, or comparing                                                                         |
| Storing NFKC output as the canonical value                                              | NFKC folds ligatures, superscripts, halfwidth katakana, and U+00B5 → U+03BC; the original text is unrecoverable                                                 | Store the original; build a separate NFKC key column or hash for lookup                                                                                                            |
| Using `str.length`, `.substring()`, `.slice()`, `.charAt()`, or `[i]` to count or split | These operate on UTF-16 code units, splitting surrogate pairs, ZWJ sequences, and combining marks                                                               | `Intl.Segmenter` with `granularity: "grapheme"`; `grapheme_strlen`/`grapheme_substr` in PHP; `BreakIterator.getCharacterInstance()` in Java                                        |
| Assuming `[...str]` fixes everything                                                    | Spread iterates code points, so `"👨‍👩‍👧"` becomes 5 items and combining marks separate from their base                                                             | Iterate grapheme clusters, not code points, whenever the unit is a user-perceived character                                                                                        |
| Using `word-break: break-all` to wrap Japanese or Chinese                               | `break-all` explicitly excludes CJK text and is a no-op there                                                                                                   | `line-break: strict` (or `loose` for short lines) plus `overflow-wrap: break-word`; leave `word-break` at `normal`                                                                 |
| Using `word-break: keep-all` on CJK body text to "stop bad breaks"                      | It forbids CJK word breaks entirely, so lines overflow their container                                                                                          | `keep-all` only for short phrases where overflow is designed for; otherwise use `line-break` to tune kinsoku strictness                                                            |
| Confusing `overflow-wrap: break-word` with `anywhere`                                   | They render the same but `anywhere` lowers `min-content`, so a `min-content`-sized flex or grid track collapses with `anywhere` and overflows with `break-word` | Pick deliberately: `anywhere` when the container should shrink, `break-word` when it should not                                                                                    |
| Calling `toLowerCase()` for case-insensitive matching                                   | Turkish `I`/`İ` and German `ß` do not round-trip; `"Straße"` and `"STRASSE"` compare unequal                                                                    | Case-_fold_ (`casefold()` in Python, `Locale.ROOT` in Java, `cases.Fold()` in Go), or compare at primary strength with a `Collator`                                                |
| Calling `toLocaleLowerCase()` with no locale for persisted keys                         | Uses the host default locale, so keys differ per machine and per container image                                                                                | Pass the locale explicitly, or use the locale-independent operation and document the choice                                                                                        |
| Trusting `strlen()` or `len(s)` as a byte count for storage limits                      | PHP `strlen` is bytes, Python `len` is code points, JS `.length` is UTF-16 code units — three different numbers                                                 | Choose the unit deliberately: bytes for column limits, graphemes for user-facing counters                                                                                          |
| Relying on HTML `maxlength` for a "characters" counter                                  | Browsers enforce it against the JS string length in UTF-16 code units, so emoji and CJK count as 2 or 3                                                         | Validate server-side by grapheme cluster count; treat `maxlength` as a soft input hint                                                                                             |
| Reversing a string with `split("").reverse().join("")`                                  | Splits surrogate pairs into lone surrogates and reorders ZWJ sequences and regional-indicator pairs, producing broken glyphs or a different flag                | Segment into grapheme clusters, reverse the cluster array, rejoin                                                                                                                  |
| Truncating with `slice(0, n) + "…"`                                                     | Can cut inside a surrogate pair, a ZWJ sequence, or a base+mark pair, producing U+FFFD or a dangling joiner                                                     | Truncate on grapheme boundaries with `Intl.Segmenter`; or let CSS `text-overflow: ellipsis` handle visual truncation                                                               |
| Using `\p{Emoji}` in a JS regex to detect emoji                                         | `\p{Emoji}` matches single code points, matches emoji _fragments_ (the `👨` inside a ZWJ sequence), and matches `#`, `*`, and digits `0-9`                      | Use `\p{RGI_Emoji}` under the `v` flag, and remember it omits non-RGI, underqualified, and overqualified sequences; `\p{Extended_Pictographic}` also matches non-emoji pictographs |
| Reaching for `\X` in JavaScript, Python `re`, Go, or Rust `regex`                       | None of those engines support the UAX #18 `\X` grapheme escape (Python's `re` raises `bad escape \X`)                                                           | Use `Intl.Segmenter`, Python's `regex` module, `rivo/uniseg`, or the `unicode-segmentation` crate; PCRE2 and Java 9+ do support `\X`                                               |
| Decoding untrusted bytes with the default `TextDecoder` options                         | Malformed input is silently replaced with U+FFFD, corrupting data that looks fine                                                                               | Use `{ fatal: true }` and handle `TypeError`; use strict detection (`mb_detect_encoding(..., true)`) in PHP                                                                        |
| Assuming `iso-8859-1` means ISO-8859-1 in a browser                                     | WHATWG maps that label to windows-1252, so bytes 0x80–0x9F decode to different characters than Python's `latin-1`                                               | Name the encoding you actually mean (`windows-1252` or `latin-1`) and verify a known byte round-trips                                                                              |
| Hashing a password without normalizing first                                            | The same typed password hashes differently depending on the keyboard, OS, or IME that produced the accents                                                      | Normalize to NFC before hashing; do not NFKC (it is lossy and reduces the effective keyspace)                                                                                      |
| Skipping restriction-level and confusable checks on usernames                           | Cyrillic `а`/`е`/`о` look identical to Latin, enabling impersonation and phishing with distinct identifiers                                                     | Screen identifiers against UTS #39 restriction levels and compare confusable skeletons against existing identifiers                                                                |
| Indexing a column as `utf8` in MySQL                                                    | `utf8` aliases the 3-byte `utf8mb3`, which rejects or mangles characters above U+FFFF, including most emoji                                                     | Use `utf8mb4` for every column that accepts user text                                                                                                                              |

## Checklist

1. Confirm every text input path normalizes to a single declared form (usually NFC) before the value is stored, indexed,
   hashed, or compared — and that the query path normalizes with the same form.
2. Verify no user-visible or comparison-sensitive value is stored in NFKC or NFKD form; NFKC-derived keys must live in a
   separate column, index, or field from the original.
3. Grep the codebase for `.substring(`, `.substr(`, `.slice(`, `.charAt(`, `.charCodeAt(`, `substr(`, `mb_substr(`, and
`[i]` indexing over text, and confirm each call site is either grapheme-safe or provably ASCII-only.
4. Replace every user-facing character counter and length validator with a grapheme cluster count (`Intl.Segmenter`,
`grapheme_strlen`, `BreakIterator.getCharacterInstance()`, `uniseg.GraphemeClusterCount`).
5. Confirm every truncation, ellipsis, excerpt, and column clip operates on grapheme boundaries, and test with a ZWJ
emoji family, a flag, and a base+combining-mark pair.
6. Confirm no string reversal uses `split("")` or byte-level reversal; reversal must segment into grapheme clusters
first, and any bidirectional script must be left to the browser's BiDi algorithm (see [intl-bidi.md](intl-bidi.md)).
7. Audit every case conversion: locale-sensitive operations must pass an explicit locale, and case-insensitive matching
must use case folding or a primary-strength `Collator`, not `toLowerCase()`.
8. Add regression cases for Turkish (`I`, `i`, `İ`, `ı`), Azerbaijani, German `ß`/`SS`, and Greek final sigma to the test suite.
9. Confirm unique constraints, primary keys, and dedupe logic apply to a normalized value, and that a test inserts both
an NFC and an NFD spelling of the same string and asserts a single row.
10. Verify the database charset and collation: `utf8mb4` in MySQL, UTF8 server encoding in PostgreSQL, and matching
normalization between application and database.
11. Check every decode site for an explicit encoding from the transport, strict error handling (`fatal: true`,
`errors="strict"`, `mb_detect_encoding(..., true)`), and deliberate BOM policy; test with a BOM-prefixed file.
12. Confirm legacy encodings (Shift_JIS, CP932, EUC-JP, GB18030, Big5, CP949, windows-1252) are named explicitly and
covered by a round-trip test, and that `iso-8859-1` is never used where `windows-1252` was meant.
13. Confirm CJK wrapping uses `line-break` for kinsoku tuning and does not rely on `word-break: break-all`, and that
`keep-all` is used only where overflow is designed for.
14. Screen human-readable identifiers against UTS #39 restriction levels and confusable skeletons, and confirm the check runs on create _and_ rename.
15. Confirm word and sentence segmentation uses `Intl.Segmenter` or an ICU-backed break iterator with the correct
locale, and that no code assumes spaces delimit words.
16. Verify search indexing and autocomplete normalize both the indexed corpus and the query, and that `\X`/`\p{...}`
patterns are only used in engines that support them.
17. Run the full text-processing test suite against strings containing NFC/NFD pairs, ZWJ emoji sequences, regional-
indicator flags, Indic conjuncts, Hangul jamo, and a lone surrogate, asserting no exception, no U+FFFD, and no split
cluster.

## References

- [UAX #15: Unicode Normalization Forms](https://www.unicode.org/reports/tr15/) — the normative definition of NFC, NFD,
  NFKC, NFKD, canonical vs compatibility equivalence, and the Quick_Check properties.
- [UAX #29: Unicode Text Segmentation](https://www.unicode.org/reports/tr29/) — extended grapheme cluster, word, and
  sentence boundary rules, including the Unicode 15.1 Indic conjunct rule GB9c.
- [UAX #14: Unicode Line Breaking Algorithm](https://www.unicode.org/reports/tr14/) — the break-class table behind CJK line breaking and CSS `line-break`.
- [UAX #11: East Asian Width](https://www.unicode.org/reports/tr11/) — width classes for fullwidth/halfwidth, wide, and ambiguous characters.
- [UTS #39: Unicode Security Mechanisms](https://www.unicode.org/reports/tr39/) — restriction levels, script-set (SOSS)
  detection, mixed-number detection, and the confusable-detection algorithm.
- [UTR #36: Unicode Security Considerations](https://www.unicode.org/reports/tr36/) — the threat model behind homoglyph and whole-script-confusable attacks.
- [UTR #21: Case Mappings](https://www.unicode.org/reports/tr21/) — simple vs full case conversion, locale-dependent mappings, and caseless matching.
- [UTS #18: Unicode Regular Expressions](https://www.unicode.org/reports/tr18/) — the `\X`, `\b{g}`, `\b{w}`, `\b{l}`,
  `\b{s}` escapes and the levels of Unicode regex support.
- [UTS #51: Unicode Emoji](https://www.unicode.org/reports/tr51/) — emoji sequences, ZWJ sequences, variation selectors,
  and the RGI set that `\p{RGI_Emoji}` encodes.
- [Unicode Character Database](https://www.unicode.org/Public/UCD/latest/ucd/) —
  [CaseFolding.txt](https://www.unicode.org/Public/UCD/latest/ucd/CaseFolding.txt),
  [SpecialCasing.txt](https://www.unicode.org/Public/UCD/latest/ucd/SpecialCasing.txt), and
  [confusables.txt](https://www.unicode.org/Public/security/latest/confusables.txt).
- [W3C JLREQ: Requirements for Japanese Text Layout](https://www.w3.org/TR/jlreq/) — the normative kinsoku rules for line-head and line-end prohibition.
- [WHATWG Encoding Standard](https://encoding.spec.whatwg.org/) — encoding labels, the `replacement` encoding, BOM
  handling, and the `iso-8859-1` → `windows-1252` aliasing.
- [MDN: `Intl.Segmenter`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/Segmenter)
  — granularity values, segment object shape, and `Segments.prototype.containing()`.
- [MDN: `String.prototype.normalize()`](https://developer.mozilla.org/en-
  US/docs/Web/JavaScript/Reference/Global_Objects/String/normalize) — accepted form values and the `RangeError` on invalid
  input.
- [MDN: `line-break`](https://developer.mozilla.org/en-US/docs/Web/CSS/line-break), [`word-
  break`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/word-break), and [`overflow-
  wrap`](https://developer.mozilla.org/en-US/docs/Web/CSS/overflow-wrap) — exact keyword values and their CJK and
  intrinsic-size behavior.
- [MDN: `TextDecoder` constructor](https://developer.mozilla.org/en-US/docs/Web/API/TextDecoder/TextDecoder) — the `fatal`
  and `ignoreBOM` options and the `RangeError` for replacement-encoding labels.
- [Python `unicodedata`](https://docs.python.org/3/library/unicodedata.html) and [Python
  `codecs`](https://docs.python.org/3/library/codecs.html) — `normalize`/`is_normalized` forms and the `utf-8-sig` BOM
  behavior.
- [Python `regex` module](https://pypi.org/project/regex/) — the `\X` extended grapheme cluster escape missing from the standard `re` module.
- [PHP `Normalizer`](https://www.php.net/manual/en/class.normalizer.php) and [PHP
  `grapheme_strlen`](https://www.php.net/manual/en/function.grapheme-strlen.php) — normalization constants including
  `NFKC_CF`, and grapheme-based length and substring functions.
- [Java `BreakIterator`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/text/BreakIterator.html) —
  character, word, line, and sentence boundary analysis and its documented extended-grapheme-cluster conformance.
- [Go `golang.org/x/text/unicode/norm`](https://pkg.go.dev/golang.org/x/text/unicode/norm) and
  [`rivo/uniseg`](https://pkg.go.dev/github.com/rivo/uniseg) — `Form.String`/`IsNormalString` and UAX #29 grapheme, word,
  sentence, and line segmentation.
- [Rust `unicode-normalization`](https://docs.rs/unicode-normalization/) and [`unicode-
  segmentation`](https://docs.rs/unicode-segmentation/) — the `UnicodeNormalization` trait and UAX #29
  `graphemes`/`unicode_words` iterators.
- [PostgreSQL string functions](https://www.postgresql.org/docs/current/functions-string.html) — `normalize()` and the `IS NFC NORMALIZED` predicate, UTF8-only.
- [MySQL `utf8mb4`](https://dev.mysql.com/doc/refman/8.0/en/charset-unicode-utf8mb4.html) — why the `utf8` alias for
  `utf8mb3` cannot store astral-plane characters.

