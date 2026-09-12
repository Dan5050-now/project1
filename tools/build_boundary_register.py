#!/usr/bin/env python3
"""Build TEA-BND-001, the portability boundary register.

Daniel cannot supply real protocol, imaging charter or EDC content outside the
company, so development splits in two. Everything that would be identical for
any oncology study on RECIST 1.1 is built here and carried in. Everything that
changes when the study or the EDC build changes is produced inside the company
by its own Claude Code, against contracts defined here.

This document is the register of that split. Every artifact in the system is
classified:

  COMMON (C)  built here, read-only in the company
  APPLY  (A)  the company's Claude Code produces it, to a contract
  KNOW   (K)  context the company's Claude Code must be given first

It also records the reference SDTM design, study profile and imaging charter
assumed here so development can proceed without real study content, and what
the company must confirm or replace in each.

Usage:  python3 tools/build_boundary_register.py
"""
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tea_style import (ACCENT, CLASS_COLOUR, FACE, MUTE, WASH, header_row,
                       kv_rows, note_block, section_label, sheet_setup,
                       title_style, write_rows)

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "docs" / "boundary" / "TEA-BND-001_portability-boundary.xlsx"

VERSION = "1.0.0"
ISSUED = "2026-09-12"

# ==========================================================================
# Cover
# ==========================================================================
COVER = [
    ("Document ID", "TEA-BND-001"),
    ("Version", VERSION),
    ("Status", "DRAFT — for review. Nothing in it changes an approved artifact; it classifies what already exists and defines what the company must add."),
    ("Issue date", ISSUED),
    ("Parent documents", "TEA-PLAN-001 v1.6.0 (development plan), TEA-SPEC-001 v2.6.0 (programming specification)"),
    ("Purpose", "Split the system into what is built outside the company and carried in, what the company's Claude Code must produce for each study and each EDC build, and what it must be told before it can do either."),
    ("Why it exists", "Real protocol, imaging charter and EDC content cannot leave the company, and study data cannot leave it either. Development therefore cannot be finished in one place. This register is what keeps the two halves compatible."),
    ("Classes", "COMMON (C) — built here, read-only in the company.   APPLY (A) — the company's Claude Code produces it, to a contract defined here.   KNOW (K) — context the company's Claude Code must be given before it can produce an APPLY artifact."),
    ("Language model", "Company-hosted GLM v5.2 for the agent at run time; the company's own Claude Code for the APPLY development work. Neither may change a deterministic verdict."),
    ("Reference assumptions", "A reference SDTM design, study protocol profile and imaging charter profile are assumed here so that development can proceed. All three are placeholders with a stated replacement path — see the three Reference sheets."),
    ("Read first", "Boundary_Law. It is one page and it is the part that matters; the registers are lookup tables."),
]

# ==========================================================================
# Boundary_Law
# ==========================================================================
THE_TEST = (
    "Would this artifact be byte-for-byte identical for a different oncology study, run on a different EDC, "
    "at a different company, as long as it used RECIST 1.1?  Yes → COMMON.  No → APPLY.")

LAWS = [
    ("L1", "COMMON is read-only inside the company.",
     "The company's Claude Code may read every COMMON artifact and must never edit one. A needed change is a change request back to this repository, not a local edit.",
     "The moment one study edits the rule pack, there is no longer one validated agent — there are as many as there are studies, and none of them carries the validation evidence. This is the single rule that the whole arrangement rests on."),
    ("L2", "APPLY artifacts are written to a contract, not to taste.",
     "Every APPLY slot names an input contract on the COMMON side and an acceptance test. The company's Claude Code is finished when the test passes, not when the output looks reasonable.",
     "It is the only way to judge work produced somewhere the reviewer cannot see. 'Looks right' does not survive an audit; a passing conformance check does."),
    ("L3", "The model never decides a verdict, on either side of the boundary.",
     "DP-01 holds in the company exactly as it holds here. The SDTM conversion is the dangerous case: the model may WRITE the conversion code, which is then reviewed and qualified, but it must never EMIT the converted values by judgement.",
     "A model that generates SDTM values sits upstream of every deterministic verdict in the agent. The guarantee that a model cannot change a finding becomes void, silently, and nothing downstream can detect it."),
    ("L4", "KNOW comes before APPLY, and missing knowledge halts.",
     "An APPLY slot cannot be started until every KNOW item it depends on has been supplied. A missing input stops the work and is reported; it is never inferred, defaulted or filled with a plausible value.",
     "Every KNOW item is something only the company has. A guessed protocol parameter produces findings that are confidently wrong, which is worse than no findings at all."),
    ("L5", "Everything crossing the boundary is versioned and hashed.",
     "A study configuration traces to a protocol document and an imaging charter by content hash. A conversion traces to a specification version. A finding traces to a rule pack version, a prompt version and a model version.",
     "ALCOA+ and 21 CFR Part 11. It is also the only way to answer 'why did the agent say that in March?' six months later, when three of the five inputs have changed."),
    ("L6", "A conflict between the protocol and the imaging charter is a finding, not a choice.",
     "Where both documents specify the same parameter and they disagree, the configuration is not resolved by preferring one. The run reports the conflict and the study team decides.",
     "Charters and protocols routinely disagree on confirmation windows, target-lesion caps and measurability thresholds. Silently preferring either one buries a real protocol-deviation risk inside a configuration file."),
]

