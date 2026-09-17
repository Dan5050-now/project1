# TEP — Study Configuration Schema

Onboarding a study to the Tumor Evaluation Profile is a configuration task. This document is the contract: everything that varies between protocols lives here, and anything a study needs that this schema cannot express is a gap in the schema, not a reason to write study-specific code.

Configuration is a YAML file per study, held in version control, loaded and validated at application start and on change. Its content hash is displayed in the profile footer and printed on every PDF page, so any output can be traced back to the rules that produced it.

---

## 1. Design rules for the schema

Four rules keep the schema from decaying into a dumping ground.

**Every key has a default that matches published practice.** A study that follows RECIST 1.1 as written should need almost no tumor-assessment configuration. Configuration expresses *deviation*, and a short configuration file is a sign the schema is working.

**No key encodes a display decision that the data can answer.** Whether to show the DLT band is determined by whether a DLT window is configured, not by a `show_dlt_band: true`. Visibility follows from substance.

**Thresholds are values, never code.** The moment a study needs an expression or a formula in its configuration, the engine is missing a parameter. Add the parameter.

**Mapping overrides are explicit and narrow.** The application reads SDTM. Where a study puts something somewhere non-standard, the override names the domain, variable and filter — it never accepts arbitrary SQL.

---

## 2. Top-level structure

```yaml
schema_version: 1
study: {...}          # identity and study-level facts
data: {...}           # where the review layer comes from, freshness rules
assessors: [...]      # who reads the scans, and from which source
tumor_assessment: {...}   # criteria, thresholds, baseline, nadir, confirmation, schedule
treatment: {...}      # cycles, DLT window, dose presentation
adverse_events: {...} # grading, relevance, grouping, AESI
characteristics: {...}# which band-1 elements this study collects
mappings: {...}       # per-study SDTM deviations
display: {...}        # labels, axis defaults, cohort context
```

---

## 3. `study` — identity

```yaml
study:
  id: ONC-1042                       # required, unique within the deployment
  title: "Phase 1b dose expansion of ONC-1042 in advanced solid tumors"
  phase: "1b"
  indication: "Advanced solid tumors"
  blinded: false                     # true withholds treatment assignment entirely
  first_subject_first_visit: 2025-09-02
  status: ongoing                    # ongoing | closed
```

`blinded: true` removes treatment assignment from the profile and from all exports. It is deliberately not a UI toggle: unblinding is a configuration change with its own approval.

---

## 4. `data` — source and freshness

```yaml
data:
  source_type: sdtm_review_layer     # the only supported value in Phase 1
  location: "s3://cdr/ONC-1042/sdtm/current/"
  refresh:
    schedule_cron: "0 */4 * * *"     # review-layer rebuild cadence
    staleness_warn_hours:            # per domain; header flags anything past these
      default: 24
      TU: 72                         # tumor data legitimately lags
      TR: 72
      RS: 72
      AE: 12
  adam:
    available: true                  # enables the reconciliation view
    location: "s3://cdr/ONC-1042/adam/current/"
```

Per-domain staleness thresholds exist because a single study-level "last refreshed" stamp misleads. Tumor domains lag safety domains as a matter of course, and a reviewer needs to see which specific domain is behind.

Setting `adam.available: true` turns on the reconciliation view described in `01-concept-and-requirements.md` §8. It should be set as soon as any ADaM build exists, even an early one.

---

## 5. `assessors` — the read model

```yaml
assessors:
  - code: INV
    label: "Investigator"
    source: edc                      # informational; drives the freshness stamp shown
    rs_eval_values: ["INVESTIGATOR", ""]    # RSEVAL/TREVAL values identifying this read
    default: true
  - code: BICR
    label: "Independent central review"
    source: imaging_vendor
    rs_eval_values: ["INDEPENDENT ASSESSOR", "BICR"]
    default: false
overlay:
  enabled: true
  discordance_summary: true
```

