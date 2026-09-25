# CSS and Styling Standards

Covers the decisions a styling audit has to settle: which styling model owns which surface, how design tokens are named and consumed, how the cascade is ordered and scoped, and how theming, internationalization, and layout stability are handled. CSS failures are rarely syntax errors — they are specificity wars that end in `!important`, hardcoded `#3b82f6` values that survive into dark mode, `100vh` heroes that jump when mobile browser chrome collapses, and dead rules shipped on the critical path. No compiler catches any of it, so the audit reconstructs the cascade by reading it.

## Contents

- [When This Applies](#when-this-applies)
- [Choosing a Styling Model](#choosing-a-styling-model)
  - [BEM, or an equivalent naming contract, for component CSS](#bem-or-an-equivalent-naming-contract-for-component-css)
  - [Utility-first still needs a scale discipline](#utility-first-still-needs-a-scale-discipline)
  - [Layout is grid and flexbox](#layout-is-grid-and-flexbox)
- [Design Tokens and the Scale Constraint](#design-tokens-and-the-scale-constraint)
  - [Three token tiers, and only one is referenced by components](#three-token-tiers-and-only-one-is-referenced-by-components)
  - [The scale constraint](#the-scale-constraint)
  - [Fluid type and space with `clamp()`](#fluid-type-and-space-with-clamp)
- [Specificity, Layers, and Scoping](#specificity-layers-and-scoping)
  - [Order the cascade with `@layer`, do not fight it](#order-the-cascade-with-layer-do-not-fight-it)
  - [Specificity budget](#specificity-budget)
  - [Scoping without global leakage](#scoping-without-global-leakage)
  - [`!important` has two legitimate uses](#important-has-two-legitimate-uses)
- [Theming, Dark Mode, and Internationalization](#theming-dark-mode-and-internationalization)
  - [Runtime theming with custom properties](#runtime-theming-with-custom-properties)
  - [Dark mode: media query as default, attribute as override](#dark-mode-media-query-as-default-attribute-as-override)
  - [Logical properties for internationalization](#logical-properties-for-internationalization)
  - [Print styles](#print-styles)
- [Layout Stability, Responsiveness, and Delivery](#layout-stability-responsiveness-and-delivery)
  - [Preventing layout shift](#preventing-layout-shift)
  - [Container queries for component-level responsiveness](#container-queries-for-component-level-responsiveness)
  - [Motion](#motion)
  - [Accessibility-adjacent CSS](#accessibility-adjacent-css)
  - [Keep the critical path small](#keep-the-critical-path-small)
  - [Formatting and linting](#formatting-and-linting)
- [Common Mistakes](#common-mistakes)
- [Checklist](#checklist)
- [References](#references)

## When This Applies

- The repository contains `.css`, `.scss`, `.sass`, `.less`, `.styl`, `.pcss`, `.module.css`, or CSS-in-JS files, or markup carrying `<style>` blocks or `style=""` attributes.
- Two or more styling models coexist — utility classes, hand-written component CSS, CSS Modules, CSS-in-JS — with no rule about which owns what.
- Raw color, spacing, radius, or shadow literals appear instead of `var(--token)` references.
- `!important` appears outside a documented utility or print context.
- Competing dark-mode strategies coexist: `prefers-color-scheme` in one file and `.dark`/`data-theme` in another, with no single source of truth.
- Physical properties (`margin-left`, `padding-top`, `width`) are used where `margin-inline-start`, `padding-block`, or `inline-size` would survive a writing-mode or direction switch.
- Stylelint is absent, or Prettier and Stylelint both claim formatting authority.
- Layout shift is observable: images without `width`/`height` or `aspect-ratio`, fonts without metric-adjusted fallbacks, `content-visibility` without `contain-intrinsic-size`.
- Layout uses `float` or `display: table`, or components restyle themselves from viewport media queries when reused at several widths.

## Choosing a Styling Model

Pick one model per surface and write the rule down. Mixed models are not inherently wrong, but mixed models with no ownership boundary produce two files that both think they style the same button.

| Model                            | Selector surface                       | Scoping                       | Where it breaks down                                                                                |
| -------------------------------- | -------------------------------------- | ----------------------------- | --------------------------------------------------------------------------------------------------- |
| Utility-first (Tailwind, UnoCSS) | Classes in markup, each single-purpose | None needed                   | Variants needing pseudo-elements or complex descendant logic; markup unreadable without a formatter |
| Component CSS + BEM              | One class per block/element            | Naming discipline only        | One descendant selector reintroduces specificity; depends on the rule being enforced                |
| CSS Modules                      | Scoped class names                     | Build-time hashing            | `:global` escapes are invisible to review                                                           |
| CSS-in-JS                        | Generated classes                      | Runtime or build-time hashing | Runtime cost and SSR hydration mismatch; build-time variants need a compiler step                   |

### BEM, or an equivalent naming contract, for component CSS

The value of BEM is not aesthetics — it is that every selector stays a single class, which keeps specificity flat and makes `@layer` and `:where()` work: `.card__title--muted`, `.card--featured`. Sass enforces the shape without string concatenation, so the compiled selector is still one class:

```scss
.card {
  &__title {
    &--muted {
      color: var(--color-text-muted);
    }
  }
  &--featured {
    border-color: var(--color-accent);
  }
}
```

Never combine BEM with descendant selectors (`.card .card__title`) — that defeats the point. One block maps to one file named for the block.

### Utility-first still needs a scale discipline

Tailwind v4 moved configuration into CSS: `@theme` generates both the utility classes and the custom properties, and custom CSS consumes the same tokens with `var()` — including the line-height companion a `--text-*` token generates (`--text-2xl--line-height`). Use `--*: initial` to wipe a namespace's defaults, and treat that as destructive.

```css
@theme {
  --spacing: 4px;
  --color-avocado-500: oklch(0.84 0.18 117.33);
}
```

### Layout is grid and flexbox

`float` and `display: table` are layout mechanisms only for email clients and legacy browsers; in application CSS they produce cleared, wrapped, non-reflowing boxes. Flexbox for one dimension, grid for two, with `gap` instead of margin arithmetic:

```css
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(18rem, 100%), 1fr));
  gap: var(--space-4);
}
```

`minmax(min(18rem, 100%), 1fr)` prevents overflow at container widths below `18rem`; a bare `minmax(18rem, 1fr)` does not.

## Design Tokens and the Scale Constraint

### Three token tiers, and only one is referenced by components

| Tier      | Names what                        | Example                             | Who references it      |
| --------- | --------------------------------- | ----------------------------------- | ---------------------- |
| Primitive | A raw value in the palette        | `--blue-600: oklch(0.55 0.2 258)`   | Semantic tokens only   |
| Semantic  | A role in the interface           | `--color-surface`, `--color-danger` | Components             |
| Component | A decision local to one component | `--button-padding-inline`           | That component's rules |

Components that reference primitives directly cannot be rethemed, because a palette change is not a role change. Generate the scale from a single map so it exists in one place — `$radius: ("sm": 4px, "md": 8px, "lg": 12px)` looped with `@each $name, $value in $radius` into `--radius-#{$name}`.

### The scale constraint

If a spacing, radius, or type scale is configured, every value must come from it. Arbitrary bracket values bypass the scale, drift a few pixels per author, and cannot be rethemed.

| Wrong                                           | Why it breaks                                             | Correct                           |
| ----------------------------------------------- | --------------------------------------------------------- | --------------------------------- |
| `padding: 13px`                                 | Off-scale; invisible to a spacing refactor                | `padding: var(--space-3)`         |
| `class="p-[13px]"`                              | Escapes the theme; not regenerated if `--spacing` changes | `class="p-3"`                     |
| `background: #3b82f6`                           | Ignores dark mode and the semantic layer                  | `background: var(--color-accent)` |
| `border-radius: 6px` here, `8px` there          | Two radii for one role                                    | `var(--radius-md)`                |
| `box-shadow: 0 1px 3px rgb(0 0 0 / 0.1)` inline | Elevation is not tokenized, so it cannot be themed        | `var(--shadow-sm)`                |

An arbitrary value is acceptable only where the design specifies a measurement the scale cannot express — a 1px hairline, a grid aligned to a vendor's fixed asset — and it belongs in a token, not in the utility.

### Fluid type and space with `clamp()`

Keep the minimum and maximum in `rem` so the value still responds to user font-size settings, and put viewport units only in the middle term: `--step-0: clamp(1rem, 0.95rem + 0.25vw, 1.125rem)`. A `clamp(12px, ...)` floor ignores zoom and fails a text-resize check.

## Specificity, Layers, and Scoping

### Order the cascade with `@layer`, do not fight it

Declare the order once, at the top of the entry stylesheet. Layer order is fixed by first appearance of the name, so a later `@layer` block cannot reorder anything.

```css
@layer reset, tokens, base, layout, components, utilities;
```

| Declaration                   | Priority                                         |
| ----------------------------- | ------------------------------------------------ |
| Unlayered normal declarations | Above every layer's normal declarations          |
| Layers, in declared order     | Later layer wins; first declared is lowest       |
| Unlayered `!important`        | Below every layer's `!important`                 |
| Layers, `!important`          | Order is **reversed**: first declared layer wins |

That reversal is why `@layer` is worth adopting: `!important` inside `utilities` beats `!important` inside `components`, so the escape hatch lands where you expect. `revert-layer` rolls a property back to its value in the previous layer — the clean way to undo a base rule inside a component, unlike `revert`, which rolls back to the user or user-agent origin.

### Specificity budget

| Selector                    | Specificity   | Note                                            |
| --------------------------- | ------------- | ----------------------------------------------- |
| `:where(.card) .title`      | `0,1,0`       | `:where()` contributes zero                     |
| `.card .title`              | `0,2,0`       | Descendant coupling                             |
| `:is(.card, .panel) .title` | `0,2,0`       | `:is()` takes its **highest** argument's weight |
| `#app .title`               | `1,1,0`       | ID defeats every later class rule               |
| `.card` in a layer          | layer-ordered | Same weight, ordered by layer                   |

Audit rules: one class per selector; no IDs in stylesheets; `:where()` for resets and default states; never `:is()` when the argument list mixes a class with an element if the higher weight is unintended.

### Scoping without global leakage

CSS Modules scope by hashing class names at build time; `:global` is an escape that must be justified in review, not a styling tool. `@scope` (Baseline newly available, March 2026) bounds a selector set to a subtree without raising specificity — the declarative replacement for the BEM-as-namespace trick. The scope root is the inclusive upper bound and `to (...)` the exclusive lower bound, a "donut scope":

```css
@scope (.article-body) to (figure) {
  img {
    border: 1px solid var(--color-border);
  }
}
```

Native nesting is not a scoping tool: `&` resolves to the parent selector and adds its specificity exactly as if written out.

### `!important` has two legitimate uses

Inside the top `utilities` layer, where a utility must beat any component rule by design; and to override a third-party stylesheet or script-set inline styles you do not control. Everywhere else it is a specificity bug wearing a costume — the fix is to lower the competing selector's weight, not raise yours.

## Theming, Dark Mode, and Internationalization

### Runtime theming with custom properties

Custom properties are the only CSS feature that participates in the cascade _and_ is readable at runtime, which makes live theme switching possible without a rebuild. Re-declare the semantic tier on a scope and every descendant inherits it — a component reading `var(--color-surface)` is themed by both scopes below for free; one that hardcoded the color is themed by neither.

```css
:root {
  color-scheme: light dark;
  --color-surface: oklch(1 0 0);
}
[data-theme="dark"] {
  --color-surface: oklch(0.18 0.02 260);
}
```

### Dark mode: media query as default, attribute as override

`prefers-color-scheme` alone cannot express an explicit in-app choice, because there is no way to make the media query stop matching. Support both, make the attribute win, and guard the media query so a user can force light mode on a dark-OS machine:

```css
:root[data-theme="dark"] {
  --color-surface: oklch(0.18 0.02 260);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --color-surface: oklch(0.18 0.02 260);
  }
}
```

`light-dark()` is shorter when only the color value differs, but requires `color-scheme: light dark` on an ancestor. In Tailwind v4 the attribute strategy is a variant definition, not a `darkMode` config key:

```css
@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *));
```

### Logical properties for internationalization

Physical properties encode a left-to-right, horizontal-writing assumption. Logical properties resolve against the writing mode, so one stylesheet serves `dir="rtl"` and `writing-mode: vertical-rl`.

| Physical                         | Logical                                     |
| -------------------------------- | ------------------------------------------- |
| `margin-left` / `margin-right`   | `margin-inline-start` / `margin-inline-end` |
| `padding-top` / `padding-bottom` | `padding-block-start` / `padding-block-end` |
| `width` / `height`               | `inline-size` / `block-size`                |
| `border-left-width`              | `border-inline-start-width`                 |
| `left` / `right` (positioned)    | `inset-inline-start` / `inset-inline-end`   |
| `text-align: left`               | `text-align: start`                         |

Shorthand caveat: `margin-inline: 1rem` and `margin-block: 1rem` are logical, but `margin: 1rem 2rem` is physical and will not mirror. Direction-sensitive effects (`transform`, `background-position`, directional iconography) still need explicit handling — see [intl-bidi.md](intl-bidi.md).

### Print styles

Print is a real render target and is usually forgotten. Hide chrome with `nav, .toolbar { display: none }`, expand link targets with `a[href^="http"]::after { content: " (" attr(href) ")"; }`, stop cards splitting across pages with `.card { break-inside: avoid }`, and set the sheet margin with `@page { margin: 2cm }`. Reset backgrounds and shadows with `* { background: transparent !important; box-shadow: none !important }` — the one place a utility `!important` is legitimate, because print must beat the screen utility layer.

## Layout Stability, Responsiveness, and Delivery

### Preventing layout shift

| Symptom                                  | Cause                                               | Fix                                                                                |
| ---------------------------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Images jump as they load                 | No reserved box                                     | `width`/`height` attributes plus `img { height: auto }`, or `aspect-ratio: 16 / 9` |
| Text reflows when a web font loads       | Fallback metrics differ                             | `font-size-adjust: from-font` (Baseline 2024), or `size-adjust` in `@font-face`    |
| Content appears late and pushes the page | `content-visibility: auto` with no placeholder size | `contain-intrinsic-size: auto 500px`                                               |
| Sticky header overlaps anchors           | Scroll offset not accounted for                     | `scroll-padding-block-start: var(--header-height)` on `:root`                      |

`contain-intrinsic-size: auto 500px` remembers the last-rendered size once an element has been seen, so the placeholder applies only to elements never yet rendered. Declare web fonts with `font-display: swap` and a metric-compatible fallback in the stack.

### Container queries for component-level responsiveness

A component that changes shape based on the _viewport_ is wrong whenever it is placed in a sidebar. `container-type: inline-size` applies layout, style, and inline-size containment — the container no longer sizes to its content in the inline axis, which is why it belongs on a wrapper, not on the component itself.

```css
.card-host {
  container-type: inline-size;
}

@container (width > 40rem) {
  .card {
    grid-template-columns: 12rem 1fr;
    align-items: start;
  }
}
```

Media queries remain correct for page-level layout, print, and user preferences.

### Motion

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Animating only under `prefers-reduced-motion: no-preference` is stricter than resetting under `reduce`, and is the better default for new components. `@starting-style` (Baseline 2024) supplies the pre-insertion values that make entry transitions fire on first paint, including for elements moving into the top layer. For height transitions between `auto` and a fixed value, `interpolate-size: allow-keywords` enables it, but it is not Baseline — gate it behind `@supports`, or prefer `grid-template-rows: 0fr` to `1fr`.

### Accessibility-adjacent CSS

- **Focus**: style `:focus-visible`, never bare `:focus`, and never `outline: none` without an equivalent visible replacement. `:focus-visible` matches keyboard focus and skips mouse clicks. A 2px outline with a 2px offset is the safe baseline.
- **Contrast**: 4.5:1 for body text, 3:1 for large text and for UI component boundaries, focus indicators, and meaningful graphics. Check a token pair in _every_ theme, not just light.
- **Target size**: WCAG 2.5.8 (Level AA) requires 24×24 CSS px, with five exceptions — Spacing, Equivalent, Inline, User Agent Control, Essential. Padding counts toward the target, so a 16px icon with 4px padding passes.

### Keep the critical path small

- `@import` inside CSS is render-blocking and resolves serially: the browser must fetch and parse the imported sheet before discovering the next. Import through the bundler instead.
- Unused CSS is not free. Utility frameworks purge by scanning source for class names, so dynamically constructed class strings (`"text-" + size`) are never generated — use a static lookup map.
- Split critical CSS (above-the-fold) from deferred CSS, and preload fonts with `crossorigin` so the metric-adjusted fallback is not itself delayed.
- A CSS-in-JS runtime that serializes styles on every render belongs on the interaction path, not the critical path; prefer build-time extraction.

### Formatting and linting

Prettier owns formatting; Stylelint owns correctness and convention. Never configure both to format the same property order.

```js
// stylelint.config.mjs
/** @type {import('stylelint').Config} */
export default {
  extends: ["stylelint-config-standard"],
  ignoreFiles: ["**/dist/**"],
  overrides: [
    {
      files: ["**/*.module.css"],
      customSyntax: "postcss-modules",
      rules: { "selector-class-pattern": null },
    },
  ],
  rules: { "declaration-no-important": true },
};
```

Stylelint 16 migrated its source to ESM; Stylelint 17 migrated configuration to ESM and requires full file paths for local `extends` and `plugins` (`"./index.js"`, not `"./"`). Non-CSS sources need a `customSyntax` — `postcss-scss`, `postcss-less`, `postcss-html`, `postcss-lit`, `postcss-modules` — set per glob under `overrides[].files`. Shared configs (`stylelint-config-standard-scss`, `stylelint-config-css-modules`) bundle the syntax and disable rules that do not apply.

## Common Mistakes

| Mistake                                                    | Why It Breaks                                                                  | Correct Approach                                                                |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| Descendant selectors in component CSS (`.card .title`)     | Specificity grows with nesting; overrides require more nesting or `!important` | Single-class BEM (`.card__title`)                                               |
| Hardcoding a hex or `px` in a component                    | Ignores dark mode, theming, and any scale refactor                             | Reference the semantic token: `var(--color-accent)`                             |
| `!important` to beat a component rule                      | The next author escalates; the cascade becomes unorderable                     | Add or reorder a `@layer`; lower the competitor with `:where()`                 |
| Dark overrides without a `:not()` guard on the media query | Forced light mode cannot beat the OS dark preference                           | `:root:not([data-theme="light"])` inside the media query                        |
| `100vh` for a full-height hero                             | Mobile browser chrome collapse makes the hero jump and overflow                | `min-block-size: 100svh` (or `dvh` where dynamic is intended)                   |
| `@import` of app stylesheets in CSS                        | Serial, render-blocking fetch chain on the critical path                       | Import through the bundler; reserve `@import` for layer-ordered design files    |
| `:focus { outline: none }`                                 | Keyboard users lose the only indication of position                            | `:focus-visible` with a visible outline and offset                              |
| Arbitrary values everywhere (`p-[13px]`, `bg-[#3b82f6]`)   | The configured scale is bypassed; refactors miss these rules                   | Scale utilities, or a token for genuinely off-scale values                      |
| `transform` for a directional effect                       | Does not mirror under `dir="rtl"`; logical properties do not cover it          | Flip explicitly under `[dir="rtl"]`, or use a logical-safe technique            |
| Nested `@layer` blocks used to reorder                     | Layer order is fixed at first declaration; later blocks cannot reorder         | Declare the full order once: `@layer reset, base, components, utilities;`       |
| `transition: all` on every element                         | Animates layout properties, causing jank and unintended motion                 | Transition named properties, only under `prefers-reduced-motion: no-preference` |
| `content-visibility: auto` with no intrinsic size          | Off-screen elements report zero height and the scrollbar jumps                 | Pair with `contain-intrinsic-size: auto <length>`                               |
| Viewport media queries inside a reusable component         | The component breaks in a narrow sidebar or a wide modal                       | `container-type: inline-size` on the host plus `@container`                     |

## Checklist

1. Enumerate every styling model present and confirm a written rule assigns each surface to exactly one; flag files mixing two without an ownership boundary.
2. Confirm component CSS uses a single-class naming contract (BEM or equivalent) and that no component selector contains a descendant combinator or an ID.
3. Trace every color, spacing, radius, and shadow declaration to a token; list each raw literal with its file and line.
4. Confirm the token set has a semantic tier and that components reference semantic tokens, not primitives.
5. Grep for arbitrary values (`\[[^\]]+\]` in class attributes, hardcoded `px` in stylesheets) and confirm each survivor is justified and tokenized.
6. Confirm a single `@layer` order statement exists at the top of the entry stylesheet and that every stylesheet assigns its rules to a declared layer.
7. Count `!important` occurrences and confirm each is inside the top utility layer or in `@media print`.
8. Confirm dark mode has one source of truth and that an explicit user override beats `prefers-color-scheme` via a `:not([data-theme=...])` guard.
9. Audit for physical properties (`left`, `right`, `margin-left`, `padding-top`, `width`) where a logical equivalent exists, and verify the layout mirrors under `dir="rtl"`.
10. Verify every raster or video element reserves space via `width`/`height` attributes, `aspect-ratio`, or explicit `inline-size`/`block-size`.
11. Confirm web fonts are declared with `font-display`, a metric-compatible fallback stack, and `font-size-adjust` or `size-adjust`.
12. Confirm every component that reflows internally uses `container-type: inline-size` plus `@container` rather than viewport media queries.
13. Confirm a `prefers-reduced-motion: reduce` reset exists, or that motion is authored only under `no-preference`.
14. Verify focus styles use `:focus-visible` and that no `outline: none` exists without an equivalent visible replacement.
15. Check target sizes against WCAG 2.5.8 (24×24 CSS px) and text and UI contrast against 4.5:1 and 3:1 in every theme.
16. Confirm critical CSS is separated from deferred CSS and that no app stylesheet is loaded via a CSS `@import`.
17. Confirm a Stylelint configuration exists in ESM form with a `customSyntax` per non-CSS glob, and that Prettier and Stylelint do not both own formatting.
18. Run the linter and formatter non-interactively (`stylelint "**/*.css"`, `prettier --check .`) and record the residual count.

## References

- [MDN: CSS cascade and inheritance](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_cascade) — origin, importance, and layer interaction order.
- [MDN: `@layer`](https://developer.mozilla.org/en-US/docs/Web/CSS/@layer) — layer declaration order, unlayered precedence, and the `!important` reversal.
- [MDN: `revert-layer`](https://developer.mozilla.org/en-US/docs/Web/CSS/revert-layer) — rollback semantics and how it differs from `revert`.
- [MDN: `@scope`](https://developer.mozilla.org/en-US/docs/Web/CSS/@scope) — donut scoping, inclusive upper and exclusive lower bounds, Baseline March 2026.
- [MDN: `:where()`](https://developer.mozilla.org/en-US/docs/Web/CSS/:where) and [`@container`](https://developer.mozilla.org/en-US/docs/Web/CSS/@container) — zero-specificity matching and container query syntax.
- [MDN: CSS container queries](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_containment/Container_queries) — `container-type: size | inline-size | normal` and its containment effects.
- [MDN: `light-dark()`](https://developer.mozilla.org/en-US/docs/Web/CSS/color_value/light-dark) — the `color-scheme: light dark` prerequisite and image support.
- [MDN: `font-size-adjust`](https://developer.mozilla.org/en-US/docs/Web/CSS/font-size-adjust) — `from-font`, `ex-height`, `cap-height`, `ch-width`, `ic-width`.
- [MDN: `contain-intrinsic-size`](https://developer.mozilla.org/en-US/docs/Web/CSS/contain-intrinsic-size) — the `auto <length>` remembered-size form.
- [MDN: `@starting-style`](https://developer.mozilla.org/en-US/docs/Web/CSS/@starting-style) — entry transitions and first-style updates for top-layer elements.
- [MDN: `interpolate-size`](https://developer.mozilla.org/en-US/docs/Web/CSS/interpolate-size) — `allow-keywords` and which intrinsic values become interpolable.
- [WCAG 2.2 Understanding SC 2.5.8: Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) — the 24×24 CSS px requirement and its five exceptions.
- [WCAG 2.2 Understanding SC 1.4.3: Contrast (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) — the 4.5:1 and 3:1 thresholds.
- [Tailwind CSS: Theme variables](https://tailwindcss.com/docs/theme) — the `@theme` directive, generated custom properties, and `--*: initial`.
- [Tailwind CSS: Dark mode](https://tailwindcss.com/docs/dark-mode) — the `@custom-variant dark` data-attribute strategy.
- [Stylelint: Configuration](https://stylelint.io/user-guide/configure) — config file formats, `ignoreFiles`, and `overrides`.
- [Stylelint: Custom syntaxes](https://stylelint.io/user-guide/options/custom-syntax) — `customSyntax` for SCSS, Less, HTML, and CSS-in-JS containers.
- [Prettier: Options](https://prettier.io/docs/options) — the formatting decisions Prettier owns and Stylelint must not duplicate.
