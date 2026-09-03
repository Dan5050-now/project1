# Tumor Evaluation Profile (TEP) — Concept & Requirements

**Status:** Draft v0.1 for team review
**Scope:** Individual-patient tumor-response review for an ongoing early-phase (Ph1/1b) oncology trial
**Data basis:** CDISC SDTM (TU / TR / RS + safety domains) and ADaM (ADSL / ADTR / ADRS / ADAE), response derived per RECIST 1.1
**Companion documents:** `02-data-model-and-derivations.md`, `03-visual-and-interaction-spec.md`

---

## 1. Why this is not "just another patient profile"

A conventional patient profile answers the question *"what happened to this subject?"* It is organised by CRF domain, it is exhaustive, and it is usually consumed as a static PDF during signal detection or at database lock. That format is optimised for completeness and traceability, not for judgement.

The question your team is actually asking is different. In an early-phase study, with a handful of subjects per dose level and no control arm, the team is trying to decide whether *this* patient moved because of the drug. Answering that requires holding four things in the head at once: how much tumor the patient started with, how that burden moved over time, what the patient's disease and treatment history predicted they would do, and what else was happening to them (toxicity, dose modification, concomitant therapy) at the moment the tumor moved. A domain-ordered profile forces the reviewer to assemble that mental picture manually, page by page, and the assembly is where signal gets lost.

The Tumor Evaluation Profile is therefore defined by a deliberate narrowing: **one subject, one shared time axis, and only the data that bears on interpreting tumor response.** Everything that does not help interpret the burden curve is either removed or pushed one click away. The profile is a *reasoning surface*, not an archive — the archive still exists as the standard patient profile, and the TEP links out to it.

Three design consequences follow from that framing, and they should be treated as non-negotiable:

1. **The time axis is the spine.** Every band in the report is drawn against the same study-day axis, so vertical alignment carries meaning. A grade 3 AE that sits directly under a scan showing a 40% shrink is a finding the reviewer sees without being told to look.
2. **The derived response is never shown without its inputs.** A reviewer who sees "PR" and cannot immediately see the sum-of-diameters that produced it will not trust the report. Every derived value must be one interaction away from the per-lesion measurements behind it.
3. **Per-lesion behaviour is first-class.** Aggregate SOD hides heterogeneous response — the case where four lesions shrink and one grows is precisely the signal an early-phase team wants. Most commercial profiles stop at the SOD line; this one must not.

---

## 2. What outside practice already establishes

The visual grammar for tumor response in oncology trials is mature and largely settled. Rather than invent, the TEP should assemble known-good components and make them interoperate on one page.

| Established artefact | What it answers | Where it belongs in the TEP |
|---|---|---|
| **Spider / longitudinal plot** — % change in sum of diameters vs. time, one line per subject | How did burden move, and when? | Core burden band, reduced to *this* subject with the cohort drawn behind as faint context |
| **Waterfall plot** — best % change per subject, ranked | How does this subject compare to the cohort? | Cohort context only — a single highlighted bar showing where this subject sits |
| **Swimmer plot** — treatment duration bar with response and event markers | How durable was the response, and is the subject still on treatment? | The disposition/exposure band at the top of the time axis |
| **cBioPortal-style event timeline** — stacked tracks (specimen, imaging, treatment, lab) on one axis | What else was happening at that moment? | The structural pattern for the whole page: parallel tracks, one axis |
| **CDISC TU/TR/RS linkage via `--LNKID` / `--LNKGRP`** | Which measurement produced which response? | The traceability model — drill-down from RS back to TR back to TU |
| **`teal` / pharmaverse patient-profile modules** | A working reference for filter-panel + linked-module review apps on CDISC data | Architectural precedent for the interactive build |

Two lessons from that body of practice are worth stating explicitly, because they are the ones teams most often get wrong.

First, **response labels and measurement data must be visually separable but spatially adjacent.** In published spider plots the response category is carried as a marker on the burden line, not as a separate table elsewhere on the page. When teams split them, reviewers stop cross-checking.

Second, **assessor provenance must be visible on the plot itself.** In early-phase studies the investigator assessment and any central/BICR read can disagree, and a profile that silently shows one of them will eventually mislead someone. The burden band needs an explicit assessor selector, and where two assessments exist the profile should be able to show both.

