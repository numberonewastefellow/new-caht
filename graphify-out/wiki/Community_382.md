# Community 382

> 39 nodes · cohesion 0.09

## Key Concepts

- **get_settings_notifications()** (11 connections) — `backend/om/server/settings/api.py`
- **Session** (9 connections) — `backend/om/db/notification.py`
- **notification.py** (9 connections) — `backend/om/db/notification.py`
- **fetch_settings()** (8 connections) — `backend/om/server/settings/api.py`
- **Notification** (7 connections) — `backend/om/db/notification.py`
- **create_notification()** (7 connections) — `backend/om/db/notification.py`
- **get_notifications()** (7 connections) — `backend/om/db/notification.py`
- **get_notifications_api()** (7 connections) — `backend/om/server/features/notifications/api.py`
- **batch_create_notifications()** (6 connections) — `backend/om/db/notification.py`
- **create_release_notifications_for_versions()** (6 connections) — `backend/om/db/release_notes.py`
- **dismiss_notification_endpoint()** (6 connections) — `backend/om/server/features/notifications/api.py`
- **get_notification_by_id()** (5 connections) — `backend/om/db/notification.py`
- **NotificationType** (5 connections) — `backend/om/db/notification.py`
- **UUID** (4 connections) — `backend/om/db/notification.py`
- **dismiss_all_notifications()** (4 connections) — `backend/om/db/notification.py`
- **dismiss_notification()** (4 connections) — `backend/om/db/notification.py`
- **update_notification_last_shown()** (4 connections) — `backend/om/db/notification.py`
- **admin_put_settings()** (4 connections) — `backend/om/server/settings/api.py`
- **User** (3 connections) — `backend/om/db/notification.py`
- **User** (3 connections) — `backend/om/server/settings/api.py`
- **batch_dismiss_notifications()** (3 connections) — `backend/om/db/notification.py`
- **api.py** (3 connections) — `backend/om/server/settings/api.py`
- **ReleaseNoteEntry** (2 connections) — `backend/om/db/release_notes.py`
- **Session** (2 connections) — `backend/om/db/release_notes.py`
- **Session** (2 connections) — `backend/om/server/features/notifications/api.py`
- *... and 14 more nodes in this community*

## Relationships

- [[User Roles & Agent Config]] (7 shared connections)
- [[Community 143]] (2 shared connections)
- [[Community 161]] (2 shared connections)
- [[Community 303]] (2 shared connections)
- [[Community 456]] (1 shared connections)
- [[Community 69]] (1 shared connections)
- [[Community 103]] (1 shared connections)
- [[Community 70]] (1 shared connections)

## Source Files

- `backend/om/db/notification.py`
- `backend/om/db/release_notes.py`
- `backend/om/server/features/notifications/api.py`
- `backend/om/server/settings/api.py`

## Audit Trail

- EXTRACTED: 118 (79%)
- INFERRED: 31 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*