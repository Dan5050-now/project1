#!/usr/bin/env python3
"""Build the Charter_Requirements sheet (TEA-CTR-005) in TEA-SPEC-001.

The imaging charter is the third configuration input, alongside the protocol
summary and the SDTM delivery, and until now it was not specified at all. It is
authoritative for how lesions are measured and read; the protocol is
authoritative for what the study does. They overlap on roughly a third of the
parameters the agent needs, and in practice they disagree — which is why the
"Also in the protocol?" column exists and why a conflict is reported rather
than resolved (TEA-BND-001 law L6).

Real charters cannot leave the company, so this is written against the general
structure of a BICR imaging charter. The assumed content used for development
is on TEA-BND-001 Reference_Charter; the extract that replaces it in the
company is APPLY slot A-08.

Idempotent: the sheet is dropped and rebuilt.

Usage:  python3 tools/build_charter_requirements_sheet.py
"""
import sys
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tea_style import (ACCENT, CRITICAL, FACE, INFO, INK, MAJOR, MINOR, MUTE,
                       WASH, find_row, header_row, note_block, section_label,
                       sheet_setup, title_style, write_rows)

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "docs" / "spec" / "TEA-SPEC-001_programming-specification.xlsx"
PLAN = REPO / "docs" / "plan" / "TEA-PLAN-001_development-plan.xlsx"

SHEET = "Charter_Requirements"
AFTER = "Query_History"

USE_COLOUR = {"R": CRITICAL, "C": MAJOR, "O": MINOR}
# "Also in the protocol?" — YES means the two documents can disagree.
OVERLAP_COLOUR = {"YES": CRITICAL, "sometimes": MAJOR, "no": INFO}

