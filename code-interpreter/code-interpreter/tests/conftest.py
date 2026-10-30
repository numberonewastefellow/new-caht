"""Suite-wide test configuration.

The service fails closed when ``CODE_INTERPRETER_API_TOKEN`` is unset. The in-process
tests (``TestClient(create_app())``) predate auth and don't send a bearer token, so
unless the caller configured a token explicitly we enable the dev-only override here,
BEFORE ``app.app_configs`` is imported. Auth behaviour itself is covered by
``integration_tests/test_security.py``, which patches the settings per test.
"""

from __future__ import annotations

import os

if not os.environ.get("CODE_INTERPRETER_API_TOKEN"):
    os.environ.setdefault("CODE_INTERPRETER_ALLOW_UNAUTHENTICATED", "true")
