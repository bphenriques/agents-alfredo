"""The household's calendars and tasks: an MCP server over the vdir the host keeps in sync, one folder per calendar
and one iCalendar file per event or task."""
import argparse
import asyncio
import os
import subprocess
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import icalendar
import language
import recurring_ical_events
from language import label, matches
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

ROOT = Path("@calendarsRoot@")
DEFAULT = "@defaultCalendar@"   # the folder new events and tasks go to
SYNC = "@syncCalendars@"   # pushes the vdir to its servers, so a change shows elsewhere at once
ZONE = ZoneInfo(os.environ.get("TZ") or os.path.realpath("/etc/localtime").split("zoneinfo/")[-1])
EVENT_LENGTH = timedelta(hours=1)   # an event given a time but no duration
CONFIRM_FOR = timedelta(minutes=10)   # a "sim" must answer the question the user just read

mcp = MCPServer("agenda")
asked = {}   # each change awaiting confirmation, and when it was asked
parsed = {}   # each file's contents, with the modification time and size they were read at


def today():
    return date.today()


def now():
    return datetime.now(ZONE)


def understood(read, *args):
    try:
        return read(*args)
    except language.NotUnderstood as e:
        raise ToolError(str(e)) from None


def resolve(day, future=False):
    """The date `day` names; with `future`, for a change, which a past date cannot be."""
    found = understood(language.day, day, today(), future)
    if future and found < today():
        raise ToolError(f"{label(found)} já passou.")
    return found


def clock(text):
    return understood(language.clock, text)


def length(text):
    return understood(language.length, text)


def calendars():
    """Each calendar's folder and name, the default first."""
    found = [(path, (path / "displayname").read_text().strip() if (path / "displayname").exists() else path.name)
             for path in sorted(ROOT.iterdir()) if path.is_dir() and not path.name.startswith(".")]
    return sorted(found, key=lambda c: c[0].name != DEFAULT)


def pick_calendar(name):
    if name is None:
        return next(c for c in calendars() if c[0].name == DEFAULT)
    found = [c for c in calendars() if matches(name, c[1])]
    if len(found) != 1:
        raise ToolError(f"{len(found)} calendars match {name!r}. The calendars are: {', '.join(c[1] for c in calendars())}.")
    return found[0]


def read(file):
    """A file's contents, parsed again only when it changed: the server lives on, and parsing every file each call
    takes seconds."""
    stat = file.stat()
    seen = (stat.st_mtime_ns, stat.st_size)
    if file not in parsed or parsed[file][0] != seen:
        parsed[file] = (seen, icalendar.Calendar.from_ical(file.read_bytes()))
    return parsed[file][1]


def items():
    """Every event and task file: its path, its calendar's name, and its contents."""
    for path, name in calendars():
        for file in sorted(path.glob("*.ics")):
            yield file, name, read(file)


def single(cal):
    """The file's one component, or an error for a repeating one, which the user changes in their calendar app."""
    parts = [c for c in cal.walk() if c.name in ("VEVENT", "VTODO")]
    if len(parts) != 1 or any(k in parts[0] for k in ("RRULE", "RDATE", "RECURRENCE-ID")):
        raise ToolError("Recorrente: altera na app do calendário.")
    return parts[0]


def local(value):
    return value.astimezone(ZONE) if isinstance(value, datetime) and value.tzinfo else value


def when(start, end):
    return language.span(local(start), local(end))


def suffix(name):
    return "" if name == calendars()[0][1] else f" · {name}"


