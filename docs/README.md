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
| TEA-PLAN-001 Development Plan | 1.0.0 | **APPROVED** 2026-08-17 | — |
| TEA-SPEC-001 Programming Specification | 1.1.0 | DRAFT | Step 2 review, round 2 |
| Rule catalog | 1.1.0 | DRAFT | Frozen at the Step 2 gate |

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

## A note on Excel formulas

The workbooks contain live formulas (item counts, review progress). LibreOffice is
unavailable in the build environment, so formula cells ship without cached values;
`fullCalcOnLoad` is set, so Excel computes them on open. Every formula range was verified
by independent recomputation against the underlying cells before release.
