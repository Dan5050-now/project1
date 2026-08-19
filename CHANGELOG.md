# Changelog

All notable changes to the Tumor Evaluation Review Agent (TEA) artifacts.
Each artifact is versioned independently; see `docs/README.md`.

## [1.1.0] — 2026-08-19

Step 2 review, round 1 (Daniel). 85 rules dispositioned: 70 Accept, 14 Discuss, 1 Reject.
8 interpretation decisions: 6 Accept, 1 Discuss, 1 Amend. Every item raised is resolved;
the record is on the Rules sheet and the new Review_Log sheet.

### Retired
- **TE-RS-010** — subsumed by TE-RS-008 (overall response versus the component table),
  TE-RS-009 (new-lesion flag versus recorded lesions) and TE-IR-001 (iUPD under iRECIST).
  No iRECIST condition needed folding into TE-RS-008.
- **TE-RS-011** — rejected. Imaging performed at investigator discretion routinely covers
  regions absent from baseline, so a new lesion found there is real. The rule's premise
  did not hold.
- Both ids are retained permanently and never reused; the catalog stays at 85 with 83 live.

### Changed — rule logic
- **TE-RS-003** — the baseline comparison is removed from the gate, widening detection to
  every missed progression from nadir. It is retained as a message discriminator and
  confidence modifier for the compared-against-baseline case.
- **TE-RS-007** — severity MAJOR → INFO, confidence 0.60 → 0.45. Collected data cannot
  settle the guideline's exceptional-circumstance test. This removes it from the default
  query worklist, making it a study-team observation rather than a site query.
- **TE-RS-002 / TE-RS-003** — declared cascade children of TE-RS-001. Both are subsumed by
  it for detection; their value is diagnostic, so they now collapse into one finding
  carrying the specific reason rather than two.
- **TE-RS-008** — suppressed behind TE-RS-001, TE-RS-005 and TE-RS-009 when a component
  finding is already open for the assessment, and now names the driving component. One
  visit yields one query.
- **TE-BL-011** and **TE-FU-001** — ACTIVE → CONDITIONAL on the sum being site-entered
  rather than system-derived, determined from the CRF specification at the AC-11 intake.
  A derived sum deactivates the rule with an explicit NOT_EVALUATED. **This answers SQ-08.**
  TE-FU-001 was accepted at round 1 but amended alongside TE-BL-011, since applying the
  guard at baseline but not at follow-up would be incoherent.
- **TE-FU-007** — a per-visit assessment schedule from the protocol intake replaces the
  single interval, so protocols that vary the window by timepoint are honoured.
- **TE-FU-009** — restricted to follow-up assessments (a nodal target cannot be absent at
  selection, having required a short axis ≥ 15 mm) and excludes the too-small-to-measure
  state so ID-02 handling is not flagged as an error.
- **TE-ST-003** — nodal axis type is resolved from the CRF specification where no
  axis-type field is collected, instead of assuming the field exists.
- **TE-RS-013** — guarded against back-dating progression where visit j establishes PD
  independently; back-dating applies only when the new lesion is the progression driver.

### Added — Rationale / source column
- States where each threshold comes from. TE-RS-014 cites RECIST 1.1's 4-week confirmation
  provision and TE-XD-007 the marker-normalisation requirement for CR. **TE-FU-004 states
  plainly that no guideline source exists** — its outlier thresholds are heuristics aimed
  at transcription error, to be calibrated on the golden dataset at Step 3 — rather than
  implying a citation it does not have. TE-FU-005 carries no threshold at all; its
  parameter is interpretation decision ID-01.

### Changed — interpretations
- **ID-06 amended** — baseline is the tumor identification form at the screening visit, as
  the CRF is designed, replacing inference from assessment dates relative to first dose.
  The date-based rule remains as a fallback.
- **ID-05 expanded** — worked examples for both the arithmetic tolerance and the threshold
  boundary case, where a percent change of 19.96% displays as 20.0% but is judged SD at
  full precision.

### Added
- **Review_Log sheet** — round-1 disposition, what was raised and how it was resolved.
- `RETIRED` added to the RuleStatus enumeration.

### Open
- Rule_Messages has not been reviewed yet; it is the round-2 surface alongside the 14
  amended rules. SQ-01 to SQ-07 and SQ-09 remain for the Step 2 gate.

