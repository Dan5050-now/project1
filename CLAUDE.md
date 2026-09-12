# Tumor Evaluation Review Agent (TEA)

An AI-assisted clinical data review agent. It re-derives RECIST 1.1 and iRECIST
response data from SDTM, detects discrepancies against what the site reported,
reconciles them against query history, and presents findings with a confidence
rate for a human to adjudicate. It never changes clinical data and it never
issues a query on its own.

**If you are the company's Claude Code, this file is your brief. Read it before
touching anything.**

---

## 1. The one rule

**COMMON artifacts are read-only here.** You may read every one of them. You may
not edit, extend, patch, monkey-patch, subclass-to-override, or locally fork a
single one.

Read-only paths:

```
docs/plan/TEA-PLAN-001_development-plan.xlsx
docs/spec/TEA-SPEC-001_programming-specification.xlsx
docs/spec/rule-catalog.yaml
docs/boundary/TEA-BND-001_portability-boundary.xlsx
tools/
src/                  (engine, rules, derivations, prompts — once it exists)
app/                  (review application — once it exists)
```

Why this is absolute rather than a preference: the moment one study edits the
rule pack, there is no longer one validated agent — there are as many as there
are studies, and none of them carries the validation evidence. A local edit that
makes this study's data pass is indistinguishable, six months later, from a bug.

If you cannot complete a task without changing a COMMON artifact, **that is the
finding**. Stop and raise a change request — see `.claude/skills/common-change-request/`.

---

## 2. The boundary

Development happens in two places because real protocol, imaging charter and EDC
content cannot leave the company.

| Class | Meaning | Who |
|---|---|---|
| **COMMON (C)** | Identical for any oncology study on RECIST 1.1 | Built outside, carried in, read-only |
| **APPLY (A)** | Changes when the study or the EDC build changes | **You produce it, to a contract** |
| **KNOW (K)** | Context you must be given before you can produce an APPLY artifact | The company provides |

**The test:** would this artifact be byte-for-byte identical for a different
study, on a different EDC, at a different company, as long as it used RECIST
1.1? Yes → COMMON. No → APPLY.

The full register is `docs/boundary/TEA-BND-001_portability-boundary.xlsx`,
sheet `Register` (21 COMMON, 13 APPLY, 13 KNOW). Read sheet `Boundary_Law`
first — it is one page and it carries the reasoning.

---

## 3. Non-negotiables

**DP-01 — the model never decides a verdict.** Code computes every finding. The
model does exactly three things: narrates findings from structured evidence,
adjudicates the rules explicitly declared `LLM_ADJUDICATED`, and reads free
text. It cannot promote, demote, suppress or create a finding.

**This binds you, not just the runtime model.** The SDTM conversion is the
dangerous case. You may *write the conversion code*, which a human then reviews
and qualifies. You may never *emit converted data values by judgement*. A model
that generates SDTM sits upstream of every deterministic verdict in the agent,
and nothing downstream can detect it.

**GLM v5.2 is the only run-time model.** No external or commercial LLM service,
in any component, at any time. Deployment is on-premise with no egress.

**The rule pack is FROZEN at 2.0.0.** 85 review points, 83 live. Changes need
change control, a version bump and an impact assessment on findings already
issued.

**Missing knowledge halts.** A KNOW item you were not given is never inferred,
defaulted or filled with a plausible value. Stop and say what is missing. A
guessed protocol parameter produces findings that are confidently wrong, which
is worse than no findings at all.

**Everything is versioned and hashed.** A configuration traces to a protocol and
a charter by content hash. A finding traces to a rule pack version, a prompt
version and a model version.

---

## 4. Before you start

Check the KNOW items your task depends on are actually present
(`TEA-BND-001` sheet `Knowledge_Pack`). The recurring ones:

- **K-01** the study protocol · **K-02** the imaging charter
- **K-03** the Veeva EDC build — CRF spec, item OIDs, codelists, repeating-group structure
- **K-04** a representative Veeva query export
- **K-05** SDTM IG version and sponsor conventions
- **K-06** sponsor SOPs · **K-13** target environment

If one is missing, say so and stop. Do not proceed on an assumption.

---

## 5. What you will be asked to produce

Thirteen APPLY slots, detailed on `TEA-BND-001` sheet `Apply_Slots` with an
acceptance test each. **Done means the test passes, not that the output looks
reasonable.** Skills for the main clusters:

| Skill | Slots | Work |
|---|---|---|
| `sdtm-conversion` | A-01, A-02 | Veeva raw → SDTM: the spec, then the code |
| `study-configuration` | A-03, A-07, A-08 | Protocol + imaging charter → the 28 parameters |
| `edc-mapping` | A-04, A-05, A-06, A-13 | Field, visit and subject maps; query write-back |
| `run-and-triage` | A-10 | Run the agent, read the coverage report, triage output |
| `validation-evidence` | A-11, A-12 | Deploy the installation, then qualify it |
| `common-change-request` | — | When COMMON has to change, and it is not yours to change |

---

## 6. Where things are

| What | Where |
|---|---|
| Rule catalog (machine-readable, 85 rules) | `docs/spec/rule-catalog.yaml` |
| Rules, messages, derivations, contracts | `docs/spec/TEA-SPEC-001_...xlsx` |
| What SDTM must contain (TEA-CTR-003) | ↳ sheet `SDTM_Requirements` |
| Query export contract (TEA-CTR-004) | ↳ sheet `Query_History` |
| Imaging charter contract (TEA-CTR-005) | ↳ sheet `Charter_Requirements` |
| Canonical input / finding contracts | ↳ sheets `Input_Contract`, `Finding_Contract` |
| Prompts and guardrails | ↳ sheet `LLM_Integration` |
| Components, architecture, screens | `docs/plan/TEA-PLAN-001_...xlsx` |
| The boundary | `docs/boundary/TEA-BND-001_...xlsx` |
| CI guards | `tools/check_*.py` |

Workbooks are read with `openpyxl`. To read a sheet:

```bash
python3 -c "
from openpyxl import load_workbook
ws = load_workbook('docs/spec/TEA-SPEC-001_programming-specification.xlsx',
                   read_only=True, data_only=True)['SDTM_Requirements']
for row in ws.iter_rows(values_only=True):
    if any(row): print(row)
"
```

---

## 7. Always run before you finish

```bash
python3 tools/check_workbook_integrity.py   # workbooks Excel can actually open
python3 tools/check_catalog_drift.py        # rule catalog vs specification
python3 tools/check_query_style.py          # query text house rules
python3 tools/check_ai_guides.py            # these guides vs TEA-BND-001
```

All four must pass. If `check_catalog_drift.py` fails, something edited a
COMMON artifact — find out what, and revert it.

---

## 8. Still open

Do not discover these by hitting them (`TEA-PLAN-001` sheet `Open_Items`):

- **OI-03** pilot study not chosen
- **OI-04** QA has not confirmed the validation deliverable list
- **OI-07** the protocol-summary content selection rule is not yet agreed between CDM and the Medical Monitor
- **OI-09** the query export supplied so far contains no site-answered queries, so the answer-assessment path is unexercised; and lesion-level query matching rests on an item-group sequence that the sample could not demonstrate
- **OI-10** no real imaging charter has been read, so the protocol-versus-charter conflict path is specified but untested
- **TEA-GLM-001** GLM v5.2's prompt budget and structured-output behaviour are assumed, not verified

---

## 9. House style

Write like the existing documents: plain, specific, no filler. State what
something does and what breaks without it. When you record an assumption, record
the consequence of it being wrong in the same breath. Never describe work as
complete when a test did not run.
