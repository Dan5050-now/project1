"""shell: start it.

    resolve the data folder  ->  serve on 127.0.0.1  ->  open the browser
                             ->  hold the main thread for file dialogs

The main thread does nothing but draw dialogs, because Tk insists on owning the
thread it was created on and the HTTP server is perfectly happy in another. That is
the only reason this file is not four lines long.

Specification: PRAP_NewApp_Specification_v1.3.xlsx sheet 10.
"""

import os
import sys
import threading
import webbrowser

from . import paths as PA
from . import server as SV


def read_version(app_dir):
    try:
        with open(os.path.join(app_dir, "version.txt"), "r", encoding="utf-8") as f:
            return f.read().strip() or "1.0"
    except OSError:
        return "1.0"


def read_page(app_dir):
    p = os.path.join(app_dir, "app", "index.html")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        raise SystemExit(
            f"Project Management APP cannot find its page.\n\n"
            f"Expected: {p}\n\n"
            f"The folder has probably been unpacked incompletely. Extract the whole "
            f"zip again, keeping the folders inside it.")


def ask_for_data_folder(app):
    """Rule 4. NR-DEP-09 says a read-only folder is told about at LAUNCH, not
    discovered at the first Save - which is the worst possible moment to find out."""
    where = None
    if app.dialogs.enabled:
        stop = threading.Event()
        answer = {}

        def once():
            answer["p"] = app.dialogs.ask(
                "folder", title="Where should Project Management APP keep your data?")
            stop.set()

        threading.Thread(target=once, daemon=True).start()
        app.dialogs.pump(stop)
        where = answer.get("p")
    if not where:
        print("\nThis application cannot write beside itself, so it needs somewhere "
              "to keep your data.")
        try:
            where = input("Folder (blank to give up): ").strip().strip('"')
        except (EOFError, KeyboardInterrupt):
            where = None
    return where or None


def main(argv=None):
    argv = sys.argv if argv is None else argv
    app_dir = PA.default_app_dir()
    version = read_version(app_dir)
    app = SV.App(app_dir=app_dir, version=version, page=read_page(app_dir))

    r = app.settle_data_dir()
    if r["mustAsk"]:
        chosen = ask_for_data_folder(app)
        if not chosen:
            print("Nowhere to keep data, so there is nothing to start. Stopping.")
            return 1
        r = app.settle_data_dir(chosen=chosen)

    httpd = SV.serve(app, port=int(os.environ.get("PM_APP_PORT", "0")))
    host, port = httpd.server_address[0], httpd.server_address[1]
    url = f"http://127.0.0.1:{port}/?k={app.key}"

    threading.Thread(target=httpd.serve_forever, daemon=True,
                     name="pm-http").start()

    print("Project Management APP")
    print("=" * 60)
    print(f"  version      {version}")
    print(f"  application  {app_dir}")
    print(f"  your data    {app.data_dir}")
    print(f"  chosen by    {r['rule']}")
    print(f"  listening    {host}:{port}  (this machine only)")
    how = "native" if app.dialogs.enabled else "in the page (no tkinter here)"
    print(f"  file dialogs {how}")
    print()
    print("  It should have opened in your browser. If it did not, paste this in:")
    print(f"    {url}")
    print()
    print("  KEEP THIS WINDOW OPEN while you work. Closing it stops the application.")
    print("=" * 60)

    if "--no-browser" not in argv:
        try:
            webbrowser.open(url)
        except Exception:                                          # noqa: BLE001
            pass

    try:
        app.dialogs.pump(app.stop)             # the main thread, until told to stop
        while not app.stop.wait(0.25):
            pass
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        app.shutdown()
        httpd.shutdown()
        httpd.server_close()
    return 0
