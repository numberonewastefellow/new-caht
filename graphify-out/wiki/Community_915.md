# Community 915

> 14 nodes · cohesion 0.21

## Key Concepts

- **handle_google_drive_oauth_callback()** (10 connections) — `backend/om/server/oauth/google_drive.py`
- **get_google_creds()** (9 connections) — `backend/om/connectors/google_utils/google_auth.py`
- **get_google_oauth_creds()** (7 connections) — `backend/om/connectors/google_utils/google_auth.py`
- **sanitize_oauth_credentials()** (5 connections) — `backend/om/connectors/google_utils/google_auth.py`
- **OAuthCredentials** (4 connections) — `backend/om/connectors/google_utils/google_auth.py`
- **google_auth.py** (4 connections) — `backend/om/connectors/google_utils/google_auth.py`
- **DocumentSource** (3 connections) — `backend/om/connectors/google_utils/google_auth.py`
- **JSONResponse** (3 connections) — `backend/om/server/oauth/google_drive.py`
- **Session** (3 connections) — `backend/om/server/oauth/google_drive.py`
- **User** (3 connections) — `backend/om/server/oauth/google_drive.py`
- **ServiceAccountCredentials** (2 connections) — `backend/om/connectors/google_utils/google_auth.py`
- **we really don't want to be persisting the client id and secret anywhere but the** (1 connections) — `backend/om/connectors/google_utils/google_auth.py`
- **creds_json only needs to contain client_id, client_secret and refresh_token to** (1 connections) — `backend/om/connectors/google_utils/google_auth.py`
- **Checks for two different types of credentials.     (1) A credential which holds** (1 connections) — `backend/om/connectors/google_utils/google_auth.py`

## Relationships

- [[Community 111]] (7 shared connections)
- [[Community 91]] (3 shared connections)
- [[Community 243]] (2 shared connections)
- [[Community 106]] (1 shared connections)
- [[Connector Indexing Types]] (1 shared connections)
- [[Google Drive Connector]] (1 shared connections)
- [[Salesforce Connector]] (1 shared connections)
- [[Community 69]] (1 shared connections)
- [[Community 103]] (1 shared connections)

## Source Files

- `backend/om/connectors/google_utils/google_auth.py`
- `backend/om/server/oauth/google_drive.py`

## Audit Trail

- EXTRACTED: 37 (66%)
- INFERRED: 19 (34%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*