# TEP — Data Model and Derivation Specification

This annex defines where each element of the profile comes from and how every derived value is computed. The application reads a **near-live SDTM-derived review layer** and computes its own derivations; ADaM, where it exists, is used for reconciliation rather than as the source. Criteria supported are RECIST 1.1 and iRECIST, selected per study by configuration (`04-study-configuration.md`).

---

## 1. The review layer

### 1.1 What it is

The review layer is a per-study, per-assessor set of derived tables built on a schedule from the current SDTM extract. It is not a database of record and it is never edited by hand. Its job is to move every expensive derivation out of request time, so a profile renders in under two seconds, and to give the application one stable shape regardless of a study's SDTM quirks.

```
SDTM extract  ──►  mapping (config overrides)  ──►  criteria engine  ──►  review layer  ──►  app
   (CDR/EDC)                                          (per assessor)        (columnar)
```

### 1.2 Tables

| Table | Grain | Contents |
|---|---|---|
| `rl_subject` | one row per subject | identity, cohort, arm, demographics, disposition, derived context (time since diagnosis, prior lines), per-assessor BOR and best change |
| `rl_lesion` | one row per subject × lesion | lesion identity, classification, site, method, measurement type, first-observed timepoint, criteria-neutral (see §1.3) |
| `rl_measurement` | one row per subject × assessor × timepoint × lesion | the measurement or qualitative status, evaluability, method used at that visit |
| `rl_timepoint` | one row per subject × assessor × timepoint | SOD, change metrics, sub-responses, overall response, confirmation state, applied-parameter snapshot |
| `rl_event` | one row per subject × event | AEs, dose records, con-meds, radiotherapy, disposition events — a single long table on the shared axis |
| `rl_coverage` | one row per subject × assessor | last covered timepoint, outstanding count, as-of timestamp |
| `rl_flag` | one row per subject × check × object | data-quality findings (§5) |
| `rl_freshness` | one row per domain | extract as-of timestamp, row count, staleness state |

Every table carries `study_id` and the configuration hash under which it was built, so a stale build cannot be served against a changed configuration without detection.

### 1.3 Criteria-neutral lesion storage

The lesion and measurement tables deliberately do **not** assume one diameter per lesion. `rl_measurement` stores `value`, `unit` and `measure_type` (`LONG_AXIS`, `SHORT_AXIS`, `QUALITATIVE`, and room for others), with the criteria module deciding which measure type contributes to the burden statistic.

RECIST 1.1 and iRECIST are the only criteria specified in this document. The storage shape above costs nothing extra today and is what makes a later addition — a criterion using bidimensional products, PET uptake scores, or lesion counts — a new module rather than a data migration. **This is a storage decision only; no plugin framework is being built.**

---

## 2. Source mapping

Where an override is configured (`mappings.overrides`), it replaces the standard location below. Everything else reads from standard SDTM.

### Band 1 — Patient characteristics

| Element | SDTM | Key variables |
|---|---|---|
| Demographics | `DM` | `AGE`, `SEX`, `RACE`, `ETHNIC`, `COUNTRY`, `SITEID`, `ARM`/`ACTARM` |
| Performance status, weight/BSA | `RS`/`QS`, `VS` | per `characteristics.performance_status.source` |
| Visit progress, disposition | `SV`, `DS` | `SVSTDTC`, `DSDECOD`, `DSTERM`, `DSSTDTC` |
| Primary cancer history, staging | `MH` (+`SUPPMH`) | `MHCAT`, `MHDECOD`, `MHSTDTC`; stage commonly in `SUPPMH` |
| Biomarkers | `LB`/`FA` | per `characteristics.biomarkers` |
| Metastatic sites at baseline | `MH`, `TU` | `TULOC`, `MHTERM` |
| Prior anti-cancer therapy | `CM` (+`SUPPCM`) | `CMTRT`, `CMSTDTC`, `CMENDTC`, `CMCAT`; best response commonly in `SUPPCM` |
| Prior surgery | `PR` | `PRTRT`, `PRSTDTC`, `PRCAT` |
| Prior radiotherapy | `PR` | `PRTRT`, `PRLOC`, `PRDOSE`, `PRSTDTC`, `PRENDTC` |
| Medical history | `MH` | `MHDECOD`, `MHBODSYS`, `MHSTDTC` |

### Band 2 — Disposition and exposure

