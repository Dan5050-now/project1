"""Cross-check the documents against the artifacts they describe.

The plan documents a schema, the specification documents a parse contract, and the
template is the file both describe. Nothing stops those three drifting apart except
a check, so this is the check.

    python tools/check_consistency.py
"""

import re
import sys
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "PRAP_Development_Plan_v1.6.xlsx"
SPEC = ROOT / "docs" / "PRAP_Programming_Specification_v0.5.xlsx"
TEMPLATE = ROOT / "templates" / "PRAP_SourceData_Template_v1.4.xlsx"
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.5.xlsx"

problems, notes = [], []


def cells(ws):
    for row in ws.iter_rows():
        for c in row:
            if c.value is not None:
                yield c


# ---- 1. the plan's data model vs the template's actual columns -------------
tpl = load_workbook(TEMPLATE)
tpl_cols = {s: [c.value for c in tpl[s][1]] for s in tpl.sheetnames if s != "00_README"}

plan = load_workbook(PLAN)
dm = plan["04_Data_Model"]
# A data-model row is identifiable by its Type cell, which keeps the scan from
# running past the end of a table into the prose that follows it.
TYPES = {"Text", "Date", "Decimal", "Integer", "List", "Derived", "-"}
documented, current = {}, None
for r in range(1, dm.max_row + 1):
    a, t = dm.cell(r, 1).value, dm.cell(r, 2).value
    if isinstance(a, str) and a.startswith("Sheet: "):
        current = a.replace("Sheet: ", "").split(" ")[0].strip()
        documented.setdefault(current, [])
    elif current and isinstance(a, str) and a and t in TYPES:
        documented[current].append(a.strip())

for sheet, cols in documented.items():
    if sheet not in tpl_cols:
        continue
    actual = [c for c in tpl_cols[sheet] if c]
    for col in cols:
        if ".." in col:                      # note_1 .. note_5 shorthand
            stem = col.split("..")[0].strip().rsplit("_", 1)[0]
            if not any(str(a).startswith(stem) for a in actual):
                problems.append(f"plan documents {sheet}.{col} but the template has no {stem}_* column")
            continue
        if "/" in col:                       # 'employment_start / employment_end'
            for part in [p.strip() for p in col.split("/")]:
                if part not in actual:
                    problems.append(f"plan documents {sheet}.{part}, absent from the template")
            continue
        if col not in actual:
            problems.append(f"plan documents {sheet}.{col}, absent from the template")

# ---- 2. sheet set matches -------------------------------------------------
plan_sheets = set(documented) & set(tpl_cols)
missing = set(tpl_cols) - set(documented)
if missing:
    notes.append(f"template sheets not itemised column-by-column in the plan: {sorted(missing)}")

# ---- 3. schema version agrees across plan, spec, template, dummy ----------
def cfg_version(path):
    wb = load_workbook(path)
    for r in wb["Config"].iter_rows(min_row=2, values_only=True):
        if r[0] == "schema_version":
            return int(r[1])
    return None


tpl_v, dum_v = cfg_version(TEMPLATE), cfg_version(DUMMY)
if tpl_v != dum_v:
    problems.append(f"template schema_version {tpl_v} != dummy {dum_v}")

spec = load_workbook(SPEC)
spec_v = None
for c in cells(spec["00_Cover"]):
    if c.value == "Schema version specified":
        spec_v = spec["00_Cover"].cell(c.row, 2).value
if str(spec_v) != str(tpl_v):
    problems.append(f"specification says schema v{spec_v}, template is v{tpl_v}")

plan_v = None
for c in cells(plan["04_Data_Model"]):
    if c.value == "schema_version":
        plan_v = plan["04_Data_Model"].cell(c.row, 3).value
if str(plan_v) != str(tpl_v):
    problems.append(f"plan documents schema v{plan_v}, template is v{tpl_v}")

# ---- 4. project_type values agree everywhere -----------------------------
lists = {}
for r in tpl["Lists"].iter_rows(min_row=2, values_only=True):
    if r[0]:
        lists.setdefault(r[0], []).append(r[1])
