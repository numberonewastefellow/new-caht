"""Build the scratch corpus on the stack under test and record its doc ids.

zip (corpus + ``.om_metadata.json`` with ``doc_updated_at``) -> file connector
(mock credential) -> document set ``rag-benchmark-<dataset>`` -> wait until
indexed -> map doc ids to file names -> apply manifest boosts.
"""

import hashlib
import io
import json
import time
import zipfile
from collections.abc import Callable
from functools import lru_cache
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import Field

from om.configs.constants import OM_METADATA_FILENAME
from om.evals.rag_benchmark.api_client import RagBenchmarkApiClient
from om.evals.rag_benchmark.models import DatasetManifest
from om.evals.rag_benchmark.models import RagBenchmarkQuestion

FILE_CONNECTOR_DOC_PREFIX = "FILE_CONNECTOR__"
_TERMINAL_OK = {"success", "completed_with_errors"}
_TERMINAL_FAIL = {"failed", "canceled"}


class CorpusSetupState(BaseModel):
    dataset_version: str
    dataset_sha256: str
    api_base: str
    connector_name: str
    cc_pair_id: int
    document_set_name: str
    document_set_id: int | None = None
    docs: dict[str, str] = Field(default_factory=dict)  # file name -> document id
    boosts_applied: dict[str, int] = Field(default_factory=dict)
    indexing_seconds: float | None = None
    created_at: datetime


# --- dataset helpers ----------------------------------------------------------


def document_set_name(dataset_version: str) -> str:
    return f"rag-benchmark-{dataset_version}"


def load_manifest(dataset_dir: Path) -> DatasetManifest:
    return DatasetManifest.model_validate_json(
        (dataset_dir / "manifest.json").read_text(encoding="utf-8")
    )


def load_questions(path: Path) -> list[RagBenchmarkQuestion]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        RagBenchmarkQuestion.model_validate_json(line) for line in lines if line.strip()
    ]


def dataset_sha256(dataset_dir: Path) -> str:
    """Identity of a dataset: manifest (which pins every file's sha256) + questions."""
    digest = hashlib.sha256()
    digest.update((dataset_dir / "manifest.json").read_bytes())
    digest.update((dataset_dir / "questions.jsonl").read_bytes())
    return digest.hexdigest()


