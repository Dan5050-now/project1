"""The Python storage layer, tested where it can actually break.

The JavaScript version of this suite (tools/test_storage.mjs) found two real defects
in the Electron shell, both of which would have reached a user. This is its port,
and it keeps the two tests that did the finding:

  * KILL THE PROCESS MID-SAVE, twelve times, at twelve different moments. After each
    one the workspace must still parse and must still hold the figures from before
    the interrupted save. A save protocol is a claim about power loss, and a claim
    about power loss is worth exactly as much as the test that pulls the plug.
  * EIGHT PROCESSES RACING FOR ONE CLAIM. Exactly one may win. Two sessions can both
    read "free"; only an exclusive create has one winner, and only a real race
    proves it.

Neither needs a window, which is the whole reason the storage layer has no window in
it. Run it against the BUILT package, because that is what gets sent:

    python tools/build_python_app.py && python tools/test_storage_py.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "dist" / "PM_APP_py"

if not (PKG / "pmapp").is_dir():
    raise SystemExit("Build it first:  python tools/build_python_app.py")

sys.path.insert(0, str(PKG))

from pmapp.shell import files as F          # noqa: E402
from pmapp.shell import paths as PA         # noqa: E402
from pmapp.storage import claim as CL       # noqa: E402
from pmapp.storage import timefmt as TF     # noqa: E402
from pmapp.storage import workspace as WS   # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"   {detail}" if detail and not ok
                                                     else ""))


def sheets(n=3):
    return {"Project": [{"project_id": f"P{i}", "project_name": f"Plan {i}"}
                        for i in range(n)],
            "Person": [{"person_id": "X1", "person_name": "A"}]}


ME = {"name": "Tester", "department": "Dev"}
OTHER = {"name": "Somebody Else", "department": "Ops"}


# ---------------------------------------------------------------- 1. the round trip

def test_roundtrip(d):
    print("\nsaving and reading back")
    ref = str(d / "plan.prap")
    out = WS.save_workspace(ref, sheets(), identity=ME)
    check("save reports where it went", out["ref"] == os.path.abspath(ref))
    check("save reports when", bool(out["savedAt"]))
    check("the file is there", os.path.exists(ref))

    w = WS.open_workspace(ref)
    check("the sheets come back unchanged", w["sheets"] == sheets())
    check("who saved it is recorded", w["header"]["last_saved_by"]["name"] == "Tester")
    check("the schema version is stamped", w["header"]["schema_version"] == 5)
    check("the format is the interchange format", True)

    # The Electron shell must be able to read it, so the timestamp must be its
    # spelling rather than Python's.
    raw = json.loads(Path(ref).read_text(encoding="utf-8"))
    stamp = raw["workspace"]["last_saved"]
    check("timestamps are in the JavaScript spelling", stamp.endswith("Z")
          and "+00:00" not in stamp, stamp)
    check("and parse back to the same instant",
          abs(TF.parse(stamp) - TF.now_ms()) < 60_000)


# --------------------------------------------------------------- 2. refusing badly

def test_refusals(d):
    print("\nrefusing things, with a sentence rather than a stack trace")
    missing = str(d / "nothing.prap")
    try:
        WS.open_workspace(missing)
        check("a missing plan is refused", False)
    except WS.StorageError as e:
        check("a missing plan is refused", e.kind == "not_found")
        check("and the message names the file", missing in e.message)

    wrong = d / "notaplan.prap"
    wrong.write_text('{"hello":1}', encoding="utf-8")
    try:
        WS.open_workspace(str(wrong))
        check("a file that is not a plan is refused", False)
    except WS.StorageError as e:
        check("a file that is not a plan is refused", e.kind == "unreadable")
        check("and it suggests Import instead", "Import" in e.message)

    torn = d / "torn.prap"
    torn.write_text('{"format":"prap-source-data", "sheets": {', encoding="utf-8")
    try:
        WS.open_workspace(str(torn))
        check("a truncated plan is refused", False)
    except WS.StorageError as e:
        check("a truncated plan is refused", e.kind == "unreadable")

    # R-N18: protection must not read as corruption.
    prot = d / "protected.xlsx"
    prot.write_bytes(bytes([0xD0, 0xCF, 0x11, 0xE0, 0xA1, 0xB1, 0x1A, 0xE1]) + b"\x00" * 64)
    check("an OLE2 file is seen as protected", WS.looks_protected(prot.read_bytes()))
    enc_zip = b"PK\x03\x04" + bytes([0, 0, 0x01, 0]) + b"\x00" * 32
    check("an encrypted zip is seen as protected", WS.looks_protected(enc_zip))
    plain_zip = b"PK\x03\x04" + bytes([0, 0, 0x00, 0]) + b"\x00" * 32
    check("an ordinary xlsx is not", not WS.looks_protected(plain_zip))
    try:
        WS.open_workspace(str(prot))
        check("and opening one says PROTECTED, not corrupt", False)
    except WS.StorageError as e:
        check("and opening one says PROTECTED, not corrupt", e.kind == "protected")

    # NR-DEP-04: refuse, never partially read.
    newer = d / "newer.prap"
    doc = json.loads(Path(str(d / "plan.prap")).read_text(encoding="utf-8"))
    doc["workspace"]["app_version"] = "99.0"
    newer.write_text(json.dumps(doc), encoding="utf-8")
    try:
        WS.open_workspace(str(newer))
        check("a plan from a newer version is refused", False)
    except WS.StorageError as e:
        check("a plan from a newer version is refused", e.kind == "too_new")


# ------------------------------------------------------------- 3. killed mid-save

KILL_SCRIPT = r'''
import os, sys, time, threading
sys.path.insert(0, sys.argv[1])
from pmapp.storage import workspace as WS
ref, delay_ms, n = sys.argv[2], float(sys.argv[3]), int(sys.argv[4])
threading.Thread(target=lambda: (time.sleep(delay_ms / 1000.0), os._exit(9)),
                 daemon=True).start()
WS.save_workspace(ref, {"Project": [{"project_id": f"NEW{i}"} for i in range(n)]},
                  identity={"name": "Killer", "department": ""})
'''


def test_kill_mid_save(d):
    print("\nkilled mid-save, twelve times")
    ref = str(d / "durable.prap")
    good = {"Project": [{"project_id": "GOOD"}]}
    WS.save_workspace(ref, good, identity=ME)
    before = Path(ref).read_text(encoding="utf-8")

    script = d / "killer.py"
    script.write_text(KILL_SCRIPT, encoding="utf-8")

    survived = 0
    for i in range(12):
        delay = 0.05 + i * 0.7                  # from "before it starts" to "well after"
        subprocess.run([sys.executable, str(script), str(PKG), ref, str(delay), "4000"],
                       capture_output=True, timeout=60)
        try:
            w = WS.open_workspace(ref)
        except WS.StorageError:
            check(f"kill at {delay:.2f}ms leaves a readable plan", False)
            continue
        ids = [r.get("project_id") for r in w["sheets"]["Project"]]
        intact = ids == ["GOOD"] or all(str(x).startswith("NEW") for x in ids)
        if not intact:
            check(f"kill at {delay:.2f}ms leaves whole data", False, str(ids[:3]))
            continue
        survived += 1

    check("twelve kills, twelve readable plans", survived == 12, f"{survived}/12")
    check("the good data is never half-replaced",
          Path(ref).read_text(encoding="utf-8") == before
          or "NEW" in Path(ref).read_text(encoding="utf-8"))
    left = [p for p in os.listdir(d) if ".tmp-" in p]
    n = WS.sweep_temp(str(d))
    check("interrupted saves leave only a .tmp, and it is swept", n == len(left),
          f"{len(left)} left, {n} swept")


# ------------------------------------------------------------------ 4. versions

def test_versions(d):
    print("\nkeeping the version before this one")
    ref = str(d / "versioned.prap")
    WS.save_workspace(ref, {"Project": [{"project_id": "V1"}]}, identity=ME)
    check("nothing is kept from the first save", WS.list_versions(ref) == [])
    WS.save_workspace(ref, {"Project": [{"project_id": "V2"}]}, identity=ME)
    vs = WS.list_versions(ref)
    check("one version is kept from the second", len(vs) == 1)
    WS.save_workspace(ref, {"Project": [{"project_id": "V3"}]}, identity=ME)
    check("and still only one, at the default", len(WS.list_versions(ref)) == 1)

    old = WS.restore_version(ref, 1)
    check("the kept version is the one before this", old["sheets"]["Project"][0]["project_id"] == "V2")
    check("restoring does not touch the current file",
          WS.open_workspace(ref)["sheets"]["Project"][0]["project_id"] == "V3")

    WS.save_workspace(ref, {"Project": [{"project_id": "V4"}]}, retain=3, identity=ME)
    WS.save_workspace(ref, {"Project": [{"project_id": "V5"}]}, retain=3, identity=ME)
    check("retain can be raised without a code change", len(WS.list_versions(ref)) == 3)


# ------------------------------------------------------------------- 5. journal

def test_journal(d):
    print("\npending edits, kept apart from what was committed")
    ref = str(d / "journalled.prap")
    WS.save_workspace(ref, sheets(), identity=ME)
    check("nothing pending to start with", WS.read_journal(ref) is None)

    time.sleep(0.02)
    WS.write_journal(ref, [{"sheet": "Project", "row": 0, "col": "project_name",
                            "was": "Plan 0", "now": "Plan Zero"}])
    j = WS.read_journal(ref)
    check("a pending edit is offered back", bool(j) and len(j["pending"]) == 1)
    check("with when it was made", bool(j.get("at")))

    WS.save_workspace(ref, sheets(), identity=ME)
    check("committing clears it", WS.read_journal(ref) is None)

    # A journal older than the workspace was written against figures that have
    # since been replaced. Offering it would put edits somewhere they never were.
    WS.write_journal(ref, [{"stale": True}])
    os.utime(WS.journal_path(ref), (time.time() - 600, time.time() - 600))
    check("a journal older than the plan is not offered", WS.read_journal(ref) is None)

    Path(WS.journal_path(ref)).write_text("{ not json", encoding="utf-8")
    check("a torn journal is no journal", WS.read_journal(ref) is None)
    WS.clear_journal(ref)
    check("clearing removes it", not os.path.exists(WS.journal_path(ref)))


# --------------------------------------------------------------------- 6. claims

RACE_SCRIPT = r'''
import sys, time
sys.path.insert(0, sys.argv[1])
from pmapp.storage import claim as CL
ref, name, at = sys.argv[2], sys.argv[3], float(sys.argv[4])
while time.time() < at:
    pass
r = CL.claim(ref, {"name": name, "department": "Race"})
print("WON" if r["ok"] else "lost")
'''


def test_claim(d):
    print("\none writer at a time")
    ref = str(d / "shared.prap")
    WS.save_workspace(ref, sheets(), identity=ME)

    check("nobody holds a new plan", CL.read_claim(ref) is None)
    check("so a save is allowed", CL.may_write(ref, ME))

    r = CL.claim(ref, ME)
    check("the first claim succeeds", r["ok"])
    check("and it says who", r["claim"]["name"] == "Tester")
    check("this session holds it", CL.holds_claim(ref, ME))

    r2 = CL.claim(ref, OTHER)
    check("a second person is refused", not r2["ok"])
    check("and told who has it", r2["holder"]["name"] == "Tester")
    check("and when it frees", bool(r2["freeAt"]))
    check("in a sentence they can act on", "editing this plan" in r2["message"])

    # The defect the Electron smoke test found: the guard must ask whether somebody
    # ELSE holds it, not whether we do.
    check("we may still write", CL.may_write(ref, ME))
    check("they may not", not CL.may_write(ref, OTHER))

    fake = {"name": "Ghost", "department": "", "machine": CL.machine(), "pid": 999999,
            "since": TF.iso(TF.now_ms() - 40 * 60_000),
            "heartbeat": TF.iso(TF.now_ms() - 40 * 60_000)}
    check("a 40-minute-old claim is expired", CL.status_of(fake) == "expired")
    check("a 2-minute-old claim is silent, not expired",
          CL.status_of({**fake, "heartbeat": TF.iso(TF.now_ms() - 120_000)}) == "silent")
    check("a claim beating now is active",
          CL.status_of({**fake, "heartbeat": TF.iso()}) == "active")

    Path(CL.lock_path(ref)).write_text(json.dumps(fake), encoding="utf-8")
    check("an expired claim may be taken over", CL.may_write(ref, OTHER))
    r3 = CL.claim(ref, OTHER)
    check("and taking it over says why", r3["ok"] and r3["why"] == "an expired claim")
    check("and remembers who was displaced", r3["claim"]["displaced"]["name"] == "Ghost")

    # N-24: your own crashed session, on your own machine, back at once.
    CL.release_claim(ref, OTHER)
    mine_dead = {"name": "Tester", "department": "Dev", "machine": CL.machine(),
                 "pid": 424242, "since": TF.iso(TF.now_ms() - 120_000),
                 "heartbeat": TF.iso(TF.now_ms() - 120_000)}
    Path(CL.lock_path(ref)).write_text(json.dumps(mine_dead), encoding="utf-8")
    r4 = CL.claim(ref, ME)
    check("your own dead session is reclaimed at once",
          r4["ok"] and r4["why"] == "your own earlier session")

    # The heartbeat stamps the time and nothing else.
    was = CL.read_claim(ref)["since"]
    time.sleep(0.02)
    CL.refresh_claim(ref, ME)
    now = CL.read_claim(ref)
    check("the heartbeat moves", TF.parse(now["heartbeat"]) >= TF.parse(was))
    check("and leaves 'since' alone", now["since"] == was)
    check("somebody else's heartbeat does nothing",
          not CL.refresh_claim(ref, OTHER)["ok"])

    CL.release_claim(ref, ME)
    check("releasing frees it", CL.read_claim(ref) is None)

    # THE RACE. Eight processes, one instant, one winner.
    script = d / "racer.py"
    script.write_text(RACE_SCRIPT, encoding="utf-8")
    at = time.time() + 1.5
    procs = [subprocess.Popen(
        [sys.executable, str(script), str(PKG), ref, f"R{i}", str(at)],
        stdout=subprocess.PIPE, text=True) for i in range(8)]
    wins = sum(1 for p in procs if (p.communicate()[0] or "").strip() == "WON")
    check("eight processes race, exactly one wins", wins == 1, f"{wins} won")
    check("and the winner is the one in the file", CL.read_claim(ref) is not None)


# ------------------------------------------------------------- 7. where data goes

def test_paths(d):
    print("\nwhere data goes, and which rule chose it")
    app = str(d / "app")
    os.makedirs(app, exist_ok=True)

    r = PA.resolve_data_dir(argv=["PM_APP.py", f"--data={d}/explicit"], app_dir=app,
                            env={"USERNAME": "kim"})
    check("rule 1: --data wins", r["rule"].startswith("1"))
    check("and files go under the account name", r["dir"].endswith(os.path.join("users", "kim")))

    r = PA.resolve_data_dir(argv=["PM_APP.py"], app_dir=app,
                            env={"PRAP_DATA": f"{d}/central", "USERNAME": "kim"})
    check("rule 2: PRAP_DATA next", r["rule"].startswith("2"))

    r = PA.resolve_data_dir(argv=["PM_APP.py"], app_dir=app, env={"USERNAME": "kim"})
    check("rule 3: data\\ beside the application", r["rule"].startswith("3"))
    check("which is where it normally goes", r["dir"].startswith(os.path.join(app, "data")))

    # NR-DEP-09. can_write is injected because a process running as root - which is
    # how this suite runs here - can write to a directory whose permissions forbid
    # it, so the real predicate cannot be made to say no.
    r = PA.resolve_data_dir(argv=["PM_APP.py"], app_dir=app, env={"USERNAME": "kim"},
                            can_write=lambda _p: False)
    check("rule 4: a read-only folder means ASK, at launch", r["mustAsk"])
    check("and it says so rather than failing at the first save",
          r["rule"].startswith("4"))

    check("odd account names are made safe for a path",
          PA.account_name({"USERNAME": "DOMAIN\\kim lee"}) == "DOMAIN_kim_lee")

    # NR-DEP-08: recent plans are stored relative, so moving the folder does not
    # break the list.
    s = PA.add_recent(dict(PA.DEFAULT_SETTINGS), os.path.join(app, "data", "p.prap"), app)
    check("a plan inside the folder is remembered relatively",
          s["recent"][0]["ref"] == "data/p.prap")
    check("and resolves back to where it is",
          PA.from_portable(s["recent"][0]["ref"], app)
          == os.path.join(app, "data", "p.prap"))
    outside = os.path.join(str(d), "elsewhere.prap")
    s = PA.add_recent(s, outside, app)
    check("one outside it keeps its full path", s["recent"][0]["ref"] == outside)
    for i in range(15):
        s = PA.add_recent(s, os.path.join(app, f"p{i}.prap"), app)
    check("the list stops at ten", len(s["recent"]) == 10)
    check("most recent first", s["recent"][0]["name"] == "p14.prap")

    PA.ensure(os.path.join(app, "data"))
    PA.write_settings(os.path.join(app, "data"), s)
    check("settings survive a round trip",
          PA.read_settings(os.path.join(app, "data"))["recent"] == s["recent"])


# --------------------------------------------------- 8. choosing a file, not uploading

def test_files(d):
    print("\nchoosing a file without the browser choosing it")
    (d / "src").mkdir(exist_ok=True)
    (d / "src" / "book.xlsx").write_bytes(b"PK\x03\x04" + b"\x00" * 60)
    (d / "src" / "data.json").write_text("{}", encoding="utf-8")
    (d / "src" / "notes.txt").write_text("no", encoding="utf-8")
    (d / "src" / "sub").mkdir(exist_ok=True)

    r = F.listing(str(d / "src"), [".xlsx", ".json"])
    names = [e["name"] for e in r["entries"]]
    check("a folder lists its folders first", names[0] == "sub")
    check("and only the file types asked for", set(names[1:]) == {"book.xlsx", "data.json"})
    check("with somewhere to start from", len(r["roots"]) >= 1)
    check("and a way back up", bool(r["parent"]))

    r = F.listing(str(d / "src" / "book.xlsx"), None)
    check("pointing it at a file lists that file's folder", r["path"] == str(d / "src"))

    r = F.listing(str(d / "does" / "not" / "exist"), None)
    check("a folder that is not there does not raise", isinstance(r, dict))

    check("whether there is a native dialog is answered before it is needed",
          isinstance(F.tk_available(), bool))


def main():
    d = Path(tempfile.mkdtemp(prefix="pm-storage-"))
    print(f"Python storage layer — {sys.version.split()[0]}")
    print(f"package  {PKG}")
    print(f"scratch  {d}")
    try:
        test_roundtrip(d)
        test_refusals(d)
        test_kill_mid_save(d)
        test_versions(d)
        test_journal(d)
        test_claim(d)
        test_paths(d)
        test_files(d)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    for f in FAIL:
        print(f"  FAILED  {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