| Element | SDTM | Key variables |
|---|---|---|
| Exposure and cycles | `EX` | `EXTRT`, `EXDOSE`, `EXDOSU`, `EXSTDTC`, `EXENDTC`, `VISIT`, `EPOCH` |
| Dose modifications | `EX` (+`SUPPEX`), `AE` | `EXADJ`, `AEACN` |
| Visit schedule / actual | `TV`, `SV` | `VISITNUM`, `VISITDY`, `SVSTDTC` |
| Discontinuation | `DS` | `DSDECOD`, `DSSTDTC` |
| DLT events | `AE` (+`SUPPAE`) | per `treatment.dlt.ae_flag_variable` |
| Survival follow-up | `DS`, `SS` | `SSSTRESC`, `DTHDTC` |

### Band 3 — Tumor evaluation

This is the CDISC oncology tumor package. The three domains are chained, and the chain is what makes drill-down possible.

| Element | SDTM | Key variables |
|---|---|---|
| Lesion identification | `TU` | `TULNKID`, `TUTESTCD`, `TUORRES` (TARGET / NON-TARGET / NEW), `TULOC`, `TULAT`, `TUMETHOD`, `TUDTC`, `TUEVAL` |
| Lesion measurements | `TR` | `TRLNKID`, `TRLNKGRP`, `TRTESTCD` (`LDIAM`, `SAXIS`, …), `TRSTRESN`, `TRORRES`, `TREVAL`, `TRMETHOD`, `TRDTC`, `VISITNUM` |
| Timepoint / overall response as recorded | `RS` | `RSLNKGRP`, `RSTESTCD` (`TRGRESP`, `NTRGRESP`, `OVRLRESP`), `RSORRES`, `RSSTRESC`, `RSEVAL`, `RSDTC` |

**The linkage model.** `TU` assigns each lesion a `TULNKID`. `TR` records carry the matching `TRLNKID`, attributing a measurement to a lesion, and carry `TRLNKGRP`, grouping all measurements in one assessment. `RS` carries the matching `RSLNKGRP`, attributing a response to the measurements that produced it. Drill-down (FR-3-11) walks `RS.RSLNKGRP → TR.TRLNKGRP → TR.TRLNKID → TU.TULNKID`.

**Verify link population during onboarding.** Studies where `--LNKID`/`--LNKGRP` are unpopulated cannot support drill-down without remediation, and this is the most common blocker. The configuration lint tool must check it explicitly and report it as a hard finding.

**Assessor partitioning.** `TR` and `RS` records are split into per-assessor series by `TREVAL`/`RSEVAL` matched against each assessor's configured `rs_eval_values`. The values must be disjoint across assessors (configuration validation rule), because an overlapping value would feed the same record into two series and corrupt both.

### Band 4 — Relevant events

| Element | SDTM | Key variables |
|---|---|---|
| Adverse events | `AE` (+`SUPPAE`) | `AETERM`, `AEDECOD`, `AEBODSYS`, `AETOXGR`, `AESER`, `AEREL`, `AEACN`, `AEOUT`, `AESTDTC`, `AEENDTC` |
| AESI / DLT flags | `SUPPAE` | per configuration |
| Concomitant anti-cancer therapy | `CM` | `CMCAT`, `CMTRT`, `CMSTDTC`, `CMENDTC` |
| On-study radiotherapy | `PR` | `PRTRT`, `PRSTDTC`, `PRLOC` |

---

## 3. Read coverage and the unread span

This section exists because investigator and central reads progress independently: site EDC entry and central image reading are separate pipelines with separate backlogs. Treating an unread scan as an absent scan is the most dangerous failure mode in the product.

For each subject and assessor, the review layer computes:

```
covered_through(subject, assessor)
    = the latest timepoint for which that assessor has a complete assessment
      (an RS overall-response record, or a full set of target-lesion TR records)

outstanding(subject, assessor)
    = count of timepoints performed (per any assessor or the visit schedule)
      that are later than covered_through for this assessor
```

Three distinct states must never be conflated on the burden curve, and each gets its own rendering (`03-visual-and-interaction-spec.md` §3):

| State | Meaning | Rendering |
|---|---|---|
| **Evaluable** | assessed, measurable, response derivable | normal point, line continues |
| **Not evaluable (NE)** | assessed, but a category cannot be assigned | NE marker, **line broken** |
| **Not yet read** | this assessor has not assessed this timepoint | shaded "not yet read" span, **line ends** — not a gap, not a value |

The distinction matters because a reviewer looking at a central-read curve that stops at Day 168 must be able to tell whether the patient stopped being scanned or the vendor has a backlog. Those two readings lead to opposite clinical conclusions.

---

## 4. Derivation specification

