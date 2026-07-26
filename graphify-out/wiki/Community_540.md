# Community 540

> 28 nodes · cohesion 0.11

## Key Concepts

- **SpanCostDetailsCalculator** (20 connections) — `phoenix/src/phoenix/server/cost_tracking/cost_details_calculator.py`
- **TestSpanCostDetailsCalculator** (6 connections) — `phoenix/tests/unit/server/cost_tracking/test_cost_details_calculator.py`
- **.test_calculate_details()** (6 connections) — `phoenix/tests/unit/server/cost_tracking/test_cost_details_calculator.py`
- **.calculate_cost()** (6 connections) — `phoenix/src/phoenix/server/daemons/span_cost_calculator.py`
- **_Cost** (5 connections) — `phoenix/tests/unit/server/cost_tracking/test_cost_details_calculator.py`
- **SpanCostCalculatorQueueItem** (5 connections) — `phoenix/src/phoenix/server/daemons/span_cost_calculator.py`
- **.test_cost_per_token_edge_cases()** (4 connections) — `phoenix/tests/unit/server/cost_tracking/test_cost_details_calculator.py`
- **.test_missing_token_count_section()** (4 connections) — `phoenix/tests/unit/server/cost_tracking/test_cost_details_calculator.py`
- **.__init__()** (4 connections) — `phoenix/src/phoenix/server/daemons/span_cost_calculator.py`
- **datetime** (4 connections) — `phoenix/src/phoenix/server/daemons/span_cost_calculator.py`
- **TokenPrice** (4 connections) — `phoenix/tests/unit/server/cost_tracking/test_cost_details_calculator.py`
- **span_cost_calculator.py** (3 connections) — `phoenix/src/phoenix/server/daemons/span_cost_calculator.py`
- **._insert_costs()** (3 connections) — `phoenix/src/phoenix/server/daemons/span_cost_calculator.py`
- **Any** (3 connections) — `phoenix/src/phoenix/server/daemons/span_cost_calculator.py`
- **DbSessionFactory** (3 connections) — `phoenix/src/phoenix/server/daemons/span_cost_calculator.py`
- **GenerativeModelStore** (3 connections) — `phoenix/src/phoenix/server/daemons/span_cost_calculator.py`
- **SpanCost** (3 connections) — `phoenix/src/phoenix/server/daemons/span_cost_calculator.py`
- **test_cost_details_calculator.py** (2 connections) — `phoenix/tests/unit/server/cost_tracking/test_cost_details_calculator.py`
- **.put_nowait()** (2 connections) — `phoenix/src/phoenix/server/daemons/span_cost_calculator.py`
- **._run()** (2 connections) — `phoenix/src/phoenix/server/daemons/span_cost_calculator.py`
- **Any** (2 connections) — `phoenix/tests/unit/server/cost_tracking/test_cost_details_calculator.py`
- **cost_details_calculator.py** (1 connections) — `phoenix/src/phoenix/server/cost_tracking/cost_details_calculator.py`
- **Calculates detailed cost breakdowns for LLM spans based on token usage and prici** (1 connections) — `phoenix/src/phoenix/server/cost_tracking/cost_details_calculator.py`
- **Represents the expected cost breakdown for a token type in tests.      This na** (1 connections) — `phoenix/tests/unit/server/cost_tracking/test_cost_details_calculator.py`
- **Comprehensive test suite for SpanCostDetailsCalculator.      This test suite c** (1 connections) — `phoenix/tests/unit/server/cost_tracking/test_cost_details_calculator.py`
- *... and 3 more nodes in this community*

## Relationships

- [[Community 66]] (13 shared connections)
- [[Community 314]] (3 shared connections)
- [[Phoenix LDAP Auth Tests]] (2 shared connections)
- [[Phoenix GraphQL Schema]] (1 shared connections)

## Source Files

- `phoenix/src/phoenix/server/cost_tracking/cost_details_calculator.py`
- `phoenix/src/phoenix/server/daemons/span_cost_calculator.py`
- `phoenix/tests/unit/server/cost_tracking/test_cost_details_calculator.py`

## Audit Trail

- EXTRACTED: 64 (63%)
- INFERRED: 37 (37%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*