# --------------------------------------------------------------------------
# Parameter | config field | R/C/O | also in protocol? | agent use | if absent
# --------------------------------------------------------------------------
PARAMS = [
    # --- which criteria are actually in force ------------------------------
    ("Response criteria and version", "criteria_version", "R", "YES",
     "Selects the guideline profile: RECIST 1.1, iRECIST, or both with iRECIST scoped to named arms. Everything else the agent derives follows from this.",
     "Cannot run. There is no safe default — assuming RECIST 1.1 for an iRECIST study produces wrong progression calls, confidently."),
    ("Modifications to the published criteria", "criteria_modifications", "R", "YES",
     "A charter that alters a threshold, a lesion cap or a progression definition has created a modified criteria set. The agent must be told explicitly, because its derivations otherwise implement the published version and every comparison is against the wrong standard.",
     "Assumed none. This is the most dangerous silent assumption in the whole configuration: an unrecorded modification makes the agent disagree with the reader on every affected timepoint, and the agent will look wrong when it is the configuration that is wrong."),
    ("Reader paradigm", "reader_paradigm", "R", "sometimes",
     "Single reader, double read with adjudication, or investigator only. Determines how many response streams exist and what a disagreement between them means.",
     "Streams merge. Every lesion and every response duplicates, and the agent reports discrepancies that are really two readers doing their job."),
    ("Evaluator streams carried in the data", "evaluator_streams", "R", "no",
     "Which of investigator and independent review reach the agent, and how they appear in TUEVAL and RSEVAL. Each stream derives independently and is never compared across streams by a rule.",
     "Cannot separate readers. See TE-RS-020."),
    # --- lesion selection --------------------------------------------------
    ("Maximum target lesions in total", "max_target_lesions", "R", "YES",
     "TE-BL-002 and the target-selection family. RECIST 1.1 default is 5.",
     "Falls back to the guideline default of 5, recorded as a default rather than a source value."),
    ("Maximum target lesions per organ", "max_target_per_organ", "R", "YES",
     "TE-BL-002, TE-IR-006. RECIST 1.1 default is 2.",
     "Falls back to 2, recorded as a default."),
    ("Lesion selection principle", "lesion_selection_rule", "C", "sometimes",
     "Reproducible, measurable, representative of overall disease burden. Used by the model when adjudicating whether a selection was defensible, not by any deterministic rule.",
     "The adjudication prompt loses its standard and falls back to the guideline wording."),
    ("Lesions that split or coalesce", "split_merge_policy", "C", "no",
     "How a target lesion that separates into two, or two that merge, is measured and counted thereafter. RECIST 1.1 is close to silent on this; charters usually are not.",
     "The lesion-count and sum rules see an unexplained change in lesion number and raise a structural finding that is actually correct reader behaviour."),
    ("Previously irradiated lesions", "irradiated_lesion_policy", "C", "sometimes",
     "Whether a lesion in a previously irradiated field may be selected as target. Feeds the XD rules that look at radiotherapy history.",
     "TE-XD rules on prior radiotherapy cannot judge selection and report NOT_EVALUATED."),
    # --- measurability -----------------------------------------------------
    ("Minimum measurable size, non-nodal", "min_measurable_mm", "R", "sometimes",
     "TE-BL-004, TE-BL-014. The threshold below which a lesion is not measurable. RECIST 1.1 default is 10 mm by CT.",
     "Falls back to 10 mm, which is wrong for any study imaging at a coarser slice thickness."),
    ("Minimum nodal short axis for target", "min_nodal_target_mm", "R", "sometimes",
     "TE-BL-005 and the nodal family. RECIST 1.1 default is 15 mm short axis.",
     "Falls back to 15 mm."),
    ("Nodal normal threshold", "nodal_normal_mm", "R", "no",
     "A node under this short axis is normal, which is what complete response of a nodal target requires. RECIST 1.1 default is 10 mm.",
     "Falls back to 10 mm. Complete-response checks are unreliable if the charter set a different threshold."),
    ("Maximum slice thickness", "slice_thickness_max_mm", "R", "no",
     "Measurability is a function of acquisition: the minimum measurable lesion is conventionally twice the slice thickness. This is why measurability belongs to the charter and not the protocol.",
     "The measurability threshold cannot be checked against acquisition. TE-BL-006 and TE-BL-015 deactivate."),
    ("Measurement axis by lesion type", "measurement_axis_rule", "R", "no",
     "Longest diameter for non-nodal, short axis for nodal. Resolves TRTESTCD when the EDC does not collect the axis type explicitly. See TE-ST-003.",
     "Cannot resolve the axis. A node measured as a longest diameter silently breaks every nodal threshold — wrong answers, not missing ones."),
    ("Measurement precision and rounding", "measurement_precision", "C", "no",
     "How many decimal places are recorded and what rounding the reader applies. The agent uses it as the tolerance below which its recomputed sum is not called a discrepancy.",
     "Tolerance falls back to a conservative default. Rounding differences surface as low-confidence findings — noise rather than error."),
    ("Non-measurable disease categories", "non_measurable_categories", "C", "sometimes",
     "Effusions, ascites, leptomeningeal disease, bone lesions without a soft-tissue component. Drives the non-target family and TE-RS-021.",
     "Falls back to the RECIST 1.1 list, which most charters restate unchanged."),
    ("Bone lesion policy", "bone_lesion_policy", "C", "no",
     "Whether a bone lesion with an identifiable soft-tissue component may be a target.",
     "Falls back to the guideline default; charter-specific restrictions go unenforced."),
    # --- acquisition -------------------------------------------------------
    ("Modalities permitted", "modalities_allowed", "R", "sometimes",
     "TE-BL-003, TE-XD-008. Which of CT, MRI, PET-CT and clinical measurement may be used, and for which lesion types.",
     "Method rules deactivate; a lesion measured by an unpermitted modality is not detected."),
    ("Modality consistency requirement", "modality_consistency_rule", "C", "no",
     "Whether a lesion must be followed by the same modality throughout. TE-BL-014 and TE-FU-013 depend on it.",
     "Modality changes mid-study are not flagged, though they are a common and consequential source of apparent change."),
    ("Contrast requirement", "contrast_requirement", "C", "no",
     "Whether contrast is required, and how a non-contrast study is handled.",
     "Contrast findings deactivate; a non-contrast scan reads as equivalent to a contrast one."),
    ("Anatomical coverage per timepoint", "required_regions", "C", "sometimes",
     "Which regions must be imaged at each assessment. This is what separates a genuinely missing measurement from a region that was never required.",
     "TE-FU-002 cannot tell an omission from an intended absence and queries scans that were never in scope."),
    ("Brain imaging policy", "brain_imaging_policy", "C", "YES",
     "Baseline requirement and whether follow-up is scheduled or clinically indicated. Frequently a protocol-versus-charter conflict.",
     "Brain lesion handling falls back to the general rules, which may over-query."),
    # --- response and progression -----------------------------------------
    ("Partial response threshold", "pr_percent_decrease", "R", "no",
     "The derivation engine. RECIST 1.1 default is a 30% decrease from baseline.",
     "Falls back to 30%."),
    ("Progression threshold", "pd_percent_increase", "R", "no",
     "The derivation engine. RECIST 1.1 default is a 20% increase from nadir.",
     "Falls back to 20%."),
    ("Progression absolute minimum", "pd_absolute_min_mm", "R", "no",
     "The 5 mm absolute increase that must accompany the 20%. Omitting it is a classic derivation error, and one of the highest-yield checks in the pack.",
     "Falls back to 5 mm."),
    ("Complete response nodal threshold", "cr_nodal_short_axis_mm", "R", "no",
     "Nodal targets must fall below this short axis for complete response. Default 10 mm.",
     "Falls back to 10 mm."),
    ("New lesion standard", "new_lesion_standard", "R", "sometimes",
     "The wording the charter uses for an unequivocal new lesion, and what happens to an equivocal finding. This is the standard the model is held to when it adjudicates a new-lesion judgement — it is quoted into the prompt, not paraphrased.",
     "The adjudication prompt falls back to the guideline wording, and the model is judged against a standard the readers were not given."),
    ("Non-target progression standard", "nt_progression_standard", "R", "no",
     "The wording for unequivocal non-target progression. Same treatment as the new-lesion standard: it is a declared judgement rule, quoted verbatim.",
     "Falls back to the guideline wording."),
    # --- timing ------------------------------------------------------------
    ("Response confirmation requirement", "confirmation_required", "R", "YES",
     "Whether complete and partial response require confirmation, and the minimum interval. The parameter most likely to differ between the protocol and the charter.",
     "Assumed required at 4 weeks. If the study does not require confirmation this produces a systematic false-finding stream."),
    ("iRECIST confirmation window", "irecist_confirm_window_weeks", "C", "YES",
     "The window in which iUPD must be reassessed to establish or refute iCPD. Typically 4 to 8 weeks. Drives the iRECIST timing rules.",
     "iRECIST timing rules deactivate and report NOT_EVALUATED."),
    ("Assessment schedule and window", "timepoint_windows_days", "C", "YES",
     "The nominal interval and the permitted deviation. Usually the protocol's, sometimes restated by the charter.",
     "Assessment-window rules deactivate. Unscheduled and out-of-window visits are not distinguished."),
    ("Non-evaluable timepoint rules", "non_evaluable_rules", "R", "sometimes",
     "When a timepoint is not evaluable, and how a partially imaged timepoint is scored. Determines whether a gap is a finding or an expected outcome.",
     "Every gap becomes a finding. This is the single largest source of avoidable query volume."),
    ("Image transfer and read lag", "read_lag_days", "C", "no",
     "The expected interval between acquisition and an available central read. The agent uses it to suppress findings about a read that cannot have happened yet at this data cut.",
     "The agent queries missing central responses for scans that are still within the normal reading lag."),
    ("Adjudication trigger", "adjudication_trigger", "O", "no",
     "What sends a timepoint to the adjudicator. An adjudicated timepoint is evidence that the call was genuinely hard; the agent weights its confidence down rather than re-litigating it.",
     "Adjudicated timepoints are treated like any other. Findings against them carry unwarranted confidence."),
]