---

## 3. Users and what each of them needs from the page

The TEP has one layout but three reading patterns, and the requirements below are shaped by all three.

The **Medical Monitor / Clinical Scientist** is the primary user. They open the profile when a scan result arrives or before a cohort review, and they are asking whether the observed change is real, drug-attributable, and clinically meaningful. They need the burden curve, the per-lesion detail, the concurrent AE and dose-modification context, and enough history to know what the patient's baseline prognosis was. They read the page top-to-bottom once, then jump around.

The **Principal Investigator / treating physician** opens the profile in the context of a single patient's continued treatment — typically at an iUPD/PD decision point or a dose-modification discussion. They care most about the per-lesion trend, new-lesion status, and whether the derived response matches their clinical impression. They need the profile to be printable and to be unambiguous about assessment date and assessor.

The **Biostatistician / Data Manager** uses the profile as a data-quality instrument. Impossible sequences — a target lesion that disappears from a visit without being recorded as "not evaluable", an RS record with no supporting TR measurements, a nadir that precedes baseline — surface far more readily on this layout than in listings. The profile should therefore make missing and inconsistent data *visible* rather than silently interpolating over it.

---

## 4. Concept options and the recommendation

Three concepts were considered.

**Concept A — Static one-page PDF profile per subject.** Generated from ADaM on a scheduled run, distributed as a PDF pack. It is cheap, it is trivially validated, it works offline in a cohort review meeting, and it is the format regulators and most CROs already expect. Its weakness is fatal for your stated need: with no interaction there is no drill-down, so per-lesion detail either bloats the page or is lost, and the reviewer cannot re-scope the time axis or switch assessor.

**Concept B — Interactive single-subject review application.** A web application over ADaM (or a curated review layer) with a subject selector, linked bands, drill-down to lesion level, and a print/export path that emits the Concept A page. It costs more and needs a validation story, but it is the only concept that satisfies "deeply watch the patient characteristics and any signal", because that need is inherently exploratory.

**Concept C — Cohort-first dashboard with patient drill-through.** Waterfall and swimmer at the study level, click a bar to open the subject. Excellent for the "how is the dose level doing overall" question, but it inverts your stated priority: the individual patient is the destination, not the entry point, and the per-patient view tends to get under-built.

**Recommendation: build Concept B, with Concept A as a first-class export and a thin slice of Concept C as the entry point.**

The reasoning is that Concept B is the only option that meets the actual requirement, and the other two fall out of it cheaply rather than competing with it. The static PDF is a rendering of the same page and costs one export path, which also gives you the regulator-friendly and meeting-friendly artefact without a second build. The cohort layer is deliberately kept thin — a subject picker enriched with a waterfall strip and best-response chips, enough to choose *which* patient to open and to place that patient in context, and no more. Building the full cohort analytics layer now would consume the budget that the per-lesion detail needs, and cohort analytics are already served by your standard efficacy outputs.

Concretely: **do not start with the PDF and retrofit interactivity.** Teams that do end up with an interactive wrapper around a page layout that was designed for paper, and the per-lesion drill-down never fits.

---

## 5. Information architecture — the four bands

The profile is one scrolling page composed of a fixed header and four bands. Bands 2 through 4 share a single, synchronised study-day axis; band 1 does not, because it is descriptive rather than longitudinal.

```
┌──────────────────────────────────────────────────────────────────────┐
│ HEADER   Subject ID · Cohort/Dose · Arm · Status · Best Overall Resp. │
│          Data cut date · Assessor toggle (INV / BICR) · Export        │
├──────────────────────────────────────────────────────────────────────┤
│ BAND 1   PATIENT CHARACTERISTICS                    (no time axis)    │
│  1a Demographics & baseline status  1b Primary cancer history         │
│  1c Prior anti-cancer therapy       1d Relevant medical history       │
├──────────────────────────────────────────────────────────────────────┤
│ BAND 2   DISPOSITION & EXPOSURE                     ── shared axis ── │
│  Swimmer bar: treatment period, cycles, dose level & modifications,   │
│  visit progress, on-study status, discontinuation reason              │
├──────────────────────────────────────────────────────────────────────┤
│ BAND 3   TUMOR EVALUATION                           ── shared axis ── │
│  3a Burden curve: % change in SOD from baseline, nadir reference,     │
│     ±20% / −30% threshold rails, timepoint response markers           │
│  3b Per-lesion trend: one row per target lesion, small-multiple       │
│     sparklines + heat strip; non-target and new lesions as status rows│
│  3c Baseline lesion inventory table (site, method, measurability)     │
├──────────────────────────────────────────────────────────────────────┤
│ BAND 4   RELEVANT EVENTS                            ── shared axis ── │
│  AE lanes by grade/seriousness, DLT flag, dose interruptions,         │
│  concomitant anti-cancer medication, and study-specific events        │
└──────────────────────────────────────────────────────────────────────┘
```

