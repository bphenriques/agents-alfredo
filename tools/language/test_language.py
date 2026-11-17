from datetime import date, datetime, timedelta

import pytest

import language as w

TODAY = date(2026, 11, 17)   # a Tuesday


@pytest.mark.parametrize("words, expected", [
    ("2026-12-01", date(2026, 12, 1)), ("hoje", TODAY), ("Amanhã", date(2026, 11, 18)),
    ("depois de amanhã", date(2026, 11, 19)), ("quinta", date(2026, 11, 19)), ("quinta-feira", date(2026, 11, 19)),
    ("Sábado", date(2026, 11, 21)), ("terça", TODAY), ("próxima terça", date(2026, 11, 24)),
    ("friday", date(2026, 11, 20)), ("29/11", date(2026, 11, 29)), ("dia 29", date(2026, 11, 29)),
    ("2/1/27", date(2027, 1, 2)),
])
def test_day(words, expected):
    assert w.day(words, TODAY, future=True) == expected


def test_day_rolls_forward_only_for_the_future():
    assert w.day("10/11", TODAY) == date(2026, 11, 10)
    assert w.day("10/11", TODAY, future=True) == date(2027, 11, 10)
    assert w.day("dia 3", TODAY, future=True) == date(2026, 12, 3)
    assert w.day("dia 3", date(2026, 12, 17), future=True) == date(2027, 1, 3)


@pytest.mark.parametrize("words", ["31/02", "breve", "dia 40", ""])
def test_day_refuses_what_is_not_one(words):
    with pytest.raises(w.NotUnderstood, match="is not a day"):
        w.day(words, TODAY)


@pytest.mark.parametrize("words, expected", [("15:30", (15, 30)), ("15h", (15, 0)), ("15h30", (15, 30)), ("9", (9, 0))])
def test_clock(words, expected):
    assert (w.clock(words).hour, w.clock(words).minute) == expected


@pytest.mark.parametrize("words", ["25h", "15:75", "tarde"])
def test_clock_refuses_what_is_not_one(words):
    with pytest.raises(w.NotUnderstood):
        w.clock(words)


@pytest.mark.parametrize("words, minutes", [("1h", 60), ("1h30", 90), ("90 min", 90), ("2 horas", 120), ("45m", 45)])
def test_length(words, minutes):
    assert w.length(words) == timedelta(minutes=minutes)


def test_matches_ignores_case_accents_and_emoji():
    assert w.matches("partilhado", "Casa 🏠 Partilhado")
    assert w.matches("MAE", "Ligar à mãe")
    assert not w.matches("casa trabalho", "Casa 🏠 Partilhado")


def test_label_and_span():
    assert w.label("2026-11-19") == w.label(date(2026, 11, 19)) == "qui 19/11"
    assert w.span(datetime(2026, 11, 19, 15), datetime(2026, 11, 19, 16, 30)) == "qui 19/11 15:00–16:30"
    assert w.span(date(2026, 11, 19), date(2026, 11, 20)) == "qui 19/11"
    assert w.span(date(2026, 11, 19), date(2026, 11, 22)) == "qui 19/11 a sáb 21/11"
