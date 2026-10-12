"""shell: start it.

    resolve the data folder  ->  serve on 127.0.0.1  ->  open the browser
                             ->  wait until something stops it

The main thread used to do nothing but draw native file dialogs, because Tk insists
on owning the thread it was created on. Those dialogs are gone (see files.py), so it
now just waits - on the same stop event the page and Ctrl-C both set.

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
    # Asked at the console, because there is no window to ask in: the server is not
    # up yet, so the page cannot draw it, and the native folder picker this used to
    # open is gone with the rest of the native dialogs (see files.py).
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

    # --version answers and stops. Nothing is served, no browser is opened and no
    # data folder is touched, so it is safe to run anywhere - including from a
    # script that only wants to know whether this Python can run this application
    # at all (tools/bundle_runtime.py asks exactly that, on a PC with no Python of
    # its own). Anything that STARTS the application cannot answer that question,
    # because starting it means waiting for a person, which never ends.
    if "--version" in argv:
        print(f"Project Management APP {version}")
        return 0

    app = SV.App(app_dir=app_dir, version=version, page=read_page(app_dir))

    r = app.settle_data_dir()
    if r["mustAsk"]:
        chosen = ask_for_data_folder(app)
        if not chosen:
            print("Nowhere to keep data, so there is nothing to start. Stopping.")
            return 1
        r = app.settle_data_dir(chosen=chosen)

    # --keep-running leaves the application up after the page is closed. For a headless
    # run, or for somebody who wants to shut one browser window and open another; the
    # console then has to be closed by hand, as it always did.
    app.keep_running = ("--keep-running" in argv
                        or os.environ.get("PM_APP_KEEP_RUNNING") == "1")

    httpd = SV.serve(app, port=int(os.environ.get("PM_APP_PORT", "0")))
    host, port = httpd.server_address[0], httpd.server_address[1]
    url = f"http://127.0.0.1:{port}/?k={app.key}"

    threading.Thread(target=httpd.serve_forever, daemon=True,
                     name="pm-http").start()
    # The window and the application go together: close the page and this stops by
    # itself, instead of leaving a console behind holding a port and a claim on a plan
    # nobody has open. Daemon, so it can never be the thread that keeps us alive.
    threading.Thread(target=app.watch_clients, daemon=True, name="pm-watch").start()

    print("Project Management APP")
    print("=" * 60)
    print(f"  version      {version}")
    print(f"  application  {app_dir}")
    print(f"  your data    {app.data_dir}")
    print(f"  chosen by    {r['rule']}")
    print(f"  listening    {host}:{port}  (this machine only)")
    print("  file dialogs in the page")
    print()
    print("  It should have opened in your browser. If it did not, paste this in:")
    print(f"    {url}")
    print()
    print("  KEEP THIS WINDOW OPEN while you work. Closing it stops the application.")
    if app.keep_running:
        print("  --keep-running: closing the page leaves this window open. Close it "
              "yourself when you are finished.")
    else:
        print("  CLOSING THE PAGE ALSO CLOSES THIS WINDOW, a few seconds later. "
              "Reloading the page does not.")
    print("=" * 60)

    if "--no-browser" not in argv:
        try:
            webbrowser.open(url)
        except Exception:                                          # noqa: BLE001
            pass

    try:
        while not app.stop.wait(0.25):         # the main thread, until told to stop
            pass
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        app.shutdown()
        httpd.shutdown()
        httpd.server_close()
    return 0
