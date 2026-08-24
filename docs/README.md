# Tumor Evaluation Review Agent (TEA) — Document Control

Controlled documents for the Tumor Evaluation Review Agent, an AI-assisted data review
agent for oncology clinical trials (RECIST 1.1 / iRECIST).

## Repository layout

```
docs/
  README.md                                          this file
  plan/TEA-PLAN-001_development-plan.xlsx            TEA-PLAN-001  v1.0.0  APPROVED
  spec/TEA-SPEC-001_programming-specification.xlsx   TEA-SPEC-001  v1.0.0  DRAFT
  spec/rule-catalog.yaml                             machine-readable rule catalog
  concept/tea-system-map.html                        concept overview — read this first
  concept/TEA-concept-overview.pptx                  the same overview as slides
  concept/build_deck.js                              regenerates the deck
  concept/qa_deck.py, render_deck.py                 deck QA (no LibreOffice here)
  contracts/*.json                                   input and finding data contracts
  superseded/                                        v0.1.0 XML drafts, history only
tools/
  build_rule_catalog.py                              writes rule-catalog.yaml
  check_catalog_drift.py                             CI guard: catalog vs workbook vs code
  rules.json                                         authoring source for the catalog
CHANGELOG.md
```

## Document format

From v1.0.0 the controlled documents are **Excel workbooks**. The v0.1.0 XML drafts are
superseded and retained under `docs/superseded/` for history only — do not edit them.

Each workbook opens on a **Contents** sheet listing every other sheet with live item
counts. Yellow cells are reviewer input; everything else is controlled content.

## Status

| Document | Version | Status | Next |
|---|---|---|---|
| TEA-PLAN-001 Development Plan | 1.1.0 | **APPROVED**, amended 2026-08-22 | — |
| TEA-SPEC-001 Programming Specification | 2.2.0 | **APPROVED**, amended 2026-08-22 | — |
| Rule catalog | 2.0.0 | **FROZEN** 2026-08-21 | Unchanged by the v2.1.0 amendment |
| Concept overview (HTML + PPTX) | — | Current | Regenerate when the plan or spec changes |

## Where to start

`docs/concept/tea-system-map.html` is the orientation map: the three clocks the system runs
on, the development gates, the review pipeline, data lineage from EDC export to issued
query, and roles and responsibilities. It is derived from the plan and the specification
and carries no independent authority — where it disagrees with them, they win.

**Step 2 is closed.** The specification is approved and the rule pack is frozen at 2.0.0 —
a rule change from here needs change control, a version bump and an impact assessment on
findings already issued, not an edit.

The approval was given as a *reasonableness review*: the reviewer's own words were that the
changes look reasonable but the detail was not individually confirmed. The specification's
**Approval** sheet records that, along with the two items covered by the blanket statement
rather than marked individually. Step 3 is what makes that basis workable — the golden
dataset tests all 83 live rules against a signed-off expected finding list, confirming the
detail by evidence rather than by reading.

**Step 3 is blocked on one decision: choosing the pilot study** (OI-03). It determines the
golden dataset and the UAT study.

## Language model

The agent runs on the **company-hosted GLM v5.2** and nothing else. Commercial and externally
hosted LLM services are out of scope, so no subject data leaves the company network. Two
deployment modes exist: GLM v5.2 on-premise, and deterministic-only.

Deterministic-only is not a degraded fallback — it is the **verdict reference**. Every commit
runs the same fixtures through both and fails the build if a deterministic verdict differs.
That is what still guarantees the model cannot change a verdict, now that there is no second
provider to compare against.

**Not yet verified:** GLM v5.2's structured-output behaviour and context limit. The 32k prompt
budget was assumed at OQ-03 against a generic gateway and was never checked against this model.
The specification's **GLM_Verification** sheet (TEA-GLM-001) is the 20-item checklist to take to
the platform team, ordered by what breaks if the answer differs from what was assumed.

One item on it is blocking rather than informational: **B2**. `P-INTAKE-PROTOCOL` (AC-11) takes
the protocol and imaging charter as input, and an oncology protocol runs 100–200 pages — very
roughly 60k–150k tokens before the charter. If the deployment's input context is near 32k, that
prompt cannot work as specified and AC-11 needs section-targeted retrieval or chunking. That is
a design change, not a configuration value.

