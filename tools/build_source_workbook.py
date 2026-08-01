"""Generate the PRAP source-data workbook: a blank template and a populated dummy file.

Both follow the schema baselined in PRAP_Development_Plan_v1.0.xlsx, sheet 04_Data_Model.

    python tools/build_source_workbook.py

Outputs into templates/:
    PRAP_SourceData_Template_v1.0.xlsx   headers, value lists, one example row per sheet
    PRAP_SourceData_Dummy_v1.0.xlsx      realistic data that exercises every rule

The dummy file is built to demonstrate the calculation, not merely to fill cells: it
contains a person who breaches the 1.50 FTE over-allocation threshold, a person who
sits below 0.80 FTE for more than three consecutive months, a trial with an interim
DB lock (so 'Conduct' occurs twice), a trial without one, and two 'Others' projects
whose periods are hand-entered.
"""

from datetime import date, timedelta
from pathlib import Path

from dateutil.relativedelta import relativedelta as rd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

SCHEMA_VERSION = 1
VERSION = "1.1"
OUTDIR = Path(__file__).resolve().parents[1] / "templates"

FONT = "Arial"
NAVY = "1F3864"
HDR_FILL = PatternFill("solid", fgColor="2F5597")
KEY_FILL = PatternFill("solid", fgColor="DDEBF7")   # identifier columns
CALC_FILL = PatternFill("solid", fgColor="E2EFDA")  # derived - do not type here
FILL_ME = PatternFill("solid", fgColor="FFFF00")    # you must supply these
EG_FILL = PatternFill("solid", fgColor="F2F2F2")    # example row

HDR_F = Font(name=FONT, size=10, bold=True, color="FFFFFF")
BODY_F = Font(name=FONT, size=10)
BOLD_F = Font(name=FONT, size=10, bold=True)
TITLE_F = Font(name=FONT, size=14, bold=True, color=NAVY)
NOTE_F = Font(name=FONT, size=9, italic=True, color="808080")
EG_F = Font(name=FONT, size=10, italic=True, color="7F7F7F")

THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
DATE_FMT = "yyyy-mm-dd"

# --------------------------------------------------------------------------
# Value lists (Lists sheet, long format per the approved data model)
# --------------------------------------------------------------------------
LISTS = [
    ("project_type", ["Clinical Trial", "Others"]),
    ("clinical_phase", ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]),
    ("outsourcing_type", ["Full outsourcing", "Partial outsourcing", "Full In-house"]),
    ("setup_party", ["by CRO", "by SB"]),
    ("EDC_system", ["Veeva EDC", "Rave", "eSOURCE"]),
    ("DataReviewSystem", ["Veeva DQS", "Medidata CDS", "No system (manual)"]),
    ("RBQM_system", ["CluePoints", "Medidata CDS", "No system (manual)"]),
    ("project_status", ["Planned", "Active", "On hold", "Completed"]),
    ("milestone_name", ["Protocol (v1)", "CTA submission", "FPI", "First SIV", "LPI",
                        "interim DB lock cut-off", "interim DB lock",
                        "final DB lock cut-off", "final DB lock", "Inspection"]),
    ("period_name_clinical", ["Before-Start-up", "Start-up", "Conduct",
                              "Close-out (interim)", "Close-out (final)",
                              "After Close-out (final)"]),
    ("period_name_others", ["Planning", "Develop", "Close"]),
    ("role_clinical", ["Project oversight", "Lead data manager", "Clinical Data Associator",
                       "Clinical Database Programmer", "Data Analyst"]),
    ("role_others", ["Project lead", "Main staff", "Other staff"]),
]

CONFIG = [
    ("schema_version", SCHEMA_VERSION, "Structure version of this workbook. The application warns on a mismatch."),
    ("fte_hours_per_month", 160, "Hours equal to 1.00 FTE: 8 h/day x 5 days/week x 20 days/month."),
    ("over_allocation_fte", 1.50, "A person-month total above this is flagged as over-allocated."),
    ("under_allocation_fte", 0.80, "A person-month total below this counts toward an under-allocated run."),
    ("under_allocation_min_months", 3, "Consecutive months below the threshold before a run is flagged."),
    ("default_horizon_months", 24, "Months shown when the dashboard opens."),
    ("capacity_unit", "FTE", "Display unit: 'FTE' or 'percent'."),
]

