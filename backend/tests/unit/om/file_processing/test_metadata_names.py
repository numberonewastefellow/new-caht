"""The file connector's metadata conventions: canonical om names plus the legacy upstream names.

Users' existing zips contain ``.onyx_metadata.json`` and their documents carry ``ONYX_METADATA=``
markers. We cannot rewrite those, so both stay readable; only the om names are ever written.
"""

import io
import json
import zipfile

import pytest

from om.configs.constants import LEGACY_METADATA_FILENAMES
from om.configs.constants import METADATA_FILENAMES
from om.configs.constants import OM_METADATA_FILENAME
from om.file_processing.extract_file_text import _extract_om_metadata
from om.file_processing.extract_file_text import load_files_from_zip
from om.server.documents.connector import save_zip_metadata_to_file_store

META = {"sample.txt": {"link": "https://example.com"}}


class _FakeFileStore:
    def __init__(self) -> None:
        self.saved: list[dict] = []

    def save_file(self, **kwargs: object) -> str:
        content = kwargs["content"]
        assert isinstance(content, io.BytesIO)
        self.saved.append({**kwargs, "bytes": content.getvalue()})
        return "file-id-1"


def _zip(names: list[str]) -> zipfile.ZipFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for n in names:
            zf.writestr(n, json.dumps(META) if n in METADATA_FILENAMES else "text")
    buf.seek(0)
    return zipfile.ZipFile(buf, "r")


def test_canonical_name_is_om_and_legacy_alias_is_listed() -> None:
    assert OM_METADATA_FILENAME == ".om_metadata.json"
    assert LEGACY_METADATA_FILENAMES == (".onyx_metadata.json",)
    assert METADATA_FILENAMES == (OM_METADATA_FILENAME, ".onyx_metadata.json")


@pytest.mark.parametrize("name", [".om_metadata.json", ".onyx_metadata.json"])
def test_zip_metadata_file_is_found_under_either_name_and_saved_under_om_name(name: str) -> None:
    store = _FakeFileStore()
    file_id = save_zip_metadata_to_file_store(_zip(["sample.txt", name]), store)  # type: ignore[arg-type]
    assert file_id == "file-id-1"
    assert len(store.saved) == 1
    assert store.saved[0]["display_name"] == OM_METADATA_FILENAME  # never written under the legacy name
    assert json.loads(store.saved[0]["bytes"]) == META


def test_zip_without_metadata_returns_none() -> None:
    assert save_zip_metadata_to_file_store(_zip(["sample.txt"]), _FakeFileStore()) is None  # type: ignore[arg-type]


@pytest.mark.parametrize("name", [".om_metadata.json", ".onyx_metadata.json"])
def test_metadata_file_is_not_treated_as_a_document(name: str) -> None:
    zf = _zip(["sample.txt", name])
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as out:
        for info in zf.infolist():
            out.writestr(info.filename, zf.read(info.filename))
    raw.seek(0)
    yielded = [info.filename for info, _ in load_files_from_zip(raw)]
    assert yielded == ["sample.txt"]


@pytest.mark.parametrize(
    "line",
    [
        '<!-- OM_METADATA={"title": "A"} -->',
        '<!-- ONYX_METADATA={"title": "A"} -->',
        '#OM_METADATA={"title": "A"}',
        '#ONYX_METADATA={"title": "A"}',
    ],
)
def test_inline_marker_accepts_om_and_legacy_names(line: str) -> None:
    assert _extract_om_metadata(line) == {"title": "A"}


def test_plain_line_is_not_metadata() -> None:
    assert _extract_om_metadata("# just a heading") is None