CONFLICTS = [
    ("Confirmation interval",
     "Protocol says 4 weeks; charter says 28 days from the first response scan.",
     "Usually the same thing stated differently, but not always — 4 weeks from the scan and 4 weeks from the response record differ when the read lags. Report, and let the study team say which."),
    ("Target lesion cap",
     "Protocol restates RECIST 1.1 at 5; charter tightens to 3 for a specific tumour type.",
     "The charter is normally authoritative for reading, but the protocol drives the endpoint definition. This is exactly the case where guessing is wrong — report it."),
    ("Measurability threshold",
     "Protocol says 10 mm; charter says twice the slice thickness, and the study images at 7 mm.",
     "The charter's rule is stricter and is the one the readers followed. The agent must use 14 mm, but only after the conflict has been seen and decided."),
    ("Brain imaging",
     "Protocol requires baseline brain MRI for all; charter says when clinically indicated.",
     "Changes whether a missing baseline brain scan is a protocol deviation or expected. Both readings produce findings; only one is right."),
    ("iRECIST scope",
     "Protocol applies iRECIST to the immunotherapy arm; charter applies it to all subjects.",
     "Determines which response set the agent derives per subject. Getting this wrong misclassifies every progression in the comparator arm."),
]

HOW_IT_RESOLVES = [
    "The charter extract (A-08) and the protocol summary (A-07) are both read by AC-11, independently.",
    "Every parameter records which document it came from, and the section within it.",
    "Where both documents supply a parameter and the values agree, the parameter is set and the agreement is recorded — that agreement is itself evidence.",
    "Where both supply it and the values disagree, the parameter is left UNRESOLVED. The run does not start with an unresolved parameter that a live rule depends on.",
    "The conflict is presented on screen S7 with both values, both citations, and the rules that depend on it. The study team decides; the decision and the person are recorded in the run provenance.",
    "Where only one document supplies it, that value is used and the single source is recorded.",
    "Where neither does, the guideline default applies and is recorded AS a default — never as a source value. The distinction matters at audit.",
]