# --------------------------------------------------------------------------
# Sheet definitions: (column, note, kind)
#   kind: 'key' identifier | 'calc' derived | 'fill' you must supply | '' normal
# --------------------------------------------------------------------------
SHEETS = {
    "Project": [
        ("project_id", "Unique key, e.g. PRJ-001.", "key"),
        ("project_name", "Unique display name.", "key"),
        ("project_type", "'Clinical Trial' or 'Others'.", ""),
        ("project_category", "Product name. Required for a clinical trial.", ""),
        ("clinical_phase", "Required for a clinical trial - it selects the period weights.", ""),
        ("outsourcing_type", "Full / Partial outsourcing, or Full In-house.", ""),
        ("EDC_setup", "Who sets up EDC. Clinical trial only.", ""),
        ("DataReviewSystem_setup", "Who sets up the data review system.", ""),
        ("RBQM_setup", "Who sets up RBQM.", ""),
        ("DM_conduct", "Who reviews the data.", ""),
        ("EDC_system", "EDC system in use.", ""),
        ("DataReviewSystem", "Data review system in use.", ""),
        ("RBQM_system", "RBQM system in use.", ""),
        ("planned_member_count", "Planned team size; compared against actual assignments.", ""),
        ("start_date", "Project start.", ""),
        ("end_date", "Planned project end.", ""),
        ("total_period_months", "DERIVED - formula, do not type.", "calc"),
        ("status", "Planned / Active / On hold / Completed.", ""),
        ("note_1", "Free text.", ""), ("note_2", "", ""), ("note_3", "", ""),
        ("note_4", "", ""), ("note_5", "", ""),
    ],
    "Milestone": [
        ("project_id", "Foreign key to Project.", "key"),
        ("project_name", "DERIVED - looked up from Project, do not type.", "calc"),
        ("milestone_name", "From the standard list of ten. 'Inspection' may appear on several rows.", ""),
        ("milestone_date", "Planned date.", ""),
        ("milestone_seq", "Display order on the timeline.", ""),
    ],
    "ProjectPeriod": [
        ("project_id", "Foreign key to Project.", "key"),
        ("period_name", "From the set for this project's type. NOT unique - 'Conduct' can appear twice.", ""),
        ("period_seq", "Orders periods along the timeline. Unique within a project.", "key"),
        ("period_start", "Inclusive.", ""),
        ("period_end", "Inclusive. Periods must not overlap or leave a gap.", ""),
        ("weight", "Effort multiplier. Clinical trial: seeded from PeriodWeightStandard. Others: type it.", ""),
    ],
    "PeriodWeightStandard": [
        ("project_type", "'Clinical Trial'. 'Others' projects take manual weights instead.", ""),
        ("clinical_phase", "The phase this standard applies to.", "key"),
        ("period_name", "One of the five clinical periods.", "key"),
        ("weight", "YOU SUPPLY. Default multiplier for this phase and period.", "fill"),
    ],
    "RoleFactor": [
        ("project_type", "Which type's role list this row belongs to.", "key"),
        ("role_name", "The role.", "key"),
        ("role_factor", "YOU SUPPLY. Relative burden of the role.", "fill"),
        ("role_note", "Basis for the factor.", ""),
    ],
    "Person": [
        ("person_id", "Unique key, e.g. PSN-001.", "key"),
        ("person_name", "Display name.", ""),
        ("department", "Grouping for the dashboard.", ""),
        ("primary_role", "Usual role; an assignment can override it.", ""),
        ("capacity_fte", "Available capacity. 1.00 = full time. Lower for a part-timer.", ""),
        ("employment_start", "Blank = open.", ""),
        ("employment_end", "Blank = open.", ""),
        ("note_1", "Free text.", ""), ("note_2", "", ""), ("note_3", "", ""),
        ("note_4", "", ""), ("note_5", "", ""),
    ],
    "Assignment": [
        ("assignment_id", "Unique key. One row per person + project + role.", "key"),
        ("person_id", "Foreign key to Person.", "key"),
        ("person_name", "DERIVED - looked up from Person, do not type.", "calc"),
        ("project_id", "Foreign key to Project.", "key"),
        ("role_name", "Must exist in RoleFactor for this project's type.", ""),
        ("assign_start_date", "Date the person joins the study.", ""),
        ("assign_end_date", "Date the person leaves. Blank = runs to project end.", ""),
        ("person_weight", "How much this person works on this project, e.g. 0.40.", ""),
        ("note_1", "Free text.", ""), ("note_2", "", ""), ("note_3", "", ""),
    ],
    "PersonPeriodWeight": [
        ("assignment_id", "Foreign key to Assignment.", "key"),
        ("period_start", "Inclusive.", ""),
        ("period_end", "Inclusive. Windows within one assignment must not overlap.", ""),
        ("weight_override", "REPLACES person_weight for these months - it does not multiply it.", ""),
        ("reason", "Why the weight differs.", ""),
    ],
    "Lists": [
        ("list_name", "Which list this value belongs to.", "key"),
        ("value", "A permitted value. Add a row inside the block to extend a list.", ""),
    ],
    "Config": [
        ("parameter", "Setting name.", "key"),
        ("value", "Setting value.", ""),
        ("note", "What it controls.", ""),
    ],
}

DATE_COLS = {
    "Project": ["start_date", "end_date"],
    "Milestone": ["milestone_date"],
    "ProjectPeriod": ["period_start", "period_end"],
    "Person": ["employment_start", "employment_end"],
    "Assignment": ["assign_start_date", "assign_end_date"],
    "PersonPeriodWeight": ["period_start", "period_end"],
}

