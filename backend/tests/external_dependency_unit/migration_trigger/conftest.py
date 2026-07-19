"""Env setup for the Tier-3 trigger tests.

Runs in the external-dependency-unit Docker matrix (real Postgres/Redis). Pins the
non-EE resolution path so the tests exercise the MIT/renamed tree, matching the
migration-safety unit suite.
"""

from __future__ import annotations

import os

os.environ.setdefault("DISABLE_TELEMETRY", "true")
