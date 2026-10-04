"""Package everything that was produced - documents, application, program, source - as
one zip to carry onto another PC.

tools/package_source.py already packages what is WRITTEN (src/ and tools/). This packages
what the project has PRODUCED, which is a different list and a different reader: somebody
who wants to open the application, read the plan, run the program, and have the source
beside it rather than somebody who wants to rebuild.

WHICH VERSIONS GO IN. The CURRENT issue of each document, and only that. The repository
keeps every superseded version alongside - 66 development plans, 31 specifications - and
docs/PRAP_Manifest.json exists precisely to say which one is in force. Carrying all of
them would quadruple the archive and leave the reader to work out which plan is the plan,
which is the one question the manifest answers. The history stays in git, where it is
browsable; the package carries the issue that is true today. The list is READ from the
manifest and from README.md's own "current" labels rather than typed here, so it cannot
drift from them - and tools/check_consistency.py already holds those two to each other.

THE ARCHIVE IS CHECKED BEFORE IT IS WRITTEN. It is extracted to a temporary folder and:

    1. the application is rebuilt from the source inside it, and must come out
       BYTE-IDENTICAL to the copy the archive carries;
    2. the desktop program is rebuilt from that same source, and every file must come
       out byte-identical to the copy the archive carries;
    3. every path the manifest calls current must be present;
    4. every Python file in the program must compile.

Nothing is written unless all four pass. An archive whose application and program cannot
be re-derived from the source beside them is three unrelated downloads in a bag, and the
way to know they belong together is to try it.

    python tools/package_release.py
    python tools/package_release.py --no-verify     skip the four checks

Output: dist/PRAP_release_package.zip
"""

import compileall
import contextlib
import hashlib
import io
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "PRAP_release_package.zip"

APP = "1_application"
PROG = "2_program"
DOCS = "3_documents"
BOOKS = "4_workbooks"
SRC = "5_source"

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SKIP_SUFFIX = {".pyc", ".pyo"}

# The one GENERATED file that lives inside src/. tools/build_desktop.py emits the desktop
# shell's page there, beside its hand-written main.js and preload.js, and .gitignore skips
# it for the same reason this does: an archive of what is WRITTEN must not carry a build
# output, and this one would make the archive's bytes depend on whether anybody had run
# build_desktop.py - which is exactly the reproducibility the fixed epoch below buys.
# It was absent from a fresh clone, so this went unnoticed until a build put it there.
SKIP_FILES = {"src/shell/desktop/index.html"}

# Documents that are not versioned in a filename and so cannot be read out of the
# manifest's version list, plus the two decks and the PDF.
EXTRA_DOCS = [
    "docs/PRAP_AI_Agent_Guide.md",
    "docs/PRAP_AI_Agent_Guide_v1.0.xlsx",
    "docs/PRAP_AI_Analysis_Guide.md",
    "docs/PRAP_Manifest.json",
    "docs/prap_contract.json",
    "docs/STEP2_OPEN_POINTS.md",
    "docs/PRAP_FTE_계산설명서.pdf",
    "docs/PRAP_FTE_Calculation_v1.0.pptx",
    "output/deck/PRAP_소개자료.pptx",
]

# The Korean manuals and the standing design review. Written for a reader on the inside
# network, which is where this package is going.
REVIEW = [
    "docs/review/PM_APP-배포와-첫실행-안내.html",
    "docs/review/PM_APP-배포준비-담당자절차.html",
    "docs/review/PM_APP-현재상태-검토서-5판.html",
    "docs/review/PRAP-PM_APP-v1.21-design-review-ko.md",
]


def readme_current():
    """The issues README.md labels current, for the families the manifest does not list.

    The second product line (PRAP_NewApp_*) is tracked in README.md rather than in the
    manifest. Reading the label is how check_consistency.py finds a stale one, and it is
    how this finds the file.
    """
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    return [f"docs/{n}" for n in
            re.findall(r"`docs/([A-Za-z0-9_.]+_v[\d.]+\.xlsx)` — \*\*current", text)]