EDGE_CASES = [
    ("A new RECIST rule is needed.", "COMMON",
     "Change control in this repository, rule pack version bump, impact assessment on findings already issued. Never a local rule module in the company."),
    ("A study caps target lesions at 3 instead of 5.", "APPLY",
     "It is a protocol_config parameter. The rule reading it is COMMON and unchanged; only the value moves."),
    ("The EDC calls the visit 'C1D1' instead of 'Cycle 1 Day 1'.", "APPLY",
     "Visit map (A-05). Nothing in COMMON ever sees an EDC visit label."),
    ("A Veeva upgrade adds columns to the query export.", "APPLY, usually nothing",
     "TEA-CTR-004 adapter rule 3 ignores unknown columns. It becomes a COMMON change only if a column the agent needs is renamed or removed."),
    ("The company wants a different finding severity for a rule.", "COMMON",
     "Severity is part of the frozen rule pack and drives triage everywhere. A study-level override would make two studies' CRITICAL counts incomparable."),
    ("A tumour form repeats per lesion and the query export must reach the right row.", "Both",
     "The requirement is COMMON (TEA-CTR-004 finding 1). Preserving the item-group sequence through the conversion is APPLY (A-01)."),
    ("The protocol requires confirmation of response after 4 weeks.", "APPLY",
     "protocol_config. The confirmation rules are COMMON and read the window from configuration."),
    ("GLM v5.2 turns out not to support structured output as assumed.", "COMMON",
     "It changes the LLM integration layer for everyone. Raise it against TEA-GLM-001, not as a local workaround."),
]

