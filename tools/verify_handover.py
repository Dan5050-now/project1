#!/usr/bin/env python3
"""Verify a TEA handover on arrival, on the company laptop.

Run this first, before doing any work. It checks, in order:

  1. Python version and the one dependency
  2. every file against MANIFEST.sha256, and the manifest against its own digest
  3. the required documents and skills are present
  4. all four CI guards pass

Exit code 0 only if everything passes. A manifest failure means the transfer is
corrupt and nothing should be worked from.

Usage:  python3 tools/verify_handover.py
"""
import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

GUARDS = [
    ("workbook integrity", "tools/check_workbook_integrity.py"),
    ("catalog drift", "tools/check_catalog_drift.py"),
    ("query style", "tools/check_query_style.py"),
    ("AI guides", "tools/check_ai_guides.py"),
]

REQUIRED_DOCS = [
    "CLAUDE.md",
    "docs/handover/HANDOVER.md",
    "docs/plan/TEA-PLAN-001_development-plan.xlsx",
    "docs/spec/TEA-SPEC-001_programming-specification.xlsx",
    "docs/spec/rule-catalog.yaml",
    "docs/boundary/TEA-BND-001_portability-boundary.xlsx",
]
REQUIRED_SKILLS = ["sdtm-conversion", "study-configuration", "edc-mapping",
                   "run-and-triage", "validation-evidence", "common-change-request"]

GREEN, RED, DIM, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def ok(msg):
    print(f"  {GREEN}pass{OFF}  {msg}")


def bad(msg):
    print(f"  {RED}FAIL{OFF}  {msg}")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_environment():
    print("\nEnvironment")
    failures = []
    v = sys.version_info
    if (v.major, v.minor) >= (3, 11):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        bad(f"Python {v.major}.{v.minor}.{v.micro} — 3.11 or later is needed")
        failures.append("python")
    try:
        import openpyxl
        ok(f"openpyxl {openpyxl.__version__}")
    except ImportError:
        bad("openpyxl not installed — run: python3 -m pip install -r requirements.txt")
        failures.append("openpyxl")
    return failures


def check_manifest():
    print("\nTransfer integrity")
    manifest = REPO / "MANIFEST.sha256"
    if not manifest.exists():
        print(f"  {DIM}skip{OFF}  no MANIFEST.sha256 — cloned from the git bundle "
              f"rather than unpacked from the archive, so git already verified "
              f"content integrity")
        return []

    digest_file = REPO / "MANIFEST.sha256.digest"
    if digest_file.exists():
        expected = digest_file.read_text().split()[0]
        actual = sha256(manifest)
        if expected == actual:
            ok("manifest matches its own digest")
        else:
            bad(f"manifest digest mismatch — the manifest itself was altered\n"
                f"        expected {expected}\n        actual   {actual}")
            return ["manifest-digest"]

    missing, altered, checked = [], [], 0
    for line in manifest.read_text().splitlines():
        if not line.strip():
            continue
        want, rel = line.split("  ", 1)
        p = REPO / rel
        if not p.exists():
            missing.append(rel)
            continue
        if sha256(p) != want:
            altered.append(rel)
        checked += 1

    if missing:
        bad(f"{len(missing)} file(s) missing from the transfer:")
        for m in missing[:10]:
            print(f"          {m}")
    if altered:
        bad(f"{len(altered)} file(s) altered in transfer:")
        for m in altered[:10]:
            print(f"          {m}")
    if not missing and not altered:
        ok(f"all {checked} files match MANIFEST.sha256")
        return []
    return ["manifest"]


def check_contents():
    print("\nContents")
    failures = []
    for rel in REQUIRED_DOCS:
        if (REPO / rel).exists():
            ok(rel)
        else:
            bad(f"{rel} — missing")
            failures.append(rel)
    present = [s for s in REQUIRED_SKILLS
               if (REPO / ".claude" / "skills" / s / "SKILL.md").exists()]
    if len(present) == len(REQUIRED_SKILLS):
        ok(f"all {len(REQUIRED_SKILLS)} AI skills present")
    else:
        bad(f"{len(REQUIRED_SKILLS) - len(present)} skill(s) missing: "
            f"{sorted(set(REQUIRED_SKILLS) - set(present))}")
        failures.append("skills")
    return failures


def check_guards():
    print("\nCI guards")
    failures = []
    for label, script in GUARDS:
        if not (REPO / script).exists():
            bad(f"{label} — {script} missing")
            failures.append(label)
            continue
        r = subprocess.run([sys.executable, script], cwd=REPO,
                           capture_output=True, text=True)
        if r.returncode == 0:
            ok(f"{label}")
        else:
            bad(f"{label}")
            for line in (r.stdout + r.stderr).strip().splitlines():
                print(f"          {line}")
            failures.append(label)
    return failures


def main():
    print("TEA handover verification")
    provenance = REPO / "PACKAGE.txt"
    if provenance.exists():
        print(f"\n{DIM}" + "\n".join(
            f"  {l}" for l in provenance.read_text().splitlines()[:6]) + f"{OFF}")

    failures = (check_environment() + check_manifest()
                + check_contents() + check_guards())

    print()
    if failures:
        print(f"{RED}VERIFICATION FAILED{OFF} — {len(failures)} problem(s): "
              f"{', '.join(failures)}")
        if "manifest" in failures or "manifest-digest" in failures:
            print("\nThe transfer is corrupt. Do not work from this copy — "
                  "request the package again.")
        return 1

    print(f"{GREEN}VERIFIED{OFF} — the handover is complete and intact.\n")
    print("Next: read docs/handover/HANDOVER.md, then open this repository with")
    print("your Claude Code. CLAUDE.md loads automatically and the six skills")
    print("become available.\n")
    print("There is no engine or application code in this package. The work you")
    print("can start on now is in HANDOVER.md section 4.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
