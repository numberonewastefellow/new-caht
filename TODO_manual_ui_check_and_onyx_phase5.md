# TODO: manual UI check + Phase 5 of the "zero onyx" cleanup

Status as of 2026-10-25. Phases 0 to 4 and the fresh-install fix are committed and pushed
(`43c112030`, `eb6902e66`, `1ab9358bd`, `75a769a7e`). Evidence for every step is in `rename-audit/`
(`PHASE2_LOG.md`, `PHASE3_LOG.md`, `PHASE4_LOG.md`, `FRESH_INSTALL_LOG.md`, `DECISIONS.md`).

There are two parts:

* **Part 1: manual UI check (about 20 minutes, do this first).** Automated tests cannot judge how a page
  looks, and they cannot use your LLM provider keys. This list is what only a person can verify.
* **Part 2: Phase 5 (stored values).** Not started. It touches live data, so it needs its own plan,
  backup and sign-off before any change.

---

## Part 1: manual UI check

### 0. Before you start (2 minutes)

- Stack must be up: `docker ps` shows the `virtualai-*` containers healthy. App is at **http://localhost:3000**.
- Use a normal browser window plus **one private/incognito window** (the incognito one is your "new visitor" test).
- Open the browser dev tools Console (F12) on the first few pages. Normal noise you can ignore:
  1. `Refused to load the stylesheet 'https://fonts.googleapis.com/...'` (the site's own security policy blocks Google Fonts; it was like this before).
  2. A `400` on `/api/converse/max-selected-document-tokens` only if no default LLM is configured.
- Anything else red in the Console on a page is worth a screenshot.
- Note for every problem: the page URL, what you did, a screenshot. A short list is enough; paste it to me.

**What changed that could look wrong (so you know what you are hunting for):**

| Change | What could break visually |
|---|---|
| Phase 1: colour tokens `--onyx-ink-*` and `--onyx-chrome-*` became `--om-*` | wrong or missing colours, text invisible in dark mode |
| Phase 1: logo files `onyx-logo` and `onyx-octagon` became `om-logo` and `om-octagon`, favicon `onyx.ico` became `om.ico` | missing logo or broken image icon |
| Phase 1: UI text "Onyx" became "VertualAI" | odd wording, "VertualAI" in a place that should say something else |
| Phase 1: element ids like `onyx-chat-input` became `om-chat-input` | chat box or send button not working |
| Phase 1: browser-storage keys `onyx:hide...` and `onyx-scroll-` became `om:...` | a popup you dismissed before shows once more (harmless) |
| Phase 2: Slack/Discord bot code moved to `ombot` | bot admin pages empty, or bot status wrong |
| Phase 3: database column `onyxbot_flow` became `ombot_flow` | chat history or query history fails to load |
| Phase 4: API-key constants renamed (values unchanged) | creating or using an API key fails |

### 1. Sign-in screens (public pages, use the incognito window)

| # | URL | Check |
|---|---|---|
| 1.1 | `/auth/login` | Tab title is **VertualAI**. Logo shows (no broken-image icon). Favicon in the tab is shown. Page contains the word "Onyx" **nowhere**. |
| 1.2 | `/auth/signup` | Same as above. Fields (email, password) are usable. |
| 1.3 | Log in with your normal admin user | You land on `/app` (chat home). No error toast. |
| 1.4 | Log out, log in again | Works both times. (Session cookies were not renamed in Phases 1 to 4, so you should NOT be logged out unexpectedly.) |

### 2. Themes: light, dark, accents (5 minutes, most likely place for a visual bug)

Where: **`/app/settings/general`** (user settings; the theme and accent chooser is in `SettingsPage`). Workspace-wide branding is
at **`/admin/theme`**.

For **each** of the 4 accents (**Default, Ocean, Emerald, Violet**) in **both** Light and Dark:

1. Choose it in `/app/settings/general`.
2. Look at, in this order: `/app` (chat home), `/app/settings/general`, `/admin/settings`, `/admin/performance/analytics` (charts use the accent).
3. Check:
   - Headings and body text are readable (no near-black text on dark background, no near-white on white).
   - Buttons, links and highlighted items use the accent colour; none are blank, black or transparent.
   - Sidebar background and the chat input area have a visible border or contrast.
   - The "VertualAI" gradient text (if you see it) is readable in dark mode at both ends of the gradient.
4. Fail signs: a block that is pure black or pure white by mistake, text you cannot see, an element with no colour at all.

Also open **`/admin/theme`** and check the preview panel shows your logo or the default icon (not a broken image).

### 3. Chat (needs a real LLM; this is the part I could not test)

Pre-requisite: an LLM provider is configured at **`/admin/configuration/llm`** (open that page first and check it lists your provider
and a default model; this is also where the "No default LLM model found" 400 comes from if nothing is set).

| # | Where | Do | Expected |
|---|---|---|---|
| 3.1 | `/app` | Type a message in the chat box, press Enter (also try the send button). | Reply streams in. Your message and the reply both appear. |
| 3.2 | same | Send 2 or 3 more messages in the same chat. | Conversation keeps going, scroll works, nothing duplicates. |
| 3.3 | sidebar | Open **Chat history** (list of past chats). Click an older chat (you have 368 stored). | It opens with messages. This exercises `ombot_flow` (Phase 3). |
| 3.4 | same | Rename a chat, delete a chat. | Both work. |
| 3.5 | `/app` | Use the agent picker to choose a different agent, ask a question. | Reply comes from that agent. |
| 3.6 | `/app` | Ask something that needs your documents (search). | Answer with citations; clicking a citation opens the document viewer. |
| 3.7 | chat | Click **Share** on a chat, open the share link in the incognito window (`/app/shared/<id>`). | The shared chat is readable. (The public chat page was touched in Phase 1.) |
| 3.8 | chat | Dismiss any popup (for example "Move custom agent"). Reload. | May appear once more (storage key renamed), then stays dismissed after you close it again. |

### 4. Agents

| # | URL | Check |
|---|---|---|
| 4.1 | `/app/agents` | Agent list loads (you have many). Cards show images and names. |
| 4.2 | `/app/agents/create` | Form opens; you can fill name and prompt; **Save** works (create a throwaway agent, then delete it). |
| 4.3 | `/app/agents/edit/<id>` (click edit on one) | Form loads with existing values. Do not need to save. |
| 4.4 | `/admin/assistants` | Admin agent list loads, drag handles or toggles work. |
| 4.5 | `/admin/configuration/default-assistant` | Page loads; toggles render. |

### 5. Workflows (both editors must stay in sync, per CLAUDE.md)

| # | URL | Check |
|---|---|---|
| 5.1 | `/app/workflows` | Workflow list loads. |
| 5.2 | `/admin/workflows` | Admin workflow list loads. |
| 5.3 | `/admin/workflows/create` (wizard editor) | Opens; steps and fields render; go through the steps without saving. |
| 5.4 | `/admin/workflows/visual` (visual builder) | Canvas opens; drag a node; open a node's config panel. Both editors must look usable. |
| 5.5 | Open one existing workflow (for example Insurance Claims) in the visual builder | Graph appears with all nodes and edges. |
| 5.6 | Run a small workflow from `/app/workflows` | It starts; trace graph panel shows (the trace component was touched in Phase 1). |

### 6. Admin pages (open each, confirm it loads, no red error banner)

Settings and configuration:

| URL | Look for |
|---|---|
| `/admin/settings` | Page loads. **"VertualAI Craft (Sandbox)"** text appears instead of "Onyx Craft" (renamed prose). Toggles render. |
| `/admin/app-settings` | Loads. |
| `/admin/configuration/llm` | Providers listed; **do not change** keys. |
| `/admin/configuration/search` | Loads. |
| `/admin/configuration/web-search` | Provider list shows the built-in crawler entry (stored value `onyx_web_crawler` intentionally unchanged; the label should read sensibly). |
| `/admin/configuration/document-processing` | Loads. |
| `/admin/configuration/image-generation` | Loads. |
| `/admin/embeddings` | Loads; current embedding model shown. |
| `/admin/document-index-migration` | Loads. |
| `/admin/theme` | See section 2. |

Bots (renamed `onyxbot` to `ombot`, Phase 2):

| URL | Look for |
|---|---|
| `/admin/bots` | Slack bot list loads. Text mentions VertualAI, not Onyx or Danswer. |
| `/admin/bots/new` | Creation form opens (do not save). |
| `/admin/discord-bot` | Page loads; shows "dormant / waiting for token" or your config. |

Data and indexing:

| URL | Look for |
|---|---|
| `/admin/indexing/status` | Connector list loads. |
| `/admin/add-connector` | Connector gallery shows icons for all sources (no broken images). |
| `/admin/documents/sets` and `/admin/documents/explorer` and `/admin/documents/feedback` | All load. |
| `/admin/kg` | Loads. |

People and access:

| URL | Look for |
|---|---|
| `/admin/users` | User list (you have 7). |
| `/admin/teams` and open one team | Team detail page loads (Phase 1/UserGroup to Team earlier). |
| `/admin/roles` and `/admin/rate-limits` and `/admin/scim` | Load. |
| `/admin/api-key` | List loads. **Create a test key, copy it, then delete it.** Test it: `curl -H "Authorization: Bearer <key>" http://localhost:3000/api/admin/agent` should return JSON (Phase 4 touched API-key constants). |

Tools and monitoring:

| URL | Look for |
|---|---|
| `/admin/actions/mcp` and `/admin/actions/open-api` | Load. For MCP, start the OAuth flow of a test server only if you use one (callback route was renamed to read `NEXT_PUBLIC_OM_BACKEND_URL`; unset means same-origin, as before). |
| `/admin/performance/analytics` | Charts render in the accent colour. |
| `/admin/performance/query-log` | Query history list loads, includes your new chat from 3.1. Open one entry. **Filter by "Slack" type if offered** (this reads `ombot_flow`). |
| `/admin/performance/reports` | Loads. |
| `/admin/systeminfo` and `/admin/debug` | Load. |

### 7. User settings

`/app/settings/general`, `/app/settings/chat-preferences`, `/app/settings/accounts-access`, `/app/settings/connectors`: each opens, saves a harmless change if you try one, and shows no leftover "Onyx" wording.

### 8. Other places

* `/app/workspaces` : workspaces list loads (Project to Workspace rename from earlier).
* `/craft` (if enabled in `/admin/settings`): loads without error.
* Browser tab titles everywhere say **VertualAI**.

### 9. Optional: Slack or Discord bot, if you actually use them

Post a message to the bot in Slack or Discord. It should answer. Then open `/admin/performance/query-log` and confirm the
conversation shows with the Slack type. If you do not use bots, skip this.

### 10. When you are done

* If everything passes: tell me "UI check passed" and I mark Phases 1 to 4 fully verified in `rename-audit/DECISIONS.md`.
* If something fails: send URL + screenshot + (if possible) the browser Console text. I fix it before Phase 5.
* Fastest rollback if something is badly broken: images tagged `om/om-backend:phase3-rollback` and `phase2-rollback` exist; DB dumps are in
  `E:\temp\vert_backup_pre_onyx_removal_20261024\` (`postgres_full.dump`, `postgres_pre_phase3_20261024.dump`).

---

## Part 2: Phase 5 (stored values). NOT STARTED

Why it is separate: these strings live inside data (database rows, Redis, files in object storage, browser cookies, installed clients).
Renaming the code constant without migrating the data breaks existing users, tokens or files. Each item needs: what exists today,
how many rows, a migration, a rollback, and a test.

### 2.1 What must happen before any change

1. **Do Part 1 and tell me the result.** Phase 5 starts from a verified base.
2. **Fresh backup** (I do it, but confirm disk space): `pg_dump`, a copy of MinIO data, `E:\temp\vert\*` folders. Old backup is from 2026-10-24.
3. **Decide per item** below: RENAME (with migration) / ACCEPT BOTH for a while / KEEP and document. I will bring a recommendation
   for each; you approve before I touch anything.
4. Work **one item at a time**: backup, change, test, deploy, 24 hours of watching if it is a login/token/file item, commit.

### 2.2 Inventory and my recommendation

Live numbers come from the probes on 2026-10-24 (`rename-audit/live_data_probes.sql` and `.sh`; re-run them first).

| # | Value | Where stored | Live impact today | Recommended approach |
|---|---|---|---|---|
| 1 | KV keys `onyx_settings`, `onyx_enterprise_settings` | `key_value_store` table (3 rows) | Settings and enterprise settings would reset to defaults if renamed blindly | Migration: copy row to the new key, read new key first, fall back to old for one release, then drop the old |
| 2 | Settings field `onyx_craft_enabled` (JSON inside those rows, also in API and web) | KV JSON + `/api/settings` + web `SettingsForm` | Craft toggle would reset | Rename in API and web together; accept both names when reading stored JSON |
| 3 | Web content provider type value `onyx_web_crawler` | `web_search/content provider` rows + web UI | Provider config would be ignored | Data migration `UPDATE ... SET provider_type`, rename enum and web together |
| 4 | Confluence group name `All_Confluence_Users_Found_By_Onyx` | external group rows (permission sync) | Permission sync would create a second group | Migration to rename the stored group, or keep (it is only a label) |
| 5 | Personal access token prefix `onyx_pat_` | issued tokens (live count: 0) | None today (no PATs exist) | Safe to rename now; still accept both prefixes for future compatibility |
| 6 | API-key synthetic email domain `onyxapikey.ai`, prefix `API_KEY__` | `user.email` rows (live count: 0) | None today | Safe to rename now; migration `UPDATE` for any rows |
| 7 | Cookies `onyx_tid`, `onyx_anonymous_user` | users' browsers | Everyone logged out / anonymous sessions lost once | Rename backend and web together; accept both on read for a week; announce re-login |
| 8 | Redis prefixes `onyx:`, `onyx_kv_store:`, `da_function_lock:`, heartbeat key | Redis (ephemeral; live scan found 0 `onyx*` keys) | Locks reset once | Plain rename; flush on deploy |
| 9 | S3 prefix `onyx-files` and bucket `onyx-file-store-bucket` | **1,718 file objects in MinIO** | Files become unreachable if the prefix changes | Highest risk: copy objects to the new prefix, flip config, verify download of sample files, keep the old copy until verified |
| 10 | `.onyx_metadata.json` file name and `ONYX_METADATA` marker | user-uploaded zips and documents | Existing metadata files silently ignored | Accept both names permanently (cannot migrate users' files) |
| 11 | Sandbox namespace `onyx-sandboxes`, label `managed-by: onyx`, local dir `~/.onyx` | Kubernetes / local disk | Running sandboxes orphaned | Rename with a one-time cleanup; only matters if Craft is used |
| 12 | HTTP headers `X-Onyx-Tenant-ID`, `X-Onyx-Request-ID`, `X-Onyx-Authorization` | clients, nginx, logs | External API clients break | Accept both, emit new; check nginx and any scripts first |
| 13 | Prometheus metric names `onyx_*` | Grafana dashboards, alerts | Dashboards go blank | Rename together with dashboard JSON; confirm you actually use Grafana first |
| 14 | PostHog property `onyx_cloud_user_id`, UTM `onyx_app`, feature flag `onyx-craft-enabled` | external analytics | Analytics history splits | Probably KEEP (external system) unless you use PostHog |
| 15 | Route prefix `/onyx-api/ingestion` | external ingestion clients | External callers get 404 | Serve both paths for a while, then retire the old |

### 2.3 Phase 6 and 7 (later, each needs its own plan)

* **Phase 6, infrastructure:** compose volume names `onyx-stack_*` and project name (renaming means a new empty volume: needs a copy
  runbook), helm chart folder `charts/onyx` and resource names, ECS/CloudFormation templates, terraform module. Your running
  stack stores data in `E:\temp\vert\*` bind mounts, so it is less exposed than a fresh deployment from these files.
* **Phase 7, external references:** URLs to `github.com/onyx-dot-app`, `onyx.app` addresses, `ONYX_GITHUB_*` CI secrets (must be renamed
  in the GitHub repo settings at the same time as the workflows), browser extension, widget and desktop app identities, license
  attribution in `NOTICE.md` and `README.md` (legally required, probably stays).

### 2.4 Known follow-ups found along the way (not Phase 5, but do not forget)

* The API container started before Postgres finished recovery after the machine restart and retried 6 times. Make the compose file wait for
  the database to be healthy (`depends_on: condition: service_healthy`).
* A fresh install has no LLM provider; the UI logs a 400 until one is added. Consider a first-run hint.
* `rename-audit/DECISIONS.md` still lists items as drafts; I update it after you report the UI check.
* 19 backend unit tests fail (pre-existing: websearch utils, censoring, chat utils, llm reasoning, connector factory). Unrelated to the
  rename but worth a ticket.
* `next lint` and eslint do not run in this repo; `.eslintrc.json` needs migrating to the new flat config.

### 2.5 Definition of done for the whole "zero onyx" effort

`git grep -iE "onyx|danswer"` returns only: NOTICE/LICENSE attribution you chose to keep, the `rename-audit` history documents, and any
value deliberately kept and listed in `DECISIONS.md` with a reason.