# ==========================================================================
# Register
# ==========================================================================
REGISTER = [
    # --- COMMON ------------------------------------------------------------
    ("C-01", "C", "Rule pack — 85 review points, 83 live",
     "TEA-SPEC-001 Rules + Rule_Messages; docs/spec/rule-catalog.yaml",
     "FROZEN at 2.0.0. Guideline logic only; no study or EDC content appears in any rule."),
    ("C-02", "C", "Derivation engine — 10 algorithms",
     "TEA-SPEC-001 Derivations",
     "Sum of diameters, nadir, percent change, the four response components, best overall response, iRECIST. Pure RECIST arithmetic."),
    ("C-03", "C", "Guideline profiles — RECIST 1.1, iRECIST",
     "TEA-SPEC-001 Guideline_Profiles",
     "The published criteria and their parameters. A study may override a parameter through configuration; it may not edit the profile."),
    ("C-04", "C", "Documented interpretations ID-01..ID-06",
     "TEA-SPEC-001 Interpretations",
     "Where the guidelines are ambiguous, the agent states its default. The same default must apply everywhere or findings stop being comparable between studies."),
    ("C-05", "C", "Canonical input contract TEA-CTR-001",
     "TEA-SPEC-001 Input_Contract",
     "The shape rules see. Source adapters map into it; no rule ever sees a source field name."),
    ("C-06", "C", "Finding contract TEA-CTR-002",
     "TEA-SPEC-001 Finding_Contract",
     "The agent's output record, and therefore the application's input. Stable across studies by definition."),
    ("C-07", "C", "SDTM input requirements TEA-CTR-003",
     "TEA-SPEC-001 SDTM_Requirements",
     "What the agent needs from an SDTM delivery, variable by variable. The conversion that satisfies it is APPLY (A-01); the requirement itself is common."),
    ("C-08", "C", "Query history input contract TEA-CTR-004",
     "TEA-SPEC-001 Query_History",
     "Derived from a real Veeva export, but the contract is EDC-shaped rather than study-shaped: it binds by column name and tolerates version drift."),
    ("C-09", "C", "Imaging charter requirements TEA-CTR-005",
     "TEA-SPEC-001 Charter_Requirements",
     "NEW. What the agent needs from an imaging charter. The charter itself is KNOW (K-02); its extract is APPLY (A-08)."),
    ("C-10", "C", "Pipeline and components AC-01..AC-11",
     "TEA-PLAN-001 Components; TEA-SPEC-001 Pipeline",
     "The processing order and each component's responsibility and mode."),
    ("C-11", "C", "Confidence model",
     "TEA-SPEC-001 Confidence_Model",
     "Base rate by rule, times evidence completeness, adjudication, acceptance history and query history. Study-independent by construction."),
    ("C-12", "C", "Query reconciliation model",
     "TEA-SPEC-001 Query_Reconciliation",
     "Matching, answer assessment and the five outcomes. The field map it uses is APPLY (A-04)."),
    ("C-13", "C", "Prioritisation and cascade grouping",
     "TEA-SPEC-001 Prioritisation",
     "One root cause produces one finding with its consequences attached, rather than one finding per affected visit."),
    ("C-14", "C", "Query style rules TEA-QS-001",
     "TEA-SPEC-001 Query_Style; enforced by tools/check_query_style.py",
     "Twelve house rules for query text. A company may have its own house style — that is a change request, not a local override, or the CI check stops meaning anything."),
    ("C-15", "C", "Prompt contracts P-* and guardrails G-*",
     "TEA-SPEC-001 LLM_Integration",
     "Every prompt the agent issues, with its schema, its refusal behaviour and its redaction rules. Prompts are versioned artifacts, not strings in code."),
    ("C-16", "C", "LLM policy — GLM v5.2 only, DP-01 deterministic-first",
     "TEA-PLAN-001 LLM_Policy; TEA-SPEC-001 LLM_Integration",
     "Code computes every verdict. The model narrates, adjudicates declared judgement rules, and reads free text. Nothing else."),
    ("C-17", "C", "Review application — screens S1..S8, API surface",
     "TEA-PLAN-001 Web_App, Architecture; TEA-SPEC-001 API",
     "Reads the finding contract. It has no study logic in it, which is exactly why it ports."),
    ("C-18", "C", "Test framework and golden dataset structure",
     "TEA-SPEC-001 Testing",
     "Ten test levels and their gates. The structure is common; the study-specific dataset that fills it is APPLY (A-09)."),
    ("C-19", "C", "CI guards — catalog drift, workbook integrity, query style",
     "tools/check_*.py",
     "Each negative-tested. They must run in the company too, against the same COMMON artifacts, or drift is undetectable."),
    ("C-20", "C", "Validation approach — GAMP 5 category, ICH E6(R3), Part 11 mapping",
     "TEA-PLAN-001 Validation",
     "The approach is common. The executed evidence for a given installation is APPLY (A-12)."),
    ("C-21", "C", "AI guides for the company's Claude Code",
     "CLAUDE.md and .claude/skills/ in this repository",
     "The instructions that tell the company's Claude Code how to do the APPLY work. Common by definition — they are what makes the APPLY work repeatable."),
    # --- APPLY -------------------------------------------------------------
    ("A-01", "A", "SDTM conversion specification — Veeva raw to SDTM",
     "Does not exist. The company's Claude Code writes it.",
     "Per EDC build. Must satisfy TEA-CTR-003 and preserve the EDC item-group sequence for lesion-level query matching."),
    ("A-02", "A", "SDTM conversion code and its qualification evidence",
     "Does not exist. The company's Claude Code writes it; a human reviews and qualifies it.",
     "Code, not model output (L3). The qualification evidence is what makes the conversion usable under GxP."),
    ("A-03", "A", "Study protocol configuration — the 28 parameters",
     "Does not exist. Produced by AC-11 from the protocol summary and the charter extract, confirmed by CDM.",
     "Per study. The single most consequential APPLY artifact: every threshold the rules read comes from here."),
    ("A-04", "A", "EDC field map — Item OID to canonical evidence field",
     "Does not exist.",
     "Per EDC build. Without it, query reconciliation degrades to subject-level matching and over-suppresses."),
    ("A-05", "A", "Visit map — EDC event labels to SDTM VISIT / VISITNUM",
     "Does not exist.",
     "Per study. Must keep unscheduled visits distinguishable and must not reorder the sequence."),
    ("A-06", "A", "Subject identifier map — EDC Subject to USUBJID",
     "Does not exist.",
     "Per study. Documented and reversible, and recorded in the run provenance."),
    ("A-07", "A", "Protocol summary document",
     "Does not exist. Prepared manually by the study data manager (OI-07).",
     "Per study. Human-prepared, not model-extracted, because the full protocol exceeds the prompt budget and because the selection rule is a clinical judgement agreed with the Medical Monitor."),
    ("A-08", "A", "Imaging charter extract — charter_config",
     "Does not exist.",
     "Per study. Satisfies TEA-CTR-005. Where it conflicts with the protocol summary, the conflict is reported rather than resolved (L6)."),
    ("A-09", "A", "Study golden dataset from real de-identified data",
     "Does not exist. A synthetic dataset is built here to the same structure.",
     "Per study, for UAT. The synthetic dataset proves the logic; only real data proves the conversion."),
    ("A-10", "A", "Rule activation profile for the study",
     "Does not exist. Derived automatically from which SDTM domains and variables arrived.",
     "Per study per data cut. Must appear on the coverage report of every run — a quiet worklist because inputs were thin is the failure mode this prevents."),
    ("A-11", "A", "Deployment configuration",
     "Does not exist.",
     "Per installation. GLM gateway endpoint, database, authentication, retention. No external egress."),
    ("A-12", "A", "Executed validation evidence for the installation",
     "Does not exist.",
     "Per installation. IQ, OQ, PQ and the traceability matrix instance, against the common approach in C-20."),
    ("A-13", "A", "Query write-back configuration",
     "Does not exist. Optional.",
     "Per EDC build, only if TEA-issued queries are loaded into Veeva. TEA writes its TE- rule id into the Query Rule column so it can recognise its own queries on the next cut."),
    # --- KNOW --------------------------------------------------------------
    ("K-01", "K", "The study protocol",
     "Company provides. Full document; the summary derived from it is A-07.",
     "Source for most of the 28 configuration parameters, the assessment schedule and the treat-beyond-progression policy."),
    ("K-02", "K", "The imaging charter",
     "Company provides.",
     "Source for measurement conventions, reader paradigm and the parameters that a protocol often leaves to the charter. See TEA-CTR-005."),
    ("K-03", "K", "The Veeva EDC study build",
     "Company provides. CRF specification, item OIDs, codelists, edit-check definitions, repeating-group structure.",
     "Everything A-01, A-04 and A-05 are derived from. The repeating-group structure is the part most often missing and most consequential."),
    ("K-04", "K", "A representative Veeva query export",
     "Company provides. One example has been supplied and is profiled in TEA-CTR-004.",
     "The supplied example contains no site-answered queries, so the answer-assessment path is still unexercised. A second export is needed."),
    ("K-05", "K", "SDTM IG version and sponsor SDTM conventions",
     "Company provides. IG version, define.xml standards, controlled terminology release, supplemental-qualifier conventions.",
     "A-01 cannot be written against 'SDTM' in the abstract. The reference design assumed here is on Reference_SDTM."),
    ("K-06", "K", "Sponsor SOPs",
     "Company provides. Data review, query management, change control, computerised system validation.",
     "Determines who signs what, how a finding becomes a query, and what evidence A-12 must contain."),
    ("K-07", "K", "The boundary law itself",
     "This document, carried in with the code.",
     "The company's Claude Code must know it may not edit COMMON. Without this it will helpfully 'fix' a rule to make a study fit, and the fix will be invisible."),
    ("K-08", "K", "DP-01 — the model may never change a verdict",
     "TEA-PLAN-001 Principles; restated in CLAUDE.md.",
     "Applies to the company's Claude Code writing conversion code just as much as to GLM at run time. See L3."),
    ("K-09", "K", "GLM v5.2 is the only run-time model",
     "TEA-SPEC-001 Cover, GLM_Verification.",
     "No external or commercial LLM service, in any component, at any time. Deployment is on-premise with no egress."),
    ("K-10", "K", "Privacy handling and G-06 redaction",
     "TEA-SPEC-001 LLM_Integration; extended by TEA-CTR-004 finding 6.",
     "What may enter a prompt. The query export carries personal data in fields that do not look like they would — birth years in value-before and value-now."),
    ("K-11", "K", "Approval state — rule pack FROZEN at 2.0.0",
     "TEA-SPEC-001 Approval; docs/spec/rule-catalog.yaml.",
     "Changes require change control, a version bump and an impact assessment on findings already issued."),
    ("K-12", "K", "What is still open",
     "TEA-PLAN-001 Open_Items.",
     "OI-03 pilot study, OI-04 QA confirmation, OI-07 protocol summary selection rule, and the two confirmations left on OI-09. The company should not discover these by hitting them."),
    ("K-13", "K", "Target environment",
     "Company provides.",
     "On-premise, containerised, no egress. Python 3.11+, FastAPI, PostgreSQL, React + TypeScript. Confirms or changes the OQ-07 technology assumption."),
]

