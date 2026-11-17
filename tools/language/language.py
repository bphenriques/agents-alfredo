"""The household's language, shared by the tools: reading the user's words into standard values (date, time,
timedelta) and presenting standard values back. Everything else stays in standard formats."""
import re
import unicodedata
from datetime import date, datetime, time, timedelta

WEEKDAYS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
# Whole words only, so "seguinte" or "terminar" is no day. Monday is the 2nd day ("2a", "2f") in Portuguese.
DAY_NAMES = {name: n for n, names in enumerate((
    ("seg", "segunda", "2a", "2f", "mon", "monday"), ("ter", "terca", "3a", "3f", "tue", "tuesday"),
    ("qua", "quarta", "4a", "4f", "wed", "wednesday"), ("qui", "quinta", "5a", "5f", "thu", "thursday"),
    ("sex", "sexta", "6a", "6f", "fri", "friday"), ("sab", "sabado", "sat", "saturday"), ("dom", "domingo", "sun", "sunday"),
)) for name in names}
MONTH_NAMES = {name: n + 1 for n, names in enumerate((
    ("jan", "janeiro", "january"), ("fev", "fevereiro", "feb", "february"), ("mar", "marco", "march"),
    ("abr", "abril", "apr", "april"), ("mai", "maio", "may"), ("jun", "junho", "june"), ("jul", "julho", "july"),
    ("ago", "agosto", "aug", "august"), ("set", "setembro", "sep", "september"), ("out", "outubro", "oct", "october"),
    ("nov", "novembro", "november"), ("dez", "dezembro", "dec", "december"),
)) for name in names}
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
    terça, 29/11, dia 29, 1 de dezembro. With `future`, a day or month given alone is the next one."""
    words = plain(text).replace("-", " ").rstrip(".")
    weekday = re.fullmatch(r"(?:(proxim[ao]|next) )?(\w+?)\.?(?: feira)?", words)
    iso = re.fullmatch(r"(\d{4}) (\d{1,2}) (\d{1,2})", words)
    numbers = re.fullmatch(r"(?:dia )?(\d{1,2})(?:(?:/| de | )(\d{1,2}|[a-z]+)\.?(?:(?:/| de | )(\d{2}|\d{4}))?)?", words)
    try:
        if words in RELATIVE:
            return today + timedelta(RELATIVE[words])
        if weekday and weekday[2] in DAY_NAMES:
            return today + timedelta((DAY_NAMES[weekday[2]] - today.weekday()) % 7 or (7 if weekday[1] else 0))
        if iso:
            return date(*map(int, iso.groups()))
        if numbers:
            d, month = int(numbers[1]), numbers[2]
            month = today.month if month is None else int(month) if month.isdigit() else MONTH_NAMES[month]
            year = int(numbers[3]) % 100 + 2000 if numbers[3] else today.year
            found = date(year, month, d)
            if future and found < today and not numbers[3]:
                found = date(year + 1, month, d) if numbers[2] else date(year + month // 12, month % 12 + 1, d)
            return found
    except (ValueError, KeyError):
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


def period(text, today):
    """The days [start, end) a week's words name: esta semana (today to Sunday), próxima semana, fim de semana. Any
    other words name one day."""
    words = plain(text).replace("-", " ")
    monday = today - timedelta(today.weekday())
    if words in ("esta semana", "this week", "semana", "nesta semana"):
        return today, monday + timedelta(7)
    if words in ("proxima semana", "semana que vem", "next week"):
        return monday + timedelta(7), monday + timedelta(14)
    if words in ("fim de semana", "este fim de semana", "no fim de semana", "weekend", "this weekend"):
        saturday = max(today, monday + timedelta(5))
        return saturday, monday + timedelta(7)
    start = day(text, today)
    return start, start + timedelta(1)


def label(d):
    """A day as the user reads it: qui 19/11."""
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return f"{WEEKDAYS[d.weekday()]} {d:%d/%m}"


def heading(d, today):
    """A day heading a list: hoje, ter 17/11, amanhã, qua 18/11, or qui 19/11."""
    near = {0: "hoje, ", 1: "amanhã, "}.get((d - today).days, "")
    return near + label(d)


def span(start, end):
    """A time span as the user reads it: qui 19/11 15:00–16:00, qui 19/11 (dia todo), or qui 19/11 a sex 20/11, whose
    end is exclusive as in iCalendar. Times are shown as given: convert them to local time first."""
    if not isinstance(start, datetime):
        last = end - timedelta(1)
        return label(start) + (f" a {label(last)}" if last > start else " (dia todo)")
    return f"{label(start.date())} {start:%H:%M}–{end:%H:%M}"
