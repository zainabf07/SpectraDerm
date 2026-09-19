# SpectraDerm design system

Every future screen inherits this. If a feature needs something not described
here, extend the token set in `src/styles.css` rather than styling the screen
independently.

## Direction

A skin-health product that happens to use AI, not an AI product with a skin
theme. Warm, editorial, clinical without feeling like a hospital. Sophistication
comes from typography, spacing and restraint. The interface never advertises
models, agents, retrieval or MCP; those appear only as what the product does.

## Colour

All values are CSS custom properties on `:root`. Nothing is hardcoded in a
component.

| Token | Value | Use |
| --- | --- | --- |
| `--ivory` | `#fbf8f3` | page |
| `--cream` | `#f4eee4` | recessed areas, image wells |
| `--paper` | `#ffffff` | the rare raised tile |
| `--ink` | `#241f1b` | headings, body, primary button |
| `--ink-soft` | `#4d453d` | secondary body |
| `--taupe` | `#8a7d70` | captions, metadata, labels |
| `--sand` / `--hairline` / `--hairline-strong` | `#e7dcca` `#e0d6c6` `#cdbfa9` | fills, rules, borders |
| `--accent` / `--accent-deep` / `--accent-wash` | muted olive | action, focus, steady states |
| `--clay` / `--clay-deep` / `--clay-wash` | muted clay | an observation worth attention |

Two rules hold everywhere. There is no alarm red — attention is carried by clay
and by position in the hierarchy, never by a warning colour. And saturated
colour appears in exactly one place: imagery returned by the analysis, plus the
thin wavelength legend that labels it. There, colour is data.

## Type

Newsreader (serif) for headings, the difference score, timeline dates and pulled
quotations. Archivo (sans) for body, navigation, buttons, labels and all
functional UI. No third family.

The scale is `--step--1` through `--step-5`, roughly a 1.25 ratio. Headings sit
at 400 weight; emphasis comes from size and space, not bold. Measure is capped
at `--measure` (62ch), and ledes at 44ch.

## Space

`--s-1` (4px) through `--s-9` (104px). Section rhythm is `--s-6`; page padding is
`--s-7` top and `--s-9` bottom. Whitespace is structural — do not fill it.

## Structure

`.section` is the default container: a hairline rule, a title, then content. It
is not a card. `.tile` exists for the few things that genuinely need lifting off
the page, and should stay rare. Radius is `--radius` (4px) or `--radius-sm`
(2px); there are no other radii and no shadows anywhere. Hierarchy comes from
rules, spacing and type.

## Components

`Section`, `Tile`, `Tag`, `Note`, `PageHead`, `BackLink`, `Spinner`, `Empty` and
`KeyValues` live in `src/components/Primitives.jsx`. New screens compose these.

Buttons have three forms and no others: `btn--primary` (solid ink, one per
screen), `btn--ghost` (outlined secondary), `btn--quiet` (underlined inline
action). Tags and notes take a tone of `steady`, `observed` or `notice`.

## Motion

Transitions run at `--ease` (180ms). Three motions exist: a dot breathing on the
active processing step, a 1px progress rule advancing, and a fade as a new image
settles into its frame. Everything else is instant. `prefers-reduced-motion` is
respected globally.

## Language

Observational, never diagnostic. The product observes, records, compares and
notes; it does not detect, flag, warn or alert.

| Use | Not |
| --- | --- |
| Observation | Scan |
| Change observed | Change detected |
| A change worth monitoring | Alert, warning, high risk |
| Difference score | Anomaly score, risk score |
| Why this was noted | Why was this flagged |
| Consider professional evaluation | You should see a doctor |
| Estimated spectral information | NIR image, hyperspectral photo |

The score is always framed as distance from the person's own baseline, never as
a probability. That wording lives in `src/lib/analysis.js` so it cannot drift
from screen to screen.

## Imagery

The only photographs in the product are the person's own. There is no stock
photography, no illustration, and no decorative graphics — nothing depicting
AI, networks, brains or devices. Where an image slot is empty, it says what will
appear there.