# ==========================================================================
# Apply_Slots — the detail behind each A- row
# ==========================================================================
SLOTS = [
    ("A-01", "SDTM conversion specification",
     "K-03 EDC build, K-05 SDTM conventions, C-07 TEA-CTR-003",
     "A written mapping from every Veeva form and item to an SDTM domain and variable, covering TU, TR, RS, DM, EX, AE, DS, CM, PR and LB, with the derivation for each standardised variable and the controlled terminology used.",
     "Every R variable in TEA-CTR-003 has a documented source. Every C variable is either mapped or explicitly declared unavailable with the consequence stated.",
     "A conformance run over the specification produces no unmapped R variable, and the rule activation profile it implies is reviewed and accepted by the study team."),
    ("A-02", "SDTM conversion code",
     "A-01, K-03, K-05",
     "Executable conversion, written by the company's Claude Code, reviewed by a human, with unit tests over the mapping rules and a reconciliation report against source record counts.",
     "Deterministic code. No model call in the conversion path at run time (L3). Reproducible: the same input produces byte-identical output.",
     "Tests pass; the reconciliation report balances; a qualification record exists naming the code version and the specification version it implements."),
    ("A-03", "Study protocol configuration",
     "A-07 protocol summary, A-08 charter extract, C-03 guideline profiles",
     "The 28 parameters, each with its value, the document and section it came from, and a confirm-or-correct decision by the CDM.",
     "Every parameter is either taken from a source document with a citation, or explicitly left at the guideline default with that choice recorded.",
     "AC-11 reports no unresolved parameter and no unreported protocol-versus-charter conflict; the CDM has confirmed each checkpoint on screen S7."),
    ("A-04", "EDC field map",
     "K-03 EDC build, C-08 TEA-CTR-004",
     "Item OID to canonical evidence field, including which item group is the repeating lesion group and how its sequence number reaches a lesion.",
     "Covers every item OID that appears in the query export. Unknown OIDs are listed, not silently dropped.",
     "A replay of a real query export against a real data cut produces the expected reconciliation outcome for a reviewed sample, including at least one lesion-level query."),
    ("A-05", "Visit map",
     "K-03 EDC build, K-01 protocol schedule",
     "EDC event label and sequence to SDTM VISIT, VISITNUM and EPOCH, including unscheduled visits and repeating cycles.",
     "Ordering by date and ordering by VISITNUM agree for scheduled visits. Unscheduled visits remain identifiable.",
     "Derived timepoint order matches the clinical sequence for a reviewed sample of subjects, including at least one with an unscheduled assessment."),
    ("A-06", "Subject identifier map",
     "K-03 EDC build, K-05 conventions",
     "EDC Subject to USUBJID, documented and reversible.",
     "One-to-one. The same identifier resolves across SDTM, the query export and the application.",
     "No unmatched subject in a full data cut; the mapping rule is recorded in the run provenance."),
    ("A-07", "Protocol summary",
     "K-01 protocol, OI-07 selection rule",
     "A condensed protocol prepared by hand by the study data manager against a content-selection rule agreed with the Medical Monitor.",
     "Within the AC-11 prompt budget. Carries a content hash that enters the run provenance.",
     "OI-07 selection rule is agreed and followed; the Medical Monitor accepts the summary as sufficient for configuration."),
    ("A-08", "Imaging charter extract",
     "K-02 charter, C-09 TEA-CTR-005",
     "The charter parameters the agent needs, each with the charter section it came from.",
     "Satisfies TEA-CTR-005. Conflicts with the protocol summary are listed, not resolved (L6).",
     "Every R parameter in TEA-CTR-005 is present or explicitly declared absent; conflicts have a study-team decision recorded against them."),
    ("A-09", "Study golden dataset",
     "A-02 conversion, K-06 SOPs, C-18 test framework",
     "A de-identified real data cut with expected findings agreed by CDM and Medical Monitor.",
     "Same structure as the synthetic dataset built here, so the common regression suite runs unchanged.",
     "The agent's output on it is reviewed and accepted; it becomes the study's regression baseline."),
    ("A-10", "Rule activation profile",
     "A-01, A-03, the arriving data cut",
     "Which rules are active, which are deactivated and why, for this study and this cut. Generated, not authored.",
     "Every deactivated rule names the missing input that deactivated it.",
     "It appears on every run's coverage report and is read before the worklist is worked."),
    ("A-11", "Deployment configuration",
     "K-13 environment, K-09 model policy",
     "Gateway endpoint, database, authentication, retention, backup.",
     "No external egress from any component.",
     "An installation qualification record exists and a deterministic-only run completes end to end."),
    ("A-12", "Executed validation evidence",
     "K-06 SOPs, C-20 approach",
     "IQ, OQ, PQ records and the traceability matrix instance for this installation.",
     "Against the common validation approach, not a locally invented one.",
     "QA accepts the package. Note OI-04 — the validation deliverable list is still unconfirmed by QA."),
    ("A-13", "Query write-back configuration",
     "K-03 EDC build, K-06 query SOP",
     "How an accepted finding becomes a Veeva query, and how TEA marks it as its own.",
     "TEA writes its TE- rule id into Query Rule so the next data cut recognises the query as its own (TEA-CTR-004).",
     "A round trip works: TEA raises a query, it appears in the next export, and the agent matches it to the originating finding rather than treating it as new."),
]

