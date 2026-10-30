# Handover to the company laptop

Everything produced outside the company, packaged for transfer in. Read this
before unpacking.

**Issued** 2026-10-30 · **Package** `TEA-handover-2026-10-30` ·
**Contents** TEA-PLAN-001 v1.7.0, TEA-SPEC-001 v2.7.0, TEA-BND-001 v1.0.0,
rule pack 2.0.0 (FROZEN), 6 AI skills, 4 CI guards

---

## 1. Read this first: where the project actually stands

This is a **Step 2 handover**. The documents and the AI guides are complete.
**There is no engine code and no application code**, because they have not been
written yet.

| Step | What | Status |
|---|---|---|
| 1 | Development plan | **COMPLETE** — TEA-PLAN-001 v1.7.0 |
| 2 | Programming specification | **COMPLETE** — TEA-SPEC-001 v2.7.0, rule pack frozen at 2.0.0 |
| 3 | Prototype output on dummy data | **NEXT** — needs a prototype engine and a dummy dataset. Neither exists. |
| 4 | Web application UI design | Not started — screens S1–S8 are specified, no design |
| 5 | Code generation | Not started — no `src/`, no `app/` |
| 6 | Finalisation | Not started |

So do not expect to run the agent on the laptop. You cannot yet. What you *can*
do on day one is section 4, and it is substantial.

### The boundary question this raises

Under TEA-BND-001, the engine, the rule pack, the derivations and the review
application are all **COMMON** — built outside the company and carried in. They
are the artifacts that need no company data to write.

That work is not finished. Two ways forward, and it is your call:

- **Keep COMMON outside.** Steps 3, 4 and 5 continue where TEA-PLAN-001 and
  TEA-SPEC-001 were written. The laptop does the APPLY work in section 4 in
  parallel — most of it is gated on company data anyway, so the two tracks do
  not block each other.
- **Move COMMON inside.** Then the laptop builds the engine too. This is
  workable, but it ends the arrangement the boundary was designed around: the
  reason COMMON sits outside is that it then has one version, one validation
  package, and no study's data shaped it.

Nothing in the package assumes either answer. If you choose the second, say so
and TEA-BND-001 needs a revision — not a local edit (law L1).

---

## 2. What is in the box

| Artifact | Version | What it is |
|---|---|---|
| `docs/plan/TEA-PLAN-001_development-plan.xlsx` | 1.7.0 | Objectives, scope, components AC-01–AC-11, architecture, screens S1–S8, 39 requirements, 18 risks, delivery steps, open items |
| `docs/spec/TEA-SPEC-001_programming-specification.xlsx` | 2.7.0 | 27 sheets. The 85 rules and their reviewer-facing messages, 10 derivations, all five data contracts, confidence model, query reconciliation, prompts and guardrails, API, testing |
| `docs/spec/rule-catalog.yaml` | 2.0.0 FROZEN | The machine-readable rule pack. This is what engine code is checked against |
| `docs/boundary/TEA-BND-001_portability-boundary.xlsx` | 1.0.0 | The COMMON / APPLY / KNOW split. 21 COMMON, 13 APPLY slots, 13 KNOW items, 6 laws, the handover order |
| `CLAUDE.md` | — | The brief your Claude Code reads automatically |
| `.claude/skills/` (6) | — | `sdtm-conversion`, `study-configuration`, `edc-mapping`, `run-and-triage`, `validation-evidence`, `common-change-request` |
| `tools/check_*.py` (4) | — | The CI guards. Each negative-tested |
| `tools/build_*.py`, `tools/tea_style.py` | — | The document builders, so the workbooks stay reproducible |
| `docs/contracts/*.schema.json` | — | Canonical input and finding contracts as JSON Schema — machine-readable, for code generation |
| `docs/concept/` | — | Concept overview (HTML and PPTX) and their build scripts |
| `docs/superseded/` | — | The original v0.1.0 XML documents, kept for traceability |
| `requirements.txt` | — | `openpyxl==3.1.5`. The only dependency |
| `MANIFEST.sha256` | — | SHA-256 of every file. Verify before you trust the transfer |

Two forms of the same content:

- **`TEA-repo-2026-10-30.bundle`** — a git bundle with the full history. Prefer
  this: `git clone TEA-repo-2026-10-30.bundle project1`. You get every commit
  message, which is where the reasoning for each decision lives, and you can
  commit your APPLY work on top.
- **`TEA-handover-2026-10-30.tar.gz`** — the plain working tree, if git is not
  available.

---

## 3. What is NOT in the box, and why

| Missing | Why |
|---|---|
| Engine code (`src/`) — rules, derivations, pipeline, prompts | Step 5. Not written. The specification is complete enough to generate it from |
| Review application (`app/`) | Steps 4–5. Screens S1–S8 specified, no design and no code |
| Dummy / golden dataset | Step 3. Needs building to the SDTM structure in TEA-CTR-003 |
| Any study content — protocol, imaging charter, EDC build, CRF spec | These are **KNOW** items (K-01 to K-03, K-05). They could never leave the company, which is the whole reason the boundary exists |
| Your Veeva query export | It is your data. It stays with you. TEA-CTR-004 records what was learned from it; the file itself was never committed |
| GLM v5.2 access or prompts tuned to it | TEA-GLM-001 lists what to confirm about the platform. Unverified |

---

## 4. What you can do on day one

