import type { HelpContent, HelpRow } from "@/components/admin/HelpDialog";
import { curlExample, DEFAULT_SECRET_HEADER } from "@/lib/schedules/webhooks";

/** Everything the admin pages say about webhooks, so the two pages can't disagree. */

export const WEBHOOKS_PAGE = "/app/schedules?tab=webhooks";
export const PULSE_HEALTH_URL = "/api/admin/pulse/health";

export const WEBHOOK_SETUP_STEPS: string[] = [
  "Open Schedules, then the Webhooks tab, and press New webhook.",
  "Pick the workflow and write what it should receive.",
  "Copy the URL and secret straight away. They're only shown once.",
  "Press Listen, then Send test event. Nothing runs.",
];

const EXAMPLE_BODY = '{"event":{"id":"evt-1"},"ticket":{"title":"Water leak on MG Road"}}';

const POWERSHELL_EXAMPLE = [
  '$url = "YOUR_WEBHOOK_URL"',
  '$secret = "YOUR_SECRET"',
  `$body = '${EXAMPLE_BODY}'`,
  `Invoke-RestMethod -Method Post -Uri $url -Headers @{ "${DEFAULT_SECRET_HEADER}" = $secret } -ContentType "application/json" -Body $body`,
].join("\n");

export const WEBHOOK_FEATURE_HELP: HelpContent = {
  title: "Webhook triggers",
  summary: "Start a workflow the moment something happens in another system.",
  sections: [
    {
      title: "What it's for",
      text: "Another system, such as a citizen portal or a ticketing tool, calls a private URL when something happens. Pulse then runs your workflow with the data it sent. Each run becomes its own chat, and it runs in the background with nobody watching.",
    },
    {
      title: "Webhook or schedule?",
      rows: [
        { name: "Schedule", detail: "The time matters: a report every Monday at 9 am. Pulse starts it, with input you wrote." },
        { name: "Webhook", detail: "An event matters: a complaint was just filed. The other system starts it, with data it sent." },
      ],
    },
    {
      title: "Set it up",
      steps: [
        "Open Schedules, then the Webhooks tab, and press New webhook.",
        "Workflow: choose the one to run. You need access to it.",
        "What the workflow receives: write the message. {{payload}} is the whole event, {{payload.ticket.title}} or {{payload.items[0]}} is one value, and {{date}} and {{now}} give the time.",
        "How the caller proves itself: use Signed (Standard Webhooks) if the other system can sign requests. Use Secret in a header only if it can't, because that mode doesn't protect the data or stop replays.",
        "What makes an event a repeat: systems often retry, and a repeat doesn't run again. Choose the webhook-id header when signed, or a field in the body such as event.id.",
        "Copy the URL and secret straight away. They're only shown once. If you lose them, press Rotate to get new ones.",
        "Give both to the other system. It has to reach this server's address, so localhost only works for trying it on the same machine.",
      ],
    },
    {
      title: "Test it safely",
      text: "On the webhook's page, press Listen, then Send test event, or call the test URL (/api/hooks/test/...). You'll see what arrived and exactly what the workflow would receive. Nothing runs, and it closes by itself after 5 minutes.",
    },
    {
      title: "Send a real event",
      text: "These are for a webhook that uses a secret header, which is the easiest to call by hand. For a signed webhook, the dialog shown after creating it has a ready-made command that signs the request.",
      code: [
        { label: "PowerShell", command: POWERSHELL_EXAMPLE },
        {
          label: "Bash",
          command: curlExample({
            url: "YOUR_WEBHOOK_URL",
            authMode: "header_token",
            headerName: DEFAULT_SECRET_HEADER,
            secret: "YOUR_SECRET",
          }),
        },
      ],
      note: "You get back a run_id. The run then appears on the webhook's page, with a link to its chat.",
    },
    {
      title: "What the caller gets back",
      rows: [
        { name: "202", detail: "Accepted. The reply has run_id, and duplicate: true for a repeat. Don't retry." },
        { name: "400", detail: "The body isn't acceptable JSON. Don't retry." },
        { name: "401", detail: "The signature or secret is wrong, or the timestamp is too old. Don't retry." },
        { name: "404", detail: "Unknown, paused, revoked, or webhooks are off. Don't retry." },
        { name: "409", detail: "The test URL was called while Listen is closed. Don't retry." },
        { name: "413", detail: "The body is over 1 MB. Don't retry." },
        { name: "429", detail: "Too many calls or too many runs waiting. Retry after the time in Retry-After." },
        { name: "503", detail: "Redis is down. Retry after the time in Retry-After." },
      ],
      note: "If a call was refused, the webhook's page shows why, such as \"Signature does not match\".",
    },
    {
      title: "Stop it",
      rows: [
        { name: "Pause", detail: "Switch it off. Calls are refused until you turn it back on. Runs still waiting are skipped when a worker reaches them, and don't come back." },
        { name: "Rotate", detail: "Get a new URL and secret. You choose how long the old ones keep working, so you can update the other system first." },
        { name: "Revoke", detail: "Use this if the URL or secret may have leaked. They stop working immediately, and runs still waiting won't start." },
        { name: "Delete", detail: "Removes the webhook and its run history. Chats from earlier runs stay." },
        { name: "Allow webhooks", detail: "Admin > Workspace > General. Turns every webhook off at once. Existing webhooks are kept." },
      ],
      note: "Admins can see every webhook under Admin > Pulse > Webhooks. They can pause or revoke one, but only its owner can rotate it, because new credentials would let someone start runs as the owner.",
    },
    {
      title: "Before you rely on it",
      text: "Runs use the owner's access: their documents, files and connected accounts. The data a system sends is marked for the AI as data rather than instructions, but that can't fully prevent an instruction hidden in it from being followed. So check which tools the workflow can use, especially ones that send or change things.",
      note: "Event data kept with each run is cleared after 7 days, but the text the workflow received stays in that run's chat. After 5 failed runs in a row a webhook pauses itself and notifies its owner.",
    },
  ],
};

