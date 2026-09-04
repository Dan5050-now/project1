#!/usr/bin/env python3
"""Enforce the query message house rules (TEA-QS-001) against the rule catalog.

The reviewer-lens pass rewrote 19 query templates to remove guideline citations
and statements of the expected answer. This keeps them out: a new or edited
review point that reintroduces either fails the build.

Usage:  python3 tools/check_query_style.py [rules.json]
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAX_CHARS = 400

# rule 3 — guideline cited as authority. Naming a CRF field is allowed (rule 4),
# so only the authority constructions are matched.
GUIDELINE_AUTHORITY = re.compile(
    r"\bunder (?:the )?(?:RECIST|iRECIST)\b"
    r"|\bper (?:the )?(?:RECIST|iRECIST)\b"
    r"|required by (?:the )?(?:RECIST|iRECIST)"
    r"|the (?:RECIST|iRECIST) criteria"
    r"|\bRECIST (?:1\.1 )?(?:requires|permits|states|classifies|treats)"
    r"|according to the guideline"
    r"|\bthe guideline\b",
    re.I)

# rule 2 — the query states the expected answer.
STATES_ANSWER = re.compile(
    r"\bshould be recorded\b|\bshould be\b(?! recorded as disease)"
    r"|\bmust be\b|\bthe correct (?:value|response|date) is\b"
    r"|\bplease correct it\b|\bplease remove it\b"
    r"|the appropriate categories are",
    re.I)

# rule 8 — never instruct deletion of recorded data.
INSTRUCTS_DELETE = re.compile(r"\b(?:please )?(?:remove|delete)\b.{0,40}\b(?:from the|the record|it)\b", re.I)

# rule 7 — never ask site staff for a medical judgement.
ASKS_JUDGEMENT = re.compile(
    r"confirm that the (?:overall )?tumou?r burden"
    r"|confirm.{0,30}\bclinically (?:significant|meaningful)\b"
    r"|in your (?:clinical )?opinion",
    re.I)

STUDY_TEAM_PREFIX = "not applicable"


def check(rules):
    problems = []
    for r in rules:
        if r.get("status") == "RETIRED":
            continue
        q = r.get("msg_query", "") or ""
        rid = r["id"]

        if q.strip().lower().startswith(STUDY_TEAM_PREFIX):
            continue                                    # rule 12

        if not q.strip():
            problems.append(f"{rid}: empty query template")
            continue
        if GUIDELINE_AUTHORITY.search(q):
            problems.append(f"{rid}: rule 3 — guideline cited as authority in the query "
                            f"({GUIDELINE_AUTHORITY.search(q).group(0)!r})")
        if STATES_ANSWER.search(q):
            problems.append(f"{rid}: rule 2 — query states the expected answer "
                            f"({STATES_ANSWER.search(q).group(0)!r})")
        if INSTRUCTS_DELETE.search(q):
            problems.append(f"{rid}: rule 8 — query instructs deletion of recorded data")
        if ASKS_JUDGEMENT.search(q):
            problems.append(f"{rid}: rule 7 — query asks site staff for a medical judgement")
        if len(q) > MAX_CHARS:
            problems.append(f"{rid}: rule 11 — query is {len(q)} characters, over {MAX_CHARS}")
        if not re.search(r"\{[a-z_]+\}", q) and r.get("audience") != "STUDY_TEAM":
            # subject-level findings legitimately have no record placeholder
            if not re.search(r"\bthis subject\b|\bat this site\b", q, re.I):
                problems.append(f"{rid}: no data placeholder and no subject-level phrasing")
    return problems


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "tools" / "rules.json"
    rules = json.loads(src.read_text())
    problems = check(rules)
    live = sum(1 for r in rules if r.get("status") != "RETIRED")
    if problems:
        print(f"QUERY STYLE — {len(problems)} problem(s):")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"all {live} live query templates satisfy TEA-QS-001")
    return 0


if __name__ == "__main__":
    sys.exit(main())
