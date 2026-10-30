# Reference study 1: workflow engines (parallel, loops, checkpoints)

Source clones live in `D:/llm/reference-frameworks/`, checked out 2026-10-30. Licenses: LangGraph MIT, graphon (Dify's engine) Apache-2.0, Langflow MIT, n8n Sustainable Use License (read only; nothing copied). Everything below is written in our own words.

## LangGraph (MIT) `libs/langgraph/langgraph/`
- **Supersteps.** Each step plans its tasks, runs them, then applies their writes and saves a checkpoint (`pregel/main.py:3055-3079`). A task's writes only become visible in the next step.
- **Concurrency.** One `ThreadPoolExecutor` per run, sized by `max_concurrency` (`pregel/_executor.py:56-83`). A single task runs inline with no pool (`_runner.py:197-200`). Finished tasks are collected as they complete (FIRST_COMPLETED), with an optional `step_timeout`.
- **Deterministic merge.** `apply_writes` sorts tasks by path before grouping their writes per channel (`_algo.py:254-322`). Reducers combine values (`channels/binop.py`). A last-value channel rejects two writes to the same key within one step.
- **Join.** `NamedBarrierValue` becomes available only once every named upstream has written. A deferred variant waits until nothing else can run.
- **Checkpoint.** Saved once per superstep: channel values, versions, and which versions each node has seen. Each task's writes are also saved as "pending writes" the moment it finishes (`_loop.py:461-557`). Durability can be sync, async or exit-only.
- **Pause during a parallel step.**
  - A `GraphInterrupt` is not a failure. Interrupts from all tasks are combined into one.
  - Sibling tasks keep their pending writes, so on resume only the tasks that wrote nothing run again.
  - The interrupted node restarts from the top; `interrupt()` answers are matched by call index.
- **Recursion limit.** `stop = step + recursion_limit + 1`. Hitting it sets `out_of_steps`. The default is 10007, overridable by env.
- **Streaming.** All threads write to one shared queue. A waiter future wakes the consumer so events can be sent mid-step, in arrival order, tagged with a namespace.
- **Retry and cancel.** Retries use exponential backoff with jitter, sleeping inside the worker. When one task fails, the others are cancelled, but a sync future can only be cancelled before it starts.

## graphon (Dify's engine, Apache-2.0) `src/graphon/`
- **Workers and dispatcher.** A fixed `WorkerPool` (default 5 threads) pulls from a ready queue. A single `Dispatcher` thread applies every state change. Workers only run node generators and push results onto a queue.
- **Join rule.** A node becomes ready once none of its inbound edges is still unresolved and at least one was taken (`engine/scheduler.py:75-93`). Branches not taken are marked skipped all the way downstream.
- **Containers don't hold a thread.** An Iteration or Loop node emits `ContainerAwaitRequest` and gives up its worker. Its children run in child "frames" on the same pool, so pools are never nested (`ARCHITECTURE.md`).
- **Iteration.**
  - Each item gets a deep copy of the variable pool with `item` and `index` set.
  - Concurrency is a sliding window: `parallel_nums` minus the items already running.
  - Outputs are put back in index order.
  - Error modes: TERMINATED, CONTINUE_ON_ERROR, REMOVE_ABNORMAL_OUTPUT.
- **Loop.** Runs rounds one after another. The break condition is checked both before and after each round, plus a LoopEnd node can break. `loop_count` is the hard cap. Loop variables are written back to the parent frame.
- **Variable pool.** Values are addressed as `[node_id, var]`.
- **Node versioning.** Node classes register by (type, version) through `__init_subclass__`. Dify resolves the requested version and falls back to `latest` (`dify/api/core/workflow/node_factory.py:153-178`).
- **Pause and abort are commands, not exceptions.** On pause, queued nodes are deferred, running nodes finish, and a snapshot is taken once idle. A human-input node puts itself back as deferred so it runs again on resume.

## n8n (read only, nothing copied) `packages/core/src/execution-engine/workflow-execute.ts`
- **No real parallelism.** One async loop takes nodes from an execution stack.
- **Execution order is a per-workflow setting.** v1 runs depth-first, with siblings sorted by canvas position. v0 behaves differently. They version the run semantics themselves.
- **Multi-input nodes (Merge).** Inputs wait in `waitingExecution[node][runIndex]` until all have arrived. When the stack empties, a node can still run with partial inputs if its `requiredInputs` allow it.
- **Loops are back-edges.** SplitInBatches keeps its cursor in its own node context. Each pass increments `runIndex`. There is no general iteration cap, only the execution timeout.
- **Partial runs** rebuild the stack from saved run data. If the start is inside a cycle, the run starts from the beginning of that cycle.

## Langflow (MIT) `src/lfx/src/lfx/graph/`
- **Layers.** Runs one layer at a time with `asyncio.gather`, then computes the next layer. Successor updates are guarded by a lock.
- **Cycles.** Detected with strongly connected components. A loop vertex may run first, then waits for its predecessors inside the cycle.
- **Iteration guard.** `start()` refuses a cyclic graph without `max_iterations`, and counts how many times each vertex has run.
- **Checkpoint.** Stores the whole run-manager state plus vertex results and human-input decisions.

## Comparison
| | LangGraph | graphon | n8n | Langflow |
|---|---|---|---|---|
| Concurrency | thread pool per superstep (`max_concurrency`) | fixed worker pool + one dispatcher thread | single thread, stack | asyncio gather per layer |
| Join | barrier channels / defer | all inbound resolved, at least one taken | waiting area + `requiredInputs` | all predecessors done |
| Merge | sorted by task path + reducers | per-item deep copy; outputs in index order | per-input item arrays | vertex results |
| Checkpoint | per step + per-task writes | snapshot when idle | run data + stack | run-manager state |
| Pause during parallel | sibling writes kept; interrupted node re-runs | running nodes finish, queue deferred | Wait node | check per layer |
| Loop model | graph cycles | container (sequential) / iteration (window) | back-edge + node state | cycles + loop flag |
| Iteration guard | `recursion_limit` | `loop_count` + step/time limits | timeout only | `max_iterations` |
| Event order | arrival order, namespaced | serialized by dispatcher | sequential | per layer |
| Cancel | future cancel (only before it starts) | abort command | abort signal | task cancel |

## Lessons we adopt
### Parallel container
1. **One coordinator.** The main generator thread is the only coordinator (graphon's dispatcher pattern). It schedules branches, merges results, writes checkpoints, does all DB work, and yields packets. Branch threads run only leaf agent steps. Never schedule a container from inside a branch thread: a nested container waiting on the same bounded pool can deadlock.
2. **Bounded pool, sliding window.** One `ThreadPoolExecutor` per run, `max_concurrency` 3-4 because of LLM rate limits. Fill it as a sliding window, not in waves (Langflow's per-layer barrier stalls on its slowest member). Run a single child inline.
3. **One event queue.** Each branch gets its own Emitter, which pushes `(branch_id, packet)` onto one shared `queue.Queue`, plus a done sentinel. The main thread does a single blocking `get(timeout=0.05)` instead of polling N buses. Give each branch its own placement range; today `max_turn_index` (`workflow_engine.py:345`) would make branches collide.
4. **Isolated branch state.** Each branch reads a frozen snapshot of `step_outputs` and writes to its own dict. At the join, merge in the declared child order. Reject duplicate `output_key`s when the workflow is saved.
5. **Thread safety first.** `AgentTool` currently gets the shared `db_session` and `emitter` (`workflow_engine.py:793-813`). Each branch needs its own session and emitter, and must reload its agents in its own session.
6. **Cooperative cancellation.** A per-run `threading.Event`, checked between LLM and tool turns. Never join threads while cancelling. Error modes: `fail_fast`, `continue`, `drop_failed`.
7. **Checkpoint inside the container.** `containers[cid] = {done: {branch_id: output}, errors, paused_branch}`, updated as each branch completes. On resume, skip branches already done.
8. **HITL pause (v2).** Stop starting new branches, let running ones finish, collect every pause, and answer each by `branch_id`. Only the paused branch runs again on resume.

### Loop container
- A container, not a back-edge: n8n's node-context loop state is hard to resume.
- `max_iterations` is mandatory, plus a global step budget (like graphon's ExecutionLimitsLayer).
- Check the break condition before and after each round. Also allow an explicit "break" from an agent's output.
- Checkpoint `{index, vars, accumulated}`. On resume, only the current iteration runs again.
- for-each reuses the parallel sliding window (`parallel_nums`, a per-item copy, results ordered by index).

### Latency
- Throttle checkpoints: a dirty flag, flushed at most every 1-2s, and always on pause, error and finish. One writer with a monotonically increasing version, so an older checkpoint can never overwrite a newer one.
- Persist the trace once per container instead of after every step (`persist_workflow_trace`, around :866).
- Retry backoff happens inside the branch thread, never on the coordinator.

### Pitfalls others hit (avoid them)
- graphon sleeps for retries on the dispatcher thread, which stalls events for all branches (`engine/event/node_failure.py:119`).
- In graphon's parallel iteration, rounds don't see each other's writes; the last write wins.
- Langflow cancels tasks after `gather(return_exceptions=True)`, so fail-fast does nothing. Its `process()` path has no iteration guard.
- LangGraph re-runs an interrupted node from the top, so side effects repeat. It also had a bug that applied pending writes twice on resume. Our resume must be idempotent, keyed by `(branch_id, idx)`.
- n8n's retry wait blocks the whole run, and the order of waiting nodes is unspecified.
- For upgrades, version both the execution semantics (n8n `executionOrder`) and the checkpoint schema (graphon runtime_state v1, v2, v3 migrations). Register node types by (type, version) with a `latest` fallback.