# ==========================================================================
# Reference assumptions
# ==========================================================================
REF_SDTM = [
    ("Standard version", "SDTMIG 3.4 with SDTM 2.0; CDISC controlled terminology, a recent quarterly release.",
     "TU, TR and RS have been stable since IG 3.2, so the agent's requirements do not turn on the exact release.",
     "Confirm the IG and terminology release in force. If it predates 3.2, the oncology domains differ and TEA-CTR-003 needs re-checking."),
    ("Domains in scope", "TU, TR, RS as the core. DM, EX, AE, DS, CM, PR, LB as the cross-domain set.",
     "The XD rule family needs the cross-domain set; without it 12 rules deactivate rather than fail.",
     "Confirm which of the cross-domain set the study actually produces, and accept the resulting rule activation profile."),
    ("Lesion identity", "TULNKID assigned once at identification and never reused; TRLNKID matches it exactly.",
     "It is the join the entire agent rests on. 60-plus rules are lesion-level.",
     "Confirm the conversion assigns it at first identification, not per visit. This is the most common conversion defect."),
    ("Measurement structure", "One TR record per lesion per timepoint. TRTESTCD of LDIAM for non-nodal, SAXIS for nodal, TUMSTATE for state.",
     "Nodal short axis versus longest diameter is a correctness issue, not a formatting one: a node measured as LDIAM silently breaks every nodal threshold.",
     "Confirm the EDC collects the axis type, or that the conversion can resolve it from lesion type. See TE-ST-003."),
    ("Units", "TRSTRESN standardised to millimetres, TRSTRESU = mm. TRORRES and TRORRESU retained as collected.",
     "Keeping the original unit is what lets TE-ST-004 catch a centimetre value entered in a millimetre field.",
     "Confirm the original unit is not dropped during standardisation."),
    ("Response records", "RS with RSCAT separating RECIST 1.1 from iRECIST; RSEVAL separating investigator from independent review.",
     "Without RSCAT the two response sets are indistinguishable and the agent may compare an iRECIST response against RECIST logic. Without RSEVAL the two reader streams merge and every lesion is duplicated.",
     "Confirm both are populated whenever the study collects both. This is the assumption most likely to be violated in practice."),
    ("Baseline identification", "EPOCH populated, with SCREENING identifying the baseline assessment; date relative to first dose as the fallback.",
     "Baseline selection changes every percentage the agent computes.",
     "Confirm EPOCH is populated. If not, confirm the fallback rule matches the protocol's baseline definition."),
    ("Dates", "ISO 8601 in --DTC. Partial dates remain partial. Actual assessment dates, not scheduled visit dates.",
     "The agent orders timepoints by date and dates progression from it. A scheduled date silently shifts a progression date.",
     "Confirm the conversion carries the actual date."),
    ("Derived values", "Carried across from source where the EDC collected them; never recomputed during conversion.",
     "The agent compares its own derivation against what the site reported. If the conversion recomputes the sum, the agent is comparing itself with itself and every discrepancy disappears.",
     "Confirm explicitly. This one is easy to get wrong while trying to be helpful."),
    ("Supplemental qualifiers", "SUPPTU carrying the EDC item-group sequence for each lesion record.",
     "New, from TEA-CTR-004 finding 1: it is the only way a Veeva query reaches a specific lesion row.",
     "Confirm with clinical programming that the sequence can be carried. If it cannot, lesion-level query matching is not achievable and the consequence must be accepted explicitly."),
]

