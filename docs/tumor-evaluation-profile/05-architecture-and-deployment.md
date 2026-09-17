# TEP — Architecture and Deployment

Target platform: **R / Shiny with the pharmaverse stack**. This document names concrete components, states why each was chosen, and defines the boundaries that keep an unvalidated review tool honest.

---

## 1. Why this stack

The decision rests on who will own the hardest part of the system. The criteria engine — RECIST 1.1 and iRECIST derivation, confirmation policy, nadir handling — is where correctness lives and where most of the maintenance will go. In R, that code is owned by statistical programmers, who already read protocols, already know what a nadir is, and already work in the idiom that `admiral` and `admiralonco` establish for CDISC derivations. In a Python or JavaScript stack it would be owned by software engineers, and every criteria question would become a translation exercise between two teams.

The secondary reasons reinforce it: CDISC handling is native, `teal` provides a working precedent for filter-panel-plus-linked-module review applications over CDISC data, and the reconciliation requirement (comparing the engine against ADaM) is trivial when both sides are R data frames.

The honest cost: Shiny's default visual vocabulary is generic, and the TEP's value depends on a dense custom layout with a shared time axis across bands. **Do not build the bands out of stock Shiny plotting components.** They should be one custom output — see §4.

---

## 2. Component architecture

```
┌────────────────────────────────────────────────────────────────────┐
│  SOURCE                                                            │
│  Clinical data repository / EDC-to-SDTM conversion                 │
│  per study: SDTM datasets + (optional) ADaM                        │
└───────────────────────────┬────────────────────────────────────────┘
                            │  scheduled pull (config: data.refresh)
┌───────────────────────────▼────────────────────────────────────────┐
│  BUILD  —  R batch job, one run per study per refresh               │
│  1. load config, validate against schema                            │
│  2. read SDTM, apply mappings.overrides                             │
│  3. partition TR/RS by assessor (rs_eval_values)                    │
│  4. criteria engine  →  per-assessor derivations                    │
│  5. data-quality checks  →  rl_flag                                 │
│  6. coverage + freshness  →  rl_coverage, rl_freshness              │
│  7. write review layer (parquet), stamped with config hash          │
└───────────────────────────┬────────────────────────────────────────┘
                            │  parquet on shared storage
┌───────────────────────────▼────────────────────────────────────────┐
│  APP  —  Shiny                                                      │
│  study picker → subject picker (+waterfall strip) → profile         │
│  bands as one custom D3/SVG output on a shared scale                │
│  derivation panel · reconciliation view · PDF export                │
└────────────────────────────────────────────────────────────────────┘
```

**The build/serve split is the most important architectural decision.** Every derivation happens in the batch job, never in a Shiny reactive. This is what makes the two-second render target achievable, it makes derivations testable without a running app, and it means a UI bug can never change a derived value.

## 3. Package choices

| Concern | Choice | Note |
|---|---|---|
| SDTM/ADaM derivation idiom | `admiral`, `admiralonco` | `admiralonco` already implements SOD, nadir and RECIST response patterns; use it as the reference implementation rather than reinventing, but wrap it so thresholds come from configuration |
| Data wrangling | `dplyr`, `tidyr` | |
| Columnar storage / fast read | `arrow` (parquet), optionally `duckdb` | Subject-level filtering from parquet is fast enough; DuckDB earns its place only if the cohort layer grows |
| Config | `yaml` + `jsonvalidate` against a published JSON Schema | Schema validation is a Must (FR-P-03) |
| App framework | `shiny`, with `bslib` for layout and theming | |
| Module pattern | Shiny modules, `teal`-style | Use `teal` itself only if the team already runs it; otherwise its filter-panel model is a pattern to copy, not a dependency to take on |
| Custom bands | `r2d3` or `htmlwidgets` wrapping D3 | See §4 |
| Tables | `reactable` or `DT` | |
| PDF export | Quarto → Chromium headless (`pagedown`/`chromote`) | Renders the same HTML band components, so print and screen cannot drift |
| Testing | `testthat` for the engine, `shinytest2` for the app | |
| Dependency pinning | `renv` | Non-GxP still needs reproducibility |

## 4. The bands are one component, not several

