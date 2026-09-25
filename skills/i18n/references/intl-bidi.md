# Bidirectional Text and RTL Layout

Bidirectional text is the rendering problem created when right-to-left scripts (Arabic, Hebrew, Syriac, Thaana, N'Ko,
Adlam, and others) share a line with left-to-right content — Latin words, digits, URLs, code. The Unicode Bidirectional
Algorithm (UAX #9) resolves that mix into a visual order at render time, and it does so from _character properties_, not
from the author's intent. Every production breakage in this domain comes from the same root cause: source text is stored
in logical order, the engine reorders it, and layout code written against physical directions (`left`, `right`,
`translateX`) silently assumes LTR.

The failure mode is rarely a crash. It is a phone number whose leading `+` renders on the wrong side, a URL that splits
mid-token, a chevron pointing backwards, an animation sliding in from the wrong edge, or a control character that makes
source code render differently from what the compiler sees.

## Contents

- [When This Applies](#when-this-applies)
- [Logical Order, the `dir` Attribute, and Isolation](#logical-order-the-dir-attribute-and-isolation)
  - [Control characters](#control-characters)
  - [CSS direction and isolation](#css-direction-and-isolation)
- [CSS Logical Properties, Flexbox, and Grid](#css-logical-properties-flexbox-and-grid)
- [Mirroring, Transforms, and Motion](#mirroring-transforms-and-motion)
- [Common Mistakes](#common-mistakes)
  - [Detecting and stripping bidi controls](#detecting-and-stripping-bidi-controls)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- Adding `dir="rtl"` support, or any RTL locale (`ar`, `he`, `fa`, `ur`, `ps`, `sd`, `ug`, `yi`, `dv`, `ckb`, `nqo`, `ff-
  Adlm`), to an existing LTR-only product.
- Rendering user-generated content, display names, comments, or chat messages that may begin with a strong RTL character.
- Rendering a token that must not be reordered: phone numbers, URLs, email addresses, IBANs, version strings, IP/MAC
  addresses, file paths, git SHAs, coordinates, coupon codes, order IDs.
- Writing or auditing CSS that positions elements with `left`/`right`/`margin-left`/`padding-right`/`translateX`, or that
  builds layout with flexbox, grid, `order`, or `position: absolute`.
- Shipping directional iconography: back/forward chevrons, undo/redo, progress indicators, sliders, breadcrumb separators, indent controls.
- Localizing a mobile or desktop client (Android, iOS/SwiftUI, Flutter, React Native, Qt) where mirroring is a platform setting rather than a stylesheet.
- Sanitizing untrusted input that reaches source code, filenames, log output, or UI labels (Trojan Source, CVE-2021-42574).
- Reviewing screenshots or snapshot tests where the text was "translated" by reversing Latin characters instead of using real RTL content.

## Logical Order, the `dir` Attribute, and Isolation

Text is always stored in **logical order** — the order a human reads it, independent of screen geometry. Visual order is
computed per line by UAX #9 and must never be persisted. Storing visually reordered text (for example, writing `,Hello`
into the database because that is what appeared on screen) corrupts the data: copy-paste, search, screen readers,
diffing, and any later render in a different direction all break, and the damage is not reversible without the original
logical string.

The algorithm works in stages. It splits content into paragraphs, sets each paragraph's base level from its first strong
character (rule P2/P3), assigns explicit levels for embedding and override controls, resolves weak types (rules W1–W7),
resolves bracket pairs and neutrals (N0–N2), assigns implicit levels (I1–I2), then reorders each line by reversing
contiguous runs from the highest level down to the lowest odd level (L2). Rule L1 separately resets trailing whitespace
and separators to the paragraph level.

The consequence that surprises engineers: a neutral character — comma, period, colon, parenthesis, slash, `+`, `@`, `#`
— between an LTR run and an RTL run, or between a run and the paragraph boundary, takes the **paragraph** direction, not
the direction of the run it visually belongs to.

| Character class             | Bidi types           | Behavior                                                                                |
| --------------------------- | -------------------- | --------------------------------------------------------------------------------------- |
| Strong LTR                  | `L`                  | Latin, Greek, Cyrillic, most other LTR scripts                                          |
| Strong RTL                  | `R`, `AL`            | Hebrew (`R`), Arabic/Syriac/Thaana (`AL`); `AL` differs from `R` in the weak-type rules |
| Weak numbers                | `EN`, `AN`           | European digits (`EN`), Arabic-Indic digits (`AN`)                                      |
| Weak separators/terminators | `ES`, `ET`, `CS`     | `+` `-` (ES), `%` `#` `$` `°` (ET), `,` `.` `:` `/` (CS)                                |
| Neutrals                    | `ON`, `WS`, `B`, `S` | punctuation, spaces, paragraph and segment separators                                   |
| Non-spacing / boundary      | `NSM`, `BN`          | combining marks, control characters                                                     |

Three rules produce most real-world bugs:

- **W2** — a European number preceded (scanning back to the first strong character) by `AL` is retyped as an Arabic
  number. A number embedded in Arabic text therefore interacts with adjacent separators differently than the same number
  in Hebrew text.
- **W4** — a single `ES` or `CS` _between two numbers of the same type_ is absorbed into the number. This is why
  `972-3-1234567` keeps its internal hyphens and why a **leading** `+` does not: nothing is to its left, so W6 demotes it
  to `ON` and N2 gives it the paragraph direction.
- **N1/N2** — a neutral sequence adopts the surrounding strong direction if both sides agree; otherwise it adopts the embedding (paragraph) direction.

The two canonical bugs follow directly. In an RTL paragraph:

```
logical:  + 9 7 2 - 3 - 1 2 3 4 5 6 7
levels:   1 2 2 2 2 2 2 2 2 2 2 2 2
visual:   9 7 2 - 3 - 1 2 3 4 5 6 7 +      the "+" jumps to the visual right
```

```
logical:  H e l l o ,
levels:   2 2 2 2 2 1
visual:   , H e l l o                        the "," jumps to the visual left
```

A bare number is safe — its two reversals cancel — which is exactly why the bug is misdiagnosed as "numbers are broken"
when it is the _adjacent neutral_ that moved.

### Control characters

| Control | Code point | Function                   | Status                       |
| ------- | ---------- | -------------------------- | ---------------------------- |
| LRM     | U+200E     | strong LTR mark            | current                      |
| RLM     | U+200F     | strong RTL mark            | current                      |
| ALM     | U+061C     | strong Arabic-letter mark  | current                      |
| LRE     | U+202A     | left-to-right embedding    | **deprecated** (Unicode 6.3) |
| RLE     | U+202B     | right-to-left embedding    | **deprecated**               |
| PDF     | U+202C     | pop directional formatting | **deprecated**               |
| LRO     | U+202D     | left-to-right override     | **deprecated**               |
| RLO     | U+202E     | right-to-left override     | **deprecated**               |
| LRI     | U+2066     | left-to-right isolate      | current                      |
| RLI     | U+2067     | right-to-left isolate      | current                      |
| FSI     | U+2068     | first-strong isolate       | current                      |
| PDI     | U+2069     | pop directional isolate    | current                      |

LRE/RLE/PDF/LRO/RLO are deprecated but still _processed_, so legacy content containing them does not break — it simply
must not be generated. They leak scope: an unbalanced RLE affects the rest of the paragraph, whereas isolates are self-
contained and nest safely. Isolates also participate correctly in bracket-pair resolution (N0) and in the surrounding
neutral resolution, which embeddings do not. The replacement rule is mechanical: `<LRE>` → `<LRI>` or `<RLI>` as
appropriate, `PDF` → `PDI`.

In HTML use the named references `&lrm;` and `&rlm;` rather than pasting invisible code points, and in CSS use `content: "\200F"` for a generated RLM.

```html
<p dir="rtl">تم الشحن <bdi dir="ltr">+972-3-1234567</bdi> أمس.</p>
<p dir="rtl">
  المرجع <span dir="ltr" style="unicode-bidi: isolate">INV-2024-0042</span>.
</p>
<p>المستخدم <bdi>@user</bdi> علّق على المنشور.</p>
```

`<bdi>` is defined as a bidi isolate and defaults to `dir="auto"`, so its base direction comes from its own first strong
character. That is the correct wrapper for an untrusted display name. `dir="auto"` on any element does the same base-
direction computation; per the HTML specification it skips strong characters inside descendants that carry their own
`dir` attribute.

`<bdo>` is **not** an isolate: it maps to `unicode-bidi: bidi-override` and reverses characters. Never wrap user data in `<bdo>`.

### CSS direction and isolation

`direction` sets the base direction of a block's paragraphs; `unicode-bidi` controls embedding and isolation. The
initial value of `unicode-bidi` is `normal`, so a bare `dir="ltr"` on a `<span>` sets `direction` without guaranteeing
isolation — set `unicode-bidi: isolate` explicitly, or use `<bdi>`, when a run must not interact with surrounding text.

| `unicode-bidi` value | Effect                                                                                                                              |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `normal`             | no embedding, no isolation (default)                                                                                                |
| `embed`              | opens a legacy embedding, equivalent to LRE/RLE                                                                                     |
| `isolate`            | isolates the element's content; equivalent to LRI/RLI/FSI depending on `direction`                                                  |
| `bidi-override`      | forces every character to `direction`, reversing as needed — do not use on user data                                                |
| `isolate-override`   | `isolate` plus `bidi-override`                                                                                                      |
| `plaintext`          | behaves as `isolate` but derives the block's base direction from its own first strong character, ignoring the inherited `direction` |

`unicode-bidi: plaintext` is the block-level analogue of `dir="auto"` and is the right tool for a user-content container
whose direction must not be inherited from the surrounding page.

## CSS Logical Properties, Flexbox, and Grid

Logical properties name sides by their role in the writing mode — `inline` runs along the text direction, `block` runs
down the page — so they flip automatically with `direction`. Under `writing-mode: horizontal-tb` and `direction: ltr`,
`inline-start` is `left`; under `direction: rtl` it is `right`.

| Physical                         | Logical                                       |
| -------------------------------- | --------------------------------------------- |
| `margin-left` / `margin-right`   | `margin-inline-start` / `margin-inline-end`   |
| `margin-top` / `margin-bottom`   | `margin-block-start` / `margin-block-end`     |
| `padding-left` / `padding-right` | `padding-inline-start` / `padding-inline-end` |
| `border-left` / `border-right`   | `border-inline-start` / `border-inline-end`   |
| `left` / `right`                 | `inset-inline-start` / `inset-inline-end`     |
| `top` / `bottom`                 | `inset-block-start` / `inset-block-end`       |
| `width` / `height`               | `inline-size` / `block-size`                  |
| `min-width` / `max-height`       | `min-inline-size` / `max-block-size`          |
| `text-align: left`               | `text-align: start`                           |
| `float: left`                    | `float: inline-start`                         |
| `clear: left`                    | `clear: inline-start`                         |
| `border-top-left-radius`         | `border-start-start-radius`                   |
| `border-top-right-radius`        | `border-start-end-radius`                     |
| `border-bottom-left-radius`      | `border-end-start-radius`                     |
| `border-bottom-right-radius`     | `border-end-end-radius`                       |
| `resize: horizontal`             | `resize: inline`                              |

Shorthands follow the same pattern: `margin-inline`, `margin-block`, `padding-inline`, `padding-block`, `border-inline`,
`border-block`, `inset-inline`, `inset-block`. The corner-radius mapping is writing-mode dependent — `border-start-
start-radius` is the top-left corner only in `horizontal-tb` with `direction: ltr`.

```css
.card {
  margin-inline-start: 1.5rem;
  padding-inline: 1rem;
  border-inline-start: 3px solid var(--accent);
  inline-size: min(100%, 32rem);
  text-align: start;
}
.drawer {
  position: fixed;
  inset-block: 0;
  inset-inline-end: 0;
}
.icon-directional {
  transform: scaleX(-1);
}
[dir="rtl"] .icon-directional {
  transform: none;
}
```

Flexbox and grid already follow the inline axis, so they flip for free once `direction` is set on an ancestor:

- `flex-direction: row` lays items from inline-start to inline-end — in RTL, the first item appears on the right. `row-
  reverse` is the _opposite of the inline axis_, so under RTL it lays out left-to-right.
- `justify-content: flex-start` / `flex-end` map to main-start / main-end, which follow the inline axis. `justify-content: start` / `end` do the same.
- Grid column 1 is at inline-start, so `grid-template-columns: 1fr 2fr` mirrors automatically, as does `grid-column: 1 / 3`.
- `order` and `grid-row` are direction-independent and do **not** flip.
- `position: absolute; left: 0` does **not** flip. This is the single most common RTL layout regression.

Never emulate RTL by reversing the DOM or by abusing `row-reverse`. `direction` reorders visually without touching DOM
order, so screen readers and keyboard tab order stay logical — which is the desired outcome. Reversing markup to fix
appearance destroys that.

Two tooling traps: Tailwind's `space-x-*` utilities have historically compiled to a physical `margin-left` on siblings
and therefore do not mirror — prefer `gap-*` on a flex or grid container. And in Tailwind, use the logical utilities
(`ms-*`, `me-*`, `ps-*`, `pe-*`, `start-*`, `end-*`, `border-s-*`, `border-e-*`, `rounded-s-*`, `rounded-e-*`, `text-
start`, `text-end`, `float-start`, `float-end`) plus the `rtl:` / `ltr:` variants instead of hand-written `[dir="rtl"]`
overrides.

## Mirroring, Transforms, and Motion

`transform`, `translate`, `left`, `right`, and `background-position` are physical and are never flipped by `direction`.
An entry animation written as `transform: translateX(-100%)` slides in from the left in both LTR and RTL; in an RTL
build it must slide in from the right.

```css
@keyframes slide-in-ltr {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(0);
  }
}
@keyframes slide-in-rtl {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

.toast {
  animation: slide-in-ltr 200ms ease-out;
}
[dir="rtl"] .toast {
  animation-name: slide-in-rtl;
}
```

Prefer animating a logical property where the effect allows it — `margin-inline-start`, `inset-inline-start`, or
`inline-size` — so no direction-specific keyframes are needed. `scaleX(-1)` mirrors glyphs as well as shapes, so apply
it to an icon element only, never to a container that holds text, and never to an icon font container where non-
directional icons live alongside directional ones.

Which glyphs mirror is a Unicode property, not a design decision: paired punctuation such as `( ) [ ] { } < >` carries
`Bidi_Mirrored` and is mirrored by the font automatically (see `BidiMirroring.txt`). Your job is the icon layer.

| Mirror in RTL                                                             | Do not mirror                                                                                   |
| ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Back / forward navigation arrows, chevrons used for next/previous         | Media transport controls: play, pause, stop (the play triangle points right in every direction) |
| Undo / redo                                                               | Clock faces, clockwise rotation, timer icons                                                    |
| Indent / outdent, list markers, tree expand chevrons on a horizontal axis | Logos, brand marks, wordmarks, flags                                                            |
| Progress bars and steppers (fill direction follows reading order)         | Charts with a meaningful axis: time series, cartesian plots, ordered scales                     |
| Breadcrumb separators, "read more" arrows, reply / forward arrows         | Checkmarks, plus / minus, mathematical and currency symbols                                     |
| Sliders and range inputs whose increase follows reading order             | Universal symbols: power, Wi-Fi, battery, search magnifier, hamburger menu                      |

Implement mirroring with the platform's own metadata rather than ad-hoc flips: `android:autoMirrored="true"` on vector
and bitmap drawables, `Image(...).flipsForRightToLeftLayoutDirection(true)` in SwiftUI, and the RTL-mirroring flag that
Material Symbols and Icons publish per glyph. Mirroring an icon that the icon set marks as non-mirrorable is a defect,
not a stylistic choice.

Platform layout APIs are direction-aware and should be used instead of physical ones:

| Platform        | Use                                                                                                                                            | Avoid                                                              |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Android         | `android:layout_marginStart` / `End`, `paddingStart` / `End`, `drawableStart`, `textAlignment="viewStart"`, `Gravity.START`, `layoutDirection` | `layout_marginLeft`, `paddingLeft`, `drawableLeft`, `Gravity.LEFT` |
| Flutter         | `EdgeInsetsDirectional`, `AlignmentDirectional`, `PositionedDirectional`, `BorderDirectional`, `Directionality.of(context)`                    | `EdgeInsets.only(left:)`, `Alignment.centerLeft`                   |
| SwiftUI / UIKit | `leading` / `trailing`, `semanticContentAttribute`, `naturalTextAlignment`                                                                     | `left` / `right` constraints                                       |
| React Native    | `marginStart` / `end`, `paddingStart` / `end`, `writingDirection`, `I18nManager.isRTL`                                                         | `marginLeft`, `paddingRight`                                       |

## Common Mistakes

| Mistake                                                                                  | Why It Breaks                                                                                                                    | Correct Approach                                                                                                        |
| ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Storing or diffing visually reordered text                                               | The reordering is a render-time artifact; persisting it corrupts search, copy-paste, screen readers, and any later render        | Store logical order only; reorder at paint time                                                                         |
| Wrapping a phone number, URL, or ID in `<span dir="ltr">` alone                          | `dir` sets `direction` but `unicode-bidi`'s initial value is `normal`, so the token can still interact with surrounding neutrals | Use `<bdi dir="ltr">` or add `unicode-bidi: isolate`                                                                    |
| Fixing a leading `+` or `@` by reversing the string or adding a space                    | `+`/`@` are `ES`/`ON`; with nothing strong to their left, W6/N2 give them the paragraph direction                                | Isolate the whole token; never mutate the data                                                                          |
| Emulating RTL with `flex-direction: row-reverse` or a reversed DOM                       | DOM order no longer matches reading order, breaking tab order, screen readers, and copy-paste                                    | Set `dir="rtl"` on the container and keep markup logical                                                                |
| Using `left`, `right`, `margin-left`, `padding-right`, `text-align: left`, `float: left` | Physical properties ignore `direction` and never mirror                                                                          | Use `inset-inline-start/end`, `margin-inline-*`, `padding-inline-*`, `text-align: start`, `float: inline-start`         |
| Assuming `transform: translateX()` flips under RTL                                       | Transforms are physical coordinates                                                                                              | Author RTL-aware keyframes, or animate a logical property such as `inset-inline-start`                                  |
| Applying `scaleX(-1)` to a container holding text or to a whole icon font                | Mirrors glyphs, producing unreadable text and backwards non-directional icons                                                    | Apply to the individual directional icon element only                                                                   |
| Mirroring play/pause, clocks, logos, or a time-series chart                              | These encode conventions or data, not reading direction; mirroring makes them wrong                                              | Consult the icon set's RTL-mirroring metadata and mirror only direction-of-travel glyphs                                |
| Using `<bdo>` or `unicode-bidi: bidi-override` on user content                           | Overrides reverse characters, so displayed text no longer matches the underlying data                                            | Use `<bdi>` or `unicode-bidi: isolate` / `plaintext`                                                                    |
| Generating LRE/RLE/PDF/LRO/RLO in new markup                                             | Deprecated since Unicode 6.3, leak scope when unbalanced, and are excluded from isolate run sequences                            | Emit LRI/RLI/FSI/PDI, or markup                                                                                         |
| Testing RTL by reversing Latin text                                                      | Latin is bidi class `L`; reversal is not the same transformation the algorithm performs and hides every neutral and number bug   | Test with real Arabic and Hebrew strings containing embedded Latin, digits, URLs, and punctuation                       |
| Ignoring bidi controls in untrusted input                                                | Trojan Source (CVE-2021-42574) makes source, logs, filenames, or labels render differently from their bytes                      | Reject U+202A–U+202E and U+2066–U+2069 in code and identifiers; validate user-supplied `dir` against `ltr`/`rtl`/`auto` |

### Detecting and stripping bidi controls

```python
import unicodedata

DANGEROUS = {"LRE", "RLE", "PDF", "LRO", "RLO", "LRI", "RLI", "FSI", "PDI"}
RTL_STRONG = {"R", "AL", "AN"}

def strip_bidi_controls(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.bidirectional(ch) not in DANGEROUS)

def first_strong_direction(text: str) -> str:
    for ch in text:
        bidi_class = unicodedata.bidirectional(ch)
        if bidi_class == "L":
            return "ltr"
        if bidi_class in RTL_STRONG:
            return "rtl"
    return "ltr"
```

```php
$controls = ['LRE', 'RLE', 'PDF', 'LRO', 'RLO', 'LRI', 'RLI', 'FSI', 'PDI'];
$clean = '';
foreach (mb_str_split($text) as $char) {
    $code = IntlChar::ord($char);
    $name = IntlChar::getPropertyValueName(
        IntlChar::PROPERTY_BIDI_CLASS,
        IntlChar::charDirection($code)
    );
    if (!in_array($name, $controls, true)) {
        $clean .= $char;
    }
}
```

```java
String clean = text.codePoints()
    .filter(cp -> switch (Character.getDirectionality(cp)) {
        case Character.DIRECTIONALITY_LEFT_TO_RIGHT_EMBEDDING,
             Character.DIRECTIONALITY_RIGHT_TO_LEFT_EMBEDDING,
             Character.DIRECTIONALITY_POP_DIRECTIONAL_FORMAT,
             Character.DIRECTIONALITY_LEFT_TO_RIGHT_OVERRIDE,
             Character.DIRECTIONALITY_RIGHT_TO_LEFT_OVERRIDE,
             Character.DIRECTIONALITY_LEFT_TO_RIGHT_ISOLATE,
             Character.DIRECTIONALITY_RIGHT_TO_LEFT_ISOLATE,
             Character.DIRECTIONALITY_FIRST_STRONG_ISOLATE,
             Character.DIRECTIONALITY_POP_DIRECTIONAL_ISOLATE -> false;
        default -> true;
    })
    .collect(StringBuilder::new, StringBuilder::appendCodePoint, StringBuilder::append)
    .toString();

boolean needsBidi = Bidi.requiresBidi(text.toCharArray(), 0, text.length());
```

```go
import (
    "strings"
    "unicode"

    "golang.org/x/text/secure/bidirule"
)

func safe(s string) bool {
    return bidirule.ValidString(s)
}

func stripBidiControls(s string) string {
    return strings.Map(func(r rune) rune {
        if unicode.Is(unicode.Bidi_Control, r) {
            return -1
        }
        return r
    }, s)
}
```

```rust
use unicode_bidi::BidiInfo;
use unicode_bidi::Level;

let bidi_info = BidiInfo::new(text, None);
let paragraph = &bidi_info.paragraphs[0];
let line = paragraph.range.clone();
let visual = bidi_info.reorder_line(paragraph, line);

let base_is_rtl = BidiInfo::new(text, Some(Level::rtl())).levels[0].is_rtl();
```

Reordering text yourself is only correct at the final paint boundary, for terminal or canvas output with no bidi-aware
layout engine. `python-bidi`'s `get_display` and ICU's `ubidi_setPara` / `ubidi_writeReordered` exist for that case;
using them to produce a string that is then stored or compared is a defect.

## Checklist

1. Confirm `<html>` carries both `dir` and `lang`, and that `dir` is set to `ltr` or `rtl` explicitly rather than left to the UA default.
2. Grep the codebase for `margin-left`, `margin-right`, `padding-left`, `padding-right`, `border-left`, `border-right`,
   `left:`, `right:`, `text-align: left`, `text-align: right`, `float: left`, and `float: right`, and replace each with its
   logical equivalent.
3. Replace every absolute-positioned element that anchors on `left` or `right` with `inset-inline-start` / `inset-inline-end`.
4. Verify that every directional icon is either auto-mirrored through the platform's metadata (`android:autoMirrored`,
`flipsForRightToLeftLayoutDirection`, the icon set's RTL flag) or explicitly mirrored under `[dir="rtl"]`, and that no
non-directional icon (play, clock, logo, chart) is mirrored.
5. Locate every animation and transition that uses `translateX`, `left`, `right`, or `background-position`, and confirm
it is direction-aware or animates a logical property.
6. Confirm that each phone number, URL, email address, ID, path, IP address, and code sample is wrapped in `<bdi
dir="ltr">` or an element with `unicode-bidi: isolate` and `direction: ltr`.
7. Confirm that every untrusted display name, comment, or user-generated string is wrapped in `<bdi>` or an element with
`dir="auto"` / `unicode-bidi: plaintext`, so its base direction comes from its own first strong character.
8. Verify that no stored or transmitted string has been visually reordered, and that no data was "fixed" by reversing
characters or inserting spaces inside a token.
9. Search the source tree, filenames, and log formatters for U+202A–U+202E and U+2066–U+2069, and add a validation gate
that rejects them in identifiers, code, and untrusted input.
10. Validate every user-supplied `dir` value against exactly `ltr`, `rtl`, and `auto` before it reaches the DOM.
11. Confirm that telephone inputs, `<code>` blocks, and `<pre>` regions keep an LTR base direction, and that `dirname`
is set on inputs whose directionality must be submitted with the form.
12. Render each component at both `dir="ltr"` and `dir="rtl"` in a snapshot or visual-regression test, using real Arabic
and Hebrew strings that embed Latin words, digits, `+`, `@`, parentheses, URLs, and trailing punctuation.
13. Force line wrapping in a narrow container for every mixed-direction string to expose L1 trailing-whitespace and
neutral-resolution defects at line boundaries.
14. Assert the computed direction in tests — `getComputedStyle(el).direction` in the browser, `I18nManager.isRTL` on
React Native, `Directionality.of(context)` in Flutter — rather than asserting on rendered pixels alone.
15. Run an algorithm-level conformance check against `BidiTest.txt` and `BidiCharacterTest.txt` if the project ships its own bidi or text-shaping code.
16. Review the rendered RTL build with a native speaker or a real RTL locale, and record any icon or punctuation placement that a native reader flags as wrong.

## References

- [Unicode Standard Annex #9: Unicode Bidirectional Algorithm](https://www.unicode.org/reports/tr9/)
- [BidiTest.txt — conformance test data for UAX #9](https://www.unicode.org/Public/UCD/latest/ucd/BidiTest.txt)
- [BidiCharacterTest.txt — per-character bidi test data](https://www.unicode.org/Public/UCD/latest/ucd/BidiCharacterTest.txt)
- [BidiMirroring.txt — the Bidi_Mirrored property](https://www.unicode.org/Public/UCD/latest/ucd/BidiMirroring.txt)
- [HTML Standard — the `dir` attribute](https://html.spec.whatwg.org/multipage/dom.html#the-dir-attribute)
- [HTML Standard — rendering section and UA stylesheet](https://html.spec.whatwg.org/multipage/rendering.html)
- [CSS Writing Modes Level 4 — `direction`, `unicode-bidi`, `writing-mode`](https://www.w3.org/TR/css-writing-modes-4/)
- [CSS Logical Properties and Values Level 1](https://www.w3.org/TR/css-logical-1/)
- [CSS Text Module Level 3 — `text-align: start` / `end`](https://www.w3.org/TR/css-text-3/)
- [W3C i18n: Inline markup and bidirectional text in HTML](https://www.w3.org/International/articles/inline-bidi-markup/)
- [W3C i18n: Unicode controls vs. markup for bidi support](https://www.w3.org/International/questions/qa-bidi-controls)
- [W3C i18n: Structural markup and right-to-left text in HTML](https://www.w3.org/International/questions/qa-html-dir)
- [Trojan Source — invisible vulnerabilities (CVE-2021-42574)](https://trojansource.codes/)
- [Go: `golang.org/x/text/secure/bidirule`](https://pkg.go.dev/golang.org/x/text/secure/bidirule)
- [Go: `golang.org/x/text/unicode/bidi`](https://pkg.go.dev/golang.org/x/text/unicode/bidi)
- [Java: `java.text.Bidi`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/text/Bidi.html)
- [PHP: `IntlChar`](https://www.php.net/manual/en/class.intlchar.php)
- [Rust: `unicode-bidi` crate](https://docs.rs/unicode-bidi/)
- [ICU: `ubidi` bidirectional text API](https://unicode-org.github.io/icu-docs/apidoc/released/icu4c/ubidi_8h.html)
- [React Native: `I18nManager`](https://reactnative.dev/docs/i18nmanager)
- [Flutter: `Directionality`](https://api.flutter.dev/flutter/widgets/Directionality-class.html)
- [SwiftUI: `layoutDirection` environment value](https://developer.apple.com/documentation/swiftui/environmentvalues/layoutdirection)
- [Android: support different languages and cultures](https://developer.android.com/training/basics/supporting-devices/languages)
- [Tailwind CSS: margin and logical properties](https://tailwindcss.com/docs/margin)
- [MDN: `dir` global attribute](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/dir)
- [MDN: `unicode-bidi`](https://developer.mozilla.org/en-US/docs/Web/CSS/unicode-bidi)
- [MDN: `<bdi>` element](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/bdi)

See also [intl-number-and-currency.md](intl-number-and-currency.md) for numbering systems and digit shaping, [intl-text-
processing.md](intl-text-processing.md) for normalization and grapheme handling, [intl-content-and-assets.md](intl-
content-and-assets.md) for mirrored image assets, and [intl-testing-and-qa.md](intl-testing-and-qa.md) for the broader
locale test matrix.

