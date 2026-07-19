"""RFC 7644 §3.5.2 PATCH application.

:func:`apply_patch` takes a resource as a plain ``dict`` (the serializer output)
and a list of :class:`ScimPatchOperation` and returns a new, modified ``dict``.
The service layer then reconciles the result to the database. PATCH is atomic —
if any operation raises, the caller discards the result and the resource is
unchanged.

Interop rules baked in (from the Okta/Entra research):
* ``op`` is already lowercased by the model.
* path-less ``add``/``replace`` merge a ``value`` object whose keys may be dotted
  (``name.givenName``) or extension URNs.
* group membership ``remove`` is accepted in both shapes — value-path
  (``members[value eq "x"]``) and value-array (``members`` + ``value:[{value:x}]``).
* ``active`` may arrive as the string ``"False"`` (handled downstream on re-parse).
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

from om.server.scim.errors import ScimError
from om.server.scim.filters import FilterNode
from om.server.scim.filters import parse_filter
from om.server.scim.resources import ScimPatchOperation

_PATH_RE = re.compile(
    r"^(?P<attr>[^\[\].]+)(?:\[(?P<filter>.+)\])?(?:\.(?P<sub>[A-Za-z0-9_.$:-]+))?$"
)


@dataclass
class _ParsedPath:
    attr: str
    value_filter: FilterNode | None
    sub_attr: str | None


def _parse_path(path: str) -> _ParsedPath:
    """Parse a PATCH ``path``: ``attr`` | ``attr.sub`` | ``attr[filter]`` |
    ``attr[filter].sub``."""
    path = path.strip()
    if "[" in path:
        match = _PATH_RE.match(path)
        if not match or not match.group("filter"):
            raise ScimError.invalid_path(f"Invalid PATCH path: {path!r}")
        return _ParsedPath(
            attr=match.group("attr"),
            value_filter=parse_filter(match.group("filter")),
            sub_attr=match.group("sub"),
        )
    # No value-filter: a plain (possibly dotted) attribute path.
    head, _, tail = path.partition(".")
    if not head:
        raise ScimError.invalid_path(f"Invalid PATCH path: {path!r}")
    return _ParsedPath(attr=head, value_filter=None, sub_attr=tail or None)


def apply_patch(
    resource: dict[str, Any], operations: list[ScimPatchOperation]
) -> dict[str, Any]:
    result = copy.deepcopy(resource)
    for operation in operations:
        _apply_one(result, operation)
    return result


def _apply_one(resource: dict[str, Any], operation: ScimPatchOperation) -> None:
    op = operation.op
    if op not in ("add", "replace", "remove"):
        raise ScimError.invalid_value(f"Unsupported PATCH op: {operation.op!r}")

    if operation.path is None:
        _apply_no_path(resource, op, operation.value)
        return

    parsed = _parse_path(operation.path)
    if parsed.value_filter is not None:
        _apply_filtered(resource, op, parsed, operation.value)
    else:
        _apply_simple(resource, op, parsed.attr, parsed.sub_attr, operation.value)


# --------------------------------------------------------------------------
# path-less add/replace (merge a value object into the resource)
# --------------------------------------------------------------------------
def _apply_no_path(resource: dict[str, Any], op: str, value: Any) -> None:
    if op == "remove":
        raise ScimError.no_target("PATCH 'remove' requires a 'path'.")
    if not isinstance(value, dict):
        raise ScimError.invalid_value(
            "path-less add/replace requires an object 'value'."
        )
    for key, item in value.items():
        if ":" in key:
            # Extension URN key — store verbatim (unpersisted attrs are ignored).
            resource[key] = item
        else:
            _set_nested(resource, key.split("."), item)


# --------------------------------------------------------------------------
# simple / dotted path
# --------------------------------------------------------------------------
def _apply_simple(
    resource: dict[str, Any],
    op: str,
    attr: str,
    sub_attr: str | None,
    value: Any,
) -> None:
    path_segments = [attr] + (sub_attr.split(".") if sub_attr else [])
    existing = _get_nested(resource, path_segments)

    if op == "remove":
        # Entra legacy member removal: op=remove, path=members, value=[{value:id}]
        # removes the *listed* entries rather than the whole attribute.
        if sub_attr is None and value is not None and isinstance(existing, list):
            resource[_actual_key(resource, attr)] = _drop_entries(existing, value)
        else:
            _remove_nested(resource, path_segments)
        return

    if op == "add" and isinstance(existing, list):
        # add appends to a multi-valued attribute
        existing.extend(value if isinstance(value, list) else [value])
        return
    # replace (any), or add on a scalar / absent attribute
    _set_nested(resource, path_segments, value)


def _drop_entries(entries: list[Any], value: Any) -> list[Any]:
    """Remove multi-valued entries identified by ``value`` (Entra legacy shape)."""
    to_remove = value if isinstance(value, list) else [value]
    remove_values = {
        item.get("value") if isinstance(item, dict) else item for item in to_remove
    }
    return [
        entry
        for entry in entries
        if not (isinstance(entry, dict) and entry.get("value") in remove_values)
        and entry not in to_remove
    ]


# --------------------------------------------------------------------------
# value-filtered path (multi-valued entries, e.g. members / emails)
# --------------------------------------------------------------------------
def _apply_filtered(
    resource: dict[str, Any],
    op: str,
    parsed: _ParsedPath,
    value: Any,
) -> None:
    entries = resource.get(parsed.attr)
    if not isinstance(entries, list):
        entries = []
    assert parsed.value_filter is not None
    matched = [e for e in entries if isinstance(e, dict) and parsed.value_filter.evaluate(e)]

    if op == "remove":
        remaining = [e for e in entries if e not in matched]
        resource[parsed.attr] = remaining
        return

    # add / replace on matched entries
    for entry in matched:
        if parsed.sub_attr:
            _set_nested(entry, parsed.sub_attr.split("."), value)
        elif isinstance(value, dict):
            entry.update(value)
    if not matched and op == "add":
        # No existing match — treat as an append of the provided value.
        entries.append(value if not isinstance(value, list) else value[0])
        resource[parsed.attr] = entries


# --------------------------------------------------------------------------
# nested get/set/remove on a dict tree
# --------------------------------------------------------------------------
def _get_nested(resource: dict[str, Any], segments: list[str]) -> Any:
    current: Any = resource
    for segment in segments:
        if not isinstance(current, dict):
            return None
        current = _get_ci(current, segment)
    return current


def _set_nested(resource: dict[str, Any], segments: list[str], value: Any) -> None:
    current = resource
    for segment in segments[:-1]:
        existing = _get_ci(current, segment)
        if not isinstance(existing, dict):
            existing = {}
            current[segment] = existing
        current = existing
    # Preserve the existing key's casing if present.
    key = _actual_key(current, segments[-1])
    current[key] = value


def _remove_nested(resource: dict[str, Any], segments: list[str]) -> None:
    current = resource
    for segment in segments[:-1]:
        existing = _get_ci(current, segment)
        if not isinstance(existing, dict):
            return
        current = existing
    key = _actual_key(current, segments[-1])
    current.pop(key, None)


def _get_ci(mapping: dict[str, Any], key: str) -> Any:
    return mapping.get(_actual_key(mapping, key))


def _actual_key(mapping: dict[str, Any], key: str) -> str:
    if key in mapping:
        return key
    lowered = key.lower()
    for existing_key in mapping:
        if existing_key.lower() == lowered:
            return existing_key
    return key