const WEBHOOK_SETTINGS: HelpRow[] = [
  { name: "PULSE_WEBHOOK_WORKER_CONCURRENCY", value: "2", detail: "Runs at once per webhook worker." },
  { name: "PULSE_WEBHOOK_RATE_PER_IP", value: "300", detail: "Requests per minute per address." },
  { name: "PULSE_WEBHOOK_RATE_PER_TOKEN", value: "120", detail: "Requests per minute per webhook URL." },
  { name: "PULSE_WEBHOOK_PROXY_HOPS", value: "1", detail: "Proxies adding to X-Forwarded-For in front of the API. Too high lets callers choose their own rate-limit bucket; too low puts all callers in one." },
  { name: "PULSE_WEBHOOK_MAX_PENDING_RUNS", value: "20", detail: "Runs waiting per webhook before callers get 429." },
  { name: "PULSE_WEBHOOK_TENANT_MAX_ACTIVE_RUNS", value: "100", detail: "Active webhook runs per tenant. Approximate: it can overshoot slightly." },
  { name: "PULSE_MAX_WEBHOOKS_PER_USER", value: "20", detail: "Webhooks per owner." },
  { name: "PULSE_WEBHOOK_MAX_BODY_BYTES", value: "1048576", detail: "Largest body accepted. nginx has its own 1 MB limit on /api/hooks/, so keep the two in step." },
  { name: "PULSE_WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS", value: "300", detail: "Allowed clock difference on signatures." },
  { name: "PULSE_WEBHOOK_PAYLOAD_RETENTION_DAYS", value: "7", detail: "How long event data is kept with each run." },
  { name: "PULSE_WEBHOOK_LISTEN_TTL_SECONDS", value: "300", detail: "How long Listen stays open." },
];

