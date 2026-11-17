import asyncio
import os
import sys
from datetime import date, datetime, timedelta

import icalendar
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import agenda as a

TODAY = date(2026, 11, 17)   # a Tuesday


def ics(*components):
    return "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:test\r\n" + "".join(components) + "END:VCALENDAR\r\n"


def event(uid, summary, start, end, extra=""):
    return (f"BEGIN:VEVENT\r\nUID:{uid}\r\nDTSTAMP:20261101T000000Z\r\n{start}\r\n{end}\r\nSUMMARY:{summary}\r\n"
            f"{extra}END:VEVENT\r\n")


def todo(uid, summary, extra=""):
    return f"BEGIN:VTODO\r\nUID:{uid}\r\nDTSTAMP:20261101T000000Z\r\nSUMMARY:{summary}\r\n{extra}END:VTODO\r\n"


@pytest.fixture
def vdir(tmp_path, monkeypatch):
    """Two calendars: the default one holds events and tasks, the shared one has an emoji in its name."""
    personal, shared = tmp_path / "personal", tmp_path / "shared"
    for folder, name in ((personal, "Calendário + Tarefas"), (shared, "Casa 🏠 Partilhado")):
        folder.mkdir()
        (folder / "displayname").write_text(name)
    files = {
        personal / "dentista.ics": ics(event("dentista", "Dentista", "DTSTART;TZID=Europe/Lisbon:20261119T150000",
                                             "DTEND;TZID=Europe/Lisbon:20261119T160000", "LOCATION:Rua Augusta 120\r\n")),
        personal / "ginasio.ics": ics(event("ginasio", "Ginásio", "DTSTART;TZID=Europe/Lisbon:20261102T070000",
                                            "DTEND;TZID=Europe/Lisbon:20261102T080000", "RRULE:FREQ=WEEKLY;BYDAY=MO,TH\r\n")),
        personal / "feriado.ics": ics(event("feriado", "Feriado", "DTSTART;VALUE=DATE:20261208", "DTEND;VALUE=DATE:20261209")),
        personal / "luz.ics": ics(todo("luz", "Pagar a luz", "DUE;VALUE=DATE:20261120\r\nSTATUS:NEEDS-ACTION\r\n")),
        personal / "pao.ics": ics(todo("pao", "Comprar pão")),
        personal / "seguro.ics": ics(todo("seguro", "Rever o seguro", "DUE;VALUE=DATE:20261110\r\n")),
        personal / "mae.ics": ics(todo("mae", "Ligar à mãe", "STATUS:COMPLETED\r\n")),
        shared / "jantar.ics": ics(event("jantar", "Jantar com amigos", "DTSTART:20261119T200000Z",
                                         "DTEND:20261119T220000Z")),
    }
    for path, text in files.items():
        path.write_text(text)
    monkeypatch.setattr(a, "ROOT", tmp_path)
    monkeypatch.setattr(a, "DEFAULT", "personal")
    monkeypatch.setattr(a, "today", lambda: TODAY)
    a.asked.clear()
    return tmp_path


def run(coroutine):
    return asyncio.run(coroutine)


def only(folder, uid=None):
    """The one component of the file in `folder` that the tools wrote, or of `uid`.ics."""
    files = [f for f in folder.glob("*.ics") if uid and f.stem == uid or not uid and len(f.stem) == 36]
    assert len(files) == 1, files
    return next(c for c in icalendar.Calendar.from_ical(files[0].read_bytes()).walk() if c.name in ("VEVENT", "VTODO"))


def test_changes_refuse_the_past_and_words_that_are_no_day(vdir):
    assert a.resolve("10/11") == date(2026, 11, 10)   # reading the past is fine
    with pytest.raises(a.ToolError, match="já passou"):
        a.resolve("ontem", future=True)
    with pytest.raises(a.ToolError, match="is not a day"):
        run(a.add_event("X", "breve"))


def test_list_events_merges_calendars_and_tasks(vdir):
    assert run(a.list_events("quinta")) == ("qui 19/11\n- 07:00–08:00 Ginásio\n- 15:00–16:00 Dentista (Rua Augusta 120)\n"
                                            "- 20:00–22:00 Jantar com amigos · Casa 🏠 Partilhado")
    assert run(a.list_events("sexta")) == "sex 20/11\n- Pagar a luz (tarefa)"
    assert run(a.list_events("8/12")) == "ter 08/12\n- Feriado (dia todo)"


def test_list_events_over_several_days(vdir):
    assert run(a.list_events("quinta", 2)).split("\n\n")[1] == "sex 20/11\n- Pagar a luz (tarefa)"
    assert run(a.list_events("21/11", 2)) == "Nada de sáb 21/11 a dom 22/11."
    assert run(a.list_events("21/11", 1)) == "Nada para sáb 21/11."


def test_add_event_timed_in_the_default_calendar(vdir):
    assert run(a.add_event("Cabeleireiro", "quinta", "9h30")) == "Adicionado: Cabeleireiro, qui 19/11 09:30–10:30."
    added = only(vdir / "personal")
    assert added["DTSTART"].dt == datetime(2026, 11, 19, 9, 30, tzinfo=a.ZONE)
    assert "- 09:30–10:30 Cabeleireiro" in run(a.list_events("quinta"))