types = lists.get("project_type", [])
# 11_Open_Questions and the change register are a historical record: the reviewer's
# own words and the change requests necessarily quote values that have since been
# retired. Rewriting them to match today's schema would falsify the review trail, so
# they are exempt from the retired-literal scan.
RECORD_SHEETS = {"11_Open_Questions", "12_Review_Log", "01_Version_History"}
for doc, wb in (("plan", plan), ("specification", spec)):
    txt = " ".join(str(c.value) for s in wb.sheetnames if s not in RECORD_SHEETS
                   for c in cells(wb[s]))
    for t in types:
        if t not in txt:
            problems.append(f"{doc} never mentions project_type '{t}'")
    if re.search(r"'Clinical Trial'", txt):
        notes.append(f"{doc} still contains the retired literal 'Clinical Trial' somewhere")

# ---- 4b. no build artefacts left in any shipped workbook -----------------
# The generators use [NEW]/[CHANGED] markers to drive row highlighting, and strip
# them on render. One missed strip ships the marker as visible text, so check.
for label, path in (("plan", PLAN), ("specification", SPEC),
                    ("template", TEMPLATE), ("dummy", DUMMY)):
    wb_ = load_workbook(path)
    for sh in wb_.sheetnames:
        for c in cells(wb_[sh]):
            v = c.value
            if not isinstance(v, str):
                continue
            if "[NEW]" in v or "[CHANGED]" in v:
                problems.append(f"{label} {sh}!{c.coordinate}: unstripped marker - {v[:60]}")
            elif v.startswith("=") and not v[1:2].isalpha():
                problems.append(f"{label} {sh}!{c.coordinate}: text starting with '=' will "
                                f"be read as a formula - {v[:60]}")

# ---- 4c. the spec's Config defaults vs the template's actual values -------
# The thresholds live in the workbook as data, and the specification quotes them.
# A threshold changed in one place and not the other is the kind of drift that
# survives review, because both documents read correctly on their own.
tpl_cfg = {r[0]: r[1] for r in tpl["Config"].iter_rows(min_row=2, values_only=True) if r[0]}
sch = spec["03_Data_Schema"]
for row in sch.iter_rows(values_only=True):
    name = row[0]
    if not isinstance(name, str) or name not in tpl_cfg or len(row) < 3:
        continue
    documented_default, actual = str(row[2]).strip(), tpl_cfg[name]
    try:
        same = float(documented_default) == float(actual)
    except (TypeError, ValueError):
        same = documented_default == str(actual).strip()
    if not same:
        problems.append(f"specification documents Config.{name} default {documented_default}, "
                        f"template holds {actual}")

# ---- 5. every requirement in the plan is traced in the specification ------
plan_reqs = {str(plan["03_Requirements"].cell(r, 1).value).strip()
             for r in range(5, plan["03_Requirements"].max_row + 1)
             if str(plan["03_Requirements"].cell(r, 1).value or "").startswith("REQ")}
spec_traced = {str(spec["09_Traceability"].cell(r, 1).value).strip()
               for r in range(5, spec["09_Traceability"].max_row + 1)
               if str(spec["09_Traceability"].cell(r, 1).value or "").startswith("REQ")}
if plan_reqs - spec_traced:
    problems.append(f"requirements in the plan but not traced in the spec: {sorted(plan_reqs - spec_traced)}")
if spec_traced - plan_reqs:
    problems.append(f"requirements traced in the spec but absent from the plan: {sorted(spec_traced - plan_reqs)}")

# ---- report ---------------------------------------------------------------
print(f"plan       {PLAN.name}")
print(f"spec       {SPEC.name}")
print(f"template   {TEMPLATE.name}   schema v{tpl_v}")
print(f"dummy      {DUMMY.name}   schema v{dum_v}")
print(f"types      {types}")
print(f"columns cross-checked: {sum(len(v) for k, v in documented.items() if k in plan_sheets)}"
      f" across {len(plan_sheets)} sheets")
print(f"requirements traced: {len(plan_reqs)}")
print()
if problems:
    print(f"PROBLEMS ({len(problems)}):")
    for p_ in problems:
        print("   ", p_)
else:
    print("PROBLEMS: none - plan, specification, template and dummy agree.")
if notes:
    print(f"\nNOTES ({len(notes)}):")
    for n in notes:
        print("   ", n)

sys.exit(1 if problems else 0)
