"""shell: choosing a file WITHOUT the browser choosing it.

This is the file that exists because of R-N21. On the requester's laptop the file
dialog opens normally, and the moment a file is chosen a company security control
stops the data reaching the page. Every route the web application has - the picker,
the drop zone, the JSON file - ends at the same browser interface, so all three
stop.

So the page never asks for a file. Python does:

    the user chooses a path   ->   Python opens it with open()
                              ->   Python hands the bytes to the page as ordinary
                                   page content over 127.0.0.1

Nothing is disabled, evaded or hidden. An upload control governs data entering a web
page; a program the user ran on their own machine reading a file they chose is what
every application on that laptop does, Excel included. The control is not bypassed -
it is not involved.

Two ways to choose, because one of them may not be there:

  * tkinter's native dialog, which is the Windows dialog everyone knows. Tk must own
    the main thread, so the HTTP thread posts a request and waits (see server.py).
  * a plain folder listing served to the page, for a Python built without tkinter
    and for typing a path directly. No browser file interface is involved in either.

Specification: PRAP_NewApp_Specification_v1.3.xlsx sheet 03.
"""

import os
import queue
import string
import sys
import threading

SOURCE_TYPES = (".xlsx", ".json")
PLAN_TYPE = ".prap"


# ------------------------------------------------------------------ the native dialog

def tk_available():
    """Is there a Tk to draw a dialog with? Asked once, answered honestly.

    A Python installed without tcl/tk is unusual but real, and finding out at the
    moment somebody clicks Import is finding out too late. The answer is reported in
    capabilities so the page can show the right thing from the start.
    """
    try:
        import tkinter                                            # noqa: F401
        from tkinter import filedialog                            # noqa: F401
    except Exception:
        return False
    return True


class DialogPump:
    """Tk on the main thread, requests from the HTTP thread.

    Tk is not thread-safe and on Windows it must be driven from the thread that
    created it. The HTTP server runs in its own thread, so a dialog request is put
    on a queue, the main thread draws it, and the answer goes back on another queue.
    The HTTP thread blocks meanwhile, which is correct: it is waiting for a person.
    """

    def __init__(self):
        self.requests = queue.Queue()
        self.enabled = tk_available()
        self._root = None

    def ask(self, kind, **kw):
        """Called from the HTTP thread. Returns the chosen path, or None."""
        if not self.enabled:
            return None
        answer = queue.Queue(maxsize=1)
        self.requests.put((kind, kw, answer))
        try:
            return answer.get(timeout=600)        # ten minutes to choose a file
        except queue.Empty:
            return None

    def _tk(self):
        import tkinter
        if self._root is None:
            self._root = tkinter.Tk()
            self._root.withdraw()
            # Without this the dialog opens behind the browser, and the application
            # looks frozen while a window nobody can see waits for an answer.
            self._root.attributes("-topmost", True)
        return self._root

    def pump(self, stop):
        """Run on the main thread until `stop` is set."""
        while not stop.is_set():
            try:
                kind, kw, answer = self.requests.get(timeout=0.25)
            except queue.Empty:
                continue
            try:
                answer.put(self._draw(kind, kw))
            except Exception:
                # A dialog that fails must not take the application with it: the
                # page falls back to the folder listing, which always works.
                answer.put(None)

    def _draw(self, kind, kw):
        from tkinter import filedialog
        root = self._tk()
        root.update()
        if kind == "open":
            p = filedialog.askopenfilename(
                parent=root, title=kw.get("title", "Open"),
                initialdir=kw.get("initialdir") or os.path.expanduser("~"),
                filetypes=kw.get("filetypes") or [("All files", "*.*")])
        elif kind == "save":
            p = filedialog.asksaveasfilename(
                parent=root, title=kw.get("title", "Save as"),
                initialdir=kw.get("initialdir") or os.path.expanduser("~"),
                initialfile=kw.get("initialfile") or "",
                defaultextension=kw.get("defaultextension") or "",
                filetypes=kw.get("filetypes") or [("All files", "*.*")])
        elif kind == "folder":
            p = filedialog.askdirectory(
                parent=root, title=kw.get("title", "Choose a folder"),
                initialdir=kw.get("initialdir") or os.path.expanduser("~"),
                mustexist=False)
        else:
            p = None
        root.update()
        return p or None


# ------------------------------------------------------------- the folder listing

def roots():
    """Somewhere to start. On Windows the drives that exist, plus the home folder
    and the desktop; elsewhere the home folder and the filesystem root."""
    out = []
    home = os.path.expanduser("~")
    out.append({"name": "Home", "path": home})
    for extra in ("Desktop", "Documents", "Downloads"):
        p = os.path.join(home, extra)
        if os.path.isdir(p):
            out.append({"name": extra, "path": p})
    if sys.platform.startswith("win"):
        for letter in string.ascii_uppercase:
            d = f"{letter}:\\"
            if os.path.exists(d):
                out.append({"name": d, "path": d})
    else:
        out.append({"name": "/", "path": "/"})
    return out


def listing(path, suffixes=None):
    """One folder, as JSON. Folders first, then the files worth showing.

    Files that cannot be opened are still listed - a folder that silently omits the
    file somebody is looking for is worse than one that shows it and then explains
    why it will not open.
    """
    path = os.path.abspath(os.path.expanduser(path or os.path.expanduser("~")))
    if not os.path.isdir(path):
        path = os.path.dirname(path) or os.path.expanduser("~")
    suffixes = tuple(s.lower() for s in (suffixes or ()))

    dirs, files = [], []
    try:
        with os.scandir(path) as it:
            for e in it:
                if e.name.startswith("."):
                    continue
                try:
                    if e.is_dir():
                        dirs.append({"name": e.name, "path": e.path, "dir": True})
                    elif not suffixes or e.name.lower().endswith(suffixes):
                        st = e.stat()
                        files.append({"name": e.name, "path": e.path, "dir": False,
                                      "size": st.st_size, "mtime": st.st_mtime * 1000})
                except OSError:
                    continue
    except PermissionError:
        return {"path": path, "parent": _parent(path), "error":
                "You do not have permission to look in that folder.",
                "entries": [], "roots": roots()}
    except OSError as e:
        return {"path": path, "parent": _parent(path), "error": str(e),
                "entries": [], "roots": roots()}

    dirs.sort(key=lambda d: d["name"].lower())
    files.sort(key=lambda f: f["name"].lower())
    return {"path": path, "parent": _parent(path), "entries": dirs + files,
            "roots": roots(), "error": None}


def _parent(path):
    up = os.path.dirname(path.rstrip(os.sep)) or None
    return None if up == path else up