All thresholds below are configuration parameters (§`tumor_assessment` in `04-study-configuration.md`); the values shown are the defaults, which match the published criteria. Every derived row in `rl_timepoint` stores the parameter snapshot it was computed under.

### 4.1 Target lesion selection and baseline

Target lesions are those identified at baseline as measurable and selected for follow-up, capped by `target_lesions.max_total` (default 5) and `max_per_organ` (default 2). Measurability defaults require a longest diameter of at least 10 mm by CT/MRI with slice thickness no greater than 5 mm, at least 20 mm by chest X-ray, or at least 10 mm by calliper. Lymph nodes are the exception: a node is eligible as a target lesion only when its **short axis** is at least 15 mm, and it is the short axis — not the longest diameter — that enters the sum. Nodes with a short axis of 10 to 15 mm are non-target; nodes below 10 mm are non-pathological and are not recorded.

The baseline assessment is selected by `baseline.rule`, defaulting to the last assessment before first dose and no earlier than `max_days_before_first_dose`. The profile states which visit was used, because protocols differ on whether screening or a later pre-dose scan is baseline.

```
SOD(t)       = Σ over target lesions L of  measure(L, t)
                 where measure = SHORT_AXIS for nodal L, LONG_AXIS otherwise
SOD_base     = SOD(baseline visit)
SOD_nadir(t) = min over evaluable t' ≤ t of SOD(t')
                 including baseline when nadir.includes_baseline is true
```

### 4.2 Change metrics

```
CHG(t)       = SOD(t) − SOD_base                                  (mm)
PCHG(t)      = 100 × (SOD(t) − SOD_base) / SOD_base               (%)
PCHGNAD(t)   = 100 × (SOD(t) − SOD_nadir(t⁻)) / SOD_nadir(t⁻)     (%)
ABSNAD(t)    = SOD(t) − SOD_nadir(t⁻)                             (mm)
```

where `t⁻` denotes the nadir over timepoints strictly before `t`. Both `PCHG` and `PCHGNAD` are required by the UI (FR-3-05), because response is defined against baseline while progression is defined against nadir. Reporting only one of them is the most common source of misread profiles.

### 4.3 Target lesion timepoint response — RECIST 1.1

| Response | Rule |
|---|---|
| **CR** | Disappearance of all target lesions; any nodal target lesion reduced to a short axis below `nodal_cr_max_short_axis_mm` (default 10 mm). |
| **PR** | `PCHG(t) ≤ −pr_pct_decrease_from_baseline` (default −30%), and CR not met. |
| **PD** | `PCHGNAD(t) ≥ pd_pct_increase_from_nadir` (default +20%) **and** `ABSNAD(t) ≥ pd_min_absolute_increase_mm` (default 5 mm). Both conditions must hold. PD is also assigned on unequivocal non-target progression or a new lesion, independent of the sum. |
| **SD** | Neither PR nor PD relative to the smallest sum on study. |
| **NE** | One or more target lesions not evaluated or not evaluable, such that no category can be assigned. |

The minimum absolute increase matters disproportionately when baseline burden is low, where a 20% relative rise can be clinically trivial. The profile exposes the absolute value alongside the percentage for this reason (FR-3-06).

### 4.4 Non-target and new lesions

Non-target lesions are assessed qualitatively: **CR** requires disappearance of all non-target lesions and normalisation of any tumor marker; **Non-CR/Non-PD** covers persistence of one or more; **PD** requires *unequivocal* progression — a threshold deliberately set high, so modest non-target growth alongside target response does not drive an overall PD.

New lesions force PD regardless of the sum. Where a new lesion is equivocal, typically because it is too small to characterise, assessment continues and it is resolved at a later timepoint; if subsequently confirmed, progression is dated to the timepoint at which the lesion was **first observed**. The review layer therefore stores both the first-observed timepoint and the confirmation state for every new lesion, and the profile shows both (FR-3-10) — the dates differ and the earlier one governs.

### 4.5 Overall timepoint response — RECIST 1.1

Implemented as an explicit lookup so it is inspectable and testable rather than nested conditionals.

| Target | Non-target | New lesions | Overall |
|---|---|---|---|
| CR | CR | No | **CR** |
| CR | Non-CR/Non-PD | No | **PR** |
| CR | NE | No | **PR** |
| PR | Non-PD or NE | No | **PR** |
| SD | Non-PD or NE | No | **SD** |
| NE | Non-PD | No | **NE** |
| PD | Any | Yes or No | **PD** |
| Any | PD | Yes or No | **PD** |
| Any | Any | Yes | **PD** |

