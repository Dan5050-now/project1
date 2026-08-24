# Changelog

All notable changes to the Tumor Evaluation Review Agent (TEA) artifacts.
Each artifact is versioned independently; see `docs/README.md`.

## [2.0.0] — 2026-08-21 — APPROVED

**Step 2 gate passed.** TEA-SPEC-001 is approved for implementation and the rule pack is
frozen at 2.0.0.

### Approval, recorded as given
- Approved by Daniel, 2026-08-21, as a **reasonableness review**: *"All the change looks
  reasonable. I haven't confirmed all the detail, but good to final."*
- The new **Approval sheet** records that verbatim, states what the approval does *not*
  claim, and names the mitigation: Step 3 tests all 83 live rules against a curated dataset
  with a signed-off expected finding list, so detail not confirmed by reading is confirmed
  there by evidence.
- Two items were approved by the blanket statement rather than marked individually and are
  flagged rather than smoothed over: **TE-XD-005** (26 of the 27 round-3 rows carry an
  individual Accept; this one does not) and the **19 Rule_Messages rewrites** (the same
  changes are marked individually on the Rules sheet, so this is duplication, not a gap).
- **ID-05 and ID-06** are flagged a third time: amended at round 1, accepted under SQ-03,
  never separately re-read. ID-06 changed where baseline comes from, and every derivation
  depends on baseline.

### Frozen
- `rule-catalog.yaml` → 2.0.0, `status: FROZEN`, with the change-control requirement in the
  file header where anyone editing it will see it.
- The Rules and Rule_Messages sheets no longer carry reviewer input columns. Every decision
  column is closed history: three review rounds plus the gate.

### Changed elsewhere
- **TEA-PLAN-001** — Step 2 marked COMPLETE with the gate outcome and the approval basis;
  Step 3 marked NEXT; cover's next gate updated. **OI-03 (pilot study) is now blocking** —
  Step 3 cannot start without it.
- **Concept overview and slide deck** — Step 2 shown as approved, Step 3 as current and
  blocked on the pilot study. The closing slide now names what to watch at Step 3: the 8
  rules whose logic changed last have no test history, and 27 confidence base rates are
  still estimates rather than measurements.

## [1.3.0] — 2026-08-21

Everything was accepted — all 85 rules, all 85 query messages, all nine open questions. This
revision is a **quality pass, not a disposition**: the rules and query messages were re-read
through a clinical data manager's eyes and a medical monitor's eyes. 27 rules changed. The
other 58 are exactly as accepted.

### SQ-05 answered and applied
- Decision: the guideline reference appears only in the reviewer-facing tips. Nine query
  texts cited a guideline as authority; all nine were rewritten. Guideline words are kept
  only where they name a CRF field or a recorded value, which the site needs to find the record.

