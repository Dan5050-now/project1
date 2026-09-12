#!/usr/bin/env python3
"""Build the Query_History sheet (TEA-CTR-004) in TEA-SPEC-001, and the edits
elsewhere in the workbook that it forces.

TEA-CTR-004 is derived from a real Veeva EDC Query Detail export supplied on
2026-09-12 (study A101-1001_TST5, 69 rows, 54 columns). Daniel's instruction
with that file was that the export format will change as Veeva releases new
versions, so the contract is written to survive that: the adapter binds by
column name, ignores columns it does not know, and fails loudly on a required
column or an unrecognised controlled value rather than guessing.

Idempotent: the sheet is dropped and rebuilt, and the other edits set cells to
fixed values. Re-running produces the same workbook.

Usage:  python3 tools/build_query_history_sheet.py
"""
import sys
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "docs" / "spec" / "TEA-SPEC-001_programming-specification.xlsx"
PLAN = REPO / "docs" / "plan" / "TEA-PLAN-001_development-plan.xlsx"

SHEET = "Query_History"
AFTER = "SDTM_Requirements"

# Palette carried from the workbook already in the repository.
INK = "16201C"
ACCENT = "1D4A3A"
MUTE = "6B7770"
PAPER = "F6F7F5"
CRITICAL = "8C2F39"
MAJOR = "B06A1F"
MINOR = "4A6B8A"

FACE = "Arial"

USE_COLOUR = {"R": CRITICAL, "C": MAJOR, "O": MINOR, "–": MUTE}


def title_style(ws, text, ncols, subtitle=None):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    c = ws.cell(1, 1, text)
    c.font = Font(name=FACE, size=13, bold=True, color=ACCENT)
    c.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 26
    if subtitle:
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
        c = ws.cell(2, 1, subtitle)
        c.font = Font(name=FACE, size=9, color=MUTE)
        c.alignment = Alignment(vertical="center", wrap_text=True)
        ws.row_dimensions[2].height = 26


def header_row(ws, labels, row, spans=None):
    spans = spans or [1] * len(labels)
    col = 1
    for label, span in zip(labels, spans):
        c = ws.cell(row, col, label)
        c.font = Font(name=FACE, size=9, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=ACCENT)
        c.alignment = Alignment(vertical="center", wrap_text=True)
        for k in range(1, span):
            ws.cell(row, col + k).fill = PatternFill("solid", fgColor=ACCENT)
        if span > 1:
            ws.merge_cells(start_row=row, start_column=col,
                           end_row=row, end_column=col + span - 1)
        col += span
    ws.row_dimensions[row].height = 30


def section_label(ws, text, row):
    c = ws.cell(row, 1, text)
    c.font = Font(name=FACE, size=11, bold=True, color=ACCENT)
    return row + 1


def write_rows(ws, rows, start, bold_cols=(), colour_cols=None, zebra=True, spans=None):
    """Write data rows. colour_cols maps a 0-based column index to a dict of
    cell-value -> hex colour. spans gives each logical column a width in physical
    columns, so a secondary table can use a layout of its own on a sheet whose
    column widths were set for the main table."""
    colour_cols = colour_cols or {}
    spans = spans or [1] * max(len(r) for r in rows)
    r = start
    for n, row in enumerate(rows):
        band = zebra and n % 2 == 1
        col = 1
        for i, val in enumerate(row):
            c = ws.cell(r, col, val)
            colour = INK
            if i in colour_cols:
                colour = colour_cols[i].get(str(val), INK)
            c.font = Font(name=FACE, size=9, bold=(i in bold_cols or i in colour_cols),
                          color=colour)
            c.alignment = Alignment(vertical="top", wrap_text=True)
            if spans[i] > 1:
                ws.merge_cells(start_row=r, start_column=col,
                               end_row=r, end_column=col + spans[i] - 1)
            if band:
                for k in range(spans[i]):
                    ws.cell(r, col + k).fill = PatternFill("solid", fgColor=PAPER)
            col += spans[i]
        set_merged_row_height(ws, r, row, spans)
        r += 1
    return r


# Excel auto-fits row height for wrapped text only in unmerged cells. Every
# secondary table here merges its cells, so the height has to be computed or the
# text is clipped on open — which no check in the repository would catch.
CHARS_PER_WIDTH_UNIT = 0.90   # deliberately pessimistic: word wrap breaks lines early
POINTS_PER_LINE = 12.5