### 4.6 Confirmation and Best Overall Response

Where `confirmation.required_for` includes a category, a timepoint response in that category counts toward BOR only when a repeat assessment at least `min_interval_days` later (default 28) also meets the criteria. Where `sd_min_duration_days` is set, a claimed SD must additionally persist that long from first dose.

BOR is the best timepoint response from first dose until progression or the start of subsequent anti-cancer therapy, applying the confirmation requirement. The profile always states whether BOR is confirmed or unconfirmed (FR-H-02). **Presenting an unconfirmed PR as "PR" without qualification is a material misrepresentation in an early-phase readout, and reviewers will catch it.**

Both an unconfirmed and a confirmed BOR are stored, so a study that does not require confirmation still shows the same field with the same labelling.

### 4.7 iRECIST

Selected by `criteria: iRECIST`. The RECIST 1.1 machinery above is unchanged; two states are added and progression becomes a two-step process.

**iUPD — immune unconfirmed progressive disease.** Assigned when RECIST 1.1 progression criteria are met: the sum rises by at least `pd_pct_increase_from_nadir` and at least `pd_min_absolute_increase_mm` from nadir, non-target disease progresses unequivocally, or a new lesion appears.

**Confirmation window.** If the patient is clinically stable (where `require_clinical_stability` is true and the study records it), treatment may continue and a confirmatory assessment is performed no earlier than `irecist.confirm_min_days` (default 28) and no later than `confirm_max_days` (default 56) after the iUPD.

**iCPD — immune confirmed progressive disease.** Assigned when the confirmatory assessment shows further progression: additional growth in the already-progressing compartment, or progression in a compartment that had not previously progressed.

**Reset.** If the confirmatory assessment does not show further progression, the iUPD is treated as pseudoprogression and the level of suspicion **resets**. A later progression event is again assigned iUPD and the confirmation cycle restarts. A subject may legitimately accumulate several iUPD episodes.

The reset is what makes iRECIST awkward to render, and it is why iUPD must be a distinct visual state rather than a variant marker (FR-3-13): a reviewer needs to count the episodes. The review layer stores an `episode_index` on each iUPD so the sequence is explicit.

**Response states under iRECIST** are prefixed (`iCR`, `iPR`, `iSD`, `iUPD`, `iCPD`) and are never mixed with unprefixed RECIST states in the same series.

---

## 5. Data quality checks

Each check writes a row to `rl_flag` and renders as an inline, non-blocking indicator on the relevant band. The profile is a natural place to expose inconsistencies that listings hide, and doing so costs little once the data is assembled.

| Check | Trigger | Flagged at |
|---|---|---|
| Lesion limits exceeded | more target lesions than configured, or more than the per-organ cap | Baseline inventory |
| Nodal lesion measured on long axis | nodal target lesion whose `TRTESTCD` is not the short axis | Baseline inventory |
| Missing measurement at a performed visit | no `TR` record for a target lesion at a visit that has an `RS` record | Per-lesion row |
| Response without supporting measurements | `RS` record whose `RSLNKGRP` matches no `TR` records | Burden curve marker |
| Unlinked records | `TR` or `RS` records with unpopulated `--LNKID`/`--LNKGRP` | Study onboarding report |
| Method change between visits | `TRMETHOD` differs from baseline for the same lesion | Per-lesion row |
| Assessment outside protocol window | actual date outside the configured tolerance | Disposition band |
| Overdue assessment | no assessment within the window while the subject is on treatment | Header + disposition band |
| Assessor read backlog | `outstanding` above a configured threshold | Header coverage indicator |
| PD without corroboration | overall PD where no new lesion, non-target PD, or target threshold is satisfied | Burden curve marker |
| Nadir precedes baseline | derived nadir dated before the baseline assessment | Burden curve |
| Response after subsequent therapy | timepoint response dated after a subsequent anti-cancer therapy start in `CM` | Burden curve + band 4 |
| Derivation disagrees with recorded `RS` | engine-derived overall response differs from `RSSTRESC` for the same `RSLNKGRP` | Burden curve marker |
| Derivation disagrees with ADaM | engine value differs from `ADRS`/`ADTR` where ADaM is available | Reconciliation view |

The last two deserve emphasis. The application derives response itself, but studies also *record* an investigator response in `RS`. Where the two disagree, that is either a data issue or an engine issue, and in an unvalidated tool the reviewer must be told which timepoints are in dispute rather than shown one silently. The same logic extends to ADaM once it exists — which is why the reconciliation view is a requirement and not a convenience.