REF_STUDY = [
    ("Phase and design", "Phase 2, open-label, two arms, advanced or metastatic solid tumour.",
     "Exercises both arms of the rule pack without the blinding complications of a registrational trial."),
    ("Indication", "NSCLC, with breast cancer as the second profile. Matches the release-1 scope already agreed.",
     "Organ-specific target limits and the nodal rules both get exercised."),
    ("Intervention", "Immune checkpoint inhibitor, with a chemotherapy comparator arm.",
     "Immunotherapy is what makes iRECIST live. A chemotherapy-only study would leave 10 rules untested."),
    ("Response criteria", "RECIST 1.1 as primary, iRECIST applied in the immunotherapy arm.",
     "The dual-criteria case is the hard one, and it is the one RSCAT exists for."),
    ("Assessment schedule", "Baseline within 28 days of first dose; then every 6 weeks for 24 weeks, every 9 weeks thereafter. Window ±7 days.",
     "Gives the assessment-window rules something to check and makes the unscheduled-visit case realistic."),
    ("Confirmation", "Response confirmed no less than 4 weeks after the first response assessment. Progression not confirmed under RECIST 1.1; confirmed under iRECIST at 4 to 8 weeks.",
     "Confirmation windows are the parameter a protocol and a charter most often state differently."),
    ("Imaging", "CT chest, abdomen and pelvis with contrast. Brain MRI at baseline and when clinically indicated. Bone scan where relevant.",
     "Sets slice thickness and measurability expectations, and makes the method-change rules meaningful."),
    ("Reader paradigm", "Investigator assessment for treatment decisions; blinded independent central review for the primary endpoint.",
     "Dual streams. TUEVAL and RSEVAL must separate them or every lesion doubles."),
    ("Treatment beyond progression", "Permitted in the immunotherapy arm under iRECIST, subject to clinical stability.",
     "This is what generates iUPD and iCPD sequences, and the disposition-versus-response cross-domain checks."),
    ("Target lesion caps", "Maximum 5 target lesions in total, maximum 2 per organ. Nodal target if short axis 15 mm or more.",
     "The RECIST 1.1 defaults. A study that changes them changes only configuration, never a rule."),
    ("Measurability", "Non-nodal 10 mm by CT with slice thickness 5 mm or less. Nodes 10 to under 15 mm short axis are non-target; under 10 mm is normal.",
     "The standard thresholds, which the charter is expected to restate and occasionally to tighten."),
    ("Population size", "Around 120 subjects, 25 sites, 4 countries.",
     "Large enough that the prioritisation and cascade grouping matter; small enough to review by hand while building."),
]