## [1.0.0] — 2026-08-17

Step 1 gate passed. Review disposition: 95 items — 78 Accept, 3 Amend, 14 open questions
closed (8 answered, 6 assumptions accepted). Reviewed by Daniel.

### Changed — document format
- Controlled documents are now **Excel workbooks**, replacing XML. The v0.1.0 XML drafts
  moved to `docs/superseded/` for history only.

### Changed — scope
- **RECIST 1.0 removed** (OBJ-06 / OQ-06). Guideline packs are RECIST 1.1 and iRECIST.
  One profile, one knowledge-base entry and one reference retired; rules previously tagged
  `ALL` now mean RECIST 1.1 + iRECIST.
- **Veeva EDC is the primary input profile** (OQ-01), with the CRF specification supplied
  as structured data. SDTM demoted to secondary.
- Release 1 simplifications: on-demand runs only (OQ-12), no strict role separation
  (OQ-08), English only (OQ-11).
- Indications: NSCLC and breast cancer; prostate, colorectal, pancreatic, head and neck
  and ovarian cancer on the post-release roadmap (OQ-05).

### Added — confidence rate (OBJ-03)
- Every finding now carries a confidence rate (xx.x%): the estimated probability that the
  finding is a correct query, distinct from certainty that the rule fired correctly.
- Confidence base rate assigned to all rules (range 0.30–0.97, mean 0.79).
- Computation model, display bands and safeguards specified; calibration error added as a
  quality metric; FR-18 added; RSK-15 added for miscalibration.

### Added — query answer assessment (OBJ-04)
- The agent now assesses whether a site's answer to an earlier query reasonably explains
  the current data, instead of escalating whenever the data still fails a check.
- New outcome `JUSTIFIED_BY_ANSWER` with permanent suppression for MINOR and INFO
  findings; CRITICAL and MAJOR are flagged for a human to close, never auto-suppressed.
- TE-QM-002 rewritten; prompt contract `P-ASSESS-ANSWER` added; FR-19 added.

### Added — protocol intake (OQ-04)
- New component AC-11 and pipeline stage ST-INTAKE: the agent summarises protocol
  parameter checkpoints for the user to confirm before the first run. FR-20 added, plus
  screen S7 and prompt contract `P-INTAKE-PROTOCOL`.

### Added — tooling
- `docs/spec/rule-catalog.yaml` — machine-readable catalog, maintained separately from the
  specification workbook by decision at the Step 1 review.
- `tools/check_catalog_drift.py` — CI guard comparing catalog, workbook and (from Step 5)
  implemented rule modules across id, family, title, guideline, severity, mode, status and
  confidence base rate. Negative-tested: it fails on an injected mismatch.
- `tools/build_rule_catalog.py` — regenerates the catalog from `tools/rules.json`.

### Documents
- **TEA-PLAN-001 v1.0.0** — 25 sheets. APPROVED.
- **TEA-SPEC-001 v1.0.0** — 20 sheets, including the 85-rule catalog split across a Rules
  sheet (logic, severity, confidence) and a Rule_Messages sheet (the five reviewer-facing
  elements). DRAFT, awaiting the Step 2 review.

### Added — rule TE-RS-021
- **New or worsening effusion used as evidence of progression without cytological
  confirmation.** MAJOR, HYBRID, PROPOSED_OPTIONAL (off by default), confidence base
  rate 0.55. RECIST 1.1 requires cytological confirmation of an effusion appearing or
  worsening on treatment before it may be taken as progression, where the measurable
  disease is responding or stable; an unconfirmed effusion is a recognised source of
  spurious progression that censors subjects early and shortens PFS. No existing rule
  covered this. Catalog is now **85 rules** (RS family 20 → 21). Decision at the Step 2
  gate under SQ-04.

### Closed
- **OI-01** — mesothelioma was not intended, so pleural effusion does not enter the
  indication roadmap. Investigating what the entry pointed at produced TE-RS-021 above.

### Open
- Five items carry into Step 2, tracked on the plan's Open_Items sheet.

## [0.1.0] — 2026-08-10

Initial XML drafts of the development plan and programming specification, the canonical
input and finding data contracts, and the document control policy. Superseded by 1.0.0.
