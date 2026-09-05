"""shell: where things live - the Python port of src/shell/desktop/paths.js.

The portable rule says everything lives in one folder. Data safety says an update
must not be able to delete a plan. Those pull against each other, and this file is
where they are resolved.

    PM_APP\\                      copy this anywhere; delete it to remove the app
      PM_APP.py                  \\
      pmapp\\                     |  replaced wholesale by an update
      app\\index.html            /
      version.txt
      data\\                      NEVER touched by an update - not in the zip
        users\\<account>\\
          settings.json
          workspaces\\
          backups\\

Specification: PRAP_NewApp_Specification_v1.3.xlsx sheet 10.
"""

import json
import os
import re
import sys

from ..storage import timefmt


def resolve_data_dir(argv=None, env=None, app_dir=None, account=None,
                     can_write=None, per_user=True):
    """Where the data folder is, resolved in ONE fixed order, and the answer says
    which rule chose it. A portable application that will not say where its data
    went is a support problem, and the answer costs one line on a dialog
    (NR-DEP-10)."""
    argv = sys.argv if argv is None else argv
    env = os.environ if env is None else env
    app_dir = default_app_dir(env) if app_dir is None else app_dir
    account = account_name(env) if account is None else account
    # Injectable ONLY so the read-only case can be tested. A process running as an
    # administrator - or as root, which is how the test suite runs here - can write
    # to a directory whose permissions forbid it, so the real predicate cannot be
    # made to say no.
    can_write = writable if can_write is None else can_write

    # 1. --data=<path> - how a personal shortcut carries it. Explicit, visible, and
    #    the user's rather than the application's.
    for a in argv:
        if str(a).startswith("--data="):
            return _settle(str(a)[7:], "1 - the --data argument", account, app_dir,
                           per_user)

    # 2. PRAP_DATA - for a site that sets it centrally.
    if env.get("PRAP_DATA"):
        return _settle(env["PRAP_DATA"], "2 - the PRAP_DATA variable", account,
                       app_dir, per_user)

    # 3. data\ beside the application, if writable. The ordinary case, single-user
    #    or shared: Q-N15 says the share would be writable, so each person simply
    #    gets their own folder under it (NR-DEP-15) and nobody is asked anything.
    beside = os.path.join(app_dir, "data")
    if can_write(app_dir) or can_write(beside):
        return _settle(beside, "3 - writable data\\ beside the application", account,
                       app_dir, per_user)

    # 4. Ask. The caller shows the dialog; this only reports that it must.
    return {"dir": None, "root": None, "rule": "4 - ask the user", "account": account,
            "mustAsk": True, "appDir": app_dir}


def _settle(root, rule, account, app_dir, per_user):
    d = root if not per_user else os.path.join(root, "users", account)
    # `root` as well as `dir`. Each person works in their own folder under it, but some
    # things belong to the INSTALLATION rather than to a person - the change log is one,
    # because a record of who changed what is only worth reading if everyone's entries
    # are in it. Returning the root is what lets the caller put those beside `users/`
    # rather than inside one person's copy.
    return {"dir": d, "root": root, "rule": rule, "account": account, "mustAsk": False,
            "appDir": app_dir}


def account_name(env=None):
    """The Windows account name, not the declared one.

    The declared name is editable and could collide - two people may both be "Kim" -
    while the account name is unique on the machine and stable. The declared name is
    what colleagues see; the account name is what files are filed under (S-N06).
    """
    env = os.environ if env is None else env
    raw = env.get("USERNAME") or env.get("USER") or ""
    if not raw:
        try:
            import getpass
            raw = getpass.getuser()
        except Exception:
            raw = "user"
    return re.sub(r"[^A-Za-z0-9._-]", "_", raw) or "user"


def default_app_dir(env=None):
    """The folder the application is in - the one holding PM_APP.py."""
    env = os.environ if env is None else env
    if env.get("PM_APP_DIR"):
        return os.path.abspath(env["PM_APP_DIR"])
    # <app>/pmapp/shell/paths.py  ->  two levels up is the application folder
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", ".."))


def writable(d):
    try:
        if os.path.isdir(d):
            return os.access(d, os.W_OK)
        parent = os.path.dirname(os.path.abspath(d))
        return os.path.isdir(parent) and os.access(parent, os.W_OK)
    except OSError:
        return False


def ensure(data_dir):
    """Create the folders the resolved location needs. Called once at launch."""
    for d in (data_dir, os.path.join(data_dir, "workspaces"),
              os.path.join(data_dir, "backups")):
        os.makedirs(d, exist_ok=True)
    return data_dir


def audit_dir(root):
    """Where the change log accumulates: ONE folder for the installation.

    Beside users/, not inside it. A change log split into one file per person answers
    "what did I do" and not "what happened to this plan", which is the question it is
    kept for - and on a shared deployment the second question is the only one worth
    asking. Every row already names who made the change, so nothing is lost by putting
    them together and the ordering across people is gained.

    Its own folder rather than files beside the plans: it is not a plan, the application
    never reads it back, and somebody looking for "the logs" should find a folder called
    that rather than have to know which file to pick out."""
    d = os.path.join(root, "audit")
    os.makedirs(d, exist_ok=True)
    return d


def settings_path(data_dir):
    return os.path.join(data_dir, "settings.json")


DEFAULT_SETTINGS = {"identity": None, "window": None, "recent": [], "preferences": {}}


def read_settings(data_dir):
    try:
        with open(settings_path(data_dir), "r", encoding="utf-8") as f:
            s = json.load(f)
        return {**DEFAULT_SETTINGS, **(s if isinstance(s, dict) else {})}
    except (OSError, ValueError):
        return dict(DEFAULT_SETTINGS)


def write_settings(data_dir, settings):
    tmp = f"{settings_path(data_dir)}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=1, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, settings_path(data_dir))


def add_recent(settings, ref, app_dir, meta=None):
    """Recent workspaces: at least ten, most recent first, per user, and stored
    RELATIVE to the application folder wherever they can be - so copying the folder
    to another machine or drive letter does not break the list (NR-DEP-08)."""
    rel = to_portable(ref, app_dir)
    rest = [r for r in (settings.get("recent") or []) if r.get("ref") != rel]
    entry = {"ref": rel, "name": os.path.basename(ref), "at": timefmt.iso()}
    entry.update(meta or {})
    settings["recent"] = [entry, *rest][:10]
    return settings


def to_portable(ref, app_dir):
    try:
        rel = os.path.relpath(os.path.abspath(ref), os.path.abspath(app_dir))
    except ValueError:                        # a different drive letter on Windows
        return os.path.abspath(ref)
    if rel.startswith("..") or os.path.isabs(rel):
        return os.path.abspath(ref)
    return rel.replace(os.sep, "/")


def from_portable(ref, app_dir):
    return ref if os.path.isabs(ref) else os.path.abspath(os.path.join(app_dir, ref))
