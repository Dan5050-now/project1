"""tools/check_share.py - the on-site check, checked here.

It exists because a result file cannot always leave a company network, so its whole
output is a dozen lines somebody reads off a screen. That places two requirements on it
that are easy to state and easy to break later:

    it must leave the folder exactly as it found it, and
    it must not print anything that would need clearing before being said out loud -
    no path, no share name, no machine, no account.

Both are checked here rather than trusted, because the second one is the kind of promise
that is made once and broken by a helpful debug line six months later.

    python tools/test_share_check.py
"""

import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check_share.py"

fails = []


def check(label, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"   {detail}" if detail else ""))
    if not ok:
        fails.append(label)


def run(*args):
    r = subprocess.run([sys.executable, str(TOOL), *args],
                       capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout


print("the on-site share check")

with tempfile.TemporaryDirectory() as d:
    # A path with something identifiable in it, so that if the tool ever prints where
    # it is looking, this test is what notices.
    share = os.path.join(d, "ACME-FILESERVER", "Department Plans")
    os.makedirs(share)
    before = sorted(os.listdir(share))
    rc, out = run(share)

    check("a healthy folder passes", rc == 0 and "SAFE FOR SHARED USE" in out)
    check("every check it makes is reported",
          all(k in out for k in ("writable", "exclusive create", "rename over existing",
                                 "append, 2 writers", "journal survives",
                                 "new file is listed", "mtime granularity")),
          f"{out.count('PASS')} PASS")
    check("THE FOLDER IS EXACTLY AS IT WAS", sorted(os.listdir(share)) == before,
          f"{len(os.listdir(share))} entries")
    check("and it says so", "nothing left behind" in out)

    # The one that makes the result sayable down a telephone.
    leaked = [w for w in ("ACME-FILESERVER", "Department Plans", share, d,
                          os.uname().nodename if hasattr(os, "uname") else "\0")
              if w and w in out]
    check("NOTHING IN THE OUTPUT IDENTIFIES THE SITE", not leaked,
          "leaked: " + ", ".join(leaked) if leaked else "no path, no host, no account")

    code = [ln for ln in out.splitlines() if ln.strip().startswith("code")]
    check("a transcription code is printed", len(code) == 1 and len(code[0].split()[-1]) == 14,
          code[0].strip() if code else "none")

    # THE CODE HAS TO BE A FUNCTION OF THE VERDICTS AND OF NOTHING ELSE. It is there so
    # that six lines read down a telephone can be checked for a slip, which only works
    # if the same verdicts always give the same code - put a timestamp or a path into
    # that digest and it becomes a number nobody can verify anything against. Two runs,
    # same folder, same verdicts.
    _, out_again = run(share)
    code_again = [ln for ln in out_again.splitlines() if ln.strip().startswith("code")]
    check("and the same verdicts give the same code, which is what makes it checkable",
          bool(code) and code_again == code, code_again[0].strip() if code_again else "none")

    rc2, out2 = run(os.path.join(d, "not-there"))
    check("a folder that is not there is refused, not guessed at",
          rc2 == 1 and "not there" in out2)

    os.mkdir(os.path.join(share, "prap-share-check"))
    rc3, out3 = run(share)
    check("an interrupted earlier run is noticed rather than written over",
          rc3 == 1 and "already there" in out3)
    os.rmdir(os.path.join(share, "prap-share-check"))

    rc4, out4 = run(share, "--keep")
    kept = os.path.isdir(os.path.join(share, "prap-share-check"))
    check("--keep leaves the scratch folder for inspection", rc4 == 0 and kept)
    if kept:
        for f in os.listdir(os.path.join(share, "prap-share-check")):
            os.unlink(os.path.join(share, "prap-share-check", f))
        os.rmdir(os.path.join(share, "prap-share-check"))

print(f"\nFAILURES: {', '.join(fails) if fails else 'none'}")
sys.exit(1 if fails else 0)
