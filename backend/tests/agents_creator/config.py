"""
Shared configuration and API client for VirtualAI agent tools.

API key resolution order:
    1. --key CLI argument
    2. apikey.txt file in this folder
    3. .env file in this folder (VIRTUALAI_API_KEY=...)
    4. VIRTUALAI_API_KEY environment variable
"""

import os
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests

# ── Paths ───────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
ASSISTANTS_DIR = ROOT_DIR / "assistants"
OPEN_WEBUI_DIR = ROOT_DIR / "open_web_ui"
APIKEY_FILE = ROOT_DIR / "apikey.txt"
ENV_FILE = ROOT_DIR / ".env"

# ── Runtime Config (mutable) ───────────────────────────────────────────────
CONFIG = {
    "base_url": "http://localhost:3000",
    "api_key": "",
}

# ── Default payload values for new assistants ──────────────────────────────
DEFAULTS = {
    "num_chunks": 10.0,
    "is_public": True,
    "recency_bias": "base_decay",
    "llm_filter_extraction": False,
    "llm_relevance_filter": False,
    "replace_base_system_prompt": True,
    "datetime_aware": True,
    "task_prompt": "",
    "document_set_ids": [],
    "tool_ids": [1],  # 1=Internal Search. Use --list-tools to see available IDs
    "users": [],
    "groups": [],
    "label_ids": [],
    "user_file_ids": [],
    "hierarchy_node_ids": [],
    "document_ids": [],
}

# ── Tool ID mapping (adjust per your VirtualAI instance) ──────────────────
TOOL_IDS = {
    "internal_search": 1,
    "image_generation": 2,
    "web_search": 3,
    "open_url": 7,
}


# ── API Key Loading ────────────────────────────────────────────────────────


def _load_env_file() -> dict[str, str]:
    """Parse a simple .env file (KEY=VALUE lines)."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("\"'")
    return env


def _load_apikey_file() -> str:
    """Read API key from apikey.txt (first non-empty line)."""
    if APIKEY_FILE.exists():
        for line in APIKEY_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    return ""


def resolve_api_key() -> str:
    """Resolve API key from all sources (CLI > apikey.txt > .env > env var)."""
    # 1. Already set via CLI --key
    if CONFIG["api_key"]:
        return CONFIG["api_key"]

    # 2. apikey.txt
    key = _load_apikey_file()
    if key:
        return key

    # 3. .env file (check VIRTUALAI_API_KEY first, fallback to ONYX_API_KEY)
    env = _load_env_file()
    key = env.get("VIRTUALAI_API_KEY", "") or env.get("ONYX_API_KEY", "")
    if key:
        return key

    # 4. System environment variable
    key = os.environ.get("VIRTUALAI_API_KEY", "") or os.environ.get("ONYX_API_KEY", "")
    if key:
        return key

    print("ERROR: No API key found. Provide it via one of:")
    print(f"  1. --key argument")
    print(f"  2. {APIKEY_FILE}")
    print(f"  3. {ENV_FILE}  (VIRTUALAI_API_KEY=...)")
    print(f"  4. VIRTUALAI_API_KEY environment variable")
    sys.exit(1)


# ── HTTP Client ─────────────────────────────────────────────────────────────


def headers() -> dict:
    return {
        "Authorization": f"Bearer {resolve_api_key()}",
        "Content-Type": "application/json",
    }


def api(method: str, path: str, data: dict | None = None) -> requests.Response:
    """Make an API call to VirtualAI."""
    url = urljoin(CONFIG["base_url"] + "/", f"api/{path.lstrip('/')}")
    return requests.request(method, url, headers=headers(), json=data, timeout=30)


# ── Label / Tag Helpers ────────────────────────────────────────────────────

# Cache label name → id to avoid repeated lookups
_label_cache: dict[str, int] = {}


def get_or_create_labels(label_names: list[str]) -> list[int]:
    """Resolve label names to IDs, creating any that don't exist yet."""
    if not label_names:
        return []

    # Populate cache once
    if not _label_cache:
        resp = api("GET", "persona/labels")
        if resp.status_code == 200:
            for lbl in resp.json():
                _label_cache[lbl["name"].lower()] = lbl["id"]

    ids = []
    for name in label_names:
        key = name.strip().lower()
        if key in _label_cache:
            ids.append(_label_cache[key])
        else:
            # Create the label
            resp = api("POST", "persona/labels", {"name": name.strip()})
            if resp.status_code == 200:
                lbl = resp.json()
                _label_cache[key] = lbl["id"]
                ids.append(lbl["id"])
                print(f"  [TAG]  Created label: {name.strip()} (ID={lbl['id']})")
            else:
                print(f"  [WARN] Could not create label '{name}': {resp.status_code}")
    return ids


# ── Common CLI args ─────────────────────────────────────────────────────────


def add_common_args(parser):
    """Add --url and --key arguments to any argparse parser."""
    parser.add_argument(
        "--url",
        default=CONFIG["base_url"],
        help=f"VirtualAI base URL (default: {CONFIG['base_url']})",
    )
    parser.add_argument(
        "--key",
        help="API key (overrides apikey.txt, .env, and env var)",
    )


def apply_common_args(args):
    """Apply --url and --key from parsed args to CONFIG."""
    CONFIG["base_url"] = args.url
    if args.key:
        CONFIG["api_key"] = args.key
