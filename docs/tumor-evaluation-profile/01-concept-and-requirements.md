# Tumor Evaluation Profile (TEP) — Product Concept & Requirements

**Status:** Draft v0.2 for team review
**Product:** A reusable, multi-study web application producing individual-patient tumor-response review profiles
**Scope:** Any oncology study using RECIST 1.1 or iRECIST; onboarding a new study is a configuration task, not a development task
**Posture:** Review-only, non-GxP. Near-live SDTM-derived review layer. Company-internal, all users see all sites.
**Companion documents:** `02-data-model-and-derivations.md`, `03-visual-and-interaction-spec.md`, `04-study-configuration.md`, `05-architecture-and-deployment.md`

---

## 1. What this product is, and what it is not

A conventional patient profile answers *"what happened to this subject?"* It is organised by CRF domain, it is exhaustive, and it is consumed as a static PDF at signal detection or database lock. That format is optimised for completeness and traceability, not for judgement.

The Tumor Evaluation Profile answers a narrower and harder question: **did the drug move this patient?** Answering it requires holding four things at once — how much tumor the patient started with, how that burden moved, what the disease and treatment history predicted, and what else was happening (toxicity, dose modification, concomitant therapy) when the tumor moved. A domain-ordered profile forces the reviewer to assemble that picture manually, and the assembly is where signal gets lost.

The TEP is therefore defined by a deliberate narrowing: **one subject, one shared time axis, and only the data that bears on interpreting tumor response.** Everything that does not help interpret the burden curve is removed or pushed one click away, with a link out to the full patient profile.

Three design consequences follow, and they are non-negotiable across every study:

1. **The time axis is the spine.** Every longitudinal band is drawn against the same axis, so vertical alignment carries meaning. A grade 3 AE directly under a scan showing a 40% shrink is a finding the reviewer sees without being told to look.
2. **The derived response is never shown without its inputs.** A reviewer who sees "PR" and cannot immediately reach the sum-of-diameters behind it will not trust the report — and in an unvalidated tool, trust is the entire value proposition.
3. **Per-lesion behaviour is first-class.** Aggregate SOD hides heterogeneous response, and the case where four lesions shrink while one grows is precisely the signal an early-phase team wants. Most commercial profiles stop at the SOD line.

**What it is not.** It is not a validated analysis system, not a source of record, not an endpoint-derivation replacement for ADaM, and not a data-entry surface. It never writes back to EDC. Its outputs inform judgement; they do not constitute a decision of record.

---

## 2. Generalisation: what makes this a product rather than a report

A study-specific profile is a script. A product is a configuration-driven application. Four things carry the generalisation, and every requirement in this document is shaped by them.

**Onboarding a study is configuration, never code.** A study is described by one declarative configuration file — criteria set, confirmation policy, assessment schedule, cycle length, DLT window, lesion limits, AE relevance rules, domain and variable mappings, display labels. The full schema is `04-study-configuration.md`. If a new study needs a code change to onboard, that is a defect in the configuration schema, and the fix belongs in the schema.

**The derivation engine is study-agnostic and parameterised.** RECIST 1.1 thresholds, the confirmation interval, the nadir definition, the baseline-visit selection rule — all of these are protocol-varying and all of them are inputs to the engine, not constants inside it. The engine ships with defaults that match the published criteria; a study that deviates overrides the default in its configuration, and the profile shows which values were in force.

**The data contract is SDTM, not a study's EDC.** The application reads a near-live SDTM-derived review layer. Studies whose collected data is not yet fully SDTM-conformant are handled by per-study mapping overrides in the configuration, not by bespoke code paths.

**The page adapts to what the study actually has.** A study without central review shows no assessor control. A study without a DLT window shows no DLT band. A study with no prior-radiotherapy collection hides that card rather than showing an empty one. Absent data collapses; it never renders as a blank frame.

---

## 3. What outside practice already establishes

The visual grammar for tumor response is mature and largely settled. The TEP should assemble known-good components and make them interoperate on one page rather than invent new forms.

