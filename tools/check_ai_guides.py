#!/usr/bin/env python3
"""Fail the build when the AI guides and TEA-BND-001 disagree.

The guides in CLAUDE.md and .claude/skills/ are what the company's Claude Code
actually reads; TEA-BND-001 is what the humans review. If an APPLY slot is added
to the register and no skill covers it, the company's Claude Code has work to do
and no instructions for it — and nothing would otherwise notice.

Checks:
  - every skill has valid frontmatter with name and description
  - the skill directory name matches the frontmatter name
  - every APPLY slot in the register (A-nn) is named by at least one skill
  - every read-only path listed in CLAUDE.md exists, or is marked as not yet
    created
  - CLAUDE.md names every skill directory, and names no skill that is absent

Exit code 1 on any mismatch.

Usage:  python3 tools/check_ai_guides.py
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO / "CLAUDE.md"
SKILLS_DIR = REPO / ".claude" / "skills"
BOUNDARY = REPO / "docs" / "boundary" / "TEA-BND-001_portability-boundary.xlsx"

# Paths CLAUDE.md lists as read-only that the build has not produced yet. Each
# is annotated in CLAUDE.md as "once it exists"; drop an entry from here when
# the directory lands.
NOT_YET_BUILT = {"src/", "app/"}


def read_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, text
    fm = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if km:
            val = km.group(2).strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            fm[km.group(1)] = val
    return fm, text[m.end():]


def apply_slots_from_register():
    from openpyxl import load_workbook
    ws = load_workbook(BOUNDARY, read_only=True, data_only=True)["Register"]
    slots = set()
    for row in ws.iter_rows(values_only=True):
        if row and row[0] and re.fullmatch(r"A-\d{2}", str(row[0])):
            slots.add(str(row[0]))
    return slots


def main():
    problems = []

    if not CLAUDE_MD.exists():
        print(f"FAIL: {CLAUDE_MD.name} not found")
        return 1
    if not SKILLS_DIR.exists():
        print(f"FAIL: {SKILLS_DIR} not found")
        return 1

    claude_text = CLAUDE_MD.read_text(encoding="utf-8")

    # --- skills ----------------------------------------------------------
    skills, covered = {}, set()
    for d in sorted(SKILLS_DIR.iterdir()):
        if not d.is_dir():
            continue
        f = d / "SKILL.md"
        if not f.exists():
            problems.append(f"{d.name}: no SKILL.md")
            continue
        fm, body = read_frontmatter(f)
        if fm is None:
            problems.append(f"{d.name}/SKILL.md: no YAML frontmatter — it will not load")
            continue
        if "name" not in fm:
            problems.append(f"{d.name}/SKILL.md: frontmatter has no 'name'")
        elif fm["name"] != d.name:
            problems.append(
                f"{d.name}/SKILL.md: frontmatter name {fm['name']!r} does not match "
                f"the directory name {d.name!r}")
        if not fm.get("description"):
            problems.append(f"{d.name}/SKILL.md: frontmatter has no 'description' — "
                            f"it will never be selected")
        skills[d.name] = fm
        covered |= set(re.findall(r"\bA-\d{2}\b", body))

    if not skills:
        problems.append("no skills found under .claude/skills/")

    # --- APPLY slot coverage ---------------------------------------------
    if BOUNDARY.exists():
        slots = apply_slots_from_register()
        if not slots:
            problems.append("TEA-BND-001 Register lists no APPLY slots — check the sheet")
        for s in sorted(slots - covered):
            problems.append(f"{s}: an APPLY slot in TEA-BND-001 that no skill mentions")
        for s in sorted(covered - slots):
            problems.append(f"{s}: named by a skill but not in the TEA-BND-001 Register")
    else:
        problems.append(f"{BOUNDARY.name} not found — cannot check APPLY slot coverage")

    # --- CLAUDE.md names every skill, and only real ones -----------------
    for name in skills:
        if name not in claude_text:
            problems.append(f"{name}: a skill CLAUDE.md does not mention")
    for named in set(re.findall(r"`([a-z][a-z0-9-]+)`", claude_text)):
        if (SKILLS_DIR / named).exists() or named in skills:
            continue
        if re.search(rf"\.claude/skills/{re.escape(named)}\b", claude_text):
            problems.append(f"{named}: CLAUDE.md points at a skill that does not exist")

    # --- read-only paths exist -------------------------------------------
    block = re.search(r"Read-only paths:\s*\n\s*```\n(.*?)```", claude_text, re.S)
    if not block:
        problems.append("CLAUDE.md: no read-only path block found")
    else:
        for line in block.group(1).splitlines():
            p = line.split("#")[0].split("(")[0].strip()
            if not p or p in NOT_YET_BUILT:
                continue
            if not (REPO / p).exists():
                problems.append(f"CLAUDE.md lists a read-only path that does not exist: {p}")

    if problems:
        print(f"AI GUIDE DRIFT — {len(problems)} problem(s):")
        for p in problems:
            print(f"  {p}")
        return 1

    print(f"AI guides consistent — {len(skills)} skills, "
          f"{len(covered)} APPLY slots covered, all read-only paths present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
