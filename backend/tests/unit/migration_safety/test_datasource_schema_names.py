"""The connector tables and ORM models are now named datasource; the API keeps its names.

Old attribute names fail silently in places mypy can't see (``getattr`` with a default,
untyped values, subquery ``.c`` columns), so this checks the mappers directly. The API
half guards the other direction: request and response models must not be renamed along
with the ORM, because the frontend and API clients read those fields.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

from sqlalchemy.orm import configure_mappers

from om.db.models import Base
from om.server.documents.models import ConnectorBase
from om.server.documents.models import ConnectorCredentialPairIdentifier
from om.server.documents.models import ConnectorSnapshot

_OLD_NAME = re.compile(r"connecto|cc_pair|ccpair", re.IGNORECASE)
_BACKEND = Path(__file__).resolve().parents[3]
# Only names that can't be anything else: local variables called connector_credential_pair
# stay, and the bare table names are covered by the metadata test below.
_OLD_TABLE_TEXT = re.compile(
    r"\b(?:document_by_connector_credential_pair"
    r"|document_set__connector_credential_pair|team__connector_credential_pair"
    r"|federated_connector__document_set|federated_connector_oauth_token)\b"
)
_MIGRATION = _BACKEND / "alembic" / "versions" / "0007_datasource_rename.py"


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_0007", _MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tables_columns_and_indexes_have_no_old_names() -> None:
    bad: list[str] = []
    for table in Base.metadata.tables.values():
        names = [table.name]
        names += [column.name for column in table.columns]
        names += [str(index.name) for index in table.indexes]
        names += [str(c.name) for c in table.constraints if c.name]
        bad += [f"{table.name}: {name}" for name in names if _OLD_NAME.search(name)]
        renamed = [name for name in names if "datasource" in name]
        assert all(len(name) <= 63 for name in renamed), table.name
    assert not bad, bad


def test_orm_classes_and_attributes_have_no_old_names() -> None:
    configure_mappers()
    bad: list[str] = []
    for mapper in Base.registry.mappers:
        name = mapper.class_.__name__
        if _OLD_NAME.search(name):
            bad.append(name)
        bad += [f"{name}.{a.key}" for a in mapper.attrs if _OLD_NAME.search(a.key)]
    assert not bad, bad


def test_migration_targets_exist_in_the_models() -> None:
    migration = _load_migration()
    tables = Base.metadata.tables
    renamed_tables = dict(migration._TABLES)
    for _, new_table in migration._TABLES:
        assert new_table in tables
    for old_table, _, new_column in migration._COLUMNS:
        table = tables[renamed_tables.get(old_table, old_table)]
        assert new_column in table.columns, f"{table.name}.{new_column}"


def test_every_new_migration_name_fits_postgres() -> None:
    migration = _load_migration()
    new_names = [new for _, new in migration._TABLES + migration._INDEXES + migration._SEQUENCES]
    new_names += [new for _, _, new in migration._CONSTRAINTS]
    assert len(new_names) == len(set(new_names))
    for name in new_names:
        assert len(name) <= 63, name
        assert not _OLD_NAME.search(name), name


def test_api_models_keep_their_field_names() -> None:
    assert "connector_specific_config" in ConnectorBase.model_fields
    assert {"id", "connector_specific_config"} <= set(ConnectorSnapshot.model_fields)
    assert {"connector_id", "credential_id"} == set(
        ConnectorCredentialPairIdentifier.model_fields
    )


def test_no_old_table_name_in_code_or_sql() -> None:
    hits: list[str] = []
    for folder in ("om", "scripts"):
        for path in (_BACKEND / folder).rglob("*.py"):
            for number, line in enumerate(
                path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1
            ):
                if _OLD_TABLE_TEXT.search(line):
                    hits.append(f"{path.relative_to(_BACKEND)}:{number}")
    assert not hits, hits
