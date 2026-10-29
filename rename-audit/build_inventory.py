"""Phase 0 inventory of every residual onyx or danswer reference, classified by rename impact.

Read-only: scans git-tracked text files and writes inventory.csv + SUMMARY.md next to this script.

Classes
  S = safe code name (nothing persisted / external reads it)
  P = persisted or runtime contract (DB, Redis, S3, cookie, volume, metric, installed client)
  X = external resource owned by someone else (URL, email, registry, CI secret)

Usage:  python rename-audit/build_inventory.py
"""

import csv
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent

# `(?<!stan)` skips StandardAnswer ("stanDARD ANSWER" contains "danswer").
PATTERN = re.compile(r"(onyx|(?<![A-Za-z])danswer)", re.IGNORECASE)

SKIP_PREFIXES = (
    "graphify-out/",
    "phoenix/",
    "Perplexica/",
    "rename-audit/",
)
SKIP_SUFFIXES = (".lock", "package-lock.json", ".png", ".jpg", ".ico", ".svg", ".woff", ".woff2", ".pdf", ".zip")
SKIP_FILES = {
    "RENAME_AUDIT.md",
    "ONYX_RENAME_REMAINING.md",
    "DO_NOT_RENAME.md",
    "API_RENAME_PLAN.md",
    "EE_MIGRATION_PLAN.md",
}

# (class, category, regex) - first match wins, evaluated against the matched line.
RULES: list[tuple[str, str, re.Pattern[str]]] = [
    ("X", "ci-secret", re.compile(r"ONYX_GITHUB_")),
    ("X", "upstream-url", re.compile(r"onyx-dot-app|onyxdotapp|hub\.docker\.com|raw\.githubusercontent", re.I)),
    ("X", "external-domain-email", re.compile(r"[\w.-]*onyx\.app|@danswer\.ai|danswerai|docs\.danswer", re.I)),
    ("P", "api-key-email-domain", re.compile(r"onyxapikey\.ai|DANSWER_API_KEY")),
    ("P", "pat-prefix", re.compile(r"onyx_pat_")),
    ("P", "cookie", re.compile(r"onyx_tid|onyx_anonymous_user")),
    ("P", "redis-prefix", re.compile(r"onyx:celery|onyx_kv_store|\"onyx:|da_function_lock|DANSWER_REDIS")),
    ("P", "s3-prefix-or-bucket", re.compile(r"onyx-files|onyx-file-store|onyx-playwright|onyx-internal")),
    ("P", "sandbox-k8s", re.compile(r"onyx-sandboxes|managed-by.*onyx")),
    ("P", "metadata-file", re.compile(r"ONYX_METADATA|onyx_metadata|OM_METADATA")),
    ("P", "compose-volume-or-project", re.compile(r"onyx-stack|^\s*name:\s*onyx|onyx_postgres|onyx-relational|onyx-api_server|onyx-postgresql|onyx-opensearch|onyx-redis|onyx-nginx", re.I)),
    ("P", "prometheus-metric", re.compile(r"\bonyx_[a-z_]+(?:_total|_seconds|_bytes|_count|_gauge)\b|prometheus", re.I)),
    ("P", "client-identity", re.compile(r"onyx-chat-widget|onyx-widget|onyxExtension|ONYX_APP_LOADED|app\.onyx\.desktop|onyxTheme|tabbingIdentifier")),
    ("P", "db-column", re.compile(r"onyxbot_flow")),
    ("P", "env-var-name", re.compile(r"\b(ONYX|DANSWER)_[A-Z0-9_]+")),
    ("P", "deploy-resource-name", re.compile(r"onyx[-_](?:backend|web|api|cluster|efs|acm|nginx|config)|charts/onyx|modules/aws/onyx|onyx\.(?:name|fullname|chart|labels)", re.I)),
]

# File-path based fallbacks for lines the line rules did not catch.
PATH_RULES: list[tuple[str, str, re.Pattern[str]]] = [
    ("P", "deploy-resource-name", re.compile(r"^deployment/")),
    ("P", "client-identity", re.compile(r"^(widget|extensions|desktop)/")),
    ("S", "docs", re.compile(r"\.(md|MD|mdx|txt|rst)$")),
    ("S", "frontend-identifier", re.compile(r"^web/")),
    ("S", "backend-test", re.compile(r"^backend/tests/")),
    ("S", "backend-code", re.compile(r"^backend/")),
]


def classify(path: str, line: str) -> tuple[str, str]:
    for cls, cat, rx in RULES:
        if rx.search(line):
            return cls, cat
    for cls, cat, rx in PATH_RULES:
        if rx.search(path):
            return cls, cat
    return "S", "other"