def test_add_event_by_calendar_name_whole_day(vdir):
    assert run(a.add_event("Férias", "29/11", calendar="partilhado")) == "Adicionado: Férias, dom 29/11 (dia todo) · Casa 🏠 Partilhado."
    assert only(vdir / "shared")["DTSTART"].dt == date(2026, 11, 29)


def test_add_event_refusals(vdir):
    with pytest.raises(a.ToolError, match="calendars match"):
        run(a.add_event("X", "quinta", calendar="trabalho"))
    with pytest.raises(a.ToolError, match="já passou"):
        run(a.add_event("X", "ontem"))
    with pytest.raises(a.ToolError, match="needs a time"):
        run(a.add_event("X", "quinta", duration="1h"))


def test_edit_event_asks_first_and_keeps_the_length(vdir):
    before = (vdir / "personal" / "dentista.ics").read_text()
    question = run(a.edit_event("dentista", "quinta", new_day="sexta", confirmed=True))   # never asked yet: asks
    assert question == "Mudo Dentista de qui 19/11 15:00–16:00 para sex 20/11 15:00–16:00?"
    assert (vdir / "personal" / "dentista.ics").read_text() == before
    assert run(a.edit_event("dentista", "quinta", new_day="sexta", confirmed=True)) == "Alterado: Dentista, sex 20/11 15:00–16:00."
    changed = only(vdir / "personal", "dentista")
    assert changed["DTEND"].dt - changed["DTSTART"].dt == timedelta(hours=1)
    assert changed["SEQUENCE"] == 1


def test_edit_event_confirms_only_what_was_asked(vdir):
    run(a.edit_event("dentista", "quinta", new_time="10h"))
    assert "?" in run(a.edit_event("dentista", "quinta", new_time="11h", confirmed=True))


def test_remove_event(vdir):
    assert run(a.remove_event("jantar", "quinta")) == "Removo Jantar com amigos, qui 19/11 20:00–22:00 · Casa 🏠 Partilhado?"
    assert run(a.remove_event("jantar", "quinta", confirmed=True)) == "Removido: Jantar com amigos, qui 19/11 20:00–22:00 · Casa 🏠 Partilhado."
    assert not (vdir / "shared" / "jantar.ics").exists()


def test_repeating_events_and_misses_are_refused(vdir):
    with pytest.raises(a.ToolError, match="Recorrente"):
        run(a.remove_event("ginasio", "quinta"))
    with pytest.raises(a.ToolError, match="That day has: Dentista, Ginásio, Jantar com amigos"):
        run(a.edit_event("reunião", "quinta", new_time="10h"))


def test_tasks_lifecycle(vdir):
    assert run(a.list_tasks()) == "- Rever o seguro (atrasada desde ter 10/11)\n- Pagar a luz (até sex 20/11)\n- Comprar pão"
    assert run(a.add_task("Renovar o cartão", "29/11")) == "Tarefa adicionada: Renovar o cartão (até dom 29/11)."
    assert run(a.complete_task("luz")) == "Feito: Pagar a luz."
    assert only(vdir / "personal", "luz")["STATUS"] == "COMPLETED"
    assert run(a.list_tasks()) == "- Rever o seguro (atrasada desde ter 10/11)\n- Renovar o cartão (até dom 29/11)\n- Comprar pão"
    assert run(a.reopen_task("luz")) == "Reaberta: Pagar a luz (até sex 20/11)."
    assert "COMPLETED" not in only(vdir / "personal", "luz")


def test_edit_and_remove_task_ask_first(vdir):
    assert run(a.edit_task("pão", new_due="sexta")) == "Mudo a data de Comprar pão para sex 20/11?"
    assert run(a.edit_task("pão", new_title="Comprar pão e leite")) == "Mudo a tarefa Comprar pão para Comprar pão e leite?"
    assert run(a.edit_task("pão", new_due="sexta", confirmed=True)) == "Tarefa alterada: Comprar pão (até sex 20/11)."
    assert run(a.remove_task("mãe", confirmed=True)) == "Removo a tarefa Ligar à mãe?"
    assert run(a.remove_task("mãe", confirmed=True)) == "Tarefa removida: Ligar à mãe."
    with pytest.raises(a.ToolError, match="No open task"):
        run(a.complete_task("mãe"))


def test_the_server_starts_and_offers_its_tools():
    async def tools():
        server = StdioServerParameters(command=sys.executable, args=[a.__file__, "serve"], env={**os.environ})
        async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            return {t.name for t in (await session.list_tools()).tools}
    assert asyncio.run(tools()) == {"list_events", "add_event", "edit_event", "remove_event", "list_tasks", "add_task",
                                    "edit_task", "complete_task", "reopen_task", "remove_task"}


def test_today_and_this_week(vdir):
    assert run(a.list_events()) == "hoje, ter 17/11\n- Rever o seguro (tarefa, atrasada desde ter 10/11)"
    week = run(a.list_events("esta semana")).split("\n\n")
    assert [d.split("\n")[0] for d in week] == ["hoje, ter 17/11", "qui 19/11", "sex 20/11"]


def test_files_are_parsed_again_only_when_they_change(vdir, monkeypatch):
    run(a.list_events("quinta"))
    calls = []
    monkeypatch.setattr(a.icalendar.Calendar, "from_ical", lambda data: calls.append(data) or icalendar.Calendar())
    run(a.list_events("quinta"))
    assert calls == []
    (vdir / "personal" / "pao.ics").write_text(ics(todo("pao", "Comprar pão e leite")))
    run(a.list_tasks())
    assert len(calls) == 1
