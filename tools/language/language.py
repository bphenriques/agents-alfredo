"""The household's language, shared by the tools: reading the user's words into standard values (date, time,
timedelta) and presenting standard values back. Everything else stays in standard formats."""
import re
import unicodedata
from datetime import date, datetime, time, timedelta

WEEKDAYS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
DAY_NAMES = (("seg", "mon"), ("ter", "tue"), ("qua", "wed"), ("qui", "thu"), ("sex", "fri"), ("sab", "sat"), ("dom", "sun"))
RELATIVE = {"hoje": 0, "today": 0, "amanha": 1, "tomorrow": 1, "depois de amanha": 2, "ontem": -1, "yesterday": -1}


class NotUnderstood(ValueError):
    """The words are not what was asked for; the message says what to pass instead."""


def plain(text):
    """Text to compare, without case, accents or emoji."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold().strip()


def matches(query, name):
    """Whether every word of `query` is in `name`."""
    return all(word in plain(name) for word in plain(query).split())


def day(text, today, future=False):
    """A date from 2026-11-29 or the user's words: hoje, amanhã, a weekday (the next one, today included), próxima
    terça, 29/11, dia 29. With `future`, a day or month given alone is the next one."""
    words = plain(text)
    weekday = re.fullmatch(r"(?:(proxim[ao]|next) )?([a-z]{3})[a-z]*(?:[- ]feira)?", words)
    numbers = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})|(?:dia )?(\d{1,2})(?:/(\d{1,2})(?:/(\d{2}|\d{4}))?)?", words)
    try:
        if words in RELATIVE:
            return today + timedelta(RELATIVE[words])
        if weekday and any(weekday[2] in names for names in DAY_NAMES):
            n = next(n for n, names in enumerate(DAY_NAMES) if weekday[2] in names)
            return today + timedelta((n - today.weekday()) % 7 or (7 if weekday[1] else 0))
        if numbers and numbers[1]:
            return date(int(numbers[1]), int(numbers[2]), int(numbers[3]))
        if numbers:
            d, month = int(numbers[4]), int(numbers[5] or today.month)
            year = int(numbers[6]) % 100 + 2000 if numbers[6] else today.year
            found = date(year, month, d)
            if future and found < today and not numbers[6]:
                found = date(year + 1, month, d) if numbers[5] else date(year + month // 12, month % 12 + 1, d)
            return found
    except ValueError:
        pass
    raise NotUnderstood(f"{text!r} is not a day: pass 2026-11-29, or the user's hoje, amanhã, quinta or 29/11.")


def clock(text):
    """A time of day from 15:30 or the user's 15h, 15h30, 9."""
    m = re.fullmatch(r"(\d{1,2})(?:\s*[h:.]\s*(\d{2})?)?\s*h?", plain(text))
    if not m or int(m[1]) > 23 or int(m[2] or 0) > 59:
        raise NotUnderstood(f"{text!r} is not a time: pass 15:30, or the user's 15h or 9h30.")
    return time(int(m[1]), int(m[2] or 0))


def length(text):
    """A duration from the user's 1h, 1h30, 90 min, 2 horas."""
    m = re.fullmatch(r"(?:(\d+)\s*h(?:oras?|ours?)?)?\s*(?:(\d+)\s*(?:m|min|minutos?|minutes?)?)?", plain(text))
    if not m or not (m[1] or m[2]):
        raise NotUnderstood(f"{text!r} is not a duration: pass 1h, 1h30 or 90 min.")
    return timedelta(hours=int(m[1] or 0), minutes=int(m[2] or 0))


def label(d):
    """A day as the user reads it: qui 19/11."""
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return f"{WEEKDAYS[d.weekday()]} {d:%d/%m}"


def span(start, end):
    """A time span as the user reads it: qui 19/11 15:00–16:00, or qui 19/11 a sex 20/11 for whole days, whose end
    is exclusive as in iCalendar. Times are shown as given: convert them to local time first."""
    if not isinstance(start, datetime):
        last = end - timedelta(1)
        return label(start) + (f" a {label(last)}" if last > start else "")
    return f"{label(start.date())} {start:%H:%M}–{end:%H:%M}"