def build_sheet(wb):
    if SHEET in wb.sheetnames:
        del wb[SHEET]
    ws = wb.create_sheet(SHEET, wb.sheetnames.index(AFTER) + 1)
    sheet_setup(ws, {"A": 38, "B": 30, "C": 7, "D": 11, "E": 84, "F": 56, "G": 4})

    title_style(
        ws, "Imaging charter requirements", 6,
        "TEA-CTR-005. What the agent needs from the imaging charter — the third configuration input, alongside the "
        "protocol summary and the SDTM delivery. The charter is authoritative for how lesions are measured and read; "
        "the protocol is authoritative for what the study does. Written against the general structure of a BICR "
        "charter, since real charters cannot leave the company. The extract that satisfies it is APPLY slot A-08.")

    header_row(ws, ["Charter parameter", "Configuration field", "R/C/O",
                    "Also in the protocol?", "What the agent uses it for",
                    "If absent"], 3)
    ws.freeze_panes = "E4"
    r = write_rows(ws, PARAMS, 4, bold_cols=(0, 1),
                   colour_cols={2: USE_COLOUR, 3: OVERLAP_COLOUR})

    r += 1
    c = ws.cell(r, 1, "R = required; without it the run stops or a named derivation is wrong.   "
                      "C = conditional; its absence deactivates a named behaviour, which is reported.   "
                      "O = optional.   "
                      "\"Also in the protocol?\" YES means both documents routinely state it and can disagree — "
                      "see the conflict section below.")
    c.font = Font(name=FACE, size=9, italic=True, color=MUTE)
    c.alignment = Alignment(vertical="top", wrap_text=True)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    ws.row_dimensions[r].height = 30
    r += 2

    r = section_label(
        ws, "When the protocol and the charter disagree", r,
        "Eight of the 34 parameters are routinely stated in both documents and another ten sometimes are, so "
        "up to half can disagree. TEA-BND-001 law L6: a conflict is a finding, not a choice. Silently "
        "preferring either document buries a real protocol-deviation risk in a configuration file.")
    spans = [2, 2, 2]
    header_row(ws, ["Parameter", "How they typically disagree",
                    "Why it cannot be resolved automatically"], r, spans)
    r = write_rows(ws, CONFLICTS, r + 1, bold_cols=(0,), spans=spans)
    r += 1

    r = section_label(ws, "How a parameter is resolved", r)
    for i, line in enumerate(HOW_IT_RESOLVES, 1):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        c = ws.cell(r, 1, f"{i}.  {line}")
        c.font = Font(name=FACE, size=9, color=INK)
        c.alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[r].height = 28 if len(line) > 150 else 15
        r += 1
    r += 1

    note_block(ws, r, 6,
               "NOT A RULE CHANGE. The conflict check is a configuration-time behaviour of AC-11 and AC-02, not a "
               "review point. The rule pack stays FROZEN at 2.0.0 and no TE- rule is added, amended or renumbered by "
               "this sheet. If experience at Step 3 shows the conflict check belongs in the rule pack, that goes "
               "through rule change control at that point.", fill=WASH, bold=True)
    return ws