The defining property of the profile is that bands 2, 3 and 4 share one time axis and one left gutter, so vertical alignment carries meaning (`03-visual-and-interaction-spec.md` §1). Composing them from independent plot outputs guarantees drift: independent margins, independent scales, independent redraws on resize.

Build the band stack as **one `htmlwidget`** that receives the subject's full payload and renders all longitudinal bands against a single scale, with the crosshair and zoom as widget-internal state. Shiny supplies data and receives events (marker clicked, lesion selected); it does not own the geometry.

This is also what makes the PDF export faithful: the same widget renders to the print page at print geometry, rather than a second implementation drifting from the first.

## 5. Refresh, staleness and concurrency

The build runs per study on the configured cron. Each run writes to a new versioned directory and flips a pointer on success, so a failed or partial build never becomes visible. A running session keeps the version it started on until the user navigates, which prevents a profile mutating mid-review.

`rl_freshness` records the extract as-of timestamp per domain, and the header renders per-domain staleness against the configured thresholds (FR-H-03). If a build fails, the previous version continues to serve and the header shows the failure and the age of what is being displayed — **never a silent stale render.**

## 6. Unvalidated posture, enforced structurally

Non-GxP is a set of engineering commitments, not a disclaimer.

- The review-only badge is rendered by the application shell, not by a page template, so no view can omit it. It appears on screen, in the footer of every PDF page, and as a header row in every data export.
- Every export carries the study ID, configuration hash, build timestamp, per-domain data as-of timestamps and the assessor selection. An artefact that leaves the system can always be traced back to the rules and the data that produced it.
- The application has **read-only credentials** to all data sources. It cannot write back to EDC or to the CDR, and this is enforced at the credential level rather than by convention.
- The reconciliation view against ADaM is part of the product, not an optional report. An unvalidated engine that is never compared to the validated one is the thing that eventually embarrasses everybody.

## 7. Engine testing

The criteria engine is the part worth real test effort.

**Worked examples.** The published RECIST 1.1 and iRECIST guidance contains worked cases; encode each as a fixture with expected timepoint responses and BOR. These are the regression floor.

**Boundary cases, explicitly.** Exactly −30.0% change; exactly +20.0% with a +4 mm absolute rise (must not be PD); nodal target falling to exactly 10.0 mm short axis; confirmation exactly at the configured interval and one day short; a nadir set at baseline for a subject who never shrank; a new lesion appearing at the same visit as a deep target response; repeated iUPD episodes with a reset between them.

**Configuration matrix.** Run the same fixture subject under several configurations (confirmation on and off, different intervals, RECIST versus iRECIST) and assert the outputs differ in exactly the expected way. This is the test that proves the engine is genuinely parameterised rather than constants with a configuration file beside them.

**Per-study regression.** On each build, compare derived results against the previous build and report the diff. A derivation that changes without a configuration change or new data is a defect.

## 8. Access, logging and environments

Company SSO in front of the app. One reviewer role with access to every study and every site, matching the stated deployment posture; one configurator role that may edit configurations through version control. No site-level authorisation.

The application logs authentication, study and subject views with timestamp and user, and configuration changes with the resulting hash. This is an operational log supporting traceability and access review — it is not a 21 CFR Part 11 audit trail and must not be described as one.

Blinded studies withhold treatment assignment entirely (`study.blinded: true`); there is no in-app unblinding control.

Three environments: **development** (synthetic data only), **validation/UAT** (a completed or locked study, used to exercise onboarding and the reconciliation view), and **production** (internal network, Posit Connect or Shiny Server Pro). Study configurations move through the same branch-and-review flow as code.

## 9. Build sequence

The order below front-loads the parts that are hard to change later.

1. **Configuration schema and validator.** Everything else depends on its shape, and its shape is the product's central claim.
2. **Criteria engine with its test suite**, headless, no app. RECIST 1.1 first, iRECIST immediately after — they share too much machinery to separate.
3. **Review-layer build job** for one study end to end, including coverage, freshness and quality flags.
4. **The band widget**, against static review-layer output. Get the shared axis and the crosshair right before wiring any reactivity.
5. **Shiny shell**: pickers, header, assessor control, derivation panel.
6. **PDF export** from the same widget.
7. **Reconciliation view** as soon as an ADaM build exists.
8. **Second study onboarded** — before polishing the first. This is the only real test of whether the configuration schema holds, and finding out late is expensive.
