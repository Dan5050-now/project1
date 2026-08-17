# Changelog

All notable changes to the Tumor Evaluation Review Agent (TEA) artifacts.
Each artifact is versioned independently; see `docs/README.md`.

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
