# HTML and Markup Standards

This domain covers the document skeleton, element semantics, accessibility tree exposure, form contracts, and resource-loading hints in HTML. Getting it wrong is not cosmetic: a `div` where a `button` belongs removes keyboard operability, a missing `lang` breaks screen-reader pronunciation and hyphenation, absent `width`/`height` on images produces layout shift that fails Core Web Vitals, and a malformed nesting pattern can cause the HTML parser to silently reparent nodes so the DOM you shipped is not the DOM you wrote.

## Contents

- [When This Applies](#when-this-applies)
- [Core Concepts](#core-concepts)
  - [Document skeleton and the head contract](#document-skeleton-and-the-head-contract)
  - [Landmarks, outline, and heading hierarchy](#landmarks-outline-and-heading-hierarchy)
  - [Buttons vs links and element semantics](#buttons-vs-links-and-element-semantics)
  - [Forms](#forms)
  - [Text direction, language, and inline foreign content](#text-direction-language-and-inline-foreign-content)
  - [Tables, images, and resource hints](#tables-images-and-resource-hints)
  - [Structured data, progressive enhancement, and parsing](#structured-data-progressive-enhancement-and-parsing)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- Auditing or normalizing templates, layouts, partials, or component markup (`.html`, `.erb`, `.blade.php`, `.twig`, `.hbs`, `.jsx`/`.tsx` output, `.vue`/`.svelte` templates).
- Reviewing a page for landmark structure, heading order, or accessible-name computation.
- Any change to forms: field naming, validation, autocomplete tokens, error association.
- Any change to `<head>`: charset, viewport, canonical, Open Graph, structured data.
- Adding images, iframes, or third-party embeds that affect LCP, CLS, or INP.
- Migrating off deprecated presentational markup (`<center>`, `<font>`, `align`, `cellpadding`, `bgcolor`).
- Establishing component/templating conventions for a project that currently has none.

## Core Concepts

### Document skeleton and the head contract

The first 1024 bytes of the response should contain `<meta charset>`; if the parser has to restart character decoding after that point it re-parses the document. `charset` must precede any element that consumes text, including `<title>`.

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Invoice #4021 — Acme Billing</title>
    <meta
      name="description"
      content="Line items, tax breakdown, and payment status for invoice 4021."
    />
    <link rel="canonical" href="https://billing.example.com/invoices/4021" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="Invoice #4021" />
    <meta
      property="og:image"
      content="https://billing.example.com/og/4021.png"
    />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
  </head>
  <body>
    …
  </body>
</html>
```

`<meta charset>` is a _character encoding declaration_, not a `http-equiv` alias — `http-equiv="Content-Type"` is obsolete and is ignored for encoding sniffing in HTML5. Send `Content-Type: text/html; charset=utf-8` from the server too; the meta tag is the fallback for `file://` and misconfigured origins, not a substitute.

`og:image` dimensions matter because crawlers reserve the card area before the image loads; declaring them prevents reflow in social previews. `og:title` is not derived from `<title>` — set it explicitly when the page title carries a suffix like `— Acme Billing` that reads badly in a card.

For a page whose content is duplicated under query parameters, `canonical` must be absolute and self-consistent; a canonical pointing at a URL that itself canonicalizes elsewhere produces a canonical chain that crawlers discard.

### Landmarks, outline, and heading hierarchy

Landmarks are the coarse navigation surface of the accessibility tree. Each landmark role should appear once per page except `complementary` and `form`, which may repeat when they have accessible names.

| Element     | Implicit role   | Rule                                                                                                       |
| ----------- | --------------- | ---------------------------------------------------------------------------------------------------------- |
| `<header>`  | `banner`        | Only when a direct child of `<body>`. Nested inside `<article>` it is generic — no landmark.               |
| `<nav>`     | `navigation`    | Give it `aria-label` when more than one nav exists ("Primary", "Breadcrumb").                              |
| `<main>`    | `main`          | Exactly one, visible, not hidden. Skipping it breaks "skip to content".                                    |
| `<article>` | `article`       | Self-contained and independently distributable (post, comment, product card with its own heading).         |
| `<section>` | `region`        | **Only** becomes a landmark when it has an accessible name. An unnamed `<section>` is a generic container. |
| `<aside>`   | `complementary` | Tangential to the main content; nested inside `<main>` it stays a landmark.                                |
| `<footer>`  | `contentinfo`   | Only when a direct child of `<body>`.                                                                      |

"Not a section": if you cannot write a heading for it that would make sense in a document outline, it is a `<div>`. A `<section>` wrapping purely for CSS grid placement is a `div` with a class. `<article>` is not "a card" — a card with no heading and no independent meaning is a `<li>` or `<div>`.

Heading levels must not skip when descending (`<h2>` → `<h4>`), and a heading must not be chosen for its font size. Level skipping is a WCAG 1.3.1 failure because the heading level is the only programmatic statement of nesting for screen-reader users who navigate by heading. Do not use `<hgroup>` to hide a subtitle; it removes the secondary heading from the outline in current implementations.

### Buttons vs links and element semantics

The decision rule is behavioral, not visual:

- Navigates to a URL (changes the address, is bookmarkable, is openable in a new tab) → `<a href="…">`.
- Performs an action in place (submit, toggle, open a dialog, delete) → `<button>`.
- An `<a>` without `href` is not focusable, is not a link, and is a placeholder — remove it or add the `href`.
- A `<div onclick>` receives no keyboard focus, no `Enter`/`Space` activation, no `:focus-visible`, and no role. `role="button"` plus `tabindex="0"` plus keydown handlers is a reimplementation of `<button>` that will drift.

`<button>` defaults to `type="submit"` inside a form. A button that is not meant to submit must carry `type="button"`, otherwise it submits the enclosing form and triggers navigation.

```html
<a href="/invoices/4021">View invoice</a>

<form action="/invoices/4021/void" method="post">
  <input type="hidden" name="_csrf" value="…" />
  <button type="submit">Void invoice</button>
  <button type="button" data-action="print">Print</button>
</form>
```

**ARIA first rule.** The first rule of ARIA is: don't use ARIA if a native HTML element or attribute already conveys the semantics. `<button>` over `role="button"`, `<nav>` over `role="navigation"`, `<input type="checkbox">` over `role="checkbox"` with `aria-checked` and manual state. `role` does not add behavior: `role="button"` gives you no keyboard activation, `role="checkbox"` gives you no toggle, `role="dialog"` gives you no focus trap. Bad ARIA is worse than no ARIA because it overwrites correct native semantics — `role="presentation"` on a focusable element, or `aria-hidden="true"` on a container holding a focusable child, creates an element that is focusable but absent from the accessibility tree.

### Forms

Every control needs a programmatically associated label. Three valid patterns, in order of preference:

```html
<label for="email">Email address</label>
<input id="email" name="email" type="email" autocomplete="email" required />

<label>
  Card number
  <input name="card" type="text" inputmode="numeric" autocomplete="cc-number" />
</label>

<fieldset>
  <legend>Shipping speed</legend>
  <label
    ><input type="radio" name="speed" value="std" checked /> Standard</label
  >
  <label><input type="radio" name="speed" value="exp" /> Expedited</label>
</fieldset>
```

`placeholder` is not a label: it disappears on input, has poor contrast by default, and is not reliably announced. `aria-label` is a fallback for controls with no visible text (icon-only buttons), not a replacement for a visible label.

`<fieldset>`/`<legend>` groups related controls and is required for radio groups — it is what makes the group's purpose announced with each option. A `<fieldset>` inside a `<table>` cell is legal but resets implicit form-associated behavior in some legacy engines; keep fieldsets at the form's structural level.

`autocomplete` tokens come from the HTML Living Standard's fixed vocabulary. Guessing a token silently disables autofill. The tokens are lowercase, hyphenated, and come in two families: field tokens (`email`, `tel`, `name`, `given-name`, `family-name`, `organization`, `street-address`, `address-line1`, `address-level2`, `postal-code`, `country`, `cc-number`, `cc-exp`, `cc-csc`, `username`, `current-password`, `new-password`, `one-time-code`) and the `section-*`/`shipping`/`billing` prefixes that disambiguate repeated groups.

`input type` selects the virtual keyboard, the browser's native validation, and the autofill heuristics. `type="text"` with `inputmode="numeric"` is not equivalent to `type="number"` — `number` rejects non-numeric input entirely and spins on scroll; use `inputmode` when you want a numeric keypad but free-form entry.

Validation attributes: `required`, `minlength`/`maxlength` (characters), `min`/`max`/`step` (numeric and date values), `pattern` (anchored full-match against the value in the `v` flag semantics), `multiple` (email/file), `accept` (file types). `novalidate` on the form or `formnovalidate` on a submit button disables native validation; server-side validation remains mandatory because all of it is client-side and bypassable.

Errors must be associated, not merely colored: `aria-describedby` pointing at the message element, `aria-invalid="true"` on the control, and a live region for messages that appear after submission.

```html
<input
  id="zip"
  name="zip"
  type="text"
  inputmode="numeric"
  autocomplete="postal-code"
  aria-describedby="zip-error"
  aria-invalid="true"
  pattern="[0-9]{5}"
/>
<p id="zip-error">Enter a 5-digit ZIP code.</p>
```

### Text direction, language, and inline foreign content

`lang` on `<html>` drives screen-reader voice selection, hyphenation, quote glyphs, and spellcheck. A page in Portuguese must not ship `lang="en"` because the framework's base template hardcoded it.

Inline foreign-language spans need their own `lang` so the screen reader switches voice for that run only:

```html
<p lang="en">
  The French term <span lang="fr">raison d'être</span> appears in the contract.
</p>
```

`dir` is `ltr`, `rtl`, or `auto`. `dir="auto"` sets direction from the first strong directional character of the element's content — correct for user-generated text of unknown script (names, comments), wrong for mixed content where the first character is a number or punctuation. For a page whose base direction is RTL, set `dir="rtl"` on `<html>` alongside `lang`; do not flip it in CSS. For a numeric run embedded in RTL text, wrap it in `<bdi>` (or `<bdo dir="ltr">`) so the number is not reordered by the bidirectional algorithm. See [intl-bidi.md](intl-bidi.md) for the full isolation and formatting rules.

### Tables, images, and resource hints

Tables are for data with two or more dimensions. Layout tables are not permitted.

```html
<table>
  <caption>
    Quarterly revenue by region (USD thousands)
  </caption>
  <thead>
    <tr>
      <th scope="col">Region</th>
      <th scope="col">Q1</th>
      <th scope="col">Q2</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">EMEA</th>
      <td>412</td>
      <td>438</td>
    </tr>
  </tbody>
</table>
```

`<caption>` is the table's accessible name and must be the first child of `<table>`. `scope="col"`/`scope="row"` makes each data cell resolvable to its headers; for irregular tables with merged headers use `headers` with cell `id`s. `role="presentation"` on a table is only for genuine layout fallbacks and strips all table semantics including header association.

Images:

```html
<img
  src="/hero.avif"
  alt="Team reviewing the Q2 roadmap on a whiteboard"
  width="1600"
  height="900"
  fetchpriority="high"
  decoding="async"
/>

<img src="/divider.svg" alt="" width="1200" height="8" />

<button type="button">
  <img src="/icons/close.svg" alt="Close dialog" width="16" height="16" />
</button>
```

Alt text policy, by role:

| Image role               | `alt` value                                                                        | Example                                                                  |
| ------------------------ | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Decorative               | `alt=""` — empty, present, not omitted                                             | Divider, background flourish, icon paired with visible text              |
| Informative              | The information it conveys, not a description of the file                          | `alt="Revenue rose 12% in Q2"` for a chart                               |
| Functional               | The action or destination, not the icon                                            | `alt="Close dialog"` on a close button; `alt="Acme home"` on a logo link |
| Complex (chart, diagram) | Short `alt` plus a full text alternative nearby, referenced via `aria-describedby` | `alt="Q2 revenue by region"` + adjacent table                            |

Omitting `alt` entirely is a defect distinct from `alt=""`: assistive tech announces the filename when `alt` is absent. A functional image inside a link or button that also has visible text should use `alt=""` so the accessible name is not duplicated.

`width` and `height` attributes are the intrinsic dimensions, not the rendered size; CSS controls rendering. Their presence lets the browser compute the aspect ratio and reserve space, which is the difference between a passing and failing CLS score. For responsive images, `srcset`/`sizes` with `width` descriptors plus the `sizes` attribute selects the right candidate before layout.

Loading hints:

- `loading="lazy"` defers an image until it approaches the viewport. Never apply it to the LCP image — it delays the largest paint. Never apply it to anything above the fold.
- `fetchpriority="high"` on the LCP image tells the preload scanner to raise its priority; `fetchpriority="low"` on offscreen carousel slides prevents them from competing with the hero.
- `decoding="async"` keeps image decode off the main thread's critical path; `decoding="sync"` is reserved for images that must be painted in the same frame.
- `<link rel="preconnect" href="https://cdn.example.com" crossorigin>` for origins used early; `<link rel="preload" as="font" type="font/woff2" crossorigin>` for the critical font — `crossorigin` is mandatory for fonts even same-origin, because font fetches are always CORS-mode.

### Structured data, progressive enhancement, and parsing

Structured data uses JSON-LD in a `<script type="application/ld+json">`, keyed to schema.org vocabulary with a `@context` and `@type`. The values must match what is visible on the page; marking up content that is not rendered is a spam signal.

```html
<script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Stainless Steel Kettle 1.7L",
    "sku": "KT-17-SS",
    "offers": {
      "@type": "Offer",
      "price": "49.00",
      "priceCurrency": "USD",
      "availability": "https://schema.org/InStock"
    }
  }
</script>
```

Progressive enhancement: core content and navigation must be present in the server-rendered HTML. A client-rendered shell that fills in via JS means the page is empty for crawlers that do not execute JS, for users with a failed script request, and for the first paint. Links must be real anchors with `href` so they work before hydration; enhance behavior (interception, partial swap) on top, do not replace the anchor. Forms must have an `action` and `method` that work without JS.

Parsing and nesting rules that bite in production:

- `<p>` cannot contain block-level elements. `<p><div>…</div></p>` closes the `<p>` before the `<div>`, producing an empty paragraph and a sibling div.
- `<a>` cannot contain `<a>`, `<button>` cannot contain `<button>`, `<li>` must be a child of `<ul>`/`<ol>`/`<menu>`.
- The parser auto-inserts `<tbody>` in a `<table>` that has `<tr>` children, so a CSS selector like `table > tr` never matches.
- Duplicate `id` values are invalid and break `for`/`aria-describedby`/`aria-labelledby` resolution, which take the first match in document order.
- `<template>` content is inert: images inside do not load, scripts do not run, and the content is not in the accessibility tree until cloned into the document.
- Void elements (`img`, `br`, `input`, `hr`, `meta`, `link`, `source`, `track`, `area`, `col`, `embed`, `wbr`) take no closing tag; a stray `</img>` is ignored, but self-closing syntax on non-void elements (`<div/>`) is treated as an open tag.

Deprecated and presentational markup to migrate: `<center>`, `<font>`, `<big>`, `<strike>`, `<tt>`, `<marquee>`, `<blink>`, `<frame>`/`<frameset>`/`<noframes>`, and the presentational attributes `align`, `valign`, `bgcolor`, `border` (on `<img>`/`<table>`), `cellpadding`, `cellspacing`, `width`/`height` on `<table>` cells for layout, and `summary` on `<table>` (replaced by `<caption>` + `<details>`). `<b>` and `<i>` remain valid but are stylistic; `<strong>` and `<em>` carry the semantic stress and should be preferred in content.

Templating component conventions: a component owns one root element, so callers can pass attributes and classes through without the framework guessing. Its markup must not depend on an ancestor's tag for validity — a component that emits `<td>` is only legal inside a `<tr>` and must be named and documented as such. Prefer composition over a `variant` prop that switches the root tag between `button` and `a`; if the root tag must vary, the semantic distinction (action vs navigation) belongs to two components.

## Common Mistakes

| Mistake                                                                                         | Why It Breaks                                                                                        | Correct Approach                                                                               |
| ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `<div onclick>` or `<span role="button">` for actions                                           | No keyboard focus, no `Enter`/`Space` activation, no role, no disabled state                         | Use `<button type="button">`; add `type` so it does not submit                                 |
| `<a href="#">` or `<a>` with no `href` used as a button                                         | Not navigable, not bookmarkable, not focusable without `href`, announced as a link that does nothing | `<button>` for actions; real URL in `href` for navigation                                      |
| Missing or omitted `alt` on informative images                                                  | Screen readers announce the file path; WCAG 1.1.1 failure                                            | `alt=""` for decorative, descriptive text for informative, action text for functional          |
| `role="presentation"` on a table or `aria-hidden="true"` on a container with focusable children | Strips semantics from real content; creates focusable elements absent from the accessibility tree    | Remove the role; if content is truly hidden, use `hidden`/`display:none` and remove focusables |
| Skipping heading levels (`h2` → `h4`) or styling a `div` as a heading                           | Outline breaks for heading-based navigation; WCAG 1.3.1 failure                                      | Keep sequential levels; style headings with CSS, never change the level for size               |
| `<section>` used as a generic wrapper without a heading                                         | An unnamed `<section>` is not a landmark and adds no structure, only noise in the tree               | `<div>` unless it has an accessible name and would appear in an outline                        |
| Missing `width`/`height` on `<img>`                                                             | Browser cannot reserve space; cumulative layout shift on every image                                 | Set intrinsic `width` and `height` attributes; size visually with CSS                          |
| `loading="lazy"` on the LCP/hero image                                                          | Defers the largest paint, worsening LCP directly                                                     | Omit lazy above the fold; use `fetchpriority="high"` on the LCP image                          |
| `charset` declared late or via `http-equiv="Content-Type"`                                      | Parser restarts decoding after 1024 bytes or never sniffs the encoding; mojibake                     | `<meta charset="utf-8">` as the first element in `<head>`, plus a server `Content-Type` header |
| `placeholder` used as the only label                                                            | Disappears on input, low contrast, not reliably announced                                            | Visible `<label for>`; keep placeholder as an example only                                     |
| Guessed `autocomplete` token (e.g. `autocomplete="zip"`)                                        | Invalid token silently disables autofill for that field                                              | Use the spec vocabulary: `postal-code`, `cc-number`, `one-time-code`, etc.                     |
| Native validation treated as the only validation                                                | Entirely client-side and bypassable; `pattern` is anchored differently than expected                 | Keep server-side validation; treat attributes as UX hints                                      |
| Layout `<table>` with `cellpadding`/`bgcolor`/`align`                                           | No semantics, wrong roles for AT, inaccessible reading order                                         | CSS grid/flex for layout; reserve `<table>` for data with `<caption>` and `scope`              |
| `lang` inherited from a base template that hardcodes `en`                                       | Wrong screen-reader voice, hyphenation, and spellcheck for the actual language                       | Set `lang` per page from the request locale; add inline `lang` on foreign-language runs        |
| Missing `dir` on RTL content or flipping direction in CSS only                                  | Bidirectional algorithm reorders numbers and punctuation; base direction lost to AT                  | `dir="rtl"` on `<html>`; `<bdi>` or `bdo` for embedded opposite-direction runs                 |
| JSON-LD that describes content not visible on the page                                          | Mismatch between markup and rendered content is treated as structured-data spam                      | Mark up only rendered values; keep prices, availability, and names in sync                     |

## Checklist

1. Confirm `<meta charset="utf-8">` is the first element inside `<head>` and that the response also carries a `Content-Type: text/html; charset=utf-8` header.
2. Verify `<html>` has a `lang` matching the page content, and that every inline foreign-language run has its own `lang`.
3. Verify `dir` is set on `<html>` for RTL locales, and that every embedded opposite-direction run (numbers, Latin names in RTL text) is wrapped in `<bdi>` or `<bdo>`.
4. Walk the landmark structure: exactly one `<main>`, `<header>`/`<footer>` as direct `<body>` children, every `<nav>` and repeated landmark given a distinct `aria-label`.
5. Walk the heading outline top to bottom and confirm no level is skipped when descending and every heading has a non-empty text alternative.
6. Locate every interactive element and confirm its tag matches its behavior: `<a href>` for navigation, `<button>` for actions, `type="button"` on non-submitting buttons.
7. Grep for `onclick=`, `role="button"`, `role="link"`, `role="checkbox"`, `role="dialog"`, and `tabindex="0"`; for each hit, verify no native element could replace it.
8. Grep for `aria-hidden="true"` and `role="presentation"`; confirm no hidden or presentational subtree contains a focusable descendant.
9. For every form control, confirm a programmatically associated label (`for`/`id` or wrapping `<label>`), a valid `autocomplete` token where a field token exists, and `type`/`inputmode` appropriate to the data.
10. Confirm every radio group and logically related control set is wrapped in `<fieldset>` with a `<legend>`.
11. Confirm validation errors set `aria-invalid="true"` and link to their message via `aria-describedby`, and that the same validation exists server-side.
12. Audit every `<img>`: non-omitted `alt` matching its role, intrinsic `width` and `height`, `loading="lazy"` only below the fold, `fetchpriority="high"` on the LCP image.
13. Confirm every `<table>` is tabular data with a `<caption>` as its first child and `scope` (or `headers`/`id` for irregular headers) on header cells.
14. Validate that all `id` values are unique and that every `for`, `aria-describedby`, `aria-labelledby`, and `headers` reference resolves to exactly one element.
15. Check nesting against the content model: no block content inside `<p>`, no nested `<a>` or `<button>`, no `<td>` outside a table section, no `<li>` outside a list.
16. Disable JavaScript and confirm core content, navigation links, and form submission still work from the server-rendered HTML.
17. Verify `<head>` metadata completeness: `<title>`, `<meta name="description">`, absolute `<link rel="canonical">`, and Open Graph tags with `og:image:width`/`og:image:height`.
18. Validate any JSON-LD block parses, uses the schema.org vocabulary, and matches the visible page content.
19. Grep for deprecated elements and presentational attributes (`<center>`, `<font>`, `align=`, `bgcolor=`, `cellpadding=`, `cellspacing=`, `http-equiv="Content-Type"`) and replace them with CSS.
20. Run the output through the Nu Html Checker and an axe-core or Lighthouse accessibility pass, and confirm zero new violations against the recorded baseline.

## References

- HTML Living Standard (WHATWG), full specification — https://html.spec.whatwg.org/multipage/
- HTML Living Standard, the `autocomplete` attribute and its token vocabulary — https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#autofill
- HTML Living Standard, content models and parsing (tree construction, auto-inserted elements) — https://html.spec.whatwg.org/multipage/parsing.html
- WAI-ARIA Authoring Practices Guide, landmark regions and patterns — https://www.w3.org/WAI/ARIA/apg/practices/landmark-regions/
- WAI-ARIA 1.2 specification, including the first rule of ARIA use — https://www.w3.org/TR/wai-aria-1.2/
- WCAG 2.2, Understanding 1.3.1 Info and Relationships — https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html
- WCAG 2.2, Understanding 1.1.1 Non-text Content (alt text decision tree) — https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html
- WAI Images Tutorial, decorative, informative, and functional images — https://www.w3.org/WAI/tutorials/images/
- W3C Internationalization, `lang` and `dir` in HTML — https://www.w3.org/International/questions/qa-html-language-declarations
- W3C Internationalization, inline markup and bidirectional text (`bdi`, `bdo`) — https://www.w3.org/International/articles/inline-bidi-markup/
- web.dev, Cumulative Layout Shift and reserving space for images — https://web.dev/articles/cls
- web.dev, `fetchpriority` and optimizing LCP images — https://web.dev/articles/optimize-lcp
- MDN, `loading` attribute on `<img>` and `<iframe>` — https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#loading
- MDN, obsolete and deprecated HTML elements — https://developer.mozilla.org/en-US/docs/Web/HTML/Element#obsolete_and_deprecated_elements
- schema.org vocabulary, Product and Offer types — https://schema.org/Product
- Nu Html Checker (validator.w3.org/nu) — https://validator.w3.org/nu/