REF_CHARTER = [
    ("Reader paradigm", "Two independent readers with a third adjudicating on discordance.",
     "Determines whether the agent sees one response stream or three, and what a disagreement means."),
    ("Adjudication triggers", "Discordance on overall response or on progression date beyond a defined tolerance.",
     "An adjudicated timepoint is evidence of a genuinely hard call; the agent should weight it, not re-litigate it."),
    ("Measurement conventions", "Longest diameter for non-nodal lesions, short axis for nodal. Measurements to one decimal place in millimetres.",
     "Directly sets TRTESTCD and the rounding the agent must tolerate before calling a discrepancy."),
    ("Slice thickness", "5 mm or less for CT. Minimum measurable lesion is twice the slice thickness.",
     "The measurability threshold is a function of acquisition, which is why it lives in the charter rather than the protocol."),
    ("Lesion selection", "Up to 5 target lesions, up to 2 per organ, reproducible and representative of overall disease burden.",
     "Restates the protocol. Where the two disagree, L6 applies — report the conflict."),
    ("Non-measurable disease", "Effusions, ascites, leptomeningeal disease, bone lesions without a soft tissue component, previously irradiated lesions.",
     "Drives the non-target rules and the cytological-confirmation rule TE-RS-021."),
    ("New lesion definition", "Unequivocal new lesion. Equivocal findings require follow-up before a progression call.",
     "This is the judgement the agent escalates to the model rather than deciding, and the charter's wording is the standard it is judged against."),
    ("Non-evaluable handling", "Rules for when a timepoint is not evaluable, and how a missing region is treated.",
     "Determines whether a missing measurement is a finding or an expected gap. Without it the agent queries scans that were never required."),
    ("Confirmation requirements", "Confirmation of response, and the iRECIST confirmation window for progression.",
     "The parameter most likely to differ between the protocol and the charter."),
    ("Progression definition", "20% increase from nadir with a 5 mm absolute minimum; unequivocal non-target progression; new lesion.",
     "The RECIST 1.1 definitions restated. A charter that modifies them is defining a modified criteria set, which the agent must be told about explicitly."),
    ("Image transfer and timing", "De-identification, transfer windows, and the lag between acquisition and read.",
     "Explains why a response record may be absent at a data cut. Prevents the agent querying a read that has not happened yet."),
]