export const WEBHOOK_SERVICE_HELP: HelpContent = {
  title: "Pulse Webhook Worker",
  summary: "Runs the workflows started by webhooks, separately from scheduled runs.",
  sections: [
    {
      title: "What it does",
      text: "A call arrives at nginx, which refuses bodies over 1 MB and hides the URL in its logs. The API server checks it, stores it as a waiting run and puts it on the pulse_webhook queue. This worker takes it from there and runs the workflow. It uses the same image as Pulse Worker, with PULSE_WORKER_QUEUE=pulse_webhook.",
      note: "It's separate so that a burst of webhook calls can only delay other webhook runs, never your schedules. Without this service, calls are still accepted, but their runs wait and never start.",
    },
    {
      title: "Start and scale",
      text: "Run these from deployment/docker_compose. They're for the default compose file: add the same -f options you start the stack with, especially for nginx, because production uses a different nginx template.",
      code: [
        { label: "Start it", command: "docker compose up -d pulse_webhook_worker" },
        { label: "Run more of them", command: "docker compose up -d --scale pulse_webhook_worker=2 pulse_webhook_worker" },
        { label: "Apply nginx limits and log redaction after an upgrade", command: "docker compose up -d --force-recreate nginx" },
      ],
    },
    {
      title: "Settings",
      text: "Set these in the .env file in deployment/docker_compose, then recreate the service that reads the setting.",
      rows: WEBHOOK_SETTINGS,
      note: "PULSE_WEBHOOK_WORKER_CONCURRENCY is read by pulse_webhook_worker, PULSE_WEBHOOK_PAYLOAD_RETENTION_DAYS by pulse_scheduler, and the others by api_server.",
    },
    {
      title: "Security settings",
      rows: [
        { name: "Allow webhooks", value: "on", detail: "Admin > Workspace > General. When off, every webhook URL returns 404 and no new ones can be created." },
        { name: "ENCRYPTION_KEY_SECRET", detail: "Webhook secrets are only encrypted when this is set. Without it they're stored as plaintext, like every other stored credential. Setting it on a running system makes existing values unreadable unless they're migrated, so plan that as its own job." },
      ],
    },
    {
      title: "Check its health",
      rows: [
        { name: `GET ${PULSE_HEALTH_URL}`, detail: "The main check. Open it in your browser as an admin. The fields are explained below." },
        { name: "GET /api/heartbeat", detail: "The API server is up. Says nothing about this worker." },
        { name: "docker compose ps pulse_webhook_worker", detail: "Shows healthy once the worker has started. It reports on the container, not on whether runs are moving." },
        { name: "pulse_webhook_events_total", detail: "Prometheus counter of calls by result, at /api/metrics, which needs no login. Each API process keeps its own count (API_SERVER_WORKERS, 4 by default) and a scrape reaches only one, so use it for trends, not exact totals." },
      ],
    },
    {
      title: "Reading the health response",
      rows: [
        { name: "webhooks.workers_alive", value: "1 or more", detail: "Workers taking new runs. 0 means none, so runs will wait. A worker that's stopping stops counting at once while it finishes its current runs. One that crashes can take up to 90 seconds to drop off. null means Redis couldn't be read, not that there are none." },
        { name: "webhooks.pending_runs", detail: "Runs waiting for a worker. Short spikes are normal." },
        { name: "webhooks.oldest_pending_seconds", value: "stays low", detail: "How long the oldest run has waited. A number that keeps growing means runs are stuck. null means nothing is waiting." },
        { name: "webhooks.running_runs", detail: "Runs in progress." },
        { name: "webhooks.active_webhooks", detail: "Webhooks that are switched on and not revoked." },
        { name: "webhooks.enabled", value: "true", detail: "The Allow webhooks switch. false means every call gets 404. null means it couldn't be read, and calls get 503." },
        { name: "webhooks.secret_encryption_configured", value: "true", detail: "false means ENCRYPTION_KEY_SECRET isn't set." },
      ],
    },
    {
      title: "If something's wrong",
      rows: [
        { name: "workers_alive is 0", detail: "Start the service, then read its logs with docker compose logs pulse_webhook_worker. Runs that were waiting start once it's back." },
        { name: "Oldest wait keeps growing", detail: "If workers are alive, they're busy. Raise PULSE_WEBHOOK_WORKER_CONCURRENCY or run more of them." },
        { name: "Callers get 404", detail: "The webhook is paused or revoked, or Allow webhooks is off. Check webhooks.enabled and the webhook's page." },
        { name: "Callers get 429", detail: "Over a rate limit, or too many runs waiting. Check pending_runs and the settings above." },
        { name: "Callers get 503", detail: "Redis is down, or the switch couldn't be read. Webhooks refuse calls rather than drop their limits." },
      ],
    },
    {
      title: "Not supported yet",
      text: "The Helm chart doesn't include this worker or the nginx limits, so webhooks won't work on Kubernetes until both are added.",
    },
  ],
};
