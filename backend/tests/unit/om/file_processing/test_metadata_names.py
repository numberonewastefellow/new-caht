import io
import json
import zipfile

import pytest

from om.configs.constants import OM_METADATA_FILENAME
from om.file_processing.extract_file_text import _extract_om_metadata
from om.file_processing.extract_file_text import load_files_from_zip
from om.server.documents.connector import save_zip_metadata_to_file_store

META = [{"filename": "x.txt", "link": "https://example.com"}]


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
            zf.writestr(n, json.dumps(META) if n.endswith("_metadata.json") else "text")
    buf.seek(0)
    return zipfile.ZipFile(buf, "r")


def test_metadata_file_name_is_om() -> None:
    assert OM_METADATA_FILENAME == ".om_metadata.json"


def test_zip_metadata_is_saved_under_the_om_name() -> None:
    store = _FakeFileStore()
    assert save_zip_metadata_to_file_store(_zip(["x.txt", ".om_metadata.json"]), store) == "file-id-1"  # type: ignore[arg-type]
    assert store.saved[0]["display_name"] == OM_METADATA_FILENAME
    assert json.loads(store.saved[0]["bytes"]) == META


def test_old_metadata_file_name_is_no_longer_recognised() -> None:
    assert save_zip_metadata_to_file_store(_zip(["x.txt", ".onyx_metadata.json"]), _FakeFileStore()) is None  # type: ignore[arg-type]


def test_metadata_file_is_not_treated_as_a_document() -> None:
    zf = _zip(["x.txt", ".om_metadata.json"])
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as out:
        for info in zf.infolist():
            out.writestr(info.filename, zf.read(info.filename))
    raw.seek(0)
    assert [info.filename for info, _ in load_files_from_zip(raw)] == ["x.txt"]


@pytest.mark.parametrize("line", ['<!-- OM_METADATA={"title": "A"} -->', '#OM_METADATA={"title": "A"}'])
def test_inline_marker_is_om(line: str) -> None:
    assert _extract_om_metadata(line) == {"title": "A"}


@pytest.mark.parametrize("line", ['<!-- ONYX_METADATA={"title": "A"} -->', '#ONYX_METADATA={"title": "A"}', "# heading"])
def test_old_marker_is_not_metadata(line: str) -> None:
    assert _extract_om_metadata(line) is None
