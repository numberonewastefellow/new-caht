"""Fixed, version-controlled document corpus for the Vespa search baseline.

The corpus is deliberately small and themed so that relevance is *checkable by eye*:
documents about clearly-distinct topics, partitioned into named knowledge bases
(document sets), varied source types, and varied update dates. This lets us assert
exact filter behavior (KB / source_type / time_cutoff) and capture a stable ranking
baseline for the Vespa -> OpenSearch migration.

Everything here is deterministic (no randomness, no timestamps computed at import
time) so the same corpus is produced on every run and on every machine.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone

from om.configs.constants import DocumentSource


# Knowledge base (document set) names used throughout the baseline tests.
KB_ENGINEERING = "Engineering"
KB_HR = "HR"
KB_FINANCE = "Finance"

ALL_KBS = [KB_ENGINEERING, KB_HR, KB_FINANCE]


def _dt(year: int, month: int = 1, day: int = 1) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


# A fixed "recent" and "old" date so time_cutoff tests are unambiguous.
RECENT_DATE = _dt(2026, 1, 15)
OLD_DATE = _dt(2022, 1, 15)
# A cutoff that sits strictly between OLD_DATE and RECENT_DATE.
TIME_CUTOFF_BETWEEN = _dt(2024, 1, 1)


@dataclass(frozen=True)
class CorpusDoc:
    """A single-chunk document in the baseline corpus."""

    doc_id: str
    title: str
    content: str
    source: DocumentSource
    document_sets: frozenset[str]
    updated_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)


# NOTE: doc_ids are stable and prefixed by KB for easy reading in snapshots.
CORPUS: list[CorpusDoc] = [
    # ----------------------------- Engineering -----------------------------
    CorpusDoc(
        doc_id="eng-k8s-deploy",
        title="Deploying containers to Kubernetes",
        content=(
            "This runbook explains how to deploy containerized services to a "
            "Kubernetes cluster. It covers writing a Deployment manifest, exposing "
            "pods with a Service, rolling updates, readiness probes, and scaling "
            "replicas with kubectl. Use a container registry to store your images "
            "before rolling out to production."
        ),
        source=DocumentSource.FILE,
        document_sets=frozenset({KB_ENGINEERING}),
        updated_at=RECENT_DATE,
    ),
    CorpusDoc(
        doc_id="eng-python-async",
        title="Python asyncio concurrency guide",
        content=(
            "A practical guide to asynchronous programming in Python. Learn how the "
            "asyncio event loop schedules coroutines, when to use async and await, "
            "how to run blocking calls in a thread pool executor, and patterns for "
            "concurrent I/O bound workloads such as HTTP requests and database calls."
        ),
        source=DocumentSource.WEB,
        document_sets=frozenset({KB_ENGINEERING}),
        updated_at=RECENT_DATE,
    ),
    CorpusDoc(
        doc_id="eng-db-indexing",
        title="Database indexing and query performance",
        content=(
            "How relational database indexes speed up queries. Covers B-tree indexes, "
            "composite indexes, covering indexes, and how the query planner chooses an "
            "index. Includes guidance on avoiding full table scans and measuring slow "
            "queries with EXPLAIN ANALYZE."
        ),
        source=DocumentSource.FILE,
        document_sets=frozenset({KB_ENGINEERING}),
        updated_at=OLD_DATE,
    ),
    CorpusDoc(
        doc_id="eng-cicd-pipeline",
        title="Setting up a CI/CD pipeline",
        content=(
            "Continuous integration and continuous deployment best practices. Describes "
            "running automated tests on every pull request, building Docker images, and "
            "promoting artifacts through staging to production with automated rollbacks."
        ),
        source=DocumentSource.GOOGLE_DRIVE,
        document_sets=frozenset({KB_ENGINEERING}),
        updated_at=RECENT_DATE,
    ),
    # --------------------------------- HR ----------------------------------
    CorpusDoc(
        doc_id="hr-parental-leave",
        title="Parental leave policy",
        content=(
            "Our parental leave policy provides paid time off for new parents following "
            "the birth or adoption of a child. Eligible employees receive sixteen weeks "
            "of fully paid leave, which can be taken continuously or intermittently "
            "within the first year. Contact the people team to start your leave request."
        ),
        source=DocumentSource.FILE,
        document_sets=frozenset({KB_HR}),
        updated_at=RECENT_DATE,
    ),
    CorpusDoc(
        doc_id="hr-performance-review",
        title="Annual performance review process",
        content=(
            "The annual performance review cycle covers self assessment, peer feedback, "
            "and manager evaluation. Goals are scored against expectations and calibrated "
            "across teams. Ratings inform promotion and compensation decisions."
        ),
        source=DocumentSource.GOOGLE_DRIVE,
        document_sets=frozenset({KB_HR}),
        updated_at=OLD_DATE,
    ),
    CorpusDoc(
        doc_id="hr-remote-work",
        title="Remote work and hybrid policy",
        content=(
            "Guidelines for working remotely. Employees may work from home up to three "
            "days per week. Covers home office stipends, core collaboration hours, and "
            "expectations for staying reachable on chat and video during the workday."
        ),
        source=DocumentSource.WEB,
        document_sets=frozenset({KB_HR}),
        updated_at=RECENT_DATE,
    ),
    # ------------------------------- Finance -------------------------------
    CorpusDoc(
        doc_id="fin-expense-report",
        title="How to submit an expense report",
        content=(
            "Step by step instructions for submitting an expense report for "
            "reimbursement. Itemize receipts, select the correct cost center, attach "
            "proof of payment, and submit for manager approval. Reimbursements are paid "
            "out with the next payroll cycle."
        ),
        source=DocumentSource.FILE,
        document_sets=frozenset({KB_FINANCE}),
        updated_at=RECENT_DATE,
    ),
    CorpusDoc(
        doc_id="fin-quarterly-budget",
        title="Quarterly budget planning",
        content=(
            "The quarterly budget planning process aligns departmental spending with "
            "revenue forecasts. Cost center owners submit projected headcount, software, "
            "and vendor costs, which finance consolidates into the company forecast."
        ),
        source=DocumentSource.GOOGLE_DRIVE,
        document_sets=frozenset({KB_FINANCE}),
        updated_at=OLD_DATE,
    ),
    CorpusDoc(
        doc_id="fin-procurement",
        title="Vendor procurement and invoicing",
        content=(
            "The procurement workflow for engaging new vendors. Covers raising a "
            "purchase order, security and legal review, negotiating contract terms, and "
            "processing supplier invoices for payment within net thirty days."
        ),
        source=DocumentSource.WEB,
        document_sets=frozenset({KB_FINANCE}),
        updated_at=RECENT_DATE,
    ),
    # ------------------- Cross-KB document (shared) ------------------------
    # Belongs to BOTH Engineering and Finance so document_set filtering that
    # returns a shared doc can be asserted.
    CorpusDoc(
        doc_id="shared-saas-cost",
        title="Managing SaaS software costs for engineering teams",
        content=(
            "A joint engineering and finance guide to controlling software as a service "
            "spending. Explains how to track per seat licensing for developer tools, "
            "right size cloud infrastructure, and forecast SaaS renewal costs in the "
            "quarterly budget."
        ),
        source=DocumentSource.FILE,
        document_sets=frozenset({KB_ENGINEERING, KB_FINANCE}),
        updated_at=RECENT_DATE,
    ),
]


def docs_in_kb(kb_name: str) -> list[CorpusDoc]:
    return [d for d in CORPUS if kb_name in d.document_sets]


def docs_with_source(source: DocumentSource) -> list[CorpusDoc]:
    return [d for d in CORPUS if d.source == source]


def doc_ids_in_kb(kb_name: str) -> set[str]:
    return {d.doc_id for d in docs_in_kb(kb_name)}


def doc_ids_with_source(source: DocumentSource) -> set[str]:
    return {d.doc_id for d in docs_with_source(source)}


def recent_doc_ids() -> set[str]:
    return {d.doc_id for d in CORPUS if d.updated_at >= TIME_CUTOFF_BETWEEN}


CORPUS_BY_ID: dict[str, CorpusDoc] = {d.doc_id: d for d in CORPUS}