### CDM lens — 19 query messages rewritten
- **Nine queries stated the expected answer** ("the overall response should be PD", "the
  lesion should be recorded as non-target"). That converts a check into an instruction: the
  site confirms rather than verifies, and if the derivation is wrong the error returns signed
  by the site. This was the commonest fault in the set.
- **TE-RS-007 asked site staff for a medical judgement** — whether overall tumor burden had
  increased substantially. Now asks only for the radiological description; the judgement
  stays with the monitor.
- **TE-BL-005 instructed a site to delete recorded data.** Now asks them to confirm intent.
- Four queries carried the agent's arithmetic; it moved to the reviewer-facing reason.
- "Nadir" replaced with "the smallest sum recorded on study" throughout.

### MM lens — 8 rule logics amended
- **TE-XD-004** raised one finding per subsequent visit for a single course of local therapy
  — eleven findings for one fact in a 12-visit study. Now one finding per lesion.
- **TE-RS-020** raised a finding per discordant assessment. Now one per subject.
- **TE-XD-005** queried a site for a scan the subject was too unwell to have. Now suppressed
  where the subject died or discontinued before the next assessment was due.
- **TE-FU-014** fired on any single lesion repeating a value, which stable disease does
  routinely. Narrowed to all target lesions repeating — the actual copy-forward signal —
  and the base rate rises 0.30 → 0.55.
- **TE-ST-002** collided two genuinely separate lesions in one organ. Added size and
  description discriminators; 0.72 → 0.80.
- **TE-XD-003** fired on protocol-permitted maintenance therapy. Guarded.
- **TE-BL-014** raised a per-lesion finding for a study-wide modality change. Now one
  study-level finding when it affects most lesions at a visit.
- **TE-FU-011** fired on an assessment dated the same day as death, which is legitimate,
  and treated partial dates as full ones. Both guarded.

### Added
- **Query_Style sheet (TEA-QS-001)** — 12 house rules for query text, so a future review
  point does not reintroduce what was just fixed.
- `tools/check_query_style.py` — CI enforcement of those rules. Negative-tested against four
  injected violations; all four caught.
- Rules and Rule_Messages carry the previous logic and previous query text beside each
  change, and Review_Log lists all 27 with the reason.

### Open
- The 27 changed rules, in the amber columns. Nothing else is outstanding.

## [1.2.0] — 2026-08-21

Step 2 review, round 2 (Daniel). All 16 rules amended or explained at round 1 were re-read
and confirmed Accept, with no comments and no further changes. **No rule logic changed at
this revision** — this is a disposition record, not an edit.

### Rule review complete
- All 85 rules now carry a decision: 70 accepted outright at round 1, 15 raised and
  resolved there, all 16 of those confirmed at round 2. Logic, severities, modes and
  confidence base rates are settled.
- The Rules sheet is closed: its decision columns are read-only history and it no longer
  offers a reviewer input column.
- Review_Log carries both rounds side by side, with the round-2 outcome per item.

### Still open — the pack is NOT frozen
- **Rule_Messages has not been reviewed.** It holds the query text that reaches a site, and
  it is the last surface before the Step 2 gate. The rule pack freezes when it is accepted,
  not before. Both the catalog header and the plan's Step 2 exit criteria say so explicitly.
- Interpretations ID-05 and ID-06 were amended at round 1 and were not re-reviewed. Flagged
  on Review_Log and on Contents rather than assumed accepted.
- Open_Questions gains a status column recording what the two rounds settled: SQ-08 answered;
  SQ-01 and SQ-02 covered by the rule-by-rule acceptance but with no separate decision
  recorded; the remaining six open.

### Changed elsewhere
- `rule-catalog.yaml` → 1.2.0, with a header stating the logic is confirmed and the pack is
  not yet frozen.
- **TEA-PLAN-001** — Step 2 status becomes "Rules complete" with exit criteria split into
  done and remaining; Review_Scope retitled to 85 points / 83 live; **OI-02 closed**, since
  confidence base rates were carried on every accepted rule row.
- **Concept overview and slide deck** — status lines corrected to "rule logic settled, query
  wording still to review", and a sixth item added to the closing list: query wording is not
  a detail, and gets its own review by people who talk to sites.

## Concept overview, slide deck — 2026-08-21

### Added
- `docs/concept/TEA-concept-overview.pptx` — the concept overview as a 15-slide deck, for
  walking a room through the system. Same content and identity as the HTML page: the three
  clocks, the development gates, the review pipeline, data lineage, roles, the identifier
  decoder, and the five things that decide whether this works. Speaker notes throughout.
- `docs/concept/build_deck.js` — regenerates the deck (pptxgenjs).
- `docs/concept/qa_deck.py` — geometry QA: off-slide shapes, 0.5" edge margins, text-frame
  overlap, estimated text overflow.
- `docs/concept/render_deck.py` — renders slides to PNG with Pillow for visual QA.
  LibreOffice cannot convert in this environment, so the usual PDF-and-look pass is
  unavailable; this draws from the real coordinates and text using Carlito and Caladea,
  metric-compatible with Calibri and Cambria, so text fit is faithful.

Fonts are Cambria, Calibri and Courier New — all ship with Office and all render
true-to-width in QA. The deck passes the pptx validator and carries no placeholder text.

## Concept overview — 2026-08-21

### Added
- `docs/concept/tea-system-map.html` — a visual orientation map for readers coming to the
  project cold, published as an artifact. Frames the system as **three clocks** running at
  different cadences (build once, configure once per study, review every data cut), which
  is what makes the eleven components and six delivery steps legible as one thing.
- Three diagrams: the development process with its approval gates; the review pipeline,
  where vertical position encodes the deterministic-versus-LLM split rather than decorating
  it; and data lineage from source systems through the canonical model to an issued query,
  including the two feedback loops that close the system.
- A roles and responsibilities matrix spanning all three clocks, stating explicitly that
  these are responsibilities rather than system permissions, since release 1 does not
  enforce role-based access (OQ-08).
- An identifier decoder mapping each id family (OBJ, AC, D, TE-XX-000, ID, TEA-CTR, P-, G-,
  SQ, OI) to the document that owns it.

The overview is derived from the controlled documents and has no independent authority.
Where it disagrees with the plan or the specification, they win.

## [1.1.1] — 2026-08-19

### Fixed
- **TEA-SPEC-001 v1.1.0 would not open cleanly in Excel.** The Interpretations sheet
  carried an empty `<dataValidations count="0"/>` element, which is schema-invalid and
  made Excel offer to repair the file. Introduced when the interpretation decisions moved
  to pre-filled columns: the call adding the dropdown range was removed but the validation
  object stayed attached to the sheet. openpyxl writes and reads such a workbook without
  complaint, so only Excel surfaced it. No content was affected — the review record and
  all counts are intact.

### Added
- `tools/check_workbook_integrity.py` — fails the build on workbook defects that trigger
  an Excel repair prompt: empty or unranged data validations, XML parts that do not parse,
  overlapping merged ranges, cells beyond the 32,767-character limit, row and column size
  limits, and illegal control characters. Negative-tested by reproducing the exact defect.
  Run it in CI alongside the catalog drift check.

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
