# TEP — Visual and Interaction Specification

This annex fixes the visual grammar of the Tumor Evaluation Profile. Its purpose is to keep the same encoding meaning the same thing in every band, so a reviewer learns the page once.

---

## 1. Layout geometry

The page is a single column at a fixed maximum width, with a sticky header. Bands 2, 3 and 4 share one plot area whose left gutter is reserved for row labels and whose right gutter is reserved for end-of-line direct labels. **The left gutter width is identical across those three bands** — this is what makes the vertical alignment read as meaningful rather than accidental. On narrow viewports the bands stack and the shared axis compresses; the alignment contract is never broken by reflowing one band independently.

Band 1 sits above the axis region as a four-card grid, because it carries no time dimension and should not borrow the axis.

## 2. The time axis

The axis is study day by default, with day 1 defined as the first dose date, and is switchable to calendar date and to a cycle-relative mode. Baseline is marked with a labelled vertical rule, since almost every value on the page is expressed relative to it. Where the subject is still on treatment at the data cut, the axis extends to the cut date and the treatment bar terminates in an explicit "ongoing" cap rather than simply stopping — a bar that stops without a cap reads as a discontinuation.

Zoom and pan act on the axis domain, not on the individual bands, so the bands cannot desynchronise by construction.

## 3. Encoding rules

### 3.1 Response categories

Response is the most important categorical variable on the page and it appears in three places: as markers on the burden curve, as a chip in the header, and in the per-timepoint table. It must be encoded identically in all three.

Response is **ordered**, not nominal — CR is better than PR is better than SD is better than PD — so it takes an ordinal treatment rather than arbitrary categorical hues, and it always carries a text label or letter code in addition to colour.

| Category | Encoding | Note |
|---|---|---|
| CR | filled circle, deepest step | always labelled `CR` |
| PR | filled circle, mid step | always labelled `PR` |
| SD | filled circle, light step | always labelled `SD` |
| PD | filled square, status-critical | shape change is deliberate — PD is a state change, not a point on the scale |
| NE | hollow circle, muted ink | never filled; absence of evaluation must not look like a value |
| iUPD | half-filled square, status-warning | only when iRECIST applies |
| iCPD | filled square, status-critical, outlined | terminal state |

**Unconfirmed responses are drawn with a hairline ring instead of a solid fill.** This is the single most important encoding decision on the page, because an unconfirmed PR is a materially different claim from a confirmed one and the difference must survive being screenshotted into a slide.

### 3.2 The burden curve

One subject, one line, 2px, in categorical slot 1. Markers at every assessment, at least 8px, carrying the response encoding above.

The two reference rails at −30% and +20% are solid hairlines in the muted ink, labelled at the right edge with their meaning (`PR threshold`, `PD threshold`) rather than only their value. They are **not** dashed — dashing reads as projection. The nadir is drawn as a second hairline with a small caption giving its value and date.

Cohort context, when enabled, is drawn as background traces in the border hairline colour at low opacity, never in a categorical hue, so that no reviewer mistakes a context trace for a second series belonging to this subject. The subject's own line always renders on top with a 2px surface ring where it crosses a context trace.

Gaps matter: **the line is broken, not interpolated, across a non-evaluable timepoint**, and the gap carries an `NE` marker. Silent interpolation across a missed scan is a correctness bug, not a cosmetic one.

### 3.3 Per-lesion rows

Each target lesion is one row: a label in the left gutter (lesion ID, site, and target/non-target status), a sparkline of that lesion's diameter over time drawn against a per-row scale, and a heat strip of percent change from that lesion's own baseline. The heat strip uses the **diverging** palette — shrinkage on the cool pole, growth on the warm pole, neutral gray at zero change — because the variable has a meaningful zero and a meaningful sign. A sequential ramp here would be wrong; it would hide the direction of change, which is the entire point of the row.

Non-target lesions get status cells rather than sparklines, since they carry no measurement. New lesions get a dedicated row rendered above the target rows, not below, so it is seen first; the first-observed date is marked distinctly from the confirmation date.

### 3.4 Adverse events

AE bars are encoded by maximum grade using the **status** palette (grade 1–2 as neutral/warning, grade 3 as serious, grade 4–5 as critical), never using categorical series colours, because grade is a state and not an identity. Every status colour ships with an icon or letter, so grade is never carried by hue alone. Serious events carry an additional marker, and DLTs carry a distinct, deliberately loud marker — a DLT in an early-phase study is the single most consequential event on the page.

### 3.5 What colour must never do here

Categorical hues are reserved for identity — the subject's own burden line, an assessor overlay, an optional second modality. They are never used for grade, never for response category, and never cycled past their fixed order. Status colours are reserved for state and never used to distinguish a series. Where two assessors are overlaid, they are two categorical slots with distinct line treatments, not a hue-only distinction.

## 4. Interaction

A crosshair follows the pointer along the axis and is drawn across all time-based bands simultaneously; the tooltip is band-local but the crosshair is global, so a reviewer hovering an AE can read the concurrent burden value directly.

Clicking a burden-curve marker opens the derivation panel for that timepoint: the contributing lesion measurements, the computed SOD, the change from baseline and from nadir, the target/non-target/new-lesion sub-responses, the resulting overall response, and the assessor and assessment date. This panel is how FR-3-11 is satisfied and it is not optional — it is the feature that makes the report trustworthy.

Selecting a lesion row highlights that lesion's contribution wherever it appears. Selecting an AE bar highlights the dose records it affected in band 2.

Filters live in a single row above the bands: assessor, AE relevance, axis mode, and burden metric. They never move.

## 5. Accessibility and output

Every colour-carried distinction on the page — response category, AE grade, confirmation status, evaluability — carries a redundant shape, position, or label. A table view is available for the burden curve and the per-lesion grid, and it is also what the CSV export emits. Dark mode is specified as its own set of steps validated against the dark surface, not as an inverted light palette.

The PDF export renders the same bands at print geometry with the axis intact, one subject per document, with the data cut stamp and the assessor selection printed in the footer of every page.