| Established artefact | What it answers | Where it belongs in the TEP |
|---|---|---|
| **Spider / longitudinal plot** — % change in SOD vs. time | How did burden move, and when? | Core burden band, reduced to *this* subject with the cohort behind as faint context |
| **Waterfall plot** — best % change per subject, ranked | How does this subject compare? | Cohort strip in the subject picker only — one highlighted bar |
| **Swimmer plot** — treatment duration with response and event markers | How durable, and still on treatment? | Disposition/exposure band |
| **Event timeline with stacked tracks** (cBioPortal patient view) | What else was happening then? | The structural pattern for the whole page |
| **CDISC TU/TR/RS linkage via `--LNKID` / `--LNKGRP`** | Which measurement produced which response? | The traceability model behind every drill-down |
| **`teal` / pharmaverse patient-profile modules** | A working reference for filter-panel + linked-module review apps on CDISC data | Architectural precedent (see `05-architecture-and-deployment.md`) |

Two lessons from that body of practice are the ones teams most often get wrong.

First, **response labels and measurement data must be visually separable but spatially adjacent.** In published spider plots the response category rides on the burden line, not in a table elsewhere on the page. When teams split them, reviewers stop cross-checking.

Second, **assessor provenance must be visible on the plot itself.** Investigator and central reads disagree, and — critically for this product — they progress at different rates. A profile that silently shows one of them will eventually mislead someone.

---

## 4. Users and reading patterns

One layout, three reading patterns.

The **Medical Monitor / Clinical Scientist** is the primary user. They open the profile when a scan result arrives or before a cohort review, asking whether the observed change is real, drug-attributable and clinically meaningful. They read top-to-bottom once, then jump around, and they move rapidly from subject to subject.

The **Principal Investigator / treating physician** opens it at a decision point for one patient — a PD or iUPD call, a dose modification. They care about per-lesion trend, new-lesion status, and whether the derived response matches their clinical impression. They need it printable and unambiguous about assessment date and assessor.

The **Biostatistician / Data Manager** uses it as a data-quality instrument. Impossible sequences surface far more readily on this layout than in listings: a target lesion that vanishes from a visit without an NE record, an RS record with no supporting TR measurements, a nadir preceding baseline. The profile must therefore make missing and inconsistent data *visible* rather than interpolating over it.

A fourth, smaller role exists because this is a product: the **Study Configurator** — typically a statistical programmer or clinical data manager — who onboards a study by writing and validating its configuration. Their needs are covered in `04-study-configuration.md`.

---

## 5. Concept and recommendation

Three concepts were considered.

**Concept A — static one-page PDF profile per subject**, generated on a schedule and distributed as a pack. Cheap, trivially validated, works offline in a cohort review, and matches what CROs and regulators already expect. Fatal weakness: with no interaction there is no drill-down, so per-lesion detail either bloats the page or is lost, and the reviewer cannot re-scope the axis or switch assessor.

**Concept B — interactive single-subject review application** over the review layer, with a subject selector, linked bands, lesion-level drill-down, and a print/export path that emits the Concept A page. Costs more, but it is the only concept that satisfies "deeply watch the patient characteristics and any signal", because that need is inherently exploratory.

**Concept C — cohort-first dashboard with patient drill-through.** Excellent for "how is this dose level doing", but it inverts the priority: the individual patient becomes a destination rather than the entry point, and the per-patient view gets under-built.

**Recommendation: build Concept B, with Concept A as a first-class export and a thin slice of Concept C as the entry point.**

Concept B is the only option that meets the requirement, and the other two fall out of it cheaply rather than competing with it. The PDF is a rendering of the same page and costs one export path, which also yields the meeting-friendly and archive-friendly artefact without a second build. The cohort layer stays deliberately thin — a study picker and a subject picker enriched with a waterfall strip and best-response chips, enough to choose which patient to open and to place that patient in context. Building full cohort analytics now would consume the budget the per-lesion detail needs, and cohort analytics are already served by standard efficacy outputs.

Concretely: **do not start with the PDF and retrofit interactivity.** Teams that do end up with an interactive wrapper around a paper layout, and the per-lesion drill-down never fits.

---

## 6. Information architecture

Two screens. The picker exists to get to the profile; the profile is the product.

### Screen 1 — Study and subject picker

A study selector, then a subject table for the chosen study: subject ID, site, cohort/dose, on-study status, best overall response, best percent change, last assessment date and staleness, and open data-quality flag count. A compact waterfall strip above the table ranks subjects by best percent change so the reviewer can see where any subject sits before opening it. Filters on cohort, status, response and flags.

