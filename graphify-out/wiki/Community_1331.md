# Community 1331

> 7 nodes · cohesion 0.33

## Key Concepts

- **kombu_message_cleanup_task()** (5 connections) — `backend/om/background/celery/tasks/periodic/tasks.py`
- **kombu_message_cleanup_task_helper()** (4 connections) — `backend/om/background/celery/tasks/periodic/tasks.py`
- **tasks.py** (3 connections) — `backend/om/background/celery/tasks/periodic/tasks.py`
- **Any** (1 connections) — `backend/om/background/celery/tasks/periodic/tasks.py`
- **Session** (1 connections) — `backend/om/background/celery/tasks/periodic/tasks.py`
- **Runs periodically to clean up the kombu_message table** (1 connections) — `backend/om/background/celery/tasks/periodic/tasks.py`
- **Helper function to clean up old messages from the `kombu_message` table that are** (1 connections) — `backend/om/background/celery/tasks/periodic/tasks.py`

## Relationships

- [[Community 106]] (1 shared connections)
- [[Backend Agent/API Test Fixtures]] (1 shared connections)

## Source Files

- `backend/om/background/celery/tasks/periodic/tasks.py`

## Audit Trail

- EXTRACTED: 15 (94%)
- INFERRED: 1 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*