# Dropdown bindings: sheet -> {column: list_name}
DROPDOWNS = {
    "Project": {"project_type": "project_type", "clinical_phase": "clinical_phase",
                "outsourcing_type": "outsourcing_type", "EDC_setup": "setup_party",
                "DataReviewSystem_setup": "setup_party", "RBQM_setup": "setup_party",
                "DM_conduct": "setup_party", "EDC_system": "EDC_system",
                "DataReviewSystem": "DataReviewSystem", "RBQM_system": "RBQM_system",
                "status": "project_status"},
    "Milestone": {"milestone_name": "milestone_name"},
    "PeriodWeightStandard": {"project_type": "project_type", "clinical_phase": "clinical_phase",
                             "period_name": "period_name_clinical"},
    "RoleFactor": {"project_type": "project_type"},
}


# --------------------------------------------------------------------------
# Period derivation - the algorithm baselined on plan sheet 05
# --------------------------------------------------------------------------
def derive_periods(start, end, milestones, inspections):
    """Return [(period_name, seq, start, end)] for a clinical trial - plan v1.1 sheet 05.

    A recorded milestone beats the month-offset fallback (REQ-CAL-13). Boundaries apply
    in sequence order, a later one winning; a period squeezed to nothing is omitted
    (REQ-CAL-12, decision C-11).
    """
    protocol = milestones.get("Protocol (v1)")
    cta = milestones.get("CTA submission")
    siv = milestones.get("First SIV") or milestones.get("FPI")
    idbl = milestones.get("interim DB lock")
    fdbl = milestones.get("final DB lock") or idbl
    if not cta or not fdbl:
        return []

    su_s = max((protocol + timedelta(days=1)) if protocol else (cta - rd(months=1)), start)
    su_e = siv if siv and siv >= su_s else (su_s + rd(months=4) - timedelta(days=1))

    # Period 7 opens only on inspection activity AFTER the final DB lock (V-21, R-03).
    later = [x for x in inspections if x > fdbl]
    p7_s = min(later) if later else None
    p7_e = max(max(later), end) if later else None

    cof_s = fdbl - rd(months=3)
    cof_e = (p7_s - timedelta(days=1)) if p7_s else max(fdbl, end)

    segs = []
    if su_s > start:
        segs.append(("Before-Start-up", start, su_s - timedelta(days=1)))
    segs.append(("Start-up", su_s, su_e))
    if idbl and idbl < fdbl:
        coi_s = idbl - rd(months=3)
        segs.append(("Conduct", su_e + timedelta(days=1), coi_s - timedelta(days=1)))
        segs.append(("Close-out (interim)", coi_s, idbl))
        cof_s = max(cof_s, idbl + timedelta(days=1))
        segs.append(("Conduct", idbl + timedelta(days=1), cof_s - timedelta(days=1)))
    else:
        segs.append(("Conduct", su_e + timedelta(days=1), cof_s - timedelta(days=1)))
    segs.append(("Close-out (final)", cof_s, cof_e))
    if p7_s:
        segs.append(("After Close-out (final)", p7_s, p7_e))

    rows = [(n, s, e) for n, s, e in segs if e >= s]
    return [(n, i + 1, s, e) for i, (n, s, e) in enumerate(rows)]