# ==========================================================================
# Handover
# ==========================================================================
HANDOVER = [
    ("1", "This repository — documents, rule catalog, engine code, application, AI guides",
     "Out → in",
     "All three CI guards run and pass inside the company against the carried artifacts. If they do not, the transfer is incomplete."),
    ("2", "The KNOW pack — K-01 to K-06 and K-13",
     "Assembled inside",
     "Each item present and current. A missing item blocks the APPLY slots that depend on it; it does not get worked around."),
    ("3", "A-01 and A-02 — conversion specification, then conversion code",
     "Inside",
     "Conformance against TEA-CTR-003 with no unmapped required variable. Reconciliation against source record counts balances."),
    ("4", "A-03 to A-08 — study configuration and the maps",
     "Inside",
     "AC-11 reports no unresolved parameter; protocol-versus-charter conflicts are listed with a study-team decision on each."),
    ("5", "First deterministic-only run on real data",
     "Inside",
     "Runs end to end with the model switched off entirely. This separates conversion defects from model behaviour, and it should always be the first real run."),
    ("6", "A-09 golden dataset and the first reviewed output",
     "Inside",
     "CDM and Medical Monitor accept the findings as correct, sufficiently explained and correctly prioritised."),
    ("7", "A-11 and A-12 — deployment and validation evidence",
     "Inside",
     "QA accepts the package. OI-04 must be closed before this step, not during it."),
    ("8", "Change requests on COMMON",
     "In → out",
     "Anything the company could not do without editing a COMMON artifact comes back as a change request. A local edit that never returns is how the two halves stop being the same system."),
]


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    # ---- Cover -----------------------------------------------------------
    ws = wb.active
    ws.title = "Cover"
    n = sheet_setup(ws, {"A": 26, "B": 30, "C": 30, "D": 30, "E": 30, "F": 22})
    ws.cell(1, 1, "Tumor Evaluation Review Agent").font = Font(
        name=FACE, size=16, bold=True, color=ACCENT)
    ws.cell(2, 1, "Portability boundary register").font = Font(
        name=FACE, size=12, color=MUTE)
    kv_rows(ws, 4, COVER, ncols=n)

    # ---- Boundary_Law ----------------------------------------------------
    ws = wb.create_sheet("Boundary_Law")
    n = sheet_setup(ws, {"A": 6, "B": 40, "C": 12, "D": 52, "E": 52, "F": 4})
    title_style(ws, "The boundary law", 5,
                "Read this page; the registers are lookup tables. Six rules, and the test that decides which side a "
                "thing belongs on.")
    r = note_block(ws, 4, 5, "THE TEST — " + THE_TEST, fill=WASH, bold=True)
    r += 1
    r = section_label(ws, "The six laws", r)
    laws_spans = [1, 2, 1, 1]
    r = header_row(ws, ["", "Law", "What it means in practice",
                        "Why it is a law and not a preference"], r, laws_spans)
    r = write_rows(ws, LAWS, r, bold_cols=(0, 1), spans=laws_spans)
    r += 1
    r = section_label(ws, "Which side does this belong on? Worked cases",
                      r, "The cases that come up, and the reasoning rather than just the answer.")
    case_spans = [2, 1, 2]
    r = header_row(ws, ["Situation", "Side", "What to do"], r, case_spans)
    r = write_rows(ws, EDGE_CASES, r, bold_cols=(1,), spans=case_spans)

    # ---- Register --------------------------------------------------------
    ws = wb.create_sheet("Register")
    n = sheet_setup(ws, {"A": 8, "B": 7, "C": 44, "D": 56, "E": 76, "F": 4})
    title_style(ws, "Classification register", 5,
                "Every artifact in the system, on one side of the boundary or the other. "
                "C = COMMON, built here and read-only in the company. A = APPLY, the company's Claude Code produces it. "
                "K = KNOW, context it must be given first.")
    r = header_row(ws, ["ID", "Class", "Artifact or requirement", "Where it is",
                        "Why it sits on this side"], 3)
    r = write_rows(ws, REGISTER, r, bold_cols=(0, 2), colour_cols={1: CLASS_COLOUR})

    # ---- Apply_Slots -----------------------------------------------------
    ws = wb.create_sheet("Apply_Slots")
    n = sheet_setup(ws, {"A": 8, "B": 30, "C": 34, "D": 60, "E": 52, "F": 52})
    title_style(ws, "APPLY slots — what the company's Claude Code produces", 6,
                "One row per slot. Each names the KNOW items it needs first, the COMMON contract it must satisfy, and "
                "the test that says it is finished. Law L2: done is a passing test, not a reasonable-looking output.")
    r = header_row(ws, ["ID", "Slot", "Needs first", "What it must produce",
                        "Contract it must satisfy", "Done when"], 3)
    r = write_rows(ws, SLOTS, r, bold_cols=(0, 1))

    # ---- Knowledge_Pack --------------------------------------------------
    ws = wb.create_sheet("Knowledge_Pack")
    n = sheet_setup(ws, {"A": 8, "B": 40, "C": 66, "D": 76, "E": 4})
    title_style(ws, "KNOW pack — what the company's Claude Code must be given", 4,
                "Law L4: an APPLY slot cannot start until the KNOW items it depends on are present. "
                "A missing item halts the work and is reported. It is never inferred or defaulted.")
    r = header_row(ws, ["ID", "What it must know", "Form it arrives in / who provides",
                        "What breaks without it"], 3)
    r = write_rows(ws, [(k[0], k[2], k[3], k[4]) for k in REGISTER if k[1] == "K"],
                   r, bold_cols=(0, 1))

    # ---- Reference sheets ------------------------------------------------
    ws = wb.create_sheet("Reference_SDTM")
    n = sheet_setup(ws, {"A": 26, "B": 60, "C": 64, "D": 64, "E": 4})
    title_style(ws, "Assumed SDTM design", 4,
                "A placeholder so development can proceed without the company's real conventions. Everything here is "
                "replaceable; the fourth column is what the company must confirm or change. None of it is a "
                "requirement — the requirements are TEA-CTR-003.")
    r = header_row(ws, ["Area", "Assumed here", "Why this assumption",
                        "What the company must confirm or change"], 3)
    r = write_rows(ws, REF_SDTM, r, bold_cols=(0,))

    ws = wb.create_sheet("Reference_Study")
    n = sheet_setup(ws, {"A": 26, "B": 74, "C": 84, "D": 4})
    title_style(ws, "Assumed study profile", 3,
                "The reference study the synthetic dataset and the worked examples are built around. Chosen to "
                "exercise the widest part of the rule pack, not to resemble any real study. Replaced by A-03 and "
                "A-07 in the company.")
    r = header_row(ws, ["Area", "Assumed here", "Why it is assumed this way"], 3)
    r = write_rows(ws, REF_STUDY, r, bold_cols=(0,))

    ws = wb.create_sheet("Reference_Charter")
    n = sheet_setup(ws, {"A": 26, "B": 74, "C": 84, "D": 4})
    title_style(ws, "Assumed imaging charter profile", 3,
                "The charter content assumed here. What the agent NEEDS from a charter is TEA-CTR-005 on the "
                "specification; this is the stand-in content, replaced by A-08 in the company.")
    r = header_row(ws, ["Area", "Assumed here", "Why it matters to the agent"], 3)
    r = write_rows(ws, REF_CHARTER, r, bold_cols=(0,))

    # ---- Handover --------------------------------------------------------
    ws = wb.create_sheet("Handover")
    n = sheet_setup(ws, {"A": 8, "B": 56, "C": 16, "D": 84, "E": 4})
    title_style(ws, "Handover order", 4,
                "What moves, in what order, and what is checked on arrival. Steps 3 to 7 are the company's work; "
                "step 8 is the return path that keeps the two halves one system.")
    r = header_row(ws, ["#", "What moves", "Direction", "Checked on arrival"], 3)
    r = write_rows(ws, HANDOVER, r, bold_cols=(0, 1))

    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    p = build()
    c = sum(1 for x in REGISTER if x[1] == "C")
    a = sum(1 for x in REGISTER if x[1] == "A")
    k = sum(1 for x in REGISTER if x[1] == "K")
    print(f"wrote {p}")
    print(f"  register: {c} COMMON, {a} APPLY, {k} KNOW  ({len(REGISTER)} rows)")
    print(f"  {len(SLOTS)} apply slots, {len(LAWS)} laws, {len(EDGE_CASES)} worked cases")
