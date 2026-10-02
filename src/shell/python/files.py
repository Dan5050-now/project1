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

ONE WAY TO CHOOSE, and it used to be two. A native tkinter dialog was drawn where
tcl/tk was available, and a folder listing in the page where it was not - so the same
application showed two different windows depending on which Python happened to run it.
Reported from the field: PM_APP.cmd and PM_APP.py looked like different programs,
because the bundled runtime the .cmd uses has no tkinter and a full installation does.

A tool that is handed round a team cannot have two front doors. The listing is the one
that always works - it needs nothing beyond the standard library, it behaves the same
on every machine, and it is the one the packaged edition was already using - so it is
now the only one. No browser file interface is involved in it, which is the point of
this file (R-N21).

Specification: PRAP_NewApp_Specification_v1.3.xlsx sheet 03.
"""

import os
import string
import sys

SOURCE_TYPES = (".xlsx", ".json")
PLAN_TYPE = ".prap"


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