def plan():
    """(archive path, source path) for every file that goes in, in archive order."""
    manifest = json.loads((ROOT / "docs" / "PRAP_Manifest.json").read_text(encoding="utf-8"))
    by_what = {e["what"]: e["path"] for e in manifest["current"]}
    out = []

    def add(dest, src):
        out.append((dest, ROOT / src))

    add(f"{APP}/PRAP.html", by_what["application"])

    for p in sorted((ROOT / "dist" / "PM_APP_py").rglob("*")):
        if p.is_file() and p.suffix not in SKIP_SUFFIX \
                and not any(d in p.parts for d in SKIP_DIRS):
            add(f"{PROG}/PM_APP_py/{p.relative_to(ROOT / 'dist' / 'PM_APP_py')}", p)

    # Documents: the manifest's own, plus README's other line, plus the unversioned ones.
    paper = [by_what[k] for k in ("development_plan", "programming_specification",
                                  "ui_component_list")]
    paper += [p for p in readme_current() if p not in paper]
    for p in paper + EXTRA_DOCS:
        add(f"{DOCS}/{pathlib.PurePosixPath(p).name}", p)
    add(f"{DOCS}/README.md", "README.md")
    for p in REVIEW:
        add(f"{DOCS}/review/{pathlib.PurePosixPath(p).name}", p)

    for k in ("source_data_template", "worked_example_large", "worked_example_small"):
        add(f"{BOOKS}/{pathlib.PurePosixPath(by_what[k]).name}", by_what[k])

    for top in ("src", "tools"):
        for p in sorted((ROOT / top).rglob("*")):
            if not p.is_file() or p.suffix in SKIP_SUFFIX:
                continue
            if any(d in p.parts for d in SKIP_DIRS):
                continue
            if p.relative_to(ROOT).as_posix() in SKIP_FILES:
                continue
            add(f"{SRC}/{p.relative_to(ROOT)}", p)

    return out, manifest


def note(manifest, files):
    """The first thing in the archive, written from the artefacts rather than typed."""
    ver = (ROOT / "dist" / "PM_APP_py" / "version.txt").read_text(encoding="utf-8").strip()
    name = {e["what"]: pathlib.PurePosixPath(e["path"]).name for e in manifest["current"]}
    counts = {}
    for dest, _ in files:
        counts[dest.split("/")[0]] = counts.get(dest.split("/")[0], 0) + 1
    return f"""PRAP / Project Management APP — 전체 패키지
==========================================

application  {manifest['application_version']}      schema  {manifest['schema_version']}
program      {ver}
생성          {manifest['generated']} 기준 문서 / 이 압축 파일은 그 뒤 최신 소스에서 만들어짐

이 압축 파일 하나에 지금까지 만들어진 것이 전부 들어 있습니다. 실행 파일(.exe)은
없고 전부 평문이거나 문서입니다.


1_application/   ({counts.get(APP, 0)} 개)

  PRAP.html      웹 애플리케이션 전체가 이 파일 하나입니다. 브라우저로 열면
                 바로 동작하고, 서버도 설치도 인터넷도 필요하지 않습니다.
                 외부 라이브러리를 하나도 쓰지 않으며 .xlsx 읽기/쓰기까지
                 직접 구현되어 있습니다.


2_program/       ({counts.get(PROG, 0)} 개)

  PM_APP_py/     바탕화면용 프로그램. PM_APP.cmd 를 두 번 누르면 실행됩니다
                 (PC 에 설치된 Python 을 찾고, 없으면 그렇게 알려 줍니다).
                 PM_APP.py 로 직접 실행해도 같은 화면이 뜹니다.
                 check_pc.py 는 이 PC 에서 실행이 가능한지만 먼저 확인합니다.
                 version.txt 에 판이 적혀 있습니다 — {ver}.


3_documents/     ({counts.get(DOCS, 0)} 개)

  {name['development_plan']}
                 개발 계획서. 요구사항과 검증 규칙의 기준 문서입니다.
  {name['programming_specification']}
                 프로그래밍 명세서. 시트/열/계산 규칙.
  {name['ui_component_list']}
                 화면 구성 목록.
  PRAP_NewApp_*  2단계(서버 구성) 계획과 명세. 아직 구현 전 문서입니다.
  PRAP_FTE_계산설명서.pdf
                 FTE 가 어떻게 계산되는지 — 수식, 입력 정보, 그리고 인원이
                 늘거나 가중치가 바뀌거나 월 값을 직접 적을 때 어떻게 되는지.
                 안의 모든 숫자는 실제 계산 엔진을 돌려 얻은 값입니다.
  PRAP_소개자료.pptx
                 소개 발표 자료.
  PRAP_AI_Agent_Guide.md / prap_contract.json / PRAP_Manifest.json
                 기계가 읽는 기준 문서. 어느 파일이 현재판인지는 Manifest 가
                 말합니다.
  README.md      프로젝트 전체 기록. 무엇을 왜 그렇게 정했는지가 여기 있습니다.
  review/        배포 안내, 담당자 절차, 현재상태 검토서, 설계 검토서.

  문서의 지난 판은 넣지 않았습니다. 저장소에는 계획서 60여 판, 명세서 30여 판이
  함께 남아 있지만, 여기 들어 있는 것은 현재 유효한 판 하나씩입니다. 지난 판이
  필요하면 저장소에서 보십시오.


4_workbooks/     ({counts.get(BOOKS, 0)} 개)

  {name['source_data_template']}
                 빈 입력 서식. 여기에 자료를 채워 애플리케이션에서 엽니다.
  {name['worked_example_large']}
                 채워진 예제(큰 것).
  {name['worked_example_small']}
                 채워진 예제(작은 것, 10 x 10). 먼저 열어 볼 파일입니다.


5_source/        ({counts.get(SRC, 0)} 개)

  src/           애플리케이션 소스. 층으로 나뉘어 있습니다 — core/ 가 숫자를
                 정하고(DOM 을 건드리지 않음), ui/ 가 그리고, storage/ 가
                 바이트를 옮기고, shell/ 이 웹·바탕화면·python 을 감쌉니다.
  tools/         빌드·검사·시험 도구. 문서 생성기, 참조 구현(prap_io.py),
                 일관성 검사기, 시험 모음.

  python tools/build_app.py          -> app/PRAP.html 재생성
  python tools/build_python_app.py   -> dist/PM_APP_py 재생성
  python tools/check_consistency.py  -> 모든 문서를 서로 대조

  1_application/PRAP.html 과 2_program/PM_APP_py 는 이 5_source/ 에서 다시
  만들어 바이트 단위로 같다는 것을 확인한 뒤에 이 압축 파일이 쓰였습니다.
  확인에 실패하면 아무것도 쓰이지 않습니다.


필요한 것

  애플리케이션(1_application/PRAP.html)은 브라우저만 있으면 됩니다.
  프로그램(2_program/)은 Python 3.9 이상. 소스의 문서 생성기는 openpyxl,
  브라우저를 직접 몰아 보는 시험은 playwright 가 추가로 필요합니다.
"""


