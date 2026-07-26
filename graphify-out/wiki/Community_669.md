# Community 669

> 22 nodes · cohesion 0.17

## Key Concepts

- **test_auto_figure_capture.py** (14 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **Session** (8 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **_figure_files()** (8 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **test_capture_without_savefig()** (7 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **test_no_phantom_capture_after_close()** (6 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **execute_ephemeral()** (5 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/conftest.py`
- **test_capture_ephemeral()** (5 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **test_capture_monotonic_across_calls()** (5 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **test_capture_on_error()** (5 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **test_capture_with_plt_show()** (5 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **test_no_capture_without_matplotlib()** (5 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **_assert_valid_png()** (3 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **_find_file()** (3 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **Helper: execute code ephemerally (no session).** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/conftest.py`
- **Tests for automatic matplotlib figure capture (A1).  Charts should reach the cli** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **A non-plotting cell produces no figure_*.png artifacts.** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **If the user saves and closes explicitly, we do not add a phantom figure.** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **A figure built before an exception is still captured (atexit/finally path).** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **The ephemeral prologue captures an open figure with no savefig.** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **A plot with no savefig is still captured as figure_1.png.** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **plt.show() (a no-op under Agg) still leaves the figure open -> captured.** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`
- **Successive cells produce figure_1, figure_2 (counter never resets/collides).** (1 connections) — `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`

## Relationships

- [[Community 748]] (7 shared connections)
- [[Community 365]] (2 shared connections)
- [[Community 1552]] (1 shared connections)

## Source Files

- `code-interpreter/code-interpreter/tests/integration_tests/session_tests/conftest.py`
- `code-interpreter/code-interpreter/tests/integration_tests/session_tests/test_auto_figure_capture.py`

## Audit Trail

- EXTRACTED: 88 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*