# --------------------------------------------------------------------------
# Dummy dataset
# --------------------------------------------------------------------------
def dummy_data():
    projects = [
        # id, name, type, category, phase, outsourcing, edc_su, drs_su, rbqm_su, dm, edc, drs, rbqm, members, start, end, status
        ("PRJ-001", "ONV-101 First-in-human", "Clinical Trial", "Onvelaris", "Phase 1", "Partial outsourcing",
         "by SB", "by SB", "by CRO", "by SB", "Veeva EDC", "Veeva DQS", "CluePoints", 5,
         date(2025, 10, 1), date(2027, 9, 30), "Active"),
        ("PRJ-002", "ONV-205 Dose expansion", "Clinical Trial", "Onvelaris", "Phase 2", "Full outsourcing",
         "by CRO", "by CRO", "by CRO", "by CRO", "Rave", "Medidata CDS", "Medidata CDS", 6,
         date(2026, 1, 1), date(2028, 9, 30), "Active"),
        ("PRJ-003", "CDX-310 Pivotal", "Clinical Trial", "Cardexa", "Phase 3", "Partial outsourcing",
         "by CRO", "by SB", "by CRO", "by SB", "Veeva EDC", "Veeva DQS", "CluePoints", 8,
         date(2025, 7, 1), date(2029, 10, 31), "Active"),
        ("PRJ-004", "NRX-410 Post-marketing", "Clinical Trial", "Neurexa", "Phase 4", "Full In-house",
         "by SB", "by SB", "by SB", "by SB", "eSOURCE", "No system (manual)", "No system (manual)", 3,
         date(2026, 4, 1), date(2028, 3, 31), "Planned"),
        ("PRJ-005", "ONV-302 Confirmatory", "Clinical Trial", "Onvelaris", "Phase 3", "Full outsourcing",
         "by CRO", "by CRO", "by CRO", "by CRO", "Rave", "Medidata CDS", "CluePoints", 7,
         date(2026, 6, 1), date(2029, 6, 30), "Planned"),
        ("PRJ-006", "CDISC library migration", "Others", "", "", "Full In-house",
         "", "", "", "", "", "", "", 4, date(2026, 1, 1), date(2026, 12, 31), "Active"),
        ("PRJ-007", "eTMF rollout", "Others", "", "", "Partial outsourcing",
         "", "", "", "", "", "", "", 3, date(2026, 3, 1), date(2027, 2, 28), "Active"),
    ]

    # milestones: project -> {name: date}
    ms = {
        "PRJ-001": {"Protocol (v1)": date(2025, 10, 15), "CTA submission": date(2026, 1, 15),
                    "First SIV": date(2026, 4, 1), "LPI": date(2026, 11, 30),
                    "final DB lock cut-off": date(2027, 3, 31), "final DB lock": date(2027, 5, 31)},
        "PRJ-002": {"Protocol (v1)": date(2026, 1, 20), "CTA submission": date(2026, 4, 1),
                    "First SIV": date(2026, 7, 1), "LPI": date(2027, 6, 30),
                    "interim DB lock cut-off": date(2027, 9, 30), "interim DB lock": date(2027, 11, 30),
                    "final DB lock cut-off": date(2028, 6, 30), "final DB lock": date(2028, 8, 31)},
        "PRJ-003": {"Protocol (v1)": date(2025, 7, 15), "CTA submission": date(2025, 10, 1),
                    "First SIV": date(2026, 1, 15), "LPI": date(2027, 9, 30),
                    "interim DB lock cut-off": date(2027, 12, 31), "interim DB lock": date(2028, 2, 29),
                    "final DB lock cut-off": date(2028, 12, 31), "final DB lock": date(2029, 2, 28)},
        "PRJ-004": {"Protocol (v1)": date(2026, 4, 10), "CTA submission": date(2026, 6, 1),
                    "First SIV": date(2026, 9, 1), "LPI": date(2027, 6, 30),
                    "final DB lock cut-off": date(2027, 12, 31), "final DB lock": date(2028, 2, 29)},
        "PRJ-005": {"Protocol (v1)": date(2026, 6, 15), "CTA submission": date(2026, 9, 1),
                    "First SIV": date(2026, 12, 1), "LPI": date(2028, 3, 31),
                    "interim DB lock cut-off": date(2028, 6, 30), "interim DB lock": date(2028, 8, 31),
                    "final DB lock cut-off": date(2029, 3, 31), "final DB lock": date(2029, 5, 31)},
    }

    # 'Inspection' may occur several times in one project (REQ-PRJ-13).
    # PRJ-003 has three after its final DB lock; PRJ-001 has one; PRJ-002 has one dated
    # BEFORE its final lock, which under V-21 stays a marker and does not open period 7.
    inspections = {
        "PRJ-001": [date(2027, 8, 15)],
        "PRJ-002": [date(2028, 5, 20)],
        "PRJ-003": [date(2029, 5, 10), date(2029, 7, 22), date(2029, 9, 30)],
    }

    people = [
        ("PSN-001", "Kim S.", "Data Management", "Lead data manager", 1.00),
        ("PSN-002", "Park J.", "Data Management", "Lead data manager", 1.00),
        ("PSN-003", "Lee H.", "Data Management", "Clinical Data Associator", 1.00),
        ("PSN-004", "Choi M.", "Data Management", "Clinical Data Associator", 0.60),
        ("PSN-005", "Jung Y.", "Programming", "Clinical Database Programmer", 1.00),
        ("PSN-006", "Han B.", "Programming", "Clinical Database Programmer", 1.00),
        ("PSN-007", "Oh K.", "Biostatistics", "Data Analyst", 1.00),
        ("PSN-008", "Seo W.", "Biostatistics", "Data Analyst", 0.80),
        ("PSN-009", "Yoon T.", "Clinical Operations", "Project oversight", 1.00),
        ("PSN-010", "Nam R.", "Clinical Operations", "Project oversight", 1.00),
        ("PSN-011", "Ahn D.", "Business Systems", "Project lead", 1.00),
        ("PSN-012", "Baek C.", "Business Systems", "Main staff", 1.00),
    ]

    # assignment_id, person, project, role, start, end, person_weight
    A = [
        # PSN-001 deliberately loaded across three projects to breach 1.50 FTE
        ("ASG-001", "PSN-001", "PRJ-001", "Lead data manager", date(2025, 10, 1), date(2027, 6, 30), 0.50),
        ("ASG-002", "PSN-001", "PRJ-002", "Lead data manager", date(2026, 1, 1), date(2028, 9, 30), 0.50),
        ("ASG-003", "PSN-001", "PRJ-006", "Project lead", date(2026, 1, 1), date(2026, 12, 31), 0.40),

        ("ASG-004", "PSN-002", "PRJ-003", "Lead data manager", date(2025, 7, 1), date(2029, 3, 31), 0.55),
        ("ASG-005", "PSN-002", "PRJ-005", "Lead data manager", date(2026, 6, 1), date(2029, 6, 30), 0.45),

        ("ASG-006", "PSN-003", "PRJ-001", "Clinical Data Associator", date(2026, 1, 1), date(2027, 6, 30), 0.55),
        ("ASG-007", "PSN-003", "PRJ-003", "Clinical Data Associator", date(2026, 1, 1), date(2029, 3, 31), 0.55),
        ("ASG-024", "PSN-003", "PRJ-005", "Clinical Data Associator", date(2027, 7, 1), date(2029, 6, 30), 0.35),

        # PSN-004 is part time (capacity 0.60) and deliberately light
        ("ASG-008", "PSN-004", "PRJ-004", "Clinical Data Associator", date(2026, 4, 1), date(2028, 3, 31), 0.30),

        ("ASG-009", "PSN-005", "PRJ-001", "Clinical Database Programmer", date(2025, 11, 1), date(2026, 12, 31), 0.45),
        ("ASG-010", "PSN-005", "PRJ-002", "Clinical Database Programmer", date(2026, 2, 1), date(2028, 9, 30), 0.45),
        ("ASG-025", "PSN-005", "PRJ-004", "Clinical Database Programmer", date(2026, 6, 1), date(2028, 3, 31), 0.30),

        ("ASG-011", "PSN-006", "PRJ-003", "Clinical Database Programmer", date(2025, 9, 1), date(2029, 3, 31), 0.50),
        ("ASG-012", "PSN-006", "PRJ-005", "Clinical Database Programmer", date(2026, 9, 1), date(2029, 6, 30), 0.40),
        ("ASG-026", "PSN-006", "PRJ-006", "Main staff", date(2026, 1, 1), date(2026, 12, 31), 0.30),

        ("ASG-013", "PSN-007", "PRJ-002", "Data Analyst", date(2026, 6, 1), date(2028, 9, 30), 0.55),
        ("ASG-014", "PSN-007", "PRJ-003", "Data Analyst", date(2026, 6, 1), date(2029, 3, 31), 0.55),
        ("ASG-015", "PSN-008", "PRJ-005", "Data Analyst", date(2026, 9, 1), date(2029, 6, 30), 0.50),
        ("ASG-027", "PSN-008", "PRJ-001", "Data Analyst", date(2026, 1, 1), date(2027, 6, 30), 0.40),

        # Oversight staff carry many projects at a low weight each
        ("ASG-016", "PSN-009", "PRJ-001", "Project oversight", date(2025, 10, 1), date(2027, 6, 30), 0.35),
        ("ASG-017", "PSN-009", "PRJ-002", "Project oversight", date(2026, 1, 1), date(2028, 9, 30), 0.35),
        ("ASG-018", "PSN-009", "PRJ-004", "Project oversight", date(2026, 4, 1), date(2028, 3, 31), 0.35),
        ("ASG-028", "PSN-009", "PRJ-006", "Project lead", date(2026, 1, 1), date(2026, 12, 31), 0.30),
        ("ASG-019", "PSN-010", "PRJ-003", "Project oversight", date(2025, 7, 1), date(2029, 3, 31), 0.45),
        ("ASG-020", "PSN-010", "PRJ-005", "Project oversight", date(2026, 6, 1), date(2029, 6, 30), 0.45),
        ("ASG-029", "PSN-010", "PRJ-007", "Project lead", date(2026, 3, 1), date(2027, 2, 28), 0.35),

        ("ASG-021", "PSN-011", "PRJ-007", "Project lead", date(2026, 3, 1), date(2027, 2, 28), 0.60),
        ("ASG-030", "PSN-011", "PRJ-006", "Main staff", date(2026, 1, 1), date(2026, 12, 31), 0.50),
        ("ASG-022", "PSN-012", "PRJ-006", "Main staff", date(2026, 1, 1), date(2026, 12, 31), 0.70),
        ("ASG-023", "PSN-012", "PRJ-007", "Other staff", date(2026, 3, 1), date(2027, 2, 28), 0.60),
    ]

    ppw = [
        ("ASG-001", date(2026, 7, 1), date(2026, 9, 30), 0.20, "Part-time - parental leave"),
        ("ASG-004", date(2027, 1, 1), date(2027, 3, 31), 0.70, "Covering interim analysis peak"),
    ]

    # Illustrative standards - the reviewer replaces these with real figures
    pws = []
    phase_profile = {
        "Phase 1": {"Before-Start-up": 0.60, "Start-up": 1.30, "Conduct": 1.00,
                    "Close-out (interim)": 1.20, "Close-out (final)": 1.40,
                    "After Close-out (final)": 0.84},
        "Phase 2": {"Before-Start-up": 0.70, "Start-up": 1.40, "Conduct": 1.10,
                    "Close-out (interim)": 1.30, "Close-out (final)": 1.50,
                    "After Close-out (final)": 0.9},
        "Phase 3": {"Before-Start-up": 0.80, "Start-up": 1.60, "Conduct": 1.20,
                    "Close-out (interim)": 1.40, "Close-out (final)": 1.70,
                    "After Close-out (final)": 1.02},
        "Phase 4": {"Before-Start-up": 0.50, "Start-up": 1.10, "Conduct": 0.90,
                    "Close-out (interim)": 1.00, "Close-out (final)": 1.20,
                    "After Close-out (final)": 0.72},
    }
    for ph, prof in phase_profile.items():
        for pn, w in prof.items():
            pws.append(("Clinical Trial", ph, pn, w))

    roles = [
        ("Clinical Trial", "Project oversight", 0.80, "Illustrative - replace with your figure"),
        ("Clinical Trial", "Lead data manager", 1.20, "Illustrative"),
        ("Clinical Trial", "Clinical Data Associator", 1.00, "Illustrative"),
        ("Clinical Trial", "Clinical Database Programmer", 1.10, "Illustrative"),
        ("Clinical Trial", "Data Analyst", 0.90, "Illustrative"),
        ("Others", "Project lead", 1.00, "Illustrative"),
        ("Others", "Main staff", 0.90, "Illustrative"),
        ("Others", "Other staff", 0.70, "Illustrative"),
    ]

    # Periods: derived for clinical trials, hand-entered for 'Others'
    periods = []
    for p in projects:
        pid, ptype, pstart, pend = p[0], p[2], p[14], p[15]
        if ptype == "Clinical Trial":
            phase = p[4]
            for name, seq, s, e in derive_periods(pstart, pend, ms[pid], inspections.get(pid, [])):
                periods.append((pid, name, seq, s, e, phase_profile[phase][name]))
        else:
            span = (pend - pstart).days
            b1 = pstart + timedelta(days=int(span * 0.25))
            b2 = pstart + timedelta(days=int(span * 0.80))
            periods.append((pid, "Planning", 1, pstart, b1, 0.80))
            periods.append((pid, "Develop", 2, b1 + timedelta(days=1), b2, 1.20))
            periods.append((pid, "Close", 3, b2 + timedelta(days=1), pend, 0.90))

    return projects, ms, periods, pws, roles, people, A, ppw, inspections


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------
def col_index(sheet, name):
    return [c for c, _, _ in SHEETS[sheet]].index(name) + 1