Steps 3–6 (prototype output, UI design, code generation, final application) are gated on
approval of the specification.

## Versioning policy

| Artifact | Versioning | Where the version lives |
|---|---|---|
| Plan / specification workbooks | SemVer | Cover sheet, plus a git tag |
| Rule pack (catalog) | SemVer, independent of the specification | `version:` in `rule-catalog.yaml` |
| Prompt templates | SemVer per prompt | prompt registry (Step 5) |
| Agent output (findings) | Stamped, never versioned in place | `provenance` block on every finding |

1. **Filenames carry no version.** The version lives inside the document and in the git
   tag (`plan-vX.Y.Z`, `spec-vX.Y.Z`, `rulepack-vX.Y.Z`), so `git diff` stays meaningful.
   Note: this environment's git proxy refuses tag pushes — the tags exist locally but must
   be pushed from a normal clone. The authoritative version is the one inside each document
   (Cover sheet, or the `version:` key in `rule-catalog.yaml`), so nothing is lost meanwhile.
2. **MAJOR** invalidates previously issued findings or breaks a data contract.
   **MINOR** adds review points or capability, backward compatible. **PATCH** is wording.
3. **Every agent run stamps its inputs**: engine, rule pack, prompt and model versions,
   guideline version, protocol config hash, dataset snapshot hash.
4. **No silent rule edits.** Changing a rule's logic requires a rule pack MINOR/MAJOR and
   a change-history entry naming the rule id.

## The rule catalog and the drift check

The Step 1 review chose to maintain the machine-readable catalog **separately** from the
specification workbook. That is only safe if divergence is detected, so:

```bash
python3 tools/check_catalog_drift.py                    # catalog vs workbook
python3 tools/check_catalog_drift.py --rules-dir src/rules   # also vs implemented modules
```

The check compares id, family, title, guideline, severity, mode, status and confidence
base rate for all 85 rules (83 live, 2 retired), and exits non-zero on any mismatch. Run it in CI on every
commit. Regenerate the catalog after editing `tools/rules.json`:

```bash
python3 tools/build_rule_catalog.py
```

## Workbook integrity check

`tools/check_workbook_integrity.py` guards against defects that make Excel show a repair
prompt on open — the most likely being an empty `<dataValidations count="0"/>` element,
which openpyxl writes and reads back without complaint but Excel rejects. It also checks
XML well-formedness, overlapping merged ranges, the 32,767-character cell limit, row and
column size limits, and illegal control characters.

```bash
python3 tools/check_workbook_integrity.py            # every workbook under docs/
python3 tools/check_workbook_integrity.py file.xlsx  # one workbook
```

Run it in CI alongside the drift check, and after any change to a workbook builder.

## Query style check

`tools/check_query_style.py` enforces the query message house rules (TEA-QS-001, the
Query_Style sheet). The reviewer-lens pass removed guideline citations and statements of the
expected answer from 19 query templates; this keeps them out.

```bash
python3 tools/check_query_style.py
```

It fails on: a guideline cited as authority (SQ-05), a query that states the expected answer,
one that instructs deletion of recorded data, one that asks site staff for a medical
judgement, and anything over 400 characters. Naming a CRF field — "the iRECIST response
field" — is allowed and is not treated as a citation.

## Regenerating the slide deck

```bash
cd docs/concept
npm install pptxgenjs          # once
node build_deck.js
python3 qa_deck.py             # geometry: bounds, margins, overlap, estimated overflow
python3 render_deck.py TEA-concept-overview.pptx /tmp/deckpreview   # then look at the PNGs
```

LibreOffice cannot convert files in this environment, so the usual
`soffice --convert-to pdf` visual QA is unavailable. `render_deck.py` draws the slides
with Pillow from the real coordinates and text in the file, using Carlito and Caladea —
metric-compatible with Calibri and Cambria — so text fit in the preview is faithful.
It approximates: no shadows, no dash patterns, no gradients.

## A note on Excel formulas

The workbooks contain live formulas (item counts, review progress). LibreOffice is
unavailable in the build environment, so formula cells ship without cached values;
`fullCalcOnLoad` is set, so Excel computes them on open. Every formula range was verified
by independent recomputation against the underlying cells before release.
