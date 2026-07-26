# Community 503

> 30 nodes · cohesion 0.16

## Key Concepts

- **input_prompt.py** (10 connections) — `backend/om/db/input_prompt.py`
- **Session** (8 connections) — `backend/om/db/input_prompt.py`
- **Session** (7 connections) — `backend/om/server/features/input_prompt/api.py`
- **User** (7 connections) — `backend/om/server/features/input_prompt/api.py`
- **update_input_prompt()** (7 connections) — `backend/om/db/input_prompt.py`
- **api.py** (7 connections) — `backend/om/server/features/input_prompt/api.py`
- **create_input_prompt()** (7 connections) — `backend/om/server/features/input_prompt/api.py`
- **patch_input_prompt()** (7 connections) — `backend/om/server/features/input_prompt/api.py`
- **InputPrompt** (6 connections) — `backend/om/db/input_prompt.py`
- **disable_input_prompt_for_user()** (6 connections) — `backend/om/db/input_prompt.py`
- **fetch_input_prompt_by_id()** (6 connections) — `backend/om/db/input_prompt.py`
- **fetch_input_prompts_by_user()** (6 connections) — `backend/om/db/input_prompt.py`
- **insert_input_prompt()** (6 connections) — `backend/om/db/input_prompt.py`
- **remove_input_prompt()** (6 connections) — `backend/om/db/input_prompt.py`
- **validate_user_prompt_authorization()** (5 connections) — `backend/om/db/input_prompt.py`
- **delete_input_prompt()** (5 connections) — `backend/om/server/features/input_prompt/api.py`
- **delete_public_input_prompt()** (5 connections) — `backend/om/server/features/input_prompt/api.py`
- **get_input_prompt()** (5 connections) — `backend/om/server/features/input_prompt/api.py`
- **hide_input_prompt_for_user()** (5 connections) — `backend/om/server/features/input_prompt/api.py`
- **list_input_prompts()** (5 connections) — `backend/om/server/features/input_prompt/api.py`
- **User** (4 connections) — `backend/om/db/input_prompt.py`
- **UUID** (4 connections) — `backend/om/db/input_prompt.py`
- **remove_public_input_prompt()** (4 connections) — `backend/om/db/input_prompt.py`
- **InputPromptSnapshot** (4 connections) — `backend/om/server/features/input_prompt/api.py`
- **fetch_public_input_prompts()** (3 connections) — `backend/om/db/input_prompt.py`
- *... and 5 more nodes in this community*

## Relationships

- [[Community 103]] (8 shared connections)
- [[User Roles & Agent Config]] (2 shared connections)

## Source Files

- `backend/om/db/input_prompt.py`
- `backend/om/server/features/input_prompt/api.py`

## Audit Trail

- EXTRACTED: 126 (84%)
- INFERRED: 24 (16%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*