def verify_corpus(dataset_dir: Path, manifest: DatasetManifest) -> list[str]:
    problems = []
    for entry in manifest.files:
        path = dataset_dir / "corpus" / entry.file_name
        if not path.exists():
            problems.append(f"missing {entry.file_name}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != entry.sha256:
            problems.append(f"sha256 mismatch {entry.file_name}")
    return problems


def build_corpus_zip(dataset_dir: Path, manifest: DatasetManifest) -> bytes:
    metadata = [
        {"filename": entry.file_name, "doc_updated_at": entry.doc_updated_at}
        for entry in manifest.files
    ]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(OM_METADATA_FILENAME, json.dumps(metadata, indent=2))
        for entry in manifest.files:
            zf.write(dataset_dir / "corpus" / entry.file_name, arcname=entry.file_name)
    return buf.getvalue()


def read_corpus_text(path: Path) -> str:
    """Text of a corpus file via our own per-type extractors (no KV store needed).
    Cached per (path, mtime, size): the corpus is read by the generator self-check,
    the judge excerpts and the offline backend."""
    stat = path.stat()
    return _read_corpus_text_cached(str(path.resolve()), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=256)
def _read_corpus_text_cached(path_str: str, _mtime_ns: int, _size: int) -> str:
    from om.file_processing.extract_file_text import file_io_to_text
    from om.file_processing.extract_file_text import pdf_to_text
    from om.file_processing.extract_file_text import read_docx_file
    from om.file_processing.extract_file_text import xlsx_to_text

    path = Path(path_str)
    suffix = path.suffix.lower()
    with path.open("rb") as handle:
        if suffix == ".pdf":
            return pdf_to_text(handle)
        if suffix == ".docx":
            return read_docx_file(handle, path.name)[0]
        if suffix == ".xlsx":
            return xlsx_to_text(handle, path.name)
        return file_io_to_text(handle)


# --- setup ------------------------------------------------------------------------


def map_doc_ids(
    file_paths: list[str], file_names: list[str], doc_ids: list[str]
) -> dict[str, str]:
    """File-connector doc ids are ``FILE_CONNECTOR__<file store id>``."""
    by_file_id = {path: name for path, name in zip(file_paths, file_names)}
    mapping: dict[str, str] = {}
    for doc_id in doc_ids:
        file_id = (
            doc_id[len(FILE_CONNECTOR_DOC_PREFIX) :]
            if doc_id.startswith(FILE_CONNECTOR_DOC_PREFIX)
            else doc_id
        )
        name = by_file_id.get(file_id)
        if name is not None:
            mapping[name] = doc_id
    return mapping


def wait_for_indexing(
    client: RagBenchmarkApiClient,
    cc_pair_id: int,
    expected_docs: int,
    timeout_s: float,
    poll_s: float = 15.0,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while True:
        info = client.get_cc_pair(cc_pair_id)
        status = (info.get("last_index_attempt_status") or "").lower()
        indexed = int(info.get("num_docs_indexed") or 0)
        log(
            f"  cc-pair {cc_pair_id}: status={status or 'pending'} docs={indexed}/{expected_docs}"
        )
        if status in _TERMINAL_FAIL:
            raise RuntimeError(f"Indexing {status} for cc-pair {cc_pair_id}")
        if (
            status in _TERMINAL_OK
            and indexed >= expected_docs
            and not info.get("indexing")
        ):
            return info
        if time.monotonic() > deadline:
            raise TimeoutError(
                f"Indexing not finished after {timeout_s:.0f}s ({indexed}/{expected_docs} docs)"
            )
        sleep(poll_s)


def setup_scratch_corpus(
    client: RagBenchmarkApiClient,
    dataset_dir: Path,
    timeout_s: float = 3600.0,
    poll_s: float = 15.0,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = print,
) -> CorpusSetupState:
    manifest = load_manifest(dataset_dir)
    problems = verify_corpus(dataset_dir, manifest)
    if problems:
        raise RuntimeError("Corpus does not match manifest: " + "; ".join(problems))
    name = document_set_name(manifest.dataset_version)
    started = time.monotonic()

    log(f"Uploading {len(manifest.files)} files as one zip ...")
    upload = client.upload_connector_files(
        [(f"{name}.zip", build_corpus_zip(dataset_dir, manifest), "application/zip")]
    )
    file_paths: list[str] = upload["file_paths"]
    file_names: list[str] = upload["file_names"]
    if sorted(file_names) != sorted(e.file_name for e in manifest.files):
        raise RuntimeError(f"Upload returned unexpected files: {file_names}")

    log("Creating file connector + cc-pair ...")
    cc_pair_id = client.create_file_connector(
        name, file_paths, file_names, upload.get("zip_metadata_file_id")
    )

    log("Creating document set ...")
    document_set_id = client.create_document_set(
        name,
        [cc_pair_id],
        description=f"RAG benchmark corpus {manifest.dataset_version} (synthetic)",
    )

    log("Waiting for indexing ...")
    wait_for_indexing(
        client, cc_pair_id, len(manifest.files), timeout_s, poll_s, sleep, log
    )

    docs = map_doc_ids(file_paths, file_names, client.get_cc_pair_doc_ids(cc_pair_id))
    missing = sorted({e.file_name for e in manifest.files} - set(docs))
    if missing:
        raise RuntimeError(f"Indexed docs missing for: {missing}")

    boosts: dict[str, int] = {}
    for entry in manifest.files:
        if entry.boost:
            client.set_boost(docs[entry.file_name], entry.boost)
            boosts[entry.file_name] = entry.boost

    return CorpusSetupState(
        dataset_version=manifest.dataset_version,
        dataset_sha256=dataset_sha256(dataset_dir),
        api_base=client.api_base,
        connector_name=name,
        cc_pair_id=cc_pair_id,
        document_set_name=name,
        document_set_id=document_set_id,
        docs=docs,
        boosts_applied=boosts,
        indexing_seconds=time.monotonic() - started,
        created_at=datetime.now(timezone.utc),
    )