### Screen 2 — The profile

A fixed header and four bands. Bands 2 through 4 share one synchronised time axis; band 1 does not, because it is descriptive rather than longitudinal.

```
┌──────────────────────────────────────────────────────────────────────┐
│ HEADER   Study · Subject · Cohort/Dose · Status · Best Overall Resp.  │
│          Criteria in force · Data freshness · Assessor · Export       │
│          REVIEW-ONLY / UNVALIDATED badge — always present             │
├──────────────────────────────────────────────────────────────────────┤
│ BAND 1   PATIENT CHARACTERISTICS                    (no time axis)    │
│  1a Demographics & visit progress   1b Primary cancer history         │
│  1c Prior anti-cancer therapy       1d Surgery, radiotherapy, history │
├──────────────────────────────────────────────────────────────────────┤
│ BAND 2   DISPOSITION & EXPOSURE                     ── shared axis ── │
│  Swimmer: treatment period, cycles, dose level & modifications,       │
│  DLT window, assessment schedule vs. actual, discontinuation          │
├──────────────────────────────────────────────────────────────────────┤
│ BAND 3   TUMOR EVALUATION                           ── shared axis ── │
│  3a Burden curve: % change in SOD, nadir, criteria-derived rails,     │
│     timepoint response markers, assessor overlay                      │
│  3b Per-lesion trend: one row per lesion; non-target status rows;     │
│     new-lesion track                                                  │
│  3c Baseline lesion inventory                                         │
├──────────────────────────────────────────────────────────────────────┤
│ BAND 4   RELEVANT EVENTS                            ── shared axis ── │
│  AE lanes by grade, DLT/SAE markers, dose actions, concomitant        │
│  anti-cancer therapy and on-study radiotherapy                        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 7. Functional requirements

Priorities are **Must** (Phase 1), **Should** (Phase 2), **Could** (Phase 3). Requirements marked *(cfg)* are driven by study configuration.

### 7.1 Product-level — multi-study operation

| ID | Requirement | Priority |
|---|---|---|
| FR-P-01 | Support multiple studies concurrently in one deployment, each with its own configuration and its own review-layer build. | Must |
| FR-P-02 | Onboard a new study by adding a configuration file and pointing it at a data source — no application code change. | Must |
| FR-P-03 | Validate a study configuration on load against the published schema, and refuse to serve a study whose configuration fails validation, naming the offending keys. | Must |
| FR-P-04 | Display the configuration identity (name and content hash) in the profile footer and in every PDF export, so any output can be traced to the rules that produced it. | Must |
| FR-P-05 | Adapt the page to the study: hide bands, cards, controls and tracks for which the study collects no data, rather than rendering empty frames. | Must |
| FR-P-06 | Provide a configuration preview/lint tool that reports, for a candidate configuration and a data extract, which required domains and variables are missing or unpopulated. | Should |
| FR-P-07 | Support per-study display label overrides (treatment name, cohort naming, assessor labels) without code change. *(cfg)* | Should |

### 7.2 Header and global controls

| ID | Requirement | Priority |
|---|---|---|
| FR-H-01 | Display subject identity (USUBJID, site, screening number), cohort and dose level, and current on-study/on-treatment status. | Must |
| FR-H-02 | Display Best Overall Response with an explicit confirmed/unconfirmed indicator and the criteria set and version in force. | Must |
| FR-H-03 | **Display data freshness per domain**, not a single study-level timestamp: the as-of time of the last successful extract for each source domain, with a stale indicator against a configured threshold. Tumor data routinely lags safety data and the reviewer must see that. | Must |
| FR-H-04 | Display a persistent **REVIEW-ONLY / UNVALIDATED** badge on screen and on every exported page. It is never dismissible. | Must |
| FR-H-05 | Provide an assessor selector across the assessor set defined for the study, including an overlay mode. *(cfg)* | Must |
| FR-H-06 | Provide previous/next subject navigation preserving axis zoom, assessor selection and band state. | Should |
| FR-H-07 | Export the profile to PDF, and export the underlying subject-level data to CSV/XLSX. | Must |
| FR-H-08 | Provide a deep link to a specific subject, assessor and axis state, so a profile can be cited in an email or a meeting invitation. | Should |

### 7.3 Assessor model and read coverage

The study runs investigator and central reads that progress at different rates, because site EDC entry and central image reading are independent pipelines. The profile must make this explicit rather than let a reviewer mistake an unread scan for an unchanged patient. **This is the single most important correctness requirement in the product.**

| ID | Requirement | Priority |
|---|---|---|
| FR-A-01 | Model assessors as a configured list rather than a fixed pair, each with its own source, label and as-of timestamp. *(cfg)* | Must |
| FR-A-02 | For each assessor, display the **read coverage**: the latest timepoint for which that assessor has a complete assessment for this subject, and the count of assessments outstanding relative to the other assessor. | Must |
| FR-A-03 | Where the selected assessor's coverage ends before the subject's last performed assessment, render the uncovered span as an explicit "not yet read" region on the burden curve — visually distinct from both a gap and a not-evaluable timepoint. **An unread timepoint must never appear as a missing data point or as a flat line.** | Must |
| FR-A-04 | In overlay mode, draw both assessors on one axis with distinct line treatments, and mark every timepoint where the two assign different timepoint responses. | Must |
| FR-A-05 | Present a discordance summary for the subject: count and list of timepoints where investigator and central responses differ, including differing BOR. | Should |
| FR-A-06 | Never derive a cross-assessor "consensus" or blended value. Each assessor's series is derived independently end to end, including its own baseline and nadir. | Must |
| FR-A-07 | Where a study population differs by assessor (a subject read by one and not the other), reflect that in the subject picker rather than hiding the subject. | Must |

### 7.4 Band 1 — Patient characteristics

| ID | Requirement | Priority |
|---|---|---|
| FR-1-01 | Demographics: age at consent, sex, race/ethnicity as collected, country and site, weight/BSA, baseline performance status (scale per configuration). *(cfg)* | Must |
| FR-1-02 | Visit progress and ongoing status: current cycle/visit, days on treatment, days on study, and the next scheduled tumor assessment window with an overdue flag computed from the configured schedule. *(cfg)* | Must |
| FR-1-03 | Primary cancer history: tumor type and histology, date of initial diagnosis, stage at diagnosis and at entry, biomarker/mutation status, and baseline sites of metastatic disease. | Must |
| FR-1-04 | Prior anti-cancer therapy as an ordered list of lines: agent/regimen, start and stop dates, cycles, best response to that line, reason for discontinuation. | Must |
| FR-1-05 | Prior surgical history relevant to the malignancy: procedure, date, intent. | Must |
| FR-1-06 | Prior radiotherapy: site, dose/fractions where collected, dates — **and an explicit flag where an irradiated site coincides with a lesion selected for follow-up**, since shrinkage there may not be drug-attributable. | Must |
| FR-1-07 | Other medical history, filtered by configured relevance rules, with the full history on expand. *(cfg)* | Should |
| FR-1-08 | Derived context: time since diagnosis and number of prior lines. | Should |

### 7.5 Band 2 — Disposition and exposure

| ID | Requirement | Priority |
|---|---|---|
| FR-2-01 | Render treatment exposure from first to last dose (or to the data cut, marked ongoing) on the shared axis. | Must |
| FR-2-02 | Mark cycle boundaries from the configured cycle length, and render dose level per cycle including reductions, interruptions and omitted doses, with the dose labelled. *(cfg)* | Must |
| FR-2-03 | Mark end of treatment and end of study with the recorded reason. | Must |
| FR-2-04 | Mark every protocol-scheduled tumor assessment (from the configured schedule) and every actual assessment, so missed and out-of-window scans are visible as gaps. *(cfg)* | Must |
| FR-2-05 | Where the study defines one, mark the DLT observation window and any DLT-qualifying event. *(cfg)* | Must |
| FR-2-06 | Show survival follow-up status after discontinuation where collected. | Should |

### 7.6 Band 3 — Tumor identification and evaluation

| ID | Requirement | Priority |
|---|---|---|
| FR-3-01 | Baseline lesion inventory: lesion ID, anatomical site, laterality, target/non-target classification, measurement method, and baseline measurement with its measurement type (long axis, short axis). | Must |
| FR-3-02 | Display baseline SOD and target-lesion count, with a non-blocking warning where the configured lesion limits are exceeded. *(cfg)* | Must |
| FR-3-03 | Burden curve: percent change in SOD from baseline at every evaluable timepoint on the shared axis. | Must |
| FR-3-04 | Draw criteria-derived reference rails (PR and PD thresholds from configuration) and the nadir as an explicit labelled reference. *(cfg)* | Must |
| FR-3-05 | Toggle between percent change from baseline and from nadir, because response is defined against baseline while progression is defined against nadir. | Must |
| FR-3-06 | Offer an absolute-SOD view, since the minimum absolute increase rule governs when baseline burden is small. | Must |
| FR-3-07 | Mark each timepoint with its derived response, visually distinguishing confirmed from unconfirmed. | Must |
| FR-3-08 | Per-lesion trend: one row per target lesion showing that lesion's measurement over time as a sparkline and a change heat strip. | Must |
| FR-3-09 | Non-target lesions as status rows over time, not measurements. | Must |
| FR-3-10 | New lesions as an explicit track: first-observed date, site, equivocal status, and confirmation status. A new lesion must be unmissable, since it forces PD independent of SOD. | Must |
| FR-3-11 | Every derived value exposes its inputs on interaction — contributing lesion measurements, assessment date, assessor, and the configuration values applied. | Must |
| FR-3-12 | Make data quality explicit: not-evaluable lesions, missing visits, and method changes are flagged, never silently interpolated. **The burden curve is broken, not interpolated, across a non-evaluable or unread timepoint.** | Must |
| FR-3-13 | Where the study configures iRECIST, support iUPD and iCPD as distinct states, the configured confirmation window, and the reset behaviour after pseudoprogression, including repeated iUPD episodes. *(cfg)* | Must |
| FR-3-14 | Cohort context: faint background traces for other subjects in the same cohort, and the subject's position in the cohort waterfall. | Should |
| FR-3-15 | Optional additional longitudinal rows on the same axis where the study collects them — tumor markers, ctDNA. *(cfg)* | Could |

### 7.7 Band 4 — Relevant events

| ID | Requirement | Priority |
|---|---|---|
| FR-4-01 | Adverse events as time-spanning bars encoded by maximum grade, with seriousness marked distinctly. | Must |
| FR-4-02 | Group AEs by SOC or a configured AESI grouping, collapsible to a summary lane. *(cfg)* | Must |
| FR-4-03 | Flag DLTs, SAEs, AEs leading to dose modification, and AEs leading to discontinuation. | Must |
| FR-4-04 | Show causality and action taken as recorded. | Must |
| FR-4-05 | Show concomitant anti-cancer medication and on-study radiotherapy, because both confound response attribution. | Must |
| FR-4-06 | On interaction, show verbatim term, preferred term, dates, grade, seriousness, causality, action taken and outcome. | Must |
| FR-4-07 | Default to a configured clinical-relevance filter, with the full listing on expand. *(cfg)* | Should |

### 7.8 Cross-band interaction

| ID | Requirement | Priority |
|---|---|---|
| FR-X-01 | Zoom and pan apply simultaneously to all time-based bands; they never desynchronise. | Must |
| FR-X-02 | A hover draws a crosshair across all time-based bands so concurrent events are read off directly. | Must |
| FR-X-03 | Selecting a lesion row highlights its contribution in the burden curve and inventory. | Should |
| FR-X-04 | The axis supports study day, calendar date and a cycle-relative mode. | Should |
| FR-X-05 | Any point on any band links out to the corresponding record in the full patient profile or source listing. | Should |

---

## 8. Non-functional requirements

**Unvalidated posture, stated everywhere.** Because the tool reads a near-live review layer and computes its own derivations, every value it shows is review-only output. The badge is persistent on screen, printed in the footer of every PDF page, and repeated in the header row of every data export. No output may leave the application without it. The product must never present itself as a source of endpoint values.

**Reconciliation against ADaM.** Non-GxP does not mean unchecked. Where a study has ADaM available, the application must offer a reconciliation view comparing its own derived timepoint responses, SOD and BOR against `ADTR`/`ADRS`, listing every subject and timepoint that differs. This is the mechanism that keeps an unvalidated tool honest, and it is also the fastest way to find genuine data issues. It is a **Must** for any study where ADaM exists.

**Data freshness.** Per-domain as-of timestamps, surfaced in the header (FR-H-03). A profile that cannot state when each of its domains was extracted must not render.

**Derivation isolation.** Derivations live in one documented, independently testable layer, never in presentation code. The engine is covered by unit tests built from the published worked examples in the criteria guidelines, plus regression tests per study configuration.

**Access and audit.** Company SSO; a single reviewer role with access to all sites and all studies, plus a configurator role that may edit study configurations. Even with uniform access, subject-level oncology data is highly identifying, so the application logs who viewed which subject and when, and who changed which configuration. The log is operational, not a GxP audit trail, and should be described as such.

**Blinding.** Uniform access does not imply unblinded access. Where a study is blinded, treatment assignment is withheld from the profile entirely and the configuration declares this; an unblinding decision is a configuration change with its own approval, not a UI toggle.

**Performance.** A profile renders in under two seconds from subject selection, including all bands. This is achievable only if derivations are precomputed at review-layer build time rather than per request.

**Print fidelity.** The PDF export is a paginated rendering of the same bands with the axis intact — not a screenshot — carrying the review-only badge, the data-freshness stamp, the assessor selection and the configuration hash in the footer of every page.

**Accessibility.** No distinction is carried by colour alone; response categories, AE grades, confirmation status and evaluability all carry redundant shape, position or label. Contrast holds in light and dark rendering.

---

## 9. Delivery phasing

**Phase 1 — the reasoning surface, one study onboarded.** Configuration schema and loader; review-layer build for one study; study/subject picker; header with freshness and the review-only badge; bands 1, 2, 3a, 3c and 4 with the relevance filter; shared axis and crosshair; RECIST 1.1 derivation engine with the confirmation policy; assessor selection with read-coverage display; PDF export. This alone answers the question teams are asking today.

**Phase 2 — depth and honesty.** Band 3b per-lesion trends, non-target and new-lesion tracks, full drill-down from every derived value, nadir-referenced view, data-quality flagging, iRECIST state handling, assessor overlay with discordance, and the ADaM reconciliation view. This is what differentiates the TEP from a generic profile; it should not slip past Phase 2.

**Phase 3 — breadth and comfort.** Cohort background traces and waterfall position, cycle-relative axis, configuration lint tooling, deep links, additional longitudinal modality rows, and the second and third studies onboarded as a genuine test of the configuration schema.

**A note on sequencing.** Onboard the second study before Phase 2 is complete, not after. The configuration schema is the product's central claim, and the only way to find out whether it holds is to point it at a study it was not designed around.

---

## 10. Decisions taken

| # | Decision | Consequence |
|---|---|---|
| 1 | **Source layer:** near-live SDTM-derived review layer, not ADaM | Faster data, own derivation engine required, reconciliation view becomes a Must |
| 2 | **Validation posture:** review-only, non-GxP | Persistent unvalidated badge; no decision-of-record use; operational access log rather than a Part 11 audit trail |
| 3 | **Assessor model:** investigator and central reads, differing populations and progress | Read-coverage modelling (FR-A-01…07) is a core requirement, not a refinement |
| 4 | **Criteria:** RECIST 1.1 and iRECIST, selected per study by configuration | Criteria-neutral lesion storage; only these two get derivation specs |
| 5 | **Confirmation policy:** configurable per protocol, including the required interval | Confirmation is an engine parameter; BOR is always labelled confirmed or unconfirmed |
| 6 | **Deployment:** company-internal web app plus PDF export; all users see all sites | Single reviewer role; no site-level authorisation; view logging retained for traceability |

## 11. Remaining open questions

1. Where does the SDTM extract come from — a clinical data repository, a nightly EDC-to-SDTM conversion, or per-study programmer-run jobs? This determines refresh cadence and who owns breakage.
2. What is the acceptable staleness threshold per domain before the header flags the study as stale?
3. Is the central read delivered as SDTM `RS`/`TR` records, or as a vendor-format file needing its own mapping?
4. Who owns study configurations — the study programmer, a central standards group, or the medical monitor? This determines whether the configuration editor is a file in version control or an in-app form.
