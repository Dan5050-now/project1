"""The three pieces that let a PC with no Python run the application - checked.

Some staff PCs have no Python and no way to get one without a request to IT. The
answer is not to install anything: Windows publishes an EMBEDDABLE PACKAGE, which is
unpacked rather than installed, and the application's own design already suits it -
standard library only, and a folder browser of its own where there is no tkinter.

Three things carry that, and each of them fails silently if it drifts:

    PM_APP.cmd              finds a runtime beside the app, or Python on the PC,
                            and says so plainly when there is neither
    bundle_runtime.py       puts the runtime there, and refuses the wrong file
    check_pc.py             answers "can this PC run it" on screen, with nothing
                            in the output that would need clearing first

    python tools/test_no_python.py
"""

import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "dist" / "PM_APP_py"
BUNDLE = ROOT / "tools" / "bundle_runtime.py"
CHECK = ROOT / "tools" / "check_pc.py"

fails = []


def check(label, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"   {detail}" if detail else ""))
    if not ok:
        fails.append(label)


def run(*args, **kw):
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True,
                       timeout=180, **kw)
    return r.returncode, r.stdout + r.stderr


def embeddable_zip(path, ver="314"):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("python.exe", b"MZ")
        z.writestr(f"python{ver}.zip", b"stdlib")
        z.writestr(f"python{ver}._pth", f"python{ver}.zip\n.\n")
        z.writestr("python3.dll", b"dll")
    return path


print("a PC with no Python")

# ---- 1. the launcher -------------------------------------------------------
cmd = APP / "PM_APP.cmd"
check("the build ships a launcher", cmd.is_file(), cmd.name)
if cmd.is_file():
    raw = cmd.read_bytes()
    text = raw.decode("ascii", "replace")
    check("cmd.exe can read it: CRLF and no BOM",
          b"\r\n" in raw and not raw.startswith(b"\xef\xbb\xbf"))
    # The order is the whole design: a runtime beside the app means nothing on this
    # PC is consulted, so it has to be looked at FIRST.
    order = [m for m in re.findall(r"runtime\\python\.exe|py -3|python --version", text)]
    check("it looks for the bundled runtime BEFORE anything installed",
          order[:1] == ["runtime\\python.exe"], " then ".join(dict.fromkeys(order)))
    check("every path is anchored to the launcher's own folder, not the working "
          "directory", text.count("%~dp0") >= 4 and "cd /d \"%~dp0\"" in text)
    check("and it pauses when there is no Python, instead of flashing shut",
          "pause" in text and "no Python" in text)
    # THE ONE THAT BITES THE TARGET USER. Windows 10 and 11 ship an app execution
    # alias for python.exe by default, and RUNNING it opens the Microsoft Store - on
    # a PC with no Python, which is the PC this launcher exists for. `where` looks
    # without starting anything, so the alias can be found and skipped.
    check("it never STARTS `python` to find out whether it is real - it looks first, "
          "or the Microsoft Store opens on the very PC this is for",
          "where python" in text and "WindowsApps" in text
          and not re.search(r"^\s*python --version", text, re.M))

# ---- 2. the bundler --------------------------------------------------------
with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    app = d / "PM_APP_py"
    app.mkdir()
    (app / "PM_APP.py").write_text(
        "import os, sys\n"
        "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n",
        encoding="utf-8")

    good = embeddable_zip(d / "python-3.14.7-embed-amd64.zip")
    rc, out = run(str(BUNDLE), str(good), "--into", str(app))
    check("an embeddable package is unpacked beside the application",
          rc == 0 and (app / "runtime" / "python.exe").is_file())
    check("and it reports which Python, for the version rule", "3.14" in out)

    rc2, _ = run(str(BUNDLE), str(good), "--into", str(app))
    check("a runtime already there is not overwritten by accident", rc2 == 1)
    rc3, _ = run(str(BUNDLE), str(good), "--into", str(app), "--replace")
    check("--replace overwrites it on purpose", rc3 == 0)

    # The two things people reach for instead, both of which look plausible.
    full = d / "python-3.14.7-full.zip"
    with zipfile.ZipFile(full, "w") as z:
        z.writestr("python.exe", b"MZ")
        z.writestr("Lib/os.py", "x")
    rc4, out4 = run(str(BUNDLE), str(full), "--into", str(app), "--replace")
    check("the full distribution is refused, and named", rc4 == 1
          and "not a Windows embeddable package" in out4)
    exe = d / "python-3.14.7-amd64.exe"
    exe.write_bytes(b"MZ installer")
    rc5, out5 = run(str(BUNDLE), str(exe), "--into", str(app))
    check("so is the installer, with the difference explained", rc5 == 1
          and "the installer" in out5)

    # THE LOAD-BEARING LINE. An embeddable Python fixes sys.path from its ._pth and
    # ignores PYTHONPATH, so PM_APP.py putting its own folder on the path is what
    # makes `import pmapp` work at all - and it is one tidy-up away from being gone.
    (app / "PM_APP.py").write_text("import os, sys\n", encoding="utf-8")
    rc6, out6 = run(str(BUNDLE), str(good), "--into", str(app), "--replace")
    check("IT REFUSES TO BUNDLE AGAINST A LAUNCHER THAT LOST ITS sys.path LINE",
          rc6 == 1 and "sys.path" in out6 and "Nothing has been unpacked" in out6)

