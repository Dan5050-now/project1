"""Timestamps both shells can read.

The Electron build writes JavaScript's `new Date().toISOString()` -
`2026-08-18T09:41:07.412Z` - into workspaces, journals and claim files. Python's
own `datetime.isoformat()` writes `2026-08-18T09:41:07.412000+00:00`, which is the
same instant in a different spelling.

That difference does not matter until the day a plan on the shared folder has been
touched by both shells, and then it matters completely: a claim whose heartbeat
cannot be parsed reads as a claim from 1970, which is expired, which hands somebody
else a plan that is being edited right now.

So one file owns the format. It writes the JavaScript spelling, and reads either.

Specification: PRAP_NewApp_Specification_v1.3.xlsx sheet 06.
"""

from datetime import datetime, timedelta, timezone

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def now_ms() -> float:
    """Milliseconds since the epoch - the unit both shells compare in."""
    return datetime.now(timezone.utc).timestamp() * 1000.0


def iso(ms: float | None = None) -> str:
    """The JavaScript spelling: UTC, three decimal places, a trailing Z."""
    t = EPOCH + timedelta(milliseconds=now_ms() if ms is None else ms)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def parse(text) -> float:
    """Milliseconds since the epoch, or 0 for anything unparseable.

    0 rather than an exception on purpose. Every caller is asking "how long ago?"
    about a value that came out of a file somebody else wrote, and the safe answer
    for a timestamp that makes no sense is "a very long time ago" - which is what
    the callers already handle.
    """
    if not text:
        return 0.0
    s = str(text).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return 0.0
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.timestamp() * 1000.0