def amend_related(wb):
    cov = wb["Cover"]
    cov.cell(8, 2).value = "2.7.0 — APPROVED, imaging charter requirements"
    cov.cell(12, 2).value = "v2.6.0, issued 2026-09-12"

    ic = wb["Input_Contract"]
    row = find_row(ic, "charter_config")
    for col, val in enumerate(
            ["charter_config", "criteria_version, criteria_modifications, reader_paradigm, measurability and "
             "response thresholds, non-evaluable rules, source citations", "object", "yes",
             "NEW v2.7.0. The imaging charter extract. See Charter_Requirements (TEA-CTR-005). Produced in the "
             "company as APPLY slot A-08. Where it and protocol_summary disagree, AC-11 reports the conflict and "
             "leaves the parameter unresolved rather than choosing."], start=1):
        c = ic.cell(row, col, val)
        c.font = Font(name=FACE, size=9, color=INK)
        c.alignment = Alignment(vertical="top", wrap_text=True)

    cts = wb["Contents"]
    row = find_row(cts, SHEET)
    for col, val in enumerate(
            ["Charter_Requirements", "What the agent needs from the imaging charter",
             f"=COUNTA({SHEET}!A4:A37)", "NEW", "TEA-CTR-005 — feeds A-08"], start=1):
        c = cts.cell(row, col, val)
        c.font = Font(name=FACE, size=9, color=INK)
        c.alignment = Alignment(vertical="top", wrap_text=True)


def amend_plan():
    wb = load_workbook(PLAN)
    wb["Cover"].cell(8, 2).value = "1.7.0"
    wb["Cover"].cell(11, 2).value = "v1.6.0, issued 2026-09-12"
    wb["Cover"].cell(18, 2).value = "TEA-SPEC-001 v2.7.0 — APPROVED, rule pack frozen at 2.0.0"

    oi = wb["Open_Items"]
    row = find_row(oi, "OI-10")
    for col, val in enumerate(
            ["OI-10",
             "Imaging charter access and extract. TEA-CTR-005 defines what the agent needs from the charter; the "
             "extract itself is APPLY slot A-08 and cannot be produced outside the company. Eight of the 34 "
             "parameters are routinely stated in the protocol too, and ten more sometimes are, so up to half "
             "can disagree.",
             "Until a real charter is read, the conflict-resolution path (AC-11 leaving a parameter unresolved and "
             "asking the study team) is specified but unexercised. It is also the path that most affects "
             "configuration correctness.",
             "CDM + Medical Monitor", "Before Step 3 output is reviewed"], start=1):
        c = oi.cell(row, col, val)
        c.font = Font(name=FACE, size=9, color=INK)
        c.alignment = Alignment(vertical="top", wrap_text=True)
    wb.save(PLAN)
    return PLAN


def main():
    wb = load_workbook(SPEC)
    build_sheet(wb)
    amend_related(wb)
    wb.save(SPEC)
    print(f"wrote {SPEC.name} — {SHEET} with {len(PARAMS)} parameters, "
          f"{sum(1 for p in PARAMS if p[3] == 'YES')} shared with the protocol, "
          f"{len(CONFLICTS)} worked conflicts")
    p = amend_plan()
    print(f"wrote {p.name} — OI-10 added")
    return 0


if __name__ == "__main__":
    sys.exit(main())
