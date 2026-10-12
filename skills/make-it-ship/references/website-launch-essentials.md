# Website launch essentials

Source group 4. Apply to website surfaces, not native-only interfaces. Public marketing, authenticated applications and search-indexable pages have different requirements. Account for every source ID using [SKILL.md](../SKILL.md).

| ID | Source item | Applicability and evidence to seek |
| ----- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| WL-01 | custom 404 page | Inspect invalid routes for useful recovery and correct HTTP status where applicable, not a branded page returning 200 for every URL. Browser/deployment behavior must be verified separately from template existence. Related: WQ-03. |
| WL-02 | CTA above the fold | Acquisition/action pages: verify the primary action is understandable, usable and visible at relevant viewports. Do not force marketing CTAs onto unrelated app screens. |
| WL-03 | meta title per page | Indexable/shareable routes: inspect meaningful page-specific titles in relevant rendered/server metadata. Related: WQ-05. |
| WL-04 | meta description per page | Public search surfaces: inspect accurate page-specific descriptions, avoiding unsupported promises. Private dashboards may not need SEO descriptions. Related: WQ-06. |
| WL-05 | open graph image | Public shared pages: inspect resolved metadata URL, image response/dimensions and accurate preview. File existence alone does not prove a crawler can fetch it. Related: WQ-07. |
| WL-06 | favicon set | Website identity: inspect valid icon references and supported browser/device appearance. Scope the icon set to actual targets rather than requiring every legacy size. Related: WQ-14. |
| WL-07 | robots.txt | Check intended search/crawler policy for the deployed origin. robots.txt is not access control and must not be used to protect secrets. Preserve intentional AI-crawler blocking. Related: WQ-13. |
| WL-08 | sitemap.xml | Public indexable content: verify canonical accessible URLs, exclusions and freshness. A tiny or non-indexable app may not need a sitemap. Related: WQ-15. |
| WL-09 | alt text on every image | Informative images need useful alternatives; decorative images normally use alt="". Functional image labels describe the action. Inspect actual purpose, not merely non-empty attributes. Related: LP-09, WQ-17. |
| WL-10 | mobile breakpoints | Inspect core journeys at representative viewport sizes, text zoom and orientations; check overflow, readable content and touch targets. Breakpoint definitions alone are not proof. |
| WL-11 | sticky mobile CTA | Optional conversion design. Check whether a sticky action helps and avoids obscuring content, consent controls or keyboard focus. An effective nonsticky action can pass the product goal. |
| WL-12 | loading states | Async journeys: inspect pending, success, failure and empty states with accessible announcements where needed, duplicate-action protection and stable layout. Skeletons are optional. Related: DC-15, WP-05, MP-10. |
| WL-13 | form error states | Inspect field and submission errors, accessible association, retained valid input and safe server-error messages. Test evidence must cover rejection, not only successful submission. |
| WL-14 | thank you page | Submitted/conversion flows: verify clear confirmed success and a useful next step. Inline confirmation can satisfy the need; a separate page is not universally necessary. Do not show success before server acknowledgement. |
| WL-15 | privacy policy page | Reuse LP-11 for accurate disclosure, applicable data flows and jurisdiction; a link or generated template alone is insufficient. |
| WL-16 | terms page | Reuse LP-01 for applicable terms and review ownership; do not invent business terms. |
| WL-17 | cookie banner | Only where nonessential storage/tracking and applicable requirements call for consent. Verify actual pre-consent blocking, refusal and withdrawal; do not add a banner to claim compliance without examining behavior. Related: LP-19. |
| WL-18 | analytics installed | Optional product measurement. Verify a documented need, events, privacy/consent and data minimization if installed. No analytics is a valid choice; never install tracking during audit. Related: LP-02. |
| WL-19 | real contact address | Inspect a genuine authorized business/support contact suitable for the product. Do not publish personal home addresses or invent company details; physical-address obligations need jurisdictional review. Related: LP-04. |
| WL-20 | compressed images | Inspect actual transfer sizes, dimensions, quality and responsive formats. Avoid blanket quality loss or lazy-loading critical imagery. Related: WP-04, MP-01, MP-15. |

[W3C decorative-image guidance](https://www.w3.org/WAI/tutorials/images/decorative/), consulted 2026-10-12, explains why empty alternatives are correct for genuinely decorative images.