# Same fixed timestamp as tools/package_source.py, for the same reason: without it each
# entry carries its mtime, a fresh checkout rewrites those, and two archives of identical
# content hash differently - so the sha256 says nothing about the content.
EPOCH = (1980, 1, 1, 0, 0, 0)


def write(files, text, dst):
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        def add(name, data):
            info = zipfile.ZipInfo(name, date_time=EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            # compresslevel HERE, not on the ZipFile: writestr() with a ZipInfo ignores
            # the archive's setting and falls back to the default.
            z.writestr(info, data, compresslevel=9)

        add("READ ME FIRST.txt", text.encode("utf-8"))
        for dest, src in files:
            add(dest, src.read_bytes())


def verify(dst, manifest):
    """Extract it elsewhere, rebuild both products from the source inside it, and compare.

    Returns a list of (ok, line) so every check is reported, not just the first failure -
    when two things are wrong, knowing one of them is half an answer.
    """
    out = []
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="prap-rel-"))
    try:
        with zipfile.ZipFile(dst) as z:
            z.extractall(tmp)
        src = tmp / SRC

        # 1. the application, rebuilt from the source in the archive
        r = subprocess.run([sys.executable, str(src / "tools" / "build_app.py")],
                           cwd=src, capture_output=True, text=True)
        built = src / "app" / "PRAP.html"
        carried = tmp / APP / "PRAP.html"
        if r.returncode != 0:
            out.append((False, "application rebuild failed: "
                               + (r.stdout + r.stderr).strip().splitlines()[-1][:150]))
        elif not built.exists():
            out.append((False, "the application build wrote no app/PRAP.html"))
        elif built.read_bytes() != carried.read_bytes():
            out.append((False, f"rebuilt application {built.stat().st_size:,} bytes, "
                               f"carried {carried.stat().st_size:,} - NOT identical"))
        else:
            out.append((True, f"application rebuilds byte-identically   "
                              f"{built.stat().st_size:,} bytes"))

        # 2. the program, rebuilt from that same source
        r = subprocess.run([sys.executable, str(src / "tools" / "build_python_app.py")],
                           cwd=src, capture_output=True, text=True)
        rebuilt = src / "dist" / "PM_APP_py"
        if r.returncode != 0:
            out.append((False, "program rebuild failed: "
                               + (r.stdout + r.stderr).strip().splitlines()[-1][:150]))
        else:
            mine = {str(p.relative_to(tmp / PROG / "PM_APP_py")): p.read_bytes()
                    for p in (tmp / PROG / "PM_APP_py").rglob("*") if p.is_file()}
            theirs = {str(p.relative_to(rebuilt)): p.read_bytes()
                      for p in rebuilt.rglob("*") if p.is_file()}
            bad = sorted(set(mine) ^ set(theirs)) \
                + sorted(k for k in set(mine) & set(theirs) if mine[k] != theirs[k])
            if bad:
                out.append((False, f"program differs from a rebuild in {len(bad)} file(s): "
                                   + ", ".join(bad[:4])))
            else:
                out.append((True, f"program rebuilds byte-identically     "
                                  f"{len(mine)} files"))

        # 3. everything the manifest calls current is actually in here
        names = {pathlib.PurePosixPath(n).name for n in
                 zipfile.ZipFile(dst).namelist()}
        missing = [e["path"] for e in manifest["current"]
                   if pathlib.PurePosixPath(e["path"]).name not in names]
        out.append((not missing,
                    f"all {len(manifest['current'])} current artifacts present"
                    if not missing else "missing from the archive: " + ", ".join(missing)))

        # 4. the program's Python compiles. Not a test of behaviour - tools/ has 40
        #    suites for that - but a syntax error in a shipped file would reach the
        #    reader as a traceback on first launch, and this costs a second. Nor is it
        #    covered by 2: a syntax error present in BOTH the source and the build
        #    rebuilds byte-identically and sails through that comparison. Demonstrated
        #    by breaking src/shell/python/paths.py and rebuilding before packaging -
        #    2 passed, this failed.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            # quiet=1 so the failing file and its error are the only thing printed,
            # and captured rather than scrolling past in the middle of the report.
            ok = compileall.compile_dir(str(tmp / PROG), quiet=1, force=True)
        out.append((bool(ok), "every Python file in the program compiles"
                    if ok else "a Python file in the program does not compile: "
                               + " ".join(buf.getvalue().split())[:200]))
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# What builds each thing the package expects to find but might not, so a fresh clone or a
# restarted container gets told the command rather than a FileNotFoundError traceback from
# somewhere inside write(). dist/ and output/deck/ are both gitignored, so this is the
# ordinary case after a checkout, not an exotic one.
BUILT_BY = {
    "dist/PM_APP_py": "python tools/build_python_app.py",
    "output/deck": "python tools/build_deck.py",
}