def write_sheet(wb, name, rows, example=None, list_ranges=None):
    ws = wb.create_sheet(name)
    ws.sheet_view.showGridLines = False
    cols = SHEETS[name]

    for i, (col, note, kind) in enumerate(cols, start=1):
        c = ws.cell(row=1, column=i, value=col)
        c.font = HDR_F
        c.fill = HDR_FILL
        c.border = BOX
        c.alignment = Alignment(vertical="center", wrap_text=True, horizontal="center")
        if note:
            width = max(12, min(30, len(col) + 6))
        else:
            width = 12
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "A2"

    start = 2
    if example is not None:
        for i, v in enumerate(example, start=1):
            c = ws.cell(row=start, column=i, value=v)
            c.font = EG_F
            c.fill = EG_FILL
            c.border = BOX
        start += 1

    for r, row in enumerate(rows, start=start):
        for i, v in enumerate(row, start=1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = BODY_F
            c.border = BOX

    # column tinting by kind
    last = max(start + len(rows) - 1, start)
    for i, (col, note, kind) in enumerate(cols, start=1):
        fill = {"key": KEY_FILL, "calc": CALC_FILL, "fill": FILL_ME}.get(kind)
        if not fill:
            continue
        for r in range(2, last + 1):
            if ws.cell(row=r, column=i).value is not None or kind == "fill":
                ws.cell(row=r, column=i).fill = fill

    # date formatting
    for col in DATE_COLS.get(name, []):
        i = col_index(name, col)
        for r in range(2, last + 1):
            ws.cell(row=r, column=i).number_format = DATE_FMT

    # dropdowns
    if list_ranges:
        for col, list_name in DROPDOWNS.get(name, {}).items():
            rng = list_ranges.get(list_name)
            if not rng:
                continue
            dv = DataValidation(type="list", formula1=rng, allow_blank=True, showDropDown=False)
            ws.add_data_validation(dv)
            letter = get_column_letter(col_index(name, col))
            dv.add(f"{letter}2:{letter}{max(last, 400)}")

    return ws


def add_readme(wb, kind):
    ws = wb.create_sheet("00_README", 0)
    ws.sheet_view.showGridLines = False
    ws["A1"] = f"PRAP source data - {kind}"
    ws["A1"].font = TITLE_F
    ws.column_dimensions["A"].width = 120

    body = [
        "",
        f"Schema version {SCHEMA_VERSION}. Matches PRAP_Development_Plan_v1.0.xlsx, sheet 04_Data_Model.",
        "",
        "COLOUR KEY",
        "   Blue    identifier or key column - these link the sheets together.",
        "   Green   derived by formula. Do not type in these; they recalculate.",
        "   Yellow  you must supply this value. The application cannot work it out.",
        "   Grey italic row   an example, in the template only. Delete it before use.",
        "",
        "SHEETS",
        "   Project               one row per project.",
        "   Milestone             one row per milestone. Eight standard names.",
        "   ProjectPeriod         the periods each project passes through, with their weights.",
        "   PeriodWeightStandard  default weights per clinical phase. Clinical trials only.",
        "   RoleFactor            the roles and their relative burden, per project type.",
        "   Person                one row per person.",
        "   Assignment            one row per person + project + role.",
        "   PersonPeriodWeight    optional windows where a person's weight differs.",
        "   Lists                 permitted values for every dropdown.",
        "   Config                thresholds and settings.",
        "",
        "HOW THE CALCULATION USES THIS",
        "   monthly load = project period weight  x  role factor  x  person weight  x  month coverage",
        "   The result is FTE, where 1.00 FTE = 160 hours per month.",
        "   Over-allocated:  a person's monthly total above 1.50 FTE.",
        "   Under-allocated: below 0.80 FTE for three or more consecutive months.",
        "",
        "PERIODS",
        "   Clinical trial periods are derived from the milestone dates:",
        "      Before-Start-up      project start, to the day before Start-up",
        "      Start-up             one month before CTA submission, lasting four months",
        "      Conduct              from the end of Start-up to the day before the next close-out",
        "      Close-out (interim)  three months before the interim DB lock, to that lock",
        "      Conduct  (again)     from the interim DB lock to the day before Close-out (final)",
        "      Close-out (final)    three months before the final DB lock, to that lock",
        "      After Close-out (final)  the inspection activity that follows the final DB lock",
        "",
        "   Where 'Protocol (v1)' is recorded, Before-Start-up ends on it and Start-up begins the day after.",
        "   Where 'First SIV' (or 'FPI') is recorded, Start-up ends on it instead of running a fixed four",
        "   months. A recorded milestone always beats the month-offset fallback.",
        "",
        "   'Conduct' therefore appears TWICE where a trial has an interim DB lock. period_seq keeps",
        "   the two apart. A period squeezed to nothing by a tight timeline is simply omitted.",
        "",
        "   'Inspection' is the one milestone that may be recorded SEVERAL TIMES for a project. Only",
        "   inspections dated AFTER the final DB lock open the last period; an earlier one stays a marker.",
        "",
        "   'Others' projects have no milestones. Their period dates and weights are both typed in.",
        "",
        "ADDING A PERMITTED VALUE",
        "   Insert a row inside that list's block on the Lists sheet, so the block stays contiguous -",
        "   the dropdowns read a range, not a scattered set of rows.",
    ]
    if kind == "template":
        body += [
            "",
            "BEFORE YOU USE THIS FILE",
            "   1. Delete the grey example row from every sheet.",
            "   2. Fill in the yellow columns: PeriodWeightStandard.weight and RoleFactor.role_factor.",
            "      Nothing simulates correctly until those are set.",
            "   3. Enter your projects, people and assignments.",
        ]
    else:
        body += [
            "",
            "WHAT THIS DUMMY FILE DEMONSTRATES",
            "   - PSN-001 is loaded across three projects and breaches the 1.50 FTE over-allocation",
            "     threshold in several months.",
            "   - PSN-004 sits below 0.80 FTE for well over three consecutive months, so an",
            "     under-allocation run is raised.",
            "   - PRJ-002, PRJ-003 and PRJ-005 have an interim DB lock, so each has TWO Conduct",
            "     stretches and two close-out periods.",
            "   - PRJ-001 and PRJ-004 have no interim lock, so Conduct runs once.",
            "   - PRJ-006 and PRJ-007 are 'Others' projects with hand-entered periods.",
            "   - ASG-001 and ASG-004 carry PersonPeriodWeight overrides.",
            "   - PRJ-003 records THREE 'Inspection' events after its final DB lock, so it carries the",
            "     seventh period. PRJ-001 records one. PRJ-002 records one dated BEFORE its final lock,",
            "     which stays a marker and opens no period - the case raised as R-03 in the plan.",
            "",
            "   The weights and role factors here are ILLUSTRATIVE, so the numbers can be exercised.",
            "   Replace them with your own before drawing any conclusion from the output.",
        ]

    for i, line in enumerate(body, start=2):
        c = ws.cell(row=i, column=1, value=line)
        if line.isupper() and line.strip():
            c.font = BOLD_F
        elif line.startswith("   ") or line.startswith("      "):
            c.font = Font(name="Consolas", size=9)
        else:
            c.font = BODY_F
    return ws


def build(kind):
    wb = Workbook()
    wb.remove(wb.active)

    # Lists first, so ranges are known for the dropdowns
    list_rows, list_ranges = [], {}
    r = 2
    for name, values in LISTS:
        for v in values:
            list_rows.append((name, v))
        list_ranges[name] = f"Lists!$B${r}:$B${r + len(values) - 1}"
        r += len(values)

    if kind == "dummy":
        projects, ms, periods, pws, roles, people, A, ppw, inspections = dummy_data()
        proj_rows = [list(p[:16]) + [None] + [p[16]] + [None] * 5 for p in projects]
        mile_rows = []
        for pid, mm in ms.items():
            events = sorted(mm.items(), key=lambda kv: kv[1])
            events += [("Inspection", x) for x in inspections.get(pid, [])]
            for seq, (nm, dt) in enumerate(sorted(events, key=lambda kv: kv[1]), start=1):
                mile_rows.append([pid, None, nm, dt, seq])
        period_rows = [list(x) for x in periods]
        pws_rows = [list(x) for x in pws]
        role_rows = [list(x) for x in roles]
        person_rows = [list(p) + [None, None] + [None] * 5 for p in people]
        asg_rows = [[a[0], a[1], None, a[2], a[3], a[4], a[5], a[6], None, None, None] for a in A]
        ppw_rows = [list(x) for x in ppw]
        examples = {k: None for k in SHEETS}
    else:
        proj_rows = mile_rows = period_rows = pws_rows = role_rows = []
        person_rows = asg_rows = ppw_rows = []
        # one example row per sheet (REQ-IMP-03)
        examples = {
            "Project": ["PRJ-001", "ONV-101 First-in-human", "Clinical Trial", "Onvelaris", "Phase 1",
                        "Partial outsourcing", "by SB", "by SB", "by CRO", "by SB", "Veeva EDC",
                        "Veeva DQS", "CluePoints", 5, date(2025, 10, 1), date(2027, 6, 30), None,
                        "Active", "example row - delete before use", None, None, None, None],
            "Milestone": ["PRJ-001", None, "CTA submission", date(2026, 1, 15), 2],
            "ProjectPeriod": ["PRJ-001", "Start-up", 2, date(2025, 12, 15), date(2026, 4, 14), 1.30],
            "PeriodWeightStandard": ["Clinical Trial", "Phase 1", "Start-up", None],
            "RoleFactor": ["Clinical Trial", "Lead data manager", None, "example row - delete before use"],
            "Person": ["PSN-001", "Kim S.", "Data Management", "Lead data manager", 1.00,
                       None, None, "example row - delete before use", None, None, None, None],
            "Assignment": ["ASG-001", "PSN-001", None, "PRJ-001", "Lead data manager",
                           date(2025, 10, 1), date(2027, 6, 30), 0.45, "example row - delete before use", None, None],
            "PersonPeriodWeight": ["ASG-001", date(2026, 7, 1), date(2026, 9, 30), 0.20, "Part-time - parental leave"],
            "Lists": None,
            "Config": None,
        }

    add_readme(wb, kind)
    write_sheet(wb, "Project", proj_rows, examples["Project"], list_ranges)
    write_sheet(wb, "Milestone", mile_rows, examples["Milestone"], list_ranges)
    write_sheet(wb, "ProjectPeriod", period_rows, examples["ProjectPeriod"], list_ranges)
    write_sheet(wb, "PeriodWeightStandard", pws_rows, examples["PeriodWeightStandard"], list_ranges)
    write_sheet(wb, "RoleFactor", role_rows, examples["RoleFactor"], list_ranges)
    write_sheet(wb, "Person", person_rows, examples["Person"], list_ranges)
    write_sheet(wb, "Assignment", asg_rows, examples["Assignment"], list_ranges)
    write_sheet(wb, "PersonPeriodWeight", ppw_rows, examples["PersonPeriodWeight"], list_ranges)
    write_sheet(wb, "Lists", list_rows, None, None)
    write_sheet(wb, "Config", [list(c) for c in CONFIG], None, None)

    # derived formulas
    ws = wb["Project"]
    ci = col_index("Project", "total_period_months")
    for row in range(2, ws.max_row + 1):
        if ws.cell(row=row, column=1).value:
            ws.cell(row=row, column=ci,
                    value=f"=IF(OR($O{row}=\"\",$P{row}=\"\"),\"\","
                          f"(YEAR($P{row})-YEAR($O{row}))*12+MONTH($P{row})-MONTH($O{row})+1)")
    ws = wb["Milestone"]
    ci = col_index("Milestone", "project_name")
    for row in range(2, ws.max_row + 1):
        if ws.cell(row=row, column=1).value:
            ws.cell(row=row, column=ci,
                    value=f'=IFERROR(INDEX(Project!$B:$B,MATCH($A{row},Project!$A:$A,0)),"")')
    ws = wb["Assignment"]
    ci = col_index("Assignment", "person_name")
    for row in range(2, ws.max_row + 1):
        if ws.cell(row=row, column=1).value:
            ws.cell(row=row, column=ci,
                    value=f'=IFERROR(INDEX(Person!$B:$B,MATCH($B{row},Person!$A:$A,0)),"")')

    OUTDIR.mkdir(exist_ok=True)
    suffix = "Template" if kind == "template" else "Dummy"
    out = OUTDIR / f"PRAP_SourceData_{suffix}_v{VERSION}.xlsx"
    wb.save(out)
    return out


if __name__ == "__main__":
    for k in ("template", "dummy"):
        print("Written:", build(k))
