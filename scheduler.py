"""Time parsing helpers + job-name conventions."""
import re
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

_REL = re.compile(
    r"^\+?\s*(\d+)\s*(s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours|d|day|days)$",
    re.I,
)
_ABS = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{1,2}:\d{2}$")
_HHMM = re.compile(r"^\d{1,2}:\d{2}$")

WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def parse_when(text: str):
    """Return an aware UTC datetime or None. Accepts +10m, 30m, 2h, 1d,
    HH:MM (today/tomorrow), YYYY-MM-DD HH:MM."""
    text = text.strip()
    now = datetime.now(UTC)

    m = _REL.match(text)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        if unit.startswith("s"):
            delta = timedelta(seconds=n)
        elif unit.startswith("m"):
            delta = timedelta(minutes=n)
        elif unit.startswith("h"):
            delta = timedelta(hours=n)
        else:
            delta = timedelta(days=n)
        return now + delta

    if _ABS.match(text):
        try:
            dt = datetime.strptime(text.replace("T", " "), "%Y-%m-%d %H:%M")
            return dt.replace(tzinfo=UTC)
        except ValueError:
            return None

    if _HHMM.match(text):
        try:
            hh, mm = map(int, text.split(":"))
            if not (0 <= hh < 24 and 0 <= mm < 60):
                return None
            dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if dt <= now:
                dt += timedelta(days=1)
            return dt
        except ValueError:
            return None

    return None


_DUR = re.compile(r"(\d+)\s*(h|hr|hrs|hours|m|min|mins|minutes|s|sec|secs|seconds)", re.I)


def parse_duration_seconds(text: str):
    text = text.strip().replace(" ", "")
    matches = _DUR.findall(text)
    if not matches:
        return None
    total = 0
    for value, unit in matches:
        v = int(value)
        u = unit.lower()
        if u.startswith("h"):
            total += v * 3600
        elif u.startswith("m"):
            total += v * 60
        else:
            total += v
    return total or None


def humanize_seconds(sec: int) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s or not parts:
        parts.append(f"{s}s")
    return " ".join(parts)