# ---- 2b. the trap between the two -----------------------------------------
# Rebuilding the application empties its folder, runtime and all. Silently would be
# the worst of it: the launcher goes on working on the machine that built it, by
# falling back to the Python there, and tells somebody with no Python that none was
# supplied - long after anyone is still looking.
with tempfile.TemporaryDirectory() as d:
    z = embeddable_zip(pathlib.Path(d) / "python-3.14.7-embed-amd64.zip")
    run(str(BUNDLE), str(z), "--into", str(APP), "--replace")
check("a runtime can be bundled into the real application folder",
      (APP / "runtime" / "python.exe").is_file())
rc, out = run(str(ROOT / "tools" / "build_python_app.py"))
check("A REBUILD THAT REMOVES A BUNDLED RUNTIME SAYS SO - silently would leave the "
      "launcher working here and failing on a PC with no Python",
      rc == 0 and "runtime" in out and "bundle_runtime" in out,
      [ln.strip() for ln in out.splitlines() if "runtime" in ln][:1])
check("and the runtime really is gone, so the warning is not decoration",
      not (APP / "runtime").exists())

# AND THE ZIP THAT GETS HANDED OUT. `build_python_app.py --zip` is the obvious command
# for "make me something to give people", and it rebuilds before it packages - so the
# zip it writes has no runtime in it and says nothing about that. The packaging that
# keeps the runtime lives in bundle_runtime.py, and the difference is checked here
# because it is invisible until somebody on a PC with no Python opens the wrong one.
with tempfile.TemporaryDirectory() as d:
    z = embeddable_zip(pathlib.Path(d) / "python-3.14.7-embed-amd64.zip")
    run(str(BUNDLE), str(z), "--into", str(APP), "--replace", "--zip")
    made = sorted(APP.parent.glob("PM_APP_python_v*_with_runtime.zip"))
    check("bundle_runtime --zip packages the folder as it stands", len(made) == 1,
          made[0].name if made else "nothing written")
    if made:
        with zipfile.ZipFile(made[0]) as zf:
            names = zf.namelist()
        check("AND THE RUNTIME IS INSIDE IT",
              any(n.startswith("PM_APP/runtime/") for n in names),
              f"{sum(1 for n in names if 'runtime' in n)} runtime file(s)")
        check("along with the launcher and the PC check",
              "PM_APP/PM_APP.cmd" in names and "PM_APP/check_pc.py" in names)
        # Running the application leaves __pycache__ behind, and this packages the
        # folder AS IT STANDS - so the droppings go out with it unless they are
        # excluded. They are worse than clutter here: compiled by whichever Python
        # the packager used, which is not the one in runtime\ and which nothing on
        # the far side can use. Made real rather than hoped for.
        (APP / "pmapp" / "__pycache__").mkdir(parents=True, exist_ok=True)
        (APP / "pmapp" / "__pycache__" / "junk.cpython-311.pyc").write_bytes(b"x")
        run(str(BUNDLE), str(z), "--into", str(APP), "--replace", "--zip")
        with zipfile.ZipFile(made[0]) as zf:
            after = zf.namelist()
        check("AND NO BUILD DROPPINGS GO OUT WITH IT",
              not [n for n in after if "__pycache__" in n or n.endswith(".pyc")],
              f"{len(after)} files, none of them .pyc")
        made[0].unlink()

rc, _ = run(str(ROOT / "tools" / "build_python_app.py"), "--zip")
plain = sorted(APP.parent.glob("PM_APP_python_v*.zip"))
plain = [q for q in plain if "with_runtime" not in q.name]
if plain:
    with zipfile.ZipFile(plain[0]) as zf:
        names = zf.namelist()
    check("while the plain --zip has none - which is why the two are named apart",
          not any("runtime" in n for n in names), plain[0].name)

# ---- 2c. the checks the bundler makes, which were the bug --------------------
# A shipped version of bundle_runtime.py asked the application for its version before
# --version existed. The application ignores words it does not know, so it STARTED:
# served a page, opened a browser, waited for a person. subprocess then timed out and
# threw, the run died before the packaging, and what the operator saw was a login
# screen and no zip. Two things let that out of the door, and both are checked here:
# the check started something that never returns, and it sat inside `if os.name ==
# "nt"`, where nothing on this side could ever run it.
sys.path.insert(0, str(ROOT / "tools"))
import bundle_runtime as BR                                          # noqa: E402