def set_merged_row_height(ws, row, values, spans):
    if all(s == 1 for s in spans):
        return                      # unmerged: let Excel auto-fit
    widths = [ws.column_dimensions[chr(64 + c)].width or 8.43
              for c in range(1, sum(spans) + 1)]
    lines, col = 1, 0
    for val, span in zip(values, spans):
        usable = sum(widths[col:col + span]) * CHARS_PER_WIDTH_UNIT
        text = str(val or "")
        lines = max(lines, -(-len(text) // max(1, int(usable))))
        col += span
    # One spare line: over-sizing a row costs nothing, clipping loses content.
    ws.row_dimensions[row].height = min(409, (lines + 1) * POINTS_PER_LINE + 4)


# --------------------------------------------------------------------------
# Section 1 — the column map.
# Export column | Canonical field | R/C/O | In the 2026-09-12 export |
# What the agent does with it | If absent
# --------------------------------------------------------------------------
COLUMNS = [
    # --- identity and scope -------------------------------------------------
    ("Study", "study_id", "R", "A101-1001_TST5 — note the filename says A001-1001. The column wins; never parse the filename.",
     "Checked against the study_id on the SDTM delivery before any rule runs. A query file from a different study is a wrong-data event, not a warning.",
     "Fail the run."),
    ("Site", "site_id", "C", "5 sites across 4 countries.",
     "Scopes the site-facing worklist and lets a reviewer see query load per site.",
     "Matching still works on subject alone. The per-site view is lost."),
    ("Subject", "subject_id", "R", "23 subjects, e.g. A0019501001.",
     "The first matching key. Must be the same identifier as SDTM USUBJID, or mapped to it by a documented, reversible rule recorded in the run provenance.",
     "Fail the run. Reconciliation is impossible without it."),
    ("Subject Status", "subject_status", "O", "Enrolled, In Screening, Screen Failure.",
     "Suppresses query aging on screen failures, which would otherwise accumulate TE-QM-004 findings nobody intends to action.",
     "TE-QM-004 counts screen-failed subjects. Noise, not error."),
    ("Country", "site_country", "O", "Australia, South Korea, Spain, United States.",
     "Evidence display only. Never used for matching.",
     "No effect."),
    # --- visit / form / field scope ----------------------------------------
    ("Event Group Label", "visit_group", "C", "Screening only — this export covers one event group.",
     "Second matching key with Event Label. Must reconcile to SDTM VISIT through the study visit map.",
     "Matching degrades to subject + field, which over-suppresses: a query on one visit can hide a finding on another."),
    ("Event Label", "visit_name", "R", "Screening.",
     "The visit a query sits on. Together with Subject and Item OID this is the structural match.",
     "Fail the run."),
    ("Event Group Sequence Number", "visit_occurrence", "C", "1 throughout.",
     "Distinguishes repeating cycles. Required as soon as the study has a repeating event group, which every oncology tumour-assessment schedule does.",
     "Cycles collapse. A query on cycle 2 suppresses a finding on cycle 5. This is the most likely silent failure in the whole contract."),
    ("Event Date", "visit_date", "C", "10 distinct dates, ISO-8601 date only.",
     "Confirms the query's visit is the visit the finding is on, where visit labels repeat.",
     "Falls back to the visit label alone."),
    ("Form Label", "form_name", "C", "Essential Information.",
     "Narrows to the CRF page. Needed where one visit carries several forms feeding the same SDTM domain.",
     "Matching degrades to visit + field."),
    ("Form Sequence Number", "form_occurrence", "C", "1 throughout.",
     "Repeating forms, in designs that put one form per lesion rather than one repeating group.",
     "Same failure as Item Group Sequence Number, for those designs."),
    ("Form Status", "form_status", "O", "In Edit, Submitted.",
     "Evidence only. A finding against an In Edit form is de-prioritised — the site has not finished with it.",
     "No effect."),
    ("Item Group Label", "item_group", "C", "Demographic Information, Enrollment Information.",
     "Names the repeating group a query belongs to. With the sequence number, this is how a query reaches one specific lesion row.",
     "Lesion-level matching is lost."),
    ("Item Group Sequence Number", "item_group_seq", "R*", "1 on every row — the forms in this sample do not repeat, so this export does not exercise the field at all.",
     "THE LESION KEY. On a tumour form this is the repeating-row number, and it is the only thing in the export that says which lesion a query is about. TEA-CTR-003 must therefore preserve it through the SDTM conversion so it can be joined to TULNKID. See finding 1 below.",
     "Every lesion query matches every lesion finding at that visit. Mass false suppression of real findings — the worst outcome the agent can produce."),
    ("Item OID", "field_id", "R", "6 values: BRTHDAT, DMENDAT, DMSFREAS2, ETHNIC, LBSEX, RACE.",
     "Third matching key. Mapped to the canonical evidence field names through a study-level field map maintained beside the visit map.",
     "Fail the run. Structural matching is impossible."),
    ("Item Label", "field_label", "O", "One label per Item OID.",
     "Evidence display, so a reviewer sees the question the site saw.",
     "No effect."),
    # --- query core ---------------------------------------------------------
    ("Query ID", "query_id", "R", "69 unique, VV-nnnnnn.",
     "The stable handle shown to the reviewer and stored on the finding link. Also the dedupe key for the query side of reconciliation.",
     "Fail the run."),
    ("Query Vault ID", "query_uid", "O", "69 unique, OPW-prefixed.",
     "Internal Vault key. Kept so a finding can be traced back to the EDC record during an audit.",
     "No effect."),
    ("Query Status", "status", "R", "Open (64) and Closed (5) ONLY. No Answered row appears — see finding 2.",
     "Drives the entire reconciliation branch. Mapped through the status table below; an unrecognised value fails the run.",
     "Fail the run."),
    ("Restricted Query", "is_restricted", "R", "No on every row, although the filename is marked RESTRICTED.",
     "A restricted query may carry access-controlled content. Restricted rows load as existence-only — id, status, scope and dates — with every free-text field dropped before the record leaves the adapter.",
     "Treated as restricted. Failing safe costs some matching quality; failing open leaks."),
    ("Query Team", "owning_team", "O", "Data Management.",
     "Evidence and routing of the resulting finding.",
     "No effect."),
    ("Manual Query", "is_manual", "R", "No on every row — all 69 are system edit checks.",
     "Separates EDC edit checks from human queries. Only a manual query carries a person's reasoning, and only a manual query can be one TEA itself raised.",
     "Everything is treated as manual, which weakens the TEA-origin test and sends system query text to the model needlessly."),
    ("Query Rule", "source_rule_id", "R", "6 values: DM_002, DM_003, DM_007, DM_008, DM_010, R_QUERY_DMENDAT_FD.",
     "Two jobs. (a) Exact-match key for a query TEA itself raised: TEA writes its TE- rule id here. (b) Tells the agent an EDC edit check already covers a field, so it does not duplicate the sponsor's own programming.",
     "Exact matching degrades to structural and semantic only, and TEA cannot recognise its own prior queries."),
    ("Number of Query Messages", "message_count", "O", "1 on every open row, 2 on every closed row.",
     "A thread with more than two messages contains a conversation and is flagged for a human look regardless of the automated assessment.",
     "No effect."),
    ("Days Unresolved", "(deliberately not mapped)", "–", "Open rows = listing date − created. Closed rows = closed − created. Exactly reproducible from the other columns.",
     "DO NOT USE. It is computed against Last Run of Listing, not against the agent's data-cut date. TE-QM-004 recomputes aging from Query Created Date against the run's as-of date. See finding 5.",
     "n/a — the agent never reads it."),
    # --- text ---------------------------------------------------------------
    ("Original Query Text", "query_text", "R", "4 distinct system-generated texts.",
     "Input to P-MATCH-QUERY and P-ASSESS-ANSWER, inside the untrusted-data envelope (DP-07).",
     "Semantic matching deactivates. Exact and structural matching still work, so the run continues degraded rather than failing."),
    ("Original Query Text in English", "query_text_en", "C", "Identical to Original Query Text here — this study runs in English.",
     "The column the model actually reads, so a query raised in the site's language is still assessable by GLM v5.2.",
     "Falls back to Original Query Text, and a non-English query then reaches the model in its own language."),
    ("Original Query Text in the Base Language", "query_text_base", "O", "Identical to Original Query Text here.",
     "Shown to the reviewer when the study base language is not English.",
     "Falls back to Original Query Text."),
    ("Latest Query Comment", "latest_message_text", "O", "A COPY of the original query text on 64 rows; blank on all 5 closed rows.",
     "TRAP — this is not the site's answer. It is the most recent message on the thread, which for a system query is the query itself. It must never be passed to P-ASSESS-ANSWER. Carried for display only. See finding 3.",
     "No effect."),
    ("Latest Query Answer Text", "answer_text", "C", "EMPTY on all 69 rows.",
     "The only field carrying the site's reply, and the sole input to P-ASSESS-ANSWER and so to TE-QM-002 and TE-QM-005.",
     "JUSTIFIED_BY_ANSWER becomes unreachable. Every closed query whose finding still evaluates true becomes ANSWERED_UNRESOLVED and is surfaced. Safe, but noisier — and it means the answer path is untested. See finding 2."),
    # --- data change --------------------------------------------------------
    ("Item Value Changed", "value_changed", "R", "Yes on 4 rows, No on 65.",
     "DETERMINISTIC answer to 'was the data actually corrected?'. Removes the model from part of TE-QM-002 and from all of TE-QM-006. See finding 4.",
     "Falls back to comparing the current SDTM value against the finding — weaker, and unavailable for any EDC field SDTM does not carry."),
    ("Query Caused Data Change", "change_attributed_to_query", "R", "Identical to Item Value Changed on all 69 rows, so this export cannot show the two diverging.",
     "Separates a correction made in response to the query from an unrelated edit that happened to land on the same field. TE-QM-006 needs the distinction.",
     "Falls back to Item Value Changed alone, which over-credits the query."),
    ("Item Value Before Query", "value_before", "C", "Populated only on the 4 changed rows. PERSONAL DATA — three of the four are birth years.",
     "Evidence: shows the reviewer what was corrected. Redacted by guardrail G-06 before any prompt is assembled. See finding 6.",
     "Evidence display loses the before value; no rule is affected."),
    ("Item Value Now", "value_after", "C", "Populated only on the 4 changed rows.",
     "Cross-checked against the SDTM value for the same field. A mismatch means the query export and the SDTM cut are not from the same point in time, which invalidates every reconciliation outcome in the run.",
     "The cut-alignment check deactivates and a stale query file goes undetected."),
    ("Value Confirmed", "value_confirmed", "O", "Empty on all 69 rows.",
     "Site confirmed the value as correct without changing it. Direct, non-LLM evidence for JUSTIFIED_BY_ANSWER where it is populated.",
     "Falls back to assessing the answer text."),
    ("Observed Source Value", "source_value", "O", "Empty on all 69 rows.",
     "Source-data-verification value. Not used by any rule.",
     "No effect."),
    # --- lifecycle ----------------------------------------------------------
    ("Query Created Date", "opened_at", "R", "ISO-8601 UTC to the minute, e.g. 2026-01-17T01:04Z. Range 2026-01-17 to 2026-07-01.",
     "Aging (TE-QM-004, recomputed — see Days Unresolved) and the ordering that the recurrence test depends on.",
     "Fail the run."),
    ("Query Created By", "opened_by", "O", "System on every row.",
     "Evidence, and a cross-check on Manual Query.",
     "No effect."),
    ("Created By Query Team", "opened_by_team", "O", "Data Management.",
     "Evidence.",
     "No effect."),
    ("Created By Role", "opened_by_role", "O", "Empty on all 69 rows.",
     "Evidence.",
     "No effect."),
    ("Query Answered Date", "answered_at", "C", "EMPTY on all 69 rows.",
     "Orders the thread, and tells the agent whether the site's answer preceded or followed the data change — which is what separates 'corrected as promised' from 'corrected, then explained away'.",
     "Answer ordering falls back to the closed date, losing that distinction."),
    ("Query Answered By", "answered_by", "O", "Empty on all 69 rows.",
     "Evidence.",
     "No effect."),
    ("Answered By Role", "answered_by_role", "O", "Empty on all 69 rows.",
     "Evidence. Would distinguish an investigator's answer from a study coordinator's, which matters for a medical judgement.",
     "No effect on any rule."),
    ("Answered By Query Team", "answered_by_team", "O", "Empty on all 69 rows.",
     "Evidence.",
     "No effect."),
    ("Query Closed Date", "closed_at", "C", "Populated on the 5 closed rows.",
     "Required whenever status is Closed. Feeds the RECURRENT test and the aging recomputation.",
     "Recurrence detection degrades to run-to-run comparison only."),
    ("Query Closed By", "closed_by", "O", "System on all 5 closed rows.",
     "A close by System is an auto-close triggered by the data change, NOT a site-accepted resolution. The agent must not read it as agreement. Where the closer is a person, the close carries more weight.",
     "The auto-close signal is lost and a system close is treated as a human one."),
    ("Closed By Query Team", "closed_by_team", "O", "Data Management on the 5 closed rows.",
     "Evidence.",
     "No effect."),
    ("Closed By Role", "closed_by_role", "O", "Empty on all 69 rows.",
     "Evidence.",
     "No effect."),
    # --- export metadata ----------------------------------------------------
    ("Last Run of Listing", "export_as_of", "R", "2026-09-12 11:40 on every row. No timezone in the value; the filename says KST. See finding 5.",
     "The as-of timestamp of the query file. Compared against the SDTM cut date: a gap beyond the configured tolerance warns, because a stale query file manufactures false NEW findings. Enters the run provenance with the file's SHA-256.",
     "Fail the run. A query file with no as-of date cannot be safely reconciled against a data cut."),
    # --- present but unused -------------------------------------------------
    ("Visit Method", "—", "–", "Empty on all 69 rows.",
     "Not used. On-site versus remote visit; no rule depends on it.",
     "No effect."),
    ("Source Type", "—", "–", "Empty on all 69 rows.",
     "Reserved for externally sourced data (e.g. a lab feed). Not used.",
     "No effect."),
    ("Source System Name", "—", "–", "Empty on all 69 rows.",
     "Not used.",
     "No effect."),
    ("Source User", "—", "–", "Empty on all 69 rows.",
     "Not used.",
     "No effect."),
    ("Source ID", "—", "–", "Empty on all 69 rows.",
     "Not used.",
     "No effect."),
]

# --------------------------------------------------------------------------
# Section 2 — status vocabulary.
# --------------------------------------------------------------------------
STATUS = [
    ("Open", "OPEN", "64 of 69",
     "DUPLICATE_OPEN. The finding is linked to the query and suppressed from the default worklist. TE-QM-001 records it; TE-QM-004 ages it.",
     "Confirmed by this export."),
    ("Answered", "ANSWERED", "0 — never appears",
     "Answer-assessment branch: P-ASSESS-ANSWER runs and TE-QM-002 / TE-QM-005 apply.",
     "NOT confirmed. The value is assumed from the Veeva data model and must be verified against an export that contains site-answered queries before Step 3 closes."),
    ("Closed", "CLOSED", "5 of 69",
     "Answer-assessment branch, with one deterministic short-circuit: where Query Closed By is System AND Query Caused Data Change is Yes, the close is an auto-close on correction. The outcome is RESOLVED_BY_CORRECTION and the model is not called at all.",
     "Confirmed by this export — all 5 closed rows are exactly this case."),
    ("Cancelled, or any other value", "— (no mapping)", "0",
     "The run fails before any rule executes, naming the column, the value and the affected Query IDs.",
     "Deliberate. These vocabularies are small and stable; a new value is a specification event, not something to guess at. See adapter rule 6."),
]

# --------------------------------------------------------------------------
# Section 3 — adapter rules.
# --------------------------------------------------------------------------
ADAPTER = [
    ("1. Bind by column name, never by position.",
     "The export is a flat CSV with a header row and no BOM (ASCII in this sample; read as UTF-8 with a BOM tolerated). Column order is not part of the contract and a future EDC version is free to change it."),
    ("2. Match header names leniently, values strictly.",
     "Header matching trims surrounding whitespace, collapses internal runs of spaces and ignores case. Everything after that — controlled values, date formats — is matched exactly."),
    ("3. Ignore columns the adapter does not know, and list them in the run log.",
     "This is what lets a new EDC version add columns without breaking a validated run. Silently dropping them would be worse: the log entry is how anyone notices there is new information available."),
    ("4. Fail the run on a missing R column, before any rule executes.",
     "Naming the column. A partial reconciliation is more dangerous than none, because a missing key produces false suppressions that look like a clean data set."),
    ("5. Deactivate, report and continue on a missing C column.",
     "The dependent behaviour switches off and says so on the coverage report. Never silently — 'if absent' in the table above is the reviewer-facing text."),
    ("6. Fail the run on an unrecognised value in a controlled column.",
     "Query Status, Manual Query, Restricted Query, Item Value Changed and Query Caused Data Change. An operational override exists for an urgent cut: it maps the unknown value to OPEN_UNRECOGNISED, suppresses nothing, and marks every affected finding unreconciled. The override is off by default and is recorded in the run provenance."),
    ("7. Empty is unknown, not false.",
     "A blank Yes/No cell must not become False. Five of these columns are entirely empty in this export, and treating blank as No would have silently asserted things the file never said."),
    ("8. Never parse the filename.",
     "The filename in this sample says A001-1001 while the Study column says A101-1001_TST5. The columns are the contract; the filename is not."),
    ("9. Stamp the run with the adapter version, the file SHA-256 and Last Run of Listing.",
     "Reconciliation outcomes are only reproducible if the exact query file is identifiable. This is an ALCOA+ requirement, not a convenience."),
    ("10. Treat every text field as untrusted input (DP-07).",
     "Query text, comments and answers originate outside the trust boundary. They are passed to GLM v5.2 inside an explicit data envelope, with instruction-like content flagged, and they can never alter a deterministic verdict."),
]

# --------------------------------------------------------------------------
# Section 4 — what the real export changed.
# --------------------------------------------------------------------------
FINDINGS = [
    ("1. Nothing in the export identifies a lesion.",
     "A query points at (subject, visit, form, item group sequence, item OID). There is no lesion id. For a repeating tumour form, Item Group Sequence Number is the ONLY thing that says which lesion row a query sits on — and in this export it is 1 on every row, because the forms sampled do not repeat, so the mechanism is entirely untested. "
     "Consequence for TEA-CTR-003: the SDTM conversion must preserve the EDC item-group sequence alongside TULNKID, or lesion-level query matching is impossible and every lesion query at a visit will suppress every lesion finding at that visit. Added to the SDTM requirements as a conversion obligation.",
     "ACTION — confirm with clinical programming that the sequence survives the conversion."),
    ("2. This export contains no site answers at all, so the answer path is unexercised.",
     "Latest Query Answer Text, Query Answered Date, Query Answered By, Answered By Role and Answered By Query Team are empty on all 69 rows, and no row carries status Answered. All 69 are system edit checks (Manual Query = No, Query Created By = System) and the 5 closed ones were auto-closed on data change. "
     "P-ASSESS-ANSWER, TE-QM-002 and TE-QM-005 — the LLM-adjudicated part of the query model — therefore have no example to build or test against. Two possibilities need separating: this listing does not populate the answer columns, or this study genuinely has no answered queries yet.",
     "ACTION — a second export containing manual, site-answered queries is needed before Step 3 can test the answer path."),
    ("3. Latest Query Comment is not the answer, and looks exactly like one.",
     "On 64 of 69 rows it is a verbatim copy of Original Query Text, and it is blank on every closed row. It is the latest message on the thread, which for a system query is the query itself. "
     "An implementation that reaches for the obviously-named field would feed the agent's own query text to P-ASSESS-ANSWER as if it were the site's reply, and the model would dutifully assess it. Recorded here so the adapter is written against the real semantics.",
     "CLOSED by this contract — the field is display-only."),
    ("4. Part of TE-QM-002 becomes deterministic.",
     "Item Value Changed and Query Caused Data Change answer 'was the data actually corrected, and because of this query?' as a fact carried by the EDC, in a single cut. The approved design assumed this needed either LLM judgement (TE-QM-002) or a run-to-run diff (TE-QM-006). "
     "Under DP-01 the deterministic answer must win: where these columns are present, the correction fact is read, not inferred, and the model is asked only the question it is actually needed for — whether the site's reasoning justifies data that was NOT corrected. TE-QM-006 loses its two-run dependency entirely.",
     "CHANGE CONTROL — the rule pack is FROZEN at 2.0.0 and no rule text, message or base rate is changed here. This is recorded as a proposed implementation refinement, to be confirmed with evidence at the Step 3 gate and taken through rule change control at that point if it alters the stated logic of TE-QM-002 or TE-QM-006."),
    ("5. Days Unresolved is measured against the export, not against the data cut.",
     "It is exactly reproducible: closed − created for closed rows, listing date − created for open ones. In this sample the open rows read 73 to 221 days because the listing ran on 12 September, months after the queries opened. "
     "If the query file and the SDTM cut are from different dates — which is normal, they are pulled separately — an aging rule that trusts this column measures from the wrong reference. TE-QM-004 recomputes from Query Created Date against the run's as-of date. Separately, Last Run of Listing carries no timezone in the value while the filename says KST; the adapter requires the timezone as configuration and records it in the provenance.",
     "CLOSED by this contract — the column is not mapped."),
    ("6. The query export carries personal data in fields nobody would look for it in.",
     "Item Value Before Query and Item Value Now hold the raw field values, and in this sample three of the four are birth years (2008 → 1989, 1910 → 1951, 1906 → 1953). The file also carries site and subject identifiers throughout, and is marked RESTRICTED in its filename while Restricted Query reads No on every row. "
     "Guardrail G-06 was scoped for tumour data. It is extended to the query-history block: value_before and value_after are redacted before any prompt is assembled, and the file is handled at the same sensitivity as the clinical data set.",
     "CLOSED by this contract — G-06 extended, and the Restricted Query flag alone is not treated as sufficient."),
]

# --------------------------------------------------------------------------
# Section 5 — how to use it.
# --------------------------------------------------------------------------
USAGE = [
    ("Build the dummy query file to this sheet",
     "The synthetic study needs a query export with exactly these column names, and it must contain what this one does not: manual queries, site-answered queries, a query on a repeating lesion row, and a closed query whose value was NOT changed. Those four cases are the ones the approved reconciliation model turns on and the ones this export cannot test."),
    ("Reconciliation is a documented degradation, not a switch",
     "Missing C columns take capability away one behaviour at a time, and every run states which. That is the same posture as the SDTM coverage report and it exists so a reviewer is never shown a quiet worklist that is quiet because the inputs were thin."),
    ("The contract survives the EDC version changing",
     "Daniel's note with this export is that the format will change with future Veeva releases. Adapter rules 1 to 4 are the response: bind by name, tolerate additions, fail loudly on removals. When a new export arrives, re-run the profile and diff it against this sheet before changing any code."),
    ("Query history is not optional in practice",
     "TEA-CTR-001 marks the queries block not required, and that stays true — the agent runs without it. But without it every finding is NEW, the agent re-raises what the study team already asked, and OBJ-04 is unmet. Treat it as required for any real data cut."),
]


def build_sheet(wb):
    if SHEET in wb.sheetnames:
        del wb[SHEET]
    ws = wb.create_sheet(SHEET, wb.sheetnames.index(AFTER) + 1)

    widths = {"A": 36, "B": 24, "C": 8, "D": 44, "E": 80, "F": 50, "G": 4}
    for k, v in widths.items():
        ws.column_dimensions[k].width = v
    ws.sheet_view.showGridLines = False

    title_style(
        ws, "Query history input contract", 6,
        "TEA-CTR-004. Derived column by column from a real Veeva EDC Query Detail export — study A101-1001_TST5, "
        "69 queries, 54 columns, listing run 2026-09-12 11:40. Supplied by Daniel on 2026-09-12 with the warning "
        "that the format will change as Veeva releases new EDC versions, which is what adapter rules 1 to 4 are for. "
        "Feeds the query reconciliation model (OBJ-04) and the six TE-QM rules. Closes OI-09.")

    header_row(ws, ["Export column (Veeva header, verbatim)", "Canonical field", "R/C/O",
                    "In the 2026-09-12 export", "What the agent does with it", "If absent"], 3)
    ws.freeze_panes = "D4"

    r = write_rows(ws, COLUMNS, 4, bold_cols=(0, 1), colour_cols={2: USE_COLOUR})

    r += 1
    c = ws.cell(r, 1, "R = required, the run fails without it.   C = conditional, its absence deactivates a named "
                      "behaviour and is reported.   O = optional, evidence only.   – = present in the export and "
                      "deliberately not used.   R* = required for lesion-level data specifically; see finding 1.")
    c.font = Font(name=FACE, size=9, italic=True, color=MUTE)
    c.alignment = Alignment(vertical="top", wrap_text=True)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    ws.row_dimensions[r].height = 26
    r += 2

    # The secondary tables have fewer, wider logical columns than the column
    # map, so each maps its columns onto merged spans of the same six.
    r = section_label(ws, "Query status vocabulary", r)
    spans = [1, 1, 2, 1, 1]
    header_row(ws, ["Veeva value", "Canonical status", "In this export",
                    "Reconciliation branch", "Confirmed?"], r, spans)
    r = write_rows(ws, STATUS, r + 1, bold_cols=(0, 1), spans=spans)
    r += 1

    r = section_label(ws, "Adapter rules", r)
    spans = [2, 4]
    header_row(ws, ["Rule", "Why"], r, spans)
    r = write_rows(ws, ADAPTER, r + 1, bold_cols=(0,), spans=spans)
    r += 1

    r = section_label(ws, "What the real export changed, and what it could not tell us", r)
    spans = [2, 3, 1]
    header_row(ws, ["Finding", "Detail and consequence", "Disposition"], r, spans)
    r = write_rows(ws, FINDINGS, r + 1, bold_cols=(0,), spans=spans)
    r += 1

    r = section_label(ws, "How to use this while the agent is being built", r)
    for head, body in USAGE:
        a = ws.cell(r, 1, head)
        a.font = Font(name=FACE, size=9, bold=True, color=ACCENT)
        a.alignment = Alignment(vertical="top", wrap_text=True)
        b = ws.cell(r, 2, body)
        b.font = Font(name=FACE, size=9, color=INK)
        b.alignment = Alignment(vertical="top", wrap_text=True)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
        ws.row_dimensions[r].height = 48
        r += 1

    return ws


def find_row(ws, key_in_col_a):
    """Row whose column A already holds this key, else the first free row.

    Keeps the append-style edits idempotent: re-running must not stack a second
    copy of the same row onto Contents or SDTM_Requirements.
    """
    for r in range(1, ws.max_row + 1):
        if ws.cell(r, 1).value == key_in_col_a:
            return r
    return ws.max_row + 1


def amend_related(wb):
    """Edits elsewhere in the workbook that TEA-CTR-004 forces."""
    cov = wb["Cover"]
    cov.cell(8, 2).value = "2.6.0 — APPROVED, query history input contract"
    cov.cell(12, 2).value = "v2.5.0, issued 2026-08-22"
    cov.cell(4, 1).value = (
        "Executable definition of the review logic: derivations, the 85-point rule catalog with confidence "
        "base rates, data contracts, LLM integration and the query reconciliation model.")

    ic = wb["Input_Contract"]
    ic.cell(2, 1).value = (
        "TEA-CTR-001. SDTM is the primary source profile (OQ-01, reversed 2026-08-22); the Veeva EDC export "
        "profile is retained for the in-company deployment. Source adapters produce this; rules never see "
        "source field names.")
    ic.cell(13, 2).value = ("query_id, query_text, answer_text, status, opened/answered/closed dates, "
                            "source_rule_id, item_group_seq, value_changed, change_attributed_to_query, "
                            "export_as_of")
    ic.cell(13, 5).value = (
        "Veeva EDC Query Detail export. See Query_History (TEA-CTR-004) for the column-by-column contract. "
        "Formally optional — absent, every finding is NEW — but required in practice for any real data cut, "
        "or the agent re-raises what the study team already asked.")

    qr = wb["Query_Reconciliation"]
    qr.cell(2, 1).value = (
        "AMENDED at review (OBJ-04). Input contract: Query_History (TEA-CTR-004), derived from a real Veeva "
        "export on 2026-09-12.")
    for i, text in enumerate([
        "•  The correction fact is read, not inferred. Where the export carries Item Value Changed and Query "
        "Caused Data Change, 'was the data corrected in response to this query?' is answered deterministically "
        "and the model is never asked it (DP-01). A query closed by System with a caused data change resolves "
        "to RESOLVED_BY_CORRECTION with no LLM call. The model is asked only whether an answer justifies data "
        "that was NOT corrected.",
        "•  Only Latest Query Answer Text is an answer. Latest Query Comment is the newest message on the "
        "thread — for a system query, a copy of the query itself — and is never passed to P-ASSESS-ANSWER. "
        "See Query_History finding 3.",
        "•  Aging is recomputed, never read. The export's Days Unresolved is measured against the export's own "
        "listing date, so TE-QM-004 derives it from Query Created Date against the run's as-of date. A query "
        "file whose as-of date is outside tolerance of the SDTM cut warns before rules run.",
    ], start=12):
        c = qr.cell(i, 1, text)
        c.font = Font(name=FACE, size=9, color=INK)
        c.alignment = Alignment(vertical="top", wrap_text=True)

    sd = wb["SDTM_Requirements"]
    last = find_row(sd, "Preserve the EDC item-group sequence")
    a = sd.cell(last, 1, "Preserve the EDC item-group sequence")
    a.font = Font(name=FACE, size=9, bold=True, color=ACCENT)
    a.alignment = Alignment(vertical="top", wrap_text=True)
    b = sd.cell(last, 2, (
        "Added 2026-09-12 from TEA-CTR-004 finding 1. A Veeva query identifies a lesion only by the repeating "
        "form's Item Group Sequence Number; nothing else in the query export names a lesion. The conversion must "
        "therefore carry that sequence through to the tumour records — as a supplemental qualifier alongside "
        "TULNKID — or query history cannot be matched to a lesion finding, and every lesion query at a visit "
        "will suppress every lesion finding at that visit."))
    b.font = Font(name=FACE, size=9, color=INK)
    b.alignment = Alignment(vertical="top", wrap_text=True)
    sd.merge_cells(start_row=last, start_column=2, end_row=last, end_column=6)
    sd.row_dimensions[last].height = 48

    cts = wb["Contents"]
    row = find_row(cts, SHEET)
    for col, val in enumerate(
            ["Query_History", "Veeva query export, column by column",
             f"=COUNTA({SHEET}!A4:A57)", "NEW", "TEA-CTR-004 — closes OI-09"], start=1):
        c = cts.cell(row, col, val)
        c.font = Font(name=FACE, size=9, color=INK)
        c.alignment = Alignment(vertical="top", wrap_text=True)


def amend_plan():
    wb = load_workbook(PLAN)
    cov = wb["Cover"]
    cov.cell(8, 2).value = "1.6.0"
    cov.cell(11, 2).value = "v1.5.0, issued 2026-08-22"
    cov.cell(18, 2).value = "TEA-SPEC-001 v2.6.0 — APPROVED, rule pack frozen at 2.0.0"

    oi = wb["Open_Items"]
    oi.cell(12, 2).value = (
        "DRAFTED 2026-09-12 as TEA-CTR-004, on the specification's Query_History sheet, from a real Veeva "
        "Query Detail export. Three confirmations remain: (a) a second export containing manual, site-answered "
        "queries, because this one has none and the LLM answer-assessment path is therefore unexercised; "
        "(b) that Item Group Sequence Number identifies the lesion row on a repeating tumour form, which this "
        "export could not show; (c) the full Query Status vocabulary, since only Open and Closed appear.")
    oi.cell(12, 3).value = (
        "Six TE-QM rules and the whole query reconciliation model depend on it. The export resolved more than "
        "expected — the correction fact turns out to be carried deterministically — but it also showed that "
        "lesion-level matching rests on a single sequence number that must survive the SDTM conversion.")
    oi.cell(12, 5).value = "Second export before Step 3"
    wb.save(PLAN)
    return PLAN


def main():
    if not SPEC.exists():
        print(f"FAIL: {SPEC} not found")
        return 1
    wb = load_workbook(SPEC)
    ws = build_sheet(wb)
    amend_related(wb)
    wb.save(SPEC)
    print(f"wrote {SPEC.name} — {SHEET} with {len(COLUMNS)} columns, "
          f"{len(STATUS)} statuses, {len(ADAPTER)} adapter rules, {len(FINDINGS)} findings")
    p = amend_plan()
    print(f"wrote {p.name} — OI-09 updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