The header is sticky. Everything below it scrolls, and the shared axis stays registered across bands 2–4 under zoom and pan.

---

## 6. Functional requirements

### 6.1 Header and global controls

| ID | Requirement | Priority |
|---|---|---|
| FR-H-01 | Display subject identity (USUBJID, site, screening/randomisation number), cohort and assigned dose level, and current on-study/on-treatment status. | Must |
| FR-H-02 | Display Best Overall Response (BOR) with an explicit indicator of whether it is confirmed, and the criteria version applied (RECIST 1.1 / iRECIST). | Must |
| FR-H-03 | Display the data cut / extract timestamp and the source (e.g. SDTM build, ADaM build, or live EDC read). No profile may be shown without a visible data currency stamp. | Must |
| FR-H-04 | Provide an assessor toggle (Investigator / Independent review), and where both exist, an overlay mode showing both on the burden curve. | Must |
| FR-H-05 | Provide previous/next subject navigation that preserves the current axis zoom, assessor selection, and band collapse state. | Should |
| FR-H-06 | Provide export to PDF (the Concept A page) and export of the underlying subject-level data to CSV/XLSX. | Must |
| FR-H-07 | Respect study blinding: where the study is blinded, treatment assignment must not be rendered for unblinded-restricted roles. | Must |

### 6.2 Band 1 — Patient characteristics

| ID | Requirement | Priority |
|---|---|---|
| FR-1-01 | Demographics: age at consent, sex, race/ethnicity as collected, country/site, weight/BSA, and baseline ECOG performance status. | Must |
| FR-1-02 | Visit progress and ongoing status: current cycle/visit, days on treatment, days on study, and next scheduled tumor assessment window with an overdue flag. | Must |
| FR-1-03 | Primary cancer history: primary tumor type and histology, date of initial diagnosis, stage at diagnosis and at study entry, relevant biomarker/mutation status, and sites of metastatic disease at baseline. | Must |
| FR-1-04 | Prior anti-cancer therapy, presented as an ordered list of lines with agent/regimen, start and stop dates, number of cycles, best response to that line, and reason for discontinuation. | Must |
| FR-1-05 | Prior surgical history relevant to the malignancy, with procedure, date, and intent (curative/palliative/diagnostic). | Must |
| FR-1-06 | Prior radiotherapy, with anatomical site, dose/fractions where collected, and dates — and an explicit visual link where an irradiated site coincides with a lesion selected for follow-up. | Must |
| FR-1-07 | Other medical history filtered to conditions plausibly interacting with response interpretation or toxicity attribution; full medical history available on expand. | Should |
| FR-1-08 | Derive and display a "time since diagnosis" and "number of prior lines" summary, since both are routinely used as prognostic context in early-phase review. | Should |

### 6.3 Band 2 — Disposition and exposure

| ID | Requirement | Priority |
|---|---|---|
| FR-2-01 | Render treatment exposure as a horizontal bar from first dose to last dose (or to data cut, marked as ongoing) on the shared axis. | Must |
| FR-2-02 | Mark cycle boundaries, and render dose level per cycle including reductions, interruptions, and omitted doses, with the dose value labelled. | Must |
| FR-2-03 | Mark end-of-treatment and end-of-study with the recorded reason (progression, toxicity, withdrawal, death, other). | Must |
| FR-2-04 | Mark every protocol-scheduled tumor assessment visit and every actual assessment performed, so that missed or out-of-window scans are visible as gaps. | Must |
| FR-2-05 | Mark the DLT observation window and any DLT-qualifying event, since this is the defining decision object of dose escalation. | Must |
| FR-2-06 | Show survival follow-up status after treatment discontinuation where collected. | Should |