t0 = time.monotonic()
rows = BR.verify(sys.executable, APP)
elapsed = time.monotonic() - t0
by = {label: (text, ok) for label, text, ok in rows}

check("THE CHECKS CAN BE RUN FROM HERE AT ALL - they take the interpreter as an "
      "argument, instead of hiding on a Windows-only branch",
      len(rows) == 4 and all(by.values()))
check("EVERY ONE OF THEM COMES BACK BY ITSELF, and quickly - a check that starts the "
      "application never returns, and takes the packaging down with it",
      elapsed < 20, f"all four in {elapsed:.1f}s")
check("the start check asks PM_APP.py --version, and gets a version",
      by["START"][1] and "1." in by["START"][0], by["START"][0])
check("the application really does stop after --version rather than serving",
      run(str(APP / "PM_APP.py"), "--version")[0] == 0)

# A hang is reported, not raised. This is the exact shape of the failure that got out.
t0 = time.monotonic()
ok, txt = BR.run_one(sys.executable, ["-c", "import time; time.sleep(120)"], timeout=2)
check("AND IF SOMETHING DOES HANG, IT IS AN ANSWER, NOT AN EXCEPTION",
      ok is False and "did not stop by itself" in txt and time.monotonic() - t0 < 20,
      txt)

with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    old = d / "PM_APP_py"
    (old / "pmapp" / "shell").mkdir(parents=True)
    (old / "PM_APP.py").write_text(
        "import os, sys\n"
        "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
        "import time; time.sleep(600)\n", encoding="utf-8")
    (old / "pmapp" / "shell" / "launch.py").write_text("def main(argv=None):\n    pass\n",
                                                       encoding="utf-8")
    t0 = time.monotonic()
    rows = BR.verify(sys.executable, old)
    check("an older build with no --version is NOT asked - asking would start it",
          "not checked" in dict((a, b) for a, b, _ in rows)["START"]
          and time.monotonic() - t0 < 20)

    # And the packaging is not hostage to any of it. A check that fails has to leave
    # the zip written and say so, because being told at the end is worth more than
    # being told instead.
    bad = d / "bad_app"
    (bad / "pmapp" / "shell").mkdir(parents=True)
    (bad / "PM_APP.py").write_text(
        "import os, sys\n"
        "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
        "raise SystemExit('this build is broken')\n", encoding="utf-8")
    (bad / "pmapp" / "shell" / "launch.py").write_text(
        'if "--version" in argv:\n    pass\n', encoding="utf-8")
    (bad / "version.txt").write_text("9.9.9", encoding="utf-8")
    z = embeddable_zip(d / "python-3.14.7-embed-amd64.zip")
    rc, out = run(str(BUNDLE), str(z), "--into", str(bad), "--zip",
                  "--check-with", sys.executable)
    made = bad.parent / "PM_APP_python_v9.9.9_with_runtime.zip"
    check("A FAILED CHECK STILL LEAVES THE ZIP WRITTEN", made.is_file())
    check("and says, last, that it is not ready to hand out",
          rc == 1 and "NOT READY TO HAND OUT" in out and "START" in out,
          [ln.strip() for ln in out.splitlines() if "NOT READY" in ln][:1])

# ---- 3. the PC check -------------------------------------------------------
rc, out = run(str(CHECK))
check("the PC check runs and reaches a verdict",
      "verdict" in out and rc in (0, 1))
check("it checks what the application actually needs",
      all(k in out for k in ("python version", "standard library", "loopback socket",
                             "a browser to open", "write beside the app")))
check("FAIL and WARN are told apart, so a survivable thing does not read as fatal",
      "WARN" in out or "PASS" in out)

leaked = [w for w in (os.environ.get("USER", ""), os.environ.get("USERNAME", ""),
                      str(ROOT), os.uname().nodename if hasattr(os, "uname") else "")
          if w and w in out]
check("NOTHING IN THE OUTPUT IDENTIFIES THE PC", not leaked,
      "leaked: " + ", ".join(leaked) if leaked else "no path, no host, no account")

code = [ln for ln in out.splitlines() if ln.strip().startswith("code")]
check("a transcription code is printed", len(code) == 1)
_, again = run(str(CHECK))
code2 = [ln for ln in again.splitlines() if ln.strip().startswith("code")]
check("and the same verdicts give the same code", code == code2,
      code[0].strip() if code else "none")

rc7, out7 = run(str(CHECK), "--where", str(ROOT / "definitely-not-here"))
check("a folder it cannot reach is a FAIL, not a shrug",
      rc7 == 1 and "not there" in out7)

print(f"\nFAILURES: {', '.join(fails) if fails else 'none'}")
sys.exit(1 if fails else 0)
