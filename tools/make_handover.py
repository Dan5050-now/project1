#!/usr/bin/env python3
"""Build the handover package for transfer to the company laptop.

Produces, in the output directory:

  TEA-handover-<date>/              staged working tree + MANIFEST.sha256
  TEA-handover-<date>.tar.gz        the staged tree, for environments without git
  TEA-repo-<date>.bundle            git bundle with full history (preferred)
  MANIFEST.sha256                   a copy outside the archive, to check against
  HANDOVER.md                       a copy outside the archive, to read first

Only git-tracked files are staged, so nothing untracked, ignored or left over in
the working directory can travel by accident. The manifest is written in
`sha256sum -c` format so the company laptop can verify the transfer with native
tools and no Python at all.

Usage:  python3 tools/make_handover.py [--out DIR] [--date YYYY-MM-DD]
"""
import argparse
import hashlib
import shutil
import subprocess
import sys
import tarfile
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HANDOVER_DOC = REPO / "docs" / "handover" / "HANDOVER.md"

# Files that must be present or the package is not a handover at all.
REQUIRED = [
    "CLAUDE.md",
    "requirements.txt",
    "docs/handover/HANDOVER.md",
    "docs/plan/TEA-PLAN-001_development-plan.xlsx",
    "docs/spec/TEA-SPEC-001_programming-specification.xlsx",
    "docs/spec/rule-catalog.yaml",
    "docs/boundary/TEA-BND-001_portability-boundary.xlsx",
    "tools/check_workbook_integrity.py",
    "tools/check_catalog_drift.py",
    "tools/check_query_style.py",
    "tools/check_ai_guides.py",
    "tools/verify_handover.py",
]
REQUIRED_SKILLS = ["sdtm-conversion", "study-configuration", "edc-mapping",
                   "run-and-triage", "validation-evidence", "common-change-request"]


def run(args, **kw):
    return subprocess.run(args, cwd=REPO, check=True, text=True,
                          capture_output=True, **kw).stdout


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None,
                    help="output directory (default: ./dist)")
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()

    out = Path(args.out).resolve() if args.out else REPO / "dist"
    name = f"TEA-handover-{args.date}"
    stage = out / name

    # --- refuse to package a dirty tree -----------------------------------
    dirty = run(["git", "status", "--porcelain"]).strip()
    if dirty:
        print("FAIL: working tree is not clean. Commit or stash first:\n")
        print(dirty)
        return 1

    head = run(["git", "rev-parse", "HEAD"]).strip()
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip()
    tracked = [l for l in run(["git", "ls-files"]).splitlines() if l]

    # --- completeness check before staging --------------------------------
    missing = [p for p in REQUIRED if p not in tracked]
    for s in REQUIRED_SKILLS:
        p = f".claude/skills/{s}/SKILL.md"
        if p not in tracked:
            missing.append(p)
    if missing:
        print(f"FAIL: {len(missing)} required file(s) not tracked in git:")
        for m in missing:
            print(f"  {m}")
        return 1

    # --- stage -------------------------------------------------------------
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    for rel in tracked:
        src, dst = REPO / rel, stage / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # --- manifest, in sha256sum -c format ---------------------------------
    lines = [f"{sha256(stage / rel)}  {rel}" for rel in sorted(tracked)]
    manifest = stage / "MANIFEST.sha256"
    manifest.write_text("\n".join(lines) + "\n")

    # The manifest cannot contain its own hash, so it gets a separate digest.
    manifest_digest = sha256(manifest)
    (stage / "MANIFEST.sha256.digest").write_text(
        f"{manifest_digest}  MANIFEST.sha256\n")

    provenance = stage / "PACKAGE.txt"
    provenance.write_text(
        f"TEA handover package\n"
        f"built            {args.date}\n"
        f"git commit       {head}\n"
        f"git branch       {branch}\n"
        f"files            {len(tracked)}\n"
        f"manifest sha256  {manifest_digest}\n"
        f"\n"
        f"Verify on arrival:\n"
        f"  sha256sum -c MANIFEST.sha256\n"
        f"  python3 tools/verify_handover.py\n"
        f"\n"
        f"Read docs/handover/HANDOVER.md first. This package contains the\n"
        f"documents and AI guides only; there is no engine or application code.\n")

    # --- archives ----------------------------------------------------------
    tgz = out / f"{name}.tar.gz"
    with tarfile.open(tgz, "w:gz") as tf:
        tf.add(stage, arcname=name)

    bundle = out / f"TEA-repo-{args.date}.bundle"
    if bundle.exists():
        bundle.unlink()
    run(["git", "bundle", "create", str(bundle), "--all"])

    # --- loose copies, so they can be read before unpacking ---------------
    shutil.copy2(manifest, out / "MANIFEST.sha256")
    shutil.copy2(provenance, out / "PACKAGE.txt")
    shutil.copy2(HANDOVER_DOC, out / "HANDOVER.md")

    def mb(p):
        return f"{p.stat().st_size / 1_048_576:.2f} MB"

    print(f"handover package built in {out}\n")
    print(f"  {bundle.name:36s} {mb(bundle):>10s}   git bundle, full history (preferred)")
    print(f"  {tgz.name:36s} {mb(tgz):>10s}   plain working tree")
    print(f"  {'MANIFEST.sha256':36s} {mb(out / 'MANIFEST.sha256'):>10s}   {len(tracked)} files")
    print(f"  {'PACKAGE.txt':36s} {mb(out / 'PACKAGE.txt'):>10s}   provenance")
    print(f"  {'HANDOVER.md':36s} {mb(out / 'HANDOVER.md'):>10s}   read this first")
    print(f"\n  commit   {head}")
    print(f"  manifest {manifest_digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
