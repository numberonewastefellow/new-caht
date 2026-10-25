# Schedules (Pulse) — User Guide

Run any workflow automatically: every few minutes, daily, on weekdays, monthly, once at a set
time, or on a custom cron. Each run happens in the background and is saved as its own chat, so
you can open it, read the result, and even reply to continue it.

## Create a schedule
1. Open **Schedules** in the left sidebar (or click the clock button on a workflow card).
2. Click **New schedule** and pick the **workflow**.
3. Write the **message** the workflow receives on every run. Insert variables with the chips:

   | Variable | Becomes | Example |
   |---|---|---|
   | `{{date}}` | the run's date, in the schedule's timezone | `2026-10-26` |
   | `{{now}}` | the moment the run started | `2026-10-26 09:00 IST` |
   | `{{window_start}}` | the time of the last **successful** run (on the first run: one period earlier) | `2026-10-23 09:00 IST` |
   | `{{window_end}}` | this run's scheduled time | `2026-10-26 09:00 IST` |

   `{{window_start}}`/`{{window_end}}` make "only what's new since last time" briefs easy, and a
   failed run never leaves a gap (the window starts at the last *successful* run).
4. Choose **when** it runs: Every N minutes/hours, Hourly, Daily, Weekdays, Weekly (pick days),
   Monthly (day 1–28 or last day), Once, or Custom cron (`minute hour day month weekday`).
5. Pick the **timezone** (defaults to your browser's). The preview shows the next 5 runs.
6. **Save**, or **Save & run now** to test it immediately — it opens the run's chat.

## Where results appear
- Each run is a chat titled `<schedule name> · <date time>`.
- The sidebar's **Scheduled** section lists one row per schedule; click it to open the latest run.
  Scheduled runs are kept out of "Your chats" so frequent schedules don't bury your own chats,
  but they are searchable and show a clock badge.
- The schedule's page shows the full **run history**: status, duration, a preview of the output,
  and **Open chat** for every run.

## Run statuses
| Status | Meaning |
|---|---|
| Succeeded | The workflow finished. |
| Needs input | A workflow step asked a question. Open the chat and reply — the workflow continues. |
| Failed | The workflow hit an error (see the error on the run). |
| Timed out | The run exceeded the workflow's time limit and was stopped. |
| Interrupted | The machine running it stopped. It is **not** retried automatically — use Run now. |
| Skipped | Not started: the previous run was still going, you hit a usage limit, or access was lost. |
| Missed | The scheduler was unavailable at that time (more than 5 minutes late), so the slot was skipped. |
| Cancelled | The run was stopped manually. |

## Good to know
- **One run at a time per schedule.** If a run is still going when the next one is due, the new
  one is skipped.
- **Auto-pause.** After 5 failed runs in a row the schedule pauses itself and you get a
  notification. Fix the cause, then **Resume**.
- **Access is re-checked on every run.** If the workflow is deleted or you lose access to it, the
  schedule pauses.
- **Retention.** Each schedule keeps its last 50 run chats (configurable under *Advanced*). Older
  run chats are removed — except runs you replied to or shared, which are always kept.
- **Limits.** Schedules can run at most every 5 minutes, and you can have up to 20 active
  schedules (your admin can change these).
- **Daylight saving.** Times follow your chosen timezone. On the night clocks spring forward, a
  run set inside the skipped hour runs at the moment the clocks change; when clocks fall back it
  runs once, not twice. "Every N minutes/hours" schedules ignore daylight saving.
- **Duplicate** copies a schedule (the copy starts paused). **Delete** removes the schedule and its
  history; the run chats themselves stay in your chat history.

## Example: daily brief that reads your files
1. Connect a folder with the **Local Folder** connector (Admin → Connectors) so its files are
   indexed. New files dropped there are picked up on the connector's refresh.
2. Schedule the **Scheduled Intelligence Brief** workflow, weekdays at 09:00, with the message:
   `Brief for {{date}}. Topics: <your topics>. Only include items newer than {{window_start}}.`
3. Each morning you get a brief with TL;DR, internal findings (from your files), external news,
   action items and sources.