def save(path, cal):
    """Replaced whole, so the sync never reads half a file; vdirsyncer ignores the .tmp."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(cal.to_ical())
    tmp.replace(path)
    sync()


def delete(path):
    path.unlink()
    sync()


def sync():
    """In the background: the reply never waits on the network, and a failed sync leaves it to the timer."""
    subprocess.Popen([SYNC], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def new_calendar(component):
    cal = icalendar.Calendar()
    cal.add("PRODID", "-//alfredo//agenda//PT")
    cal.add("VERSION", "2.0")
    component.add("UID", str(uuid.uuid4()))
    component.add("DTSTAMP", datetime.now(timezone.utc))
    cal.add_component(component)
    cal.add_missing_timezones()
    return cal


def touch(component):
    for key in ("DTSTAMP", "LAST-MODIFIED"):
        component.pop(key, None)
        component.add(key, datetime.now(timezone.utc))
    sequence = int(component.get("SEQUENCE", 0)) + 1
    component.pop("SEQUENCE", None)
    component.add("SEQUENCE", sequence)


def replace(component, key, value):
    component.pop(key, None)
    if value is not None:
        component.add(key, value)


def confirm(change, confirmed):
    """Whether to apply `change`: only once the user was asked exactly this, a moment ago."""
    now = datetime.now()
    if confirmed and now - asked.get(change, datetime.min) <= CONFIRM_FOR:
        del asked[change]
        return True
    asked[change] = now
    return False


# Events


def occurrences(start, end):
    for file, name, cal in items():
        for event in recurring_ical_events.of(cal).between(start, end):
            yield file, name, cal, event


def find_event(title, day):
    on_day = list(occurrences(day, day + timedelta(1)))
    found = [o for o in on_day if matches(title, str(o[3].get("SUMMARY", "")))]
    if not found:
        listed = ", ".join(str(o[3].get("SUMMARY", "")) for o in on_day) or "nothing"
        raise ToolError(f"No event matching {title!r} on {label(day)}. That day has: {listed}.")
    if len(found) > 1:
        raise ToolError(f"{len(found)} events match {title!r} on {label(day)}: "
                        f"{', '.join(str(o[3]['SUMMARY']) for o in found)}. Ask the user which.")
    return found[0]


def event_line(event, name):
    """- 15:00–16:00 Dentista (Rua Augusta 120), or - Feriado (dia todo)."""
    start, end = event.start, event.end
    notes = [str(event["LOCATION"])] if event.get("LOCATION") else []
    if not isinstance(start, datetime):
        notes.insert(0, f"até {label(end - timedelta(1))}" if end - start > timedelta(1) else "dia todo")
    hours = f"{local(start):%H:%M}–{local(end):%H:%M} " if isinstance(start, datetime) else ""
    return f"- {hours}{event.get('SUMMARY', '')}{f' ({', '.join(notes)})' if notes else ''}{suffix(name)}"


@mcp.tool(structured_output=False)   # plain text for the user; a structured copy would only double it
async def list_events(day: str | None = None, days: int | None = None) -> str:
    """The events and the open tasks due in every calendar, today by default. `day` is 2026-11-19 or the user's own
    words: a day ("hoje", "quinta", "29/11") or a week ("esta semana", "próxima semana", "fim de semana"). `days` only
    to cover more days from a single day."""
    first, last = understood(language.period, day, today()) if day else (today(), today() + timedelta(1))
    last = first + timedelta(days) if days else last
    by_day = {}
    for _, name, _, event in occurrences(first, last):
        start = event.start.date() if isinstance(event.start, datetime) else event.start
        by_day.setdefault(max(start, first), []).append((local(event.start).isoformat(), event_line(event, name)))
    for _, name, task in tasks():
        due = task_due(task)
        if task_open(task) and due and (first <= due < last or due < today() and first <= today() < last):
            late = f", atrasada desde {label(due)}" if due < today() else ""
            by_day.setdefault(max(due, today()), []).append(("~", f"- {task['SUMMARY']} (tarefa{late}){suffix(name)}"))
    if not by_day:
        one_day = last - first == timedelta(1)
        return f"Nada para {language.heading(first, today())}." if one_day else f"Nada de {label(first)} a {label(last - timedelta(1))}."
    return "\n\n".join(f"{language.heading(d, today())}\n" + "\n".join(line for _, line in sorted(by_day[d]))
                       for d in sorted(by_day))


@mcp.tool(structured_output=False)
async def add_event(title: str, day: str, time: str | None = None, duration: str | None = None,
                    calendar: str | None = None) -> str:
    """Add an event. `day` is 2026-11-19 or the user's words ("quinta"), `time` 15:30 or theirs ("15h"); no time
    makes it a whole day. `duration` ("1h30") defaults to an hour. `calendar` only when the user names one."""
    path, name = pick_calendar(calendar)
    d = resolve(day, future=True)
    event = icalendar.Event()
    event.add("SUMMARY", title)
    if time:
        start = datetime.combine(d, clock(time), ZONE)
        event.add("DTSTART", start)
        event.add("DTEND", start + (length(duration) if duration else EVENT_LENGTH))
    elif duration:
        raise ToolError("A duration needs a time: ask the user when it starts.")
    else:
        event.add("DTSTART", d)
        event.add("DTEND", d + timedelta(1))
    cal = new_calendar(event)
    save(path / f"{event['UID']}.ics", cal)
    return f"Adicionado: {title}, {when(event.start, event.end)}{suffix(name)}."


@mcp.tool(structured_output=False)
async def edit_event(title: str, day: str, new_title: str | None = None, new_day: str | None = None,
                     new_time: str | None = None, new_duration: str | None = None, confirmed: bool = False) -> str:
    """Change the event called `title` on `day`. Returns a question: relay it, and only after the user says yes call
    again with the same arguments and `confirmed` true."""
    file, name, cal, _ = find_event(title, resolve(day))
    event = single(cal)
    if not (new_title or new_day or new_time or new_duration):
        raise ToolError("Nothing to change: pass new_title, new_day, new_time or new_duration.")
    start, end = event.start, event.end
    target = resolve(new_day, future=True) if new_day else (start.date() if isinstance(start, datetime) else start)
    if new_time:
        new_start = datetime.combine(target, clock(new_time), ZONE)
        new_end = new_start + (length(new_duration) if new_duration else
                               (end - start if isinstance(start, datetime) else EVENT_LENGTH))
    elif isinstance(start, datetime):
        new_start = datetime.combine(target, local(start).time(), ZONE)
        new_end = new_start + (length(new_duration) if new_duration else end - start)
    elif new_duration:
        raise ToolError("A whole-day event has no duration: ask the user for a time too.")
    else:
        new_start, new_end = target, target + (end - start)
    new_name = new_title or str(event["SUMMARY"])
    title_now, was, will = str(event["SUMMARY"]), when(start, end), when(new_start, new_end)
    after = f"{new_name}, {will}"
    if not confirm(("edit_event", str(file), after), confirmed):
        change = f"{title_now} de {was} para {will}" if new_name == title_now else f"{title_now}, {was}, para {after}"
        return f"Mudo {change}{suffix(name)}?"
    replace(event, "SUMMARY", new_name)
    replace(event, "DURATION", None)
    replace(event, "DTSTART", new_start)
    replace(event, "DTEND", new_end)
    touch(event)
    cal.add_missing_timezones()
    save(file, cal)
    return f"Alterado: {after}{suffix(name)}."


@mcp.tool(structured_output=False)
async def remove_event(title: str, day: str, confirmed: bool = False) -> str:
    """Remove the event called `title` on `day`. Returns a question: relay it, and only after the user says yes call
    again with the same arguments and `confirmed` true."""
    file, name, cal, _ = find_event(title, resolve(day))
    event = single(cal)
    what = f"{event['SUMMARY']}, {when(event.start, event.end)}{suffix(name)}"
    if not confirm(("remove_event", str(file)), confirmed):
        return f"Removo {what}?"
    delete(file)
    return f"Removido: {what}."


# Tasks


def tasks():
    for file, name, cal in items():
        for task in cal.walk("VTODO"):
            yield file, name, task


def task_open(task):
    return str(task.get("STATUS", "NEEDS-ACTION")).upper() not in ("COMPLETED", "CANCELLED")


def task_due(task):
    due = task.get("DUE")
    return None if due is None else (local(due.dt).date() if isinstance(due.dt, datetime) else due.dt)


def task_due_at(task):
    """The date the task is due, or the local time when it has one."""
    due = task.get("DUE")
    return None if due is None else local(due.dt)


def due_label(due):
    """sex 20/11, or sex 20/11 18:00."""
    return f"{label(due.date())} {due:%H:%M}" if isinstance(due, datetime) else label(due)


def due_note(due):
    if due is None:
        return ""
    day = due.date() if isinstance(due, datetime) else due
    return f" (atrasada desde {label(day)})" if day < today() else f" (até {due_label(due)})"


def task_line(task, name):
    return f"- {task['SUMMARY']}{due_note(task_due_at(task))}{suffix(name)}"


def due_from(day, time, current=None):
    """A date, or a time on one: a time alone keeps the current day (today without one), a day alone the current time."""
    if not time:
        d = resolve(day, future=True)
        return datetime.combine(d, current.time(), ZONE) if isinstance(current, datetime) else d
    d = resolve(day, future=True) if day else current.date() if isinstance(current, datetime) else current or today()
    due = datetime.combine(d, clock(time), ZONE)
    if due < now():
        raise ToolError(f"{label(d)} {due:%H:%M} já passou.")
    return due


def set_due(task, due):
    """DUE, and at a time an RFC 5545 alarm then, absolute as every client reads it; any earlier alarm goes."""
    replace(task, "DUE", due)
    task.subcomponents = [c for c in task.subcomponents if c.name != "VALARM"]
    if isinstance(due, datetime):
        alarm = icalendar.Alarm()
        alarm.add("ACTION", "DISPLAY")
        alarm.add("DESCRIPTION", str(task["SUMMARY"]))
        alarm.add("TRIGGER", due.astimezone(timezone.utc), parameters={"VALUE": "DATE-TIME"})
        task.add_component(alarm)


def find_task(title, is_open=None):
    """The task called `title`: open or done when `is_open` says, either otherwise."""
    found = [(file, name) for file, name, task in tasks()
             if (is_open is None or task_open(task) == is_open) and matches(title, str(task.get("SUMMARY", "")))]
    if not found:
        raise ToolError(f"No {'open ' if is_open else 'done ' if is_open is False else ''}task matching {title!r}. "
                        f"Open tasks: {', '.join(str(t['SUMMARY']) for _, _, t in tasks() if task_open(t)) or 'none'}.")
    if len(found) > 1:
        raise ToolError(f"{len(found)} tasks match {title!r}. Ask the user which.")
    file, name = found[0]
    cal = read(file)
    return file, name, cal, single(cal)


@mcp.tool(structured_output=False)
async def list_tasks() -> str:
    """The open tasks, soonest due first."""
    open_tasks = [(task_due(t) or date.max, task_line(t, name)) for _, name, t in tasks() if task_open(t)]
    if not open_tasks:
        return "Sem tarefas por fazer."
    return "\n".join(line for _, line in sorted(open_tasks))


@mcp.tool(structured_output=False)
async def add_task(title: str, due: str | None = None, time: str | None = None) -> str:
    """Add a task. `due`, only when the user gives one, is 2026-11-20 or their words ("sexta", "29/11"). `time`, 18:00
    or theirs ("18h"), makes it a reminder then, today when no `due`."""
    path, name = pick_calendar(None)
    task = icalendar.Todo()
    task.add("SUMMARY", title)
    task.add("STATUS", "NEEDS-ACTION")
    if due or time:
        set_due(task, due_from(due, time))
    cal = new_calendar(task)
    save(path / f"{task['UID']}.ics", cal)
    return f"Tarefa adicionada: {task_line(task, name)[2:]}."


@mcp.tool(structured_output=False)
async def edit_task(title: str, new_title: str | None = None, new_due: str | None = None,
                    new_time: str | None = None, confirmed: bool = False) -> str:
    """Change the open task called `title`; `new_time` sets its reminder. Returns a question: relay it, and only after
    the user says yes call again with the same arguments and `confirmed` true."""
    if not (new_title or new_due or new_time):
        raise ToolError("Nothing to change: pass new_title, new_due or new_time.")
    file, name, cal, task = find_task(title, is_open=True)
    before = task_line(task, name)[2:]
    current = task_due_at(task)
    due = due_from(new_due, new_time, current) if new_due or new_time else current
    new_name = new_title or str(task["SUMMARY"])
    after = f"{new_name}{due_note(due)}{suffix(name)}"
    if not confirm(("edit_task", str(file), after), confirmed):
        if new_name == str(task["SUMMARY"]):
            return f"Mudo a data de {new_name} para {due_label(due)}?"
        return f"Mudo a tarefa {before} para {after}?"
    replace(task, "SUMMARY", new_name)
    if due != current:
        set_due(task, due)
    touch(task)
    save(file, cal)
    return f"Tarefa alterada: {after}."


@mcp.tool(structured_output=False)
async def complete_task(title: str) -> str:
    """Mark the open task called `title` as done."""
    file, name, cal, task = find_task(title, is_open=True)
    replace(task, "STATUS", "COMPLETED")
    replace(task, "COMPLETED", datetime.now(timezone.utc))
    replace(task, "PERCENT-COMPLETE", 100)
    touch(task)
    save(file, cal)
    return f"Feito: {task['SUMMARY']}."


@mcp.tool(structured_output=False)
async def reopen_task(title: str) -> str:
    """Mark the done task called `title` as not done again."""
    file, name, cal, task = find_task(title, is_open=False)
    replace(task, "STATUS", "NEEDS-ACTION")
    replace(task, "COMPLETED", None)
    replace(task, "PERCENT-COMPLETE", None)
    touch(task)
    save(file, cal)
    return f"Reaberta: {task_line(task, name)[2:]}."


@mcp.tool(structured_output=False)
async def remove_task(title: str, confirmed: bool = False) -> str:
    """Remove the task called `title`, open or done. Returns a question: relay it, and only after the user says yes
    call again with the same arguments and `confirmed` true."""
    file, name, cal, task = find_task(title)
    what = task_line(task, name)[2:]
    if not confirm(("remove_task", str(file)), confirmed):
        return f"Removo a tarefa {what}?"
    delete(file)
    return f"Tarefa removida: {what}."


def main():
    p = argparse.ArgumentParser(prog="agenda", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("serve", help="the MCP server, over stdio")
    sub.add_parser("list", help="print today's events and the open tasks")
    match p.parse_args().command:
        case "serve":
            mcp.run()
        case "list":
            print(asyncio.run(list_events()), asyncio.run(list_tasks()), sep="\n\n")


if __name__ == "__main__":
    main()