### 6.4 Band 3 — Tumor identification and evaluation

This is the core of the report and the section where most implementations under-deliver.

| ID | Requirement | Priority |
|---|---|---|
| FR-3-01 | Baseline lesion inventory: for every lesion identified at baseline, show lesion ID, anatomical site/location, laterality, whether target or non-target, measurement method (CT/MRI/clinical/photograph), and baseline diameter (short axis for nodal lesions). | Must |
| FR-3-02 | Explicitly display the baseline sum of diameters (SOD) and the count of target lesions, with a validity check against RECIST 1.1 limits (≤5 total, ≤2 per organ) surfaced as a warning, not a blocker. | Must |
| FR-3-03 | Burden curve: plot percent change in SOD from baseline at every evaluable timepoint, on the shared axis. | Must |
| FR-3-04 | Draw reference rails at −30% (PR threshold) and +20% (PD threshold), and draw the nadir as an explicit reference line with its value and date labelled. | Must |
| FR-3-05 | Offer a toggle between "% change from baseline" and "% change from nadir", because PD is defined against nadir and reviewers must be able to see the operative comparator. | Must |
| FR-3-06 | Also offer an absolute-SOD (mm) view of the same curve, since absolute change matters when baseline burden is small and the ≥5 mm absolute rule governs. | Must |
| FR-3-07 | Mark each timepoint on the curve with its derived timepoint response (CR/PR/SD/PD/NE), visually distinguishing confirmed from unconfirmed responses. | Must |
| FR-3-08 | Per-lesion trend: render one row per target lesion showing that lesion's diameter over time — as a sparkline, a heat strip of % change, or both — so heterogeneous response is directly visible. | Must |
| FR-3-09 | Render non-target lesions as status rows over time (present / absent / unequivocal progression / not evaluable) rather than as measurements. | Must |
| FR-3-10 | Render new lesions as an explicit track: date first observed, site, whether equivocal, and whether subsequently confirmed. A new lesion must be visually unmissable, since it forces PD independent of SOD. | Must |
| FR-3-11 | Every derived value (SOD, % change, timepoint response, BOR) must expose its inputs on hover/click — the contributing lesion measurements, the assessment date, and the assessor. | Must |
| FR-3-12 | Show data quality explicitly: not-evaluable lesions, missing visits, and lesions measured by a different method than baseline must be flagged rather than silently interpolated. Never connect the burden curve across a non-evaluable timepoint without indicating the gap. | Must |
| FR-3-13 | Where the study uses iRECIST, support iUPD/iCPD state, the confirmation window (4–8 weeks), and the "reset" behaviour after pseudoprogression — rendered as a distinct state on the curve. | Should (Must if the asset is an immunotherapy) |
| FR-3-14 | Cohort context: draw the other subjects in the same dose level as faint background traces on the burden curve, and show the subject's position in a compact cohort waterfall. | Should |
| FR-3-15 | Support non-RECIST assessment modalities where the study collects them (e.g. tumor markers, ctDNA, bone-lesion assessment) as optional additional rows on the same axis. | Could |

### 6.5 Band 4 — Relevant events

| ID | Requirement | Priority |
|---|---|---|
| FR-4-01 | Render adverse events as time-spanning bars on the shared axis, encoded by maximum severity grade (CTCAE) with seriousness marked distinctly. | Must |
| FR-4-02 | Group AEs by SOC or by a study-defined AE of special interest (AESI) grouping, collapsible to a summary lane. | Must |
| FR-4-03 | Flag DLTs, SAEs, AEs leading to dose modification, and AEs leading to discontinuation with dedicated markers. | Must |
| FR-4-04 | Show causality/relatedness as recorded, and treatment action taken. | Must |
| FR-4-05 | Show concomitant anti-cancer medication and any palliative radiotherapy given on study, because both confound response attribution. | Must |
| FR-4-06 | On hover, show the AE verbatim term, preferred term, start/stop, grade, seriousness, causality, action taken, and outcome. | Must |
| FR-4-07 | Support a "clinically relevant only" filter (grade ≥3, serious, AESI, or related) as the default view, with full AE listing on expand. | Should |

