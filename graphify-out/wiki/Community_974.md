# Community 974

> 13 nodes · cohesion 0.17

## Key Concepts

- **PoolStateCollector** (11 connections) — `backend/om/server/metrics/postgres_connection_pool.py`
- **GaugeMetricFamily** (3 connections) — `backend/om/server/metrics/postgres_connection_pool.py`
- **.add_pool()** (3 connections) — `backend/om/server/metrics/postgres_connection_pool.py`
- **test_pool_state_collector_handles_multiple_engines()** (3 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **test_pool_state_collector_reports_pool_stats()** (3 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **.collect()** (2 connections) — `backend/om/server/metrics/postgres_connection_pool.py`
- **.describe()** (2 connections) — `backend/om/server/metrics/postgres_connection_pool.py`
- **QueuePool** (2 connections) — `backend/om/server/metrics/postgres_connection_pool.py`
- **Collector** (1 connections)
- **.__init__()** (1 connections) — `backend/om/server/metrics/postgres_connection_pool.py`
- **Custom Prometheus collector that reads QueuePool state on each scrape.      Uses** (1 connections) — `backend/om/server/metrics/postgres_connection_pool.py`
- **Verify the custom collector reads pool.checkedout/checkedin/overflow/size.** (1 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`
- **Verify the collector reports metrics for multiple engines.** (1 connections) — `backend/tests/unit/om/server/test_pool_metrics.py`

## Relationships

- [[Community 91]] (3 shared connections)
- [[Community 1131]] (3 shared connections)
- [[Community 1062]] (2 shared connections)

## Source Files

- `backend/om/server/metrics/postgres_connection_pool.py`
- `backend/tests/unit/om/server/test_pool_metrics.py`

## Audit Trail

- EXTRACTED: 27 (79%)
- INFERRED: 7 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*