The `rs_eval_values` list is how the review layer partitions `RS` and `TR` records into assessor-specific series. It is a list rather than a single value because studies are inconsistent about whether the investigator read carries a blank `RSEVAL` or an explicit one.

Each assessor's series is derived **independently end to end** — its own baseline, its own nadir, its own confirmation logic. The application never blends them. Where an assessor has no records for a subject, that subject simply has no series for that assessor, and the profile says so rather than falling back to the other read.

A study with one assessor lists one. The assessor control then disappears from the header rather than showing a single dead option.

---

## 6. `tumor_assessment` — the criteria engine parameters

This is the largest block and the one that carries the criteria selection.

```yaml
tumor_assessment:
  criteria: RECIST_1.1               # RECIST_1.1 | iRECIST

  measurability:
    min_diameter_ct_mri_mm: 10
    min_diameter_chest_xray_mm: 20
    min_diameter_caliper_mm: 10
    nodal_target_min_short_axis_mm: 15
    nodal_nontarget_min_short_axis_mm: 10
    nodal_cr_max_short_axis_mm: 10

  target_lesions:
    max_total: 5
    max_per_organ: 2
    enforce: warn                    # warn | ignore — never block

  thresholds:
    pr_pct_decrease_from_baseline: 30
    pd_pct_increase_from_nadir: 20
    pd_min_absolute_increase_mm: 5

  baseline:
    rule: last_before_first_dose     # last_before_first_dose | named_visit
    named_visit: null
    max_days_before_first_dose: 28

  nadir:
    includes_baseline: true          # baseline participates in the nadir minimum

  confirmation:
    required_for: [CR, PR]           # [] disables confirmation entirely
    min_interval_days: 28
    sd_min_duration_days: 42         # measured from first dose; null disables
    bor_label_unconfirmed: true      # always show BOR's confirmation status

  schedule:
    anchor: first_dose               # first_dose | randomization | consent
    windows:
      - from_day: 1
        interval_days: 42
        tolerance_days: 7
      - from_day: 337                # studies commonly widen the interval later
        interval_days: 84
        tolerance_days: 14
    continue_after_treatment_end: true

  irecist:                           # read only when criteria == iRECIST
    confirm_min_days: 28
    confirm_max_days: 56
    reset_on_pseudoprogression: true
    require_clinical_stability: true
```

Two parameters deserve comment because they are the ones most often assumed rather than configured.

`nadir.includes_baseline` decides whether progression can be assessed against the baseline sum for a subject who never shrank. RECIST 1.1 takes the smallest sum on study *including* baseline, so the default is `true`; some protocols word it differently, and getting it wrong silently changes PD dates.

`confirmation.min_interval_days` is the difference between a reported response rate and a confirmed one. The engine never infers it: if `required_for` is non-empty and this key is absent, configuration validation fails rather than guessing 28 days.

---

## 7. `treatment` — exposure presentation

```yaml
treatment:
  cycle_length_days: 21
  arms:
    - code: A
      label: "ONC-1042 monotherapy"
      dose_unit: mg
  dlt:
    window_days: 28
    anchor: first_dose
    ae_flag_variable: "AEDLT"        # SUPPAE or AE flag identifying DLT-qualifying events
  show_survival_followup: true
```

Omitting the `dlt` block removes the DLT window and its markers from band 2 entirely — the schema rule that visibility follows substance.

---

## 8. `adverse_events`

```yaml
adverse_events:
  grading_scale: "CTCAE 5.0"
  grouping: SOC                      # SOC | AESI | custom
  relevance_default:                 # the default band-4 filter
    min_grade: 2
    include_serious: true
    include_dlt: true
    include_aesi: true
    include_related_only: false
  aesi:
    source: SUPPAE                   # SUPPAE | AE | config_list
    variable: "AESI"
    terms: []                        # used when source == config_list
  concomitant_anticancer:
    cm_categories: ["ANTINEOPLASTIC", "PRIOR ANTINEOPLASTIC"]
    include_on_study_radiotherapy: true
```

The relevance filter is configurable because "clinically relevant" means different things in a first-in-human study and a late expansion cohort. The default above is a reasonable starting point, not a standard.

---

## 9. `characteristics` — what band 1 shows

```yaml
characteristics:
  performance_status:
    scale: ECOG                      # ECOG | KARNOFSKY | LANSKY | none
    source: {domain: RS, testcd: "ECOG"}
  collect:
    staging: true
    biomarkers: true
    metastatic_sites: true
    prior_therapy_lines: true
    prior_surgery: true
    prior_radiotherapy: true
    medical_history: true
  medical_history_relevance:
    soc_include: []                  # empty = show all on expand, none in summary
    terms_include: []
  biomarkers:
    - {label: "KRAS", source: {domain: LB, testcd: "KRASMUT"}}
    - {label: "PD-L1 TPS", source: {domain: LB, testcd: "PDL1TPS"}}
```

Each `collect` flag set to `false` removes that element from the card rather than rendering it empty. A study that does not collect prior radiotherapy loses the radiotherapy list and, with it, the irradiated-lesion flag (FR-1-06) — which the configuration lint tool should report as a lost capability rather than a silent omission.

---

## 10. `mappings` — per-study SDTM deviations

```yaml
mappings:
  overrides:
    stage_at_diagnosis:
      domain: SUPPMH
      qnam: "MHSTAGE"
      filter: {MHCAT: "PRIMARY DIAGNOSIS"}
    prior_line_best_response:
      domain: SUPPCM
      qnam: "CMBRESP"
    cohort:
      domain: DM
      variable: "ARMCD"
  domain_aliases:
    TU: "TU"
    TR: "TR"
    RS: "RS"
```

Overrides are a bounded vocabulary: the application publishes the list of override-able logical fields, and a configuration may only bind those. Anything outside the vocabulary is a schema gap to be raised, not an escape hatch. This is what stops per-study configuration from becoming per-study code by another name.

---

## 11. `display`

```yaml
display:
  axis_default: study_day            # study_day | calendar_date | cycle
  burden_metric_default: pct_baseline
  cohort_context:
    enabled: true
    group_by: cohort                 # cohort | dose_level | arm
  labels:
    subject: "Subject"
    cohort: "Cohort"
    treatment: "ONC-1042"
```

---

## 12. Validation rules

The loader refuses to serve a study whose configuration fails any of these, and the error names the offending key path.

| Rule | Reason |
|---|---|
| `schema_version` present and supported | Forward compatibility |
| `study.id` unique across the deployment | Routing and cache keys |
| At least one assessor, exactly one `default: true` | The header needs an initial selection |
| `rs_eval_values` disjoint across assessors | Overlapping values would double-count records into both series |
| `confirmation.min_interval_days` present when `required_for` is non-empty | Never guess the confirmation interval |
| `criteria: iRECIST` requires the `irecist` block | The two extra states have no safe defaults |
| `irecist.confirm_max_days` greater than `confirm_min_days` | A window, not a point |
| `schedule.windows` non-empty and ascending by `from_day` | Overdue detection depends on it |
| Every `mappings.overrides` key is in the published vocabulary | Prevents configuration becoming code |
| Every `source` reference names a domain the review layer builds | Fails at load rather than at render |

## 13. Lifecycle

A configuration lives in version control alongside the application, reviewed like code. A change takes effect on the next load, and the footer hash changes with it — which means an exported PDF from before the change remains traceable to the rules that were in force at the time.

The lint tool (FR-P-06) takes a candidate configuration plus a data extract and reports which referenced domains and variables are absent or unpopulated, so a study can be onboarded and checked before anyone opens a profile and finds an empty band.

**Recommendation on ownership:** the study's statistical programmer should own the configuration, with the medical monitor reviewing the clinically meaningful keys — criteria, confirmation policy, schedule, AE relevance. An in-app configuration editor should not be built in Phase 1: version control gives history, review and rollback for free, and the population of editors is small.