### 6.6 Cross-band interaction

| ID | Requirement | Priority |
|---|---|---|
| FR-X-01 | Zoom and pan on the time axis apply simultaneously to bands 2, 3, and 4; the bands never desynchronise. | Must |
| FR-X-02 | A hover anywhere on the axis draws a vertical crosshair across all time-based bands, so concurrent events are read off directly. | Must |
| FR-X-03 | Selecting a lesion row highlights that lesion's contribution in the burden curve and in the baseline inventory table. | Should |
| FR-X-04 | The axis supports both study day and calendar date, and a cycle-relative mode where cycle boundaries become the tick marks. | Should |
| FR-X-05 | Any point on any band links out to the corresponding record in the full patient profile / source listing. | Should |

---

## 7. Non-functional requirements

**Data currency and provenance.** Every profile carries a visible data cut timestamp and names its source layer. If the application reads from a live or near-live layer, the staleness of each domain must be individually visible, because tumor data typically lags safety data. A profile that cannot state when its data was extracted must not render.

**Traceability and validation.** Because the report derives response, it is producing analysis-adjacent output. Derivations must live in one documented, testable layer — not in the presentation code — and must be independently verifiable against the study's ADaM. The recommended posture is that the application *displays* ADRS/ADTR-derived values when ADaM exists and only computes its own derivation for a pre-ADaM review layer, in which case the computed values must be clearly badged as unvalidated review-only output. This distinction should be visible on screen.

**Blinding and access control.** Role-based access must gate treatment assignment in blinded studies, and the audit trail must record who viewed which subject, since patient-level oncology data is highly identifying.

**Regulatory posture.** If the output is used for decision-making or submitted, it falls under 21 CFR Part 11 expectations for audit trail, access control, and record integrity, and the derivation layer requires validation documentation. Decide early whether the tool is "review-only, non-GxP" or "validated" — the cost difference is large and it drives architecture.

**Performance.** A subject profile should render in under two seconds from selection, including all bands, since the review pattern is rapid subject-to-subject scanning.

**Print fidelity.** The PDF export must be a faithful, single-subject, paginated rendering with all bands present and the axis intact — not a screenshot.

**Accessibility.** Response categories and AE grades must not be encoded by colour alone; shape, position, or label must carry the same information, and the palette must be checked for the common colour-vision deficiencies. Contrast must hold in both light and dark rendering.

---

## 8. Suggested delivery phasing

**Phase 1 — MVP (the reasoning surface).** Header, band 1, band 2, band 3a (burden curve with rails and nadir), band 3c (baseline inventory), band 4 with the clinically-relevant filter, shared axis with crosshair, and PDF export. Read from ADaM if it exists, otherwise from a curated review layer built off SDTM TU/TR/RS. This phase alone answers the question the team is asking today.

**Phase 2 — per-lesion depth.** Band 3b per-lesion trends, non-target and new-lesion tracks, full drill-down from every derived value to its inputs, nadir-referenced view, and the data-quality flagging. This is what differentiates the TEP from a generic profile and it should not be deferred past phase 2.

**Phase 3 — context and criteria breadth.** Cohort background traces and waterfall position, iRECIST state handling, assessor overlay (INV vs BICR), cycle-relative axis, and non-RECIST modality rows.

---

## 9. Open decisions the team needs to make

These are the questions that will change the build, listed so they can be resolved before Phase 1 starts.

1. **Source layer:** does the tool read validated ADaM (slower, authoritative) or a near-live SDTM-derived review layer (faster, unvalidated)? This is the single biggest architectural fork.
2. **Validation posture:** review-only non-GxP, or validated for decision-making? Determines the audit and documentation burden.
3. **Assessor model:** is there a central/BICR read in this study, and if so is it available to the same review population as the investigator read?
4. **Criteria set:** RECIST 1.1 only, or is iRECIST (or a disease-specific criterion such as Lugano, RANO, PCWG3) in the protocol? Confirm before designing the response state machine.
5. **Confirmation policy:** does the protocol require confirmatory scans for CR/PR, and at what interval? This changes how BOR is derived and displayed.
6. **Deployment and identifiability:** where does this run, and who may see subject-level data across sites?