# --check: anything outside this list fails. Phase 6/7 items stay listed until their plans run.
ALLOWED_FILES = {
    "NOTICE.md",
    "README.md",
    "backend/scripts/migrate_file_store_names.py",  # one-off; deleted after the live run
    "AGENT_RENAME_STATUS.md",
    "PERSONA_RENAME_HANDOFF.md",
    "SANDBOX_CODING_UPGRADE.md",
    "TODO_manual_ui_check_and_onyx_phase5.md",
    "TODO_replace_recommended_models_link.md",
    "TODO_MD_VESPA_VS_OPENSEARCH_MIGRATION_COMPARISON.MD",
    "TODO_MD_INDEX_REINDEX_IMPLEMENTATION_PLAN.MD",
    "AGENTS.md",  # upstream attribution + pointer to DO_NOT_RENAME.md
    "LICENSE",
    "web/src/lib/extension/constants.ts",  # Phase 7: extension storage keys
    "web/src/components/context/NRFPreferencesContext.tsx",
    "backend/tests/workflow_creator/workflows/28_drug_development.json",  # fictional sponsor name
    # tests that assert the OLD names are rejected / that the one-off script maps them
    "backend/tests/unit/om/auth/test_pat_prefixes.py",
    "backend/tests/unit/om/tenancy/test_tenant_cookies.py",
    "backend/tests/unit/om/file_processing/test_metadata_names.py",
    "backend/tests/unit/om/utils/test_optional_outbound.py",
    "backend/tests/unit/scripts/test_migrate_file_store_names.py",
    "backend/tests/daily/connectors/salesforce/test_salesforce_data.json",  # recorded third-party data
}
ALLOWED_PREFIXES = (
    "deployment/",  # Phase 6
    "widget/",
    "extensions/",
    "desktop/",  # Phase 7
    ".github/",  # Phase 7 (CI secrets)
    "backend/tests/unit/migration_safety/",  # guard tests name the old packages on purpose
    "backend/tests/route_rename/",  # recorded "before" snapshots
    "rewrite-plans/",  # historical clean-room plans, name the upstream product on purpose
    "docs/scheduled-workflows/",
    "examples/widget/",  # Phase 7
)
# Lines that are fine anywhere: the checkout directory name and the required upstream notice.
ALLOWED_LINE = re.compile(r"danswer20022026|Onyx / Danswer project|NOTICE\.md")
ALLOWED_CATEGORIES = {("X", "ci-secret"), ("P", "client-identity"), ("P", "deploy-resource-name"), ("P", "compose-volume-or-project")}


def is_allowed(path: str, cls: str, cat: str, text: str = "") -> bool:
    return ALLOWED_LINE.search(text) is not None or path in ALLOWED_FILES or path.startswith(ALLOWED_PREFIXES) or (cls, cat) in ALLOWED_CATEGORIES


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8", "replace").split("\0") if p]


def main() -> None:
    check = "--check" in sys.argv
    rows: list[tuple[str, int, str, str, str]] = []
    path_hits: list[str] = []
    for rel in tracked_files():
        if rel.startswith(SKIP_PREFIXES) or rel.endswith(SKIP_SUFFIXES) or rel in SKIP_FILES:
            continue
        if PATTERN.search(rel):
            path_hits.append(rel)
        fp = ROOT / rel
        if not fp.is_file():
            continue
        try:
            text = fp.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if PATTERN.search(line):
                cls, cat = classify(rel, line)
                rows.append((rel, i, cls, cat, line.strip()[:200]))

    with open(OUT / "inventory.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "line", "class", "category", "text"])
        w.writerows(rows)
    with open(OUT / "path_renames.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(path_hits)) + "\n")

    by_cat: Counter[tuple[str, str]] = Counter((r[2], r[3]) for r in rows)
    files_by_cat: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in rows:
        files_by_cat[(r[2], r[3])].add(r[0])
    by_top: Counter[str] = Counter(r[0].split("/")[0] for r in rows)

    lines = [
        "# onyx + danswer residue inventory (auto-generated)",
        "",
        f"Total hits: **{len(rows)}** in **{len({r[0] for r in rows})}** files; "
        f"**{len(path_hits)}** tracked paths contain the name (see path_renames.txt).",
        "",
        "| Class | Category | Hits | Files |",
        "|---|---|---:|---:|",
    ]
    for (cls, cat), n in sorted(by_cat.items(), key=lambda kv: (kv[0][0], -kv[1])):
        lines.append(f"| {cls} | {cat} | {n} | {len(files_by_cat[(cls, cat)])} |")
    lines += ["", "## Hits by top-level directory", "", "| Dir | Hits |", "|---|---:|"]
    lines += [f"| {d} | {n} |" for d, n in by_top.most_common(20)]
    (OUT / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    if check:
        bad = [r for r in rows if not is_allowed(r[0], r[2], r[3], r[4])]
        for f, n, _c, cat, text in bad[:300]:
            print(f"NOT ALLOWED {f}:{n} [{cat}] {text[:100]}")
        print(f"--check: {len(bad)} hit(s) outside the allowlist")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
