# Community 522

> 29 nodes · cohesion 0.13

## Key Concepts

- **tasks.py** (12 connections) — `backend/om/db/tasks.py`
- **Session** (11 connections) — `backend/om/db/tasks.py`
- **perform_ttl_management_task()** (9 connections) — `backend/om/background/celery/tasks/ttl_management/tasks.py`
- **TaskQueueState** (6 connections) — `backend/om/db/tasks.py`
- **should_perform_chat_ttl_check()** (6 connections) — `backend/om/background/celery_utils.py`
- **get_latest_task()** (6 connections) — `backend/om/db/tasks.py`
- **register_task()** (6 connections) — `backend/om/db/tasks.py`
- **check_task_is_live_and_not_timed_out()** (5 connections) — `backend/om/db/tasks.py`
- **get_task_with_id()** (5 connections) — `backend/om/db/tasks.py`
- **mark_task_as_finished_with_id()** (5 connections) — `backend/om/db/tasks.py`
- **check_ttl_management_task()** (5 connections) — `backend/om/background/celery/tasks/ttl_management/tasks.py`
- **mark_task_as_started_with_id()** (4 connections) — `backend/om/db/tasks.py`
- **task_name_builders.py** (3 connections) — `backend/om/background/task_name_builders.py`
- **name_chat_ttl_task()** (3 connections) — `backend/om/background/task_name_builders.py`
- **get_all_tasks_with_prefix()** (3 connections) — `backend/om/db/tasks.py`
- **get_latest_task_by_type()** (3 connections) — `backend/om/db/tasks.py`
- **mark_task_finished()** (3 connections) — `backend/om/db/tasks.py`
- **mark_task_start()** (3 connections) — `backend/om/db/tasks.py`
- **datetime** (2 connections) — `backend/om/background/task_name_builders.py`
- **datetime** (2 connections) — `backend/om/db/tasks.py`
- **celery_utils.py** (2 connections) — `backend/om/background/celery_utils.py`
- **query_history_task_name()** (2 connections) — `backend/om/background/task_name_builders.py`
- **delete_task_with_id()** (2 connections) — `backend/om/db/tasks.py`
- **tasks.py** (2 connections) — `backend/om/background/celery/tasks/ttl_management/tasks.py`
- **Task** (1 connections) — `backend/om/background/celery/tasks/ttl_management/tasks.py`
- *... and 4 more nodes in this community*

## Relationships

- [[Salesforce Connector]] (3 shared connections)
- [[Backend Agent/API Test Fixtures]] (2 shared connections)
- [[Community 62]] (2 shared connections)
- [[Community 256]] (1 shared connections)
- [[Community 161]] (1 shared connections)

## Source Files

- `backend/om/background/celery/tasks/ttl_management/tasks.py`
- `backend/om/background/celery_utils.py`
- `backend/om/background/task_name_builders.py`
- `backend/om/db/tasks.py`

## Audit Trail

- EXTRACTED: 92 (80%)
- INFERRED: 23 (20%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*