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

# Webhooks

A webhook lets another system start a workflow when something happens there, like a new complaint or ticket. Use a schedule when the time is what matters, and a webhook when an event is.

## Create a webhook
1. Open **Schedules**, then the **Webhooks** tab, and press **New webhook**.
2. Pick the workflow and give the webhook a name.
3. Write what the workflow should receive. `{{payload}}` is the whole event, `{{payload.ticket.title}}` or `{{payload.items[0]}}` is one value, and `{{date}}` and `{{now}}` give the time.
4. Choose how the calling system proves itself:
   - **Signed (Standard Webhooks):** recommended. The data can't be changed or replayed later.
   - **Secret in a header:** for systems that can't sign. It doesn't protect the data or stop replays.
5. Choose what makes an event a repeat. Systems often retry, and a repeat doesn't run again.
6. **Copy the URL and secret straight away.** They're only shown once. If you lose them, press **Rotate** to get new ones.

## Before you rely on it
Runs use your access: your documents, files and connected accounts. The data a system sends is marked for the AI as data rather than instructions, but that can't fully prevent an instruction hidden in it from being followed. So a webhook's runs can only use the tools you tick when you create or edit it, and none are ticked by default. Be careful with tools that send or change things.

## Test it
On the webhook's page, press **Listen**, then **Send test event** or call the test URL (`/api/hooks/test/...`). You'll see what arrived and exactly what the workflow would receive. Nothing runs.

## See what happened
The webhook's page lists each accepted call with its result, its data and a link to its chat. If a call was refused, the page shows why, such as "Signature does not match".

## Stop it
- **Pause:** switch it off. Calls are refused until you turn it back on. Runs still waiting are skipped when a worker reaches them. The sender can resend those events once it's back on.
- **Rotate:** get a new URL and secret. You choose how long the old ones keep working, so you can update the other system first.
- **Revoke:** use this if the URL or secret may have leaked. They stop working immediately, and runs still waiting won't start.
- **Delete:** removes the webhook and its run history. Chats from earlier runs stay.

The event data kept with each run is cleared after 7 days. The text the workflow received stays in that run's chat, like any other chat, until the webhook's run limit removes it, so avoid sending data you wouldn't keep in a chat. After 5 failed runs in a row a webhook pauses itself and notifies you.

## Keep real events coming during development

Two small tools can call your webhooks by themselves. They run apart from the app: they only send HTTP requests, so stopping or deleting them changes nothing else.

- **Uptime Kuma** sends an event when a service goes down or recovers.
- **changedetection.io** sends an event when a web page or feed changes.

### Start them

Start the main stack first. Then, in `deployment/docker_compose`:

```
docker compose -p event-sources -f docker-compose.event-sources.yml up -d
```

Uptime Kuma is at http://localhost:3010 and changedetection.io at http://localhost:5010.

### Add the workflows

In `backend/tests/workflow_creator`, with your admin API key:

```
python create_workflows.py --url https://localhost --key <key> --file workflows/45_service_incident_note.json
python create_workflows.py --url https://localhost --key <key> --file workflows/46_page_change_summary.json
```

### Create one webhook per tool

Go to **Pulse > Webhooks > New webhook** and choose:

| Setting | Value |
| --- | --- |
| Workflow | Service Incident Note, or Page Change Summary |
| How the caller proves itself | Secret in a header |
| What makes an event a repeat | Don't check |
| Tools | None |
| Notify me when a run succeeds | On, if you want the result in your notifications |

The URL and secret are shown once. Use the part of the URL after `/api/hooks/` below. These tools are on the Docker network, so they call `http://nginx:8088`, not `https://localhost`.

### Connect Uptime Kuma

1. Create an account when it asks.
2. Go to **Settings > General** and turn off **NSCD**. If it stays on, Kuma keeps a restarted container's old address for an hour and keeps reporting it as down.
3. Go to **Settings > Notifications > Setup Notification** and set:
   - Notification Type: Webhook
   - Post URL: `http://nginx:8088/api/hooks/<token>`
   - Request Body: application/json
   - Additional Headers: `{"x-webhook-secret": "<secret>"}`
4. Add a monitor for each service, with that notification ticked and **Retries** at 2, so a short blip doesn't send an event:

| Service | Monitor type | Address |
| --- | --- | --- |
| API | HTTP | `http://api_server:8080/version` |
| nginx | TCP port | `nginx` port `8088` |
| Postgres | TCP port | `relational_db` port `5432` |
| Redis | TCP port | `cache` port `6379` |
| OpenSearch | TCP port | `opensearch` port `9200` |
| MinIO | TCP port | `minio` port `9000` |
| Office MCP | TCP port | `office-mcp-server` port `8100` |
| Code interpreter | TCP port | `code-interpreter` port `8000` |

### Connect changedetection.io

1. In the secret, replace `+` with `%2B`, `/` with `%2F` and `=` with `%3D`. A URL can't carry them as they are.
2. Go to **Settings > Notifications** and add this notification URL:

```
json://nginx:8088/api/hooks/<token>?+x-webhook-secret=<encoded secret>
```

3. Set the check interval to 6 hours, and add the pages to watch, such as `https://github.com/BerriAI/litellm/releases.atom`.

### Good to know

- **Cost:** each event is one run on the cheap model, about 700 tokens in testing. Keep the intervals long and watch pages that change rarely.
- **Secrets:** changedetection.io writes the notification URL, with the secret, to its own container log. Don't share those logs.
- **API or nginx down:** an alert can't arrive while they're down. You get the recovery message afterwards.
- **Background workers:** Kuma doesn't watch them, because that would need the Docker socket, which exposes every container's settings. Check them on **Admin > Services**.
- **Private pages:** changedetection.io refuses to fetch private addresses. Leave that on unless you need to watch something on your own network.

### Pause or remove them

```
docker compose -p event-sources -f docker-compose.event-sources.yml stop
docker compose -p event-sources -f docker-compose.event-sources.yml down
```

`down` keeps their settings. Adding `-v` deletes them as well.