def missing(files):
    """(path, how to get it) for everything the package wants and the tree has not got.

    dist/PM_APP_py is checked as a whole because plan() finds its contents by rglob: an
    absent folder would quietly contribute nothing rather than a missing file, and the
    package would be written without the program in it.
    """
    want = [p for p in (ROOT / "dist" / "PM_APP_py",) if not p.is_dir()]
    want += [src for _, src in files if not src.exists()]
    out = []
    for p in want:
        rel = p.relative_to(ROOT).as_posix()
        out.append((rel, next((c for k, c in BUILT_BY.items() if rel.startswith(k)), None)))
    return out


def main(check=True):
    files, manifest = plan()
    gone = missing(files)
    if gone:
        print("Not in the working tree:")
        for rel, how in gone:
            print(f"  {rel}" + (f"      run: {how}" if how else
                                "      committed - check the branch is current"))
        return 1
    text = note(manifest, files)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    staged = OUT.with_suffix(".zip.staged")
    write(files, text, staged)

    if check:
        results = verify(staged, manifest)
        for ok, line in results:
            print(f"  {'ok  ' if ok else 'FAIL'} {line}")
        if not all(ok for ok, _ in results):
            staged.unlink(missing_ok=True)
            print("\nNothing written. Fix the above and run again.")
            return 1

    staged.replace(OUT)
    size = OUT.stat().st_size
    groups = {}
    for dest, src in files:
        top = dest.split("/")[0]
        g = groups.setdefault(top, [0, 0])
        g[0] += 1
        g[1] += src.stat().st_size
    print(f"\nPackaged  {OUT.relative_to(ROOT)}")
    for top in (APP, PROG, DOCS, BOOKS, SRC):
        n, b = groups.get(top, (0, 0))
        print(f"  {top:16} {n:>4} files   {b / 1024:>8,.0f} KB")
    print(f"  {'READ ME FIRST':16} {1:>4} file")
    print(f"  size    {size:,} bytes ({size / 1024 / 1024:.1f} MB)")
    print(f"  sha256  {hashlib.sha256(OUT.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--no-verify" not in sys.argv))
