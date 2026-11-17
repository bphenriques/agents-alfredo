---
name: agenda
description: Read and change the user's calendar events and tasks.
version: 1.0.0
metadata:
  hermes:
    category: productivity
---

# Agenda

## When to Use

The user asks what they have on a day, to add, change or remove an event, or about their tasks ("tarefas").

## Procedure

Every `agenda` tool returns text for the user. Reply with it exactly as returned, then at most one short question.

Pass days, times and durations as the user said them ("quinta", "amanhã", "29/11", "15h", "1h30"), or as 2026-11-19
and 15:30. Never work out a date yourself.

Set `calendar` only when the user names a calendar or the household's notes route the event to one.

`edit_*` and `remove_*` first return a question. Relay it. Only after the user says yes ("sim", "confirmo"), call
the same tool again with the same arguments and `confirmed` true.

| The user says | Call |
|---|---|
| what do I have today, on a day, this week | `list_events` with `day`, and `days` for a week |
| add an event: "dentista quinta às 15h", "jantar sábado" | `add_event` |
| move, rename or lengthen an event | `edit_event` with the event's `title` and current `day`, and what changes |
| cancel or remove an event | `remove_event` |
| what tasks do I have | `list_tasks` |
| add a task: "lembra-me de pagar a luz até sexta" | `add_task` |
| change a task's name or date | `edit_task` |
| a task is done | `complete_task` |
| a task is not done after all | `reopen_task` |
| remove a task | `remove_task` |
