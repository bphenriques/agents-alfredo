---
name: agenda
description: Read and change the user's calendar events and tasks.
version: 1.5.0
metadata:
  hermes:
    category: productivity
---

# Agenda

## When to Use

The user asks what they have on a day or a week, to add, change or remove an event, or about their tasks ("tarefas").

## Procedure

Every `agenda` tool returns text for the user. Reply with it exactly as returned, then at most one short question.
A tool error is for you, not the user: do what it says, and ask the user only when it tells you to.

Pass days, weeks, times and durations as the user said them ("quinta", "amanhã", "29/11", "esta semana", "15h",
"1h30"), or as 2026-11-19 and 15:30. Never work out a date yourself.

Set `calendar` only when the user names a calendar or the household's notes route the event to one.

`edit_*` and `remove_*` first return a question. Relay it. Only after the user says yes ("sim", "confirmo"), call
the same tool again with the same arguments and `confirmed` true.

| The user says | Call |
|---|---|
| what do I have today, on a day | `list_events` with `day` |
| what do I have this week, next week, at the weekend | `list_events` with `day` as they said it: "esta semana", "próxima semana", "fim de semana" |
| add an event: "dentista quinta às 15h", "jantar sábado" | `add_event` |
| a message with `[From the menu's Calendar input: …]` beside it | `add_event` with what they wrote, unless it answers your last question |
| an event with no day | nothing. Say in one line that it needs a day |
| move, rename or lengthen an event | `edit_event` with the event's `title` and current `day`, and what changes |
| cancel or remove an event | `remove_event` |
| what tasks do I have | `list_tasks` |
| something to do, maybe by a day: "tenho de pagar a luz até sexta" | `add_task` |
| a reminder at a time: "lembra-me às 18h de ligar à mãe" | `add_task` with `time`, and `due` when they name a day; never `cronjob` |
| a message with `[From the menu's Tasks input: …]` beside it | `add_task` with what they wrote, and `time` and `due` when it names them, unless it answers your last question |
| change a task's name, date or reminder time | `edit_task` |
| a task is done | `complete_task` |
| a task is not done after all | `reopen_task` |
| remove a task | `remove_task` |
| "ignora", "esquece", "deixa", alone or from the menu's inputs | nothing. Reply "Ok." |