All of this is APPLY work, all of it needs company data, and none of it needs
the engine to exist. Order matters — later items depend on earlier ones.

### 4.1 Assemble the KNOW pack (blocks everything else)

TEA-BND-001 sheet `Knowledge_Pack`. Collect and confirm each is current:

- **K-01** study protocol · **K-02** imaging charter
- **K-03** Veeva EDC build — CRF specification, item OIDs, codelists, and
  **the repeating-group structure** (the item most often missing and the one
  that lesion-level query matching depends on)
- **K-04** a second query export, **one that contains site-answered queries** —
  the one supplied had none, so the answer-assessment path is still unexercised
- **K-05** SDTM IG version, sponsor conventions, controlled terminology release
- **K-06** sponsor SOPs — data review, query management, change control, CSV
- **K-13** target environment confirmation

A missing item stops the dependent slot. It is not filled with a plausible
value (law L4).

### 4.2 A-01 — the SDTM conversion specification

Skill: `sdtm-conversion`. Contract: TEA-SPEC-001 sheet `SDTM_Requirements`.

The highest-value thing you can do now. It needs K-03 and K-05 and nothing
else, and everything downstream depends on it. The skill leads with the six
failure modes rather than the happy path — read them before you start, because
every one of them is something a capable assistant walks into while trying to
be helpful.

Do not write conversion code yet (A-02). Get the specification reviewed first;
a mapping error found here costs minutes, found after conversion it costs a
re-run and an investigation.

### 4.3 A-04, A-05, A-06 — the EDC maps

Skill: `edc-mapping`. Contract: TEA-SPEC-001 sheet `Query_History`.

Field map, visit map, subject map. Needs K-03. Independent of A-01, so it can
run in parallel.

### 4.4 A-08 and A-07 — charter extract and protocol summary

Skill: `study-configuration`. Contract: TEA-SPEC-001 sheet
`Charter_Requirements`.

Needs K-01 and K-02. Expect conflicts: of the 34 charter parameters, 8 are
routinely stated in the protocol too and 10 more sometimes are, so up to half
can disagree. **Report every conflict; resolve none of them** (law L6).

Note that **A-07 is prepared by hand** by the study data manager, not extracted
by any model — and the content-selection rule for it is still open (OI-07),
needing agreement between CDM and the Medical Monitor. That agreement is worth
starting now; it is on the critical path and it is a human conversation.

### 4.5 Close two open items that need people, not code

- **OI-04** — get QA to confirm the validation deliverable list. Do this
  *before* any validation evidence is produced, not during. Underestimating
  validation scope is logged as RSK-10.
- **OI-03** — choose the pilot study. It determines the golden dataset and the
  UAT study.

---

## 5. On arrival

```bash
# 1. Unpack
git clone TEA-repo-2026-10-30.bundle project1 && cd project1
git checkout claude/tumor-evaluation-agent-asu3bs
#    or:  tar xzf TEA-handover-2026-10-30.tar.gz && cd TEA-handover-2026-10-30

# 2. Verify the transfer and the environment, and run every guard
python3 -m pip install -r requirements.txt
python3 tools/verify_handover.py
```

`verify_handover.py` checks the Python version, the dependency, every file
against `MANIFEST.sha256`, and then runs all four CI guards. It prints a single
pass or fail. If the manifest check fails, the transfer is corrupt — do not work
from it.

You can also verify with native tools and no script:

```bash
sha256sum -c MANIFEST.sha256
```

Then open the repository with your Claude Code. `CLAUDE.md` loads automatically
and the six skills become available.

---

## 6. Handling

**The package contains company identifiers.** TEA-SPEC-001 sheet
`Query_History` documents your Veeva export column by column, and its examples
include one subject identifier (`A0019501001`), the study code
(`A101-1001_TST5`), and five birth years from the four corrected records
(1906, 1910, 1951, 1953, 1989, 2008). They are there because a contract written
against a real file is worth far more than one written against an assumed
shape — and they are returning to the company they came from.

Two consequences:

- Treat the archive as company-confidential in transfer, not as generic
  documentation.
- **If these documents ever go outside the company** — to a vendor, a partner,
  a publication, a CRO — scrub those examples first. They are illustrative, not
  load-bearing; replacing them with synthetic values costs nothing and changes
  no requirement.

Nothing else in the package contains study data. The query export itself was
never committed.

---

## 7. Still open

Carried in `CLAUDE.md` section 8 and TEA-PLAN-001 sheet `Open_Items`:

| | What | Owner |
|---|---|---|
| **OI-03** | Pilot study not chosen | Daniel |
| **OI-04** | QA has not confirmed the validation deliverable list | Quality |
| **OI-07** | Protocol-summary content selection rule not agreed | CDM + Medical Monitor |
| **OI-09** | No site-answered queries seen, so the answer path is unexercised; lesion-level matching rests on an item-group sequence the sample could not demonstrate | Clinical programming |
| **OI-10** | No real imaging charter read, so the conflict path is specified but untested | CDM + Medical Monitor |
| **TEA-GLM-001** | GLM v5.2 prompt budget and structured-output behaviour assumed, not verified | Platform team |

---

## 8. The return path

Anything you cannot do without editing a COMMON artifact comes back out as a
change request — skill `common-change-request`. It is an expected outcome, not a
failure.

A local edit that never returns is how the two halves stop being the same
system. Six months later nobody can tell the local edit from a defect, and the
validation evidence covers something that is not what is running.
