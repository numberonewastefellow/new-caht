"""SCIM filter parsing and evaluation (RFC 7644 §3.4.2.2).

Supports the full comparison operator set (eq, ne, co, sw, ew, gt, ge, lt, le,
pr), the logical operators (and, or, not), grouping ``( )`` and complex-attribute
value paths ``attr[ ... ]``. Operators and attribute names are case-insensitive.

The parser produces an AST; :meth:`FilterNode.evaluate` runs it against a SCIM
resource represented as a plain ``dict`` (the same shape returned by the
resource serializers), so list endpoints can filter in memory. IdPs in practice
send only ``eq`` (plus ``and``); the fuller grammar is implemented for
correctness and forward-compatibility.
"""

from __future__ import annotations

import re
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any

from om.server.scim.errors import ScimError

# --------------------------------------------------------------------------
# Tokeniser
# --------------------------------------------------------------------------
_TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (?P<lparen>\()
      | (?P<rparen>\))
      | (?P<lbracket>\[)
      | (?P<rbracket>\])
      | (?P<string>"(?:\\.|[^"\\])*")
      | (?P<number>-?\d+(?:\.\d+)?)
      | (?P<word>[A-Za-z_][A-Za-z0-9_.:$/-]*)
    )
    """,
    re.VERBOSE,
)

_COMPARATORS = {"eq", "ne", "co", "sw", "ew", "gt", "ge", "lt", "le"}
_LOGICAL = {"and", "or", "not"}


@dataclass
class _Token:
    kind: str
    value: str


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    pos = 0
    length = len(text)
    while pos < length:
        if text[pos].isspace():
            pos += 1
            continue
        match = _TOKEN_RE.match(text, pos)
        if not match or match.end() == pos:
            raise ScimError.invalid_filter(f"Unparseable filter near: {text[pos:]!r}")
        pos = match.end()
        kind = match.lastgroup or ""
        raw = match.group(kind)
        tokens.append(_Token(kind, raw))
    return tokens


# --------------------------------------------------------------------------
# AST
# --------------------------------------------------------------------------
class FilterNode(ABC):
    @abstractmethod
    def evaluate(self, resource: dict[str, Any]) -> bool:
        ...


@dataclass
class Comparison(FilterNode):
    attr_path: str
    op: str
    value: Any  # None for "pr"

    def evaluate(self, resource: dict[str, Any]) -> bool:
        values = _resolve_path(resource, self.attr_path)
        if self.op == "pr":
            return any(v not in (None, "", [], {}) for v in values) if values else False
        return any(_compare(v, self.op, self.value) for v in values)


@dataclass
class ValuePath(FilterNode):
    """``attr[ inner ]`` — true if any entry of the multi-valued attr matches."""

    attr_path: str
    inner: FilterNode

    def evaluate(self, resource: dict[str, Any]) -> bool:
        entries = _resolve_path(resource, self.attr_path)
        for entry in entries:
            if isinstance(entry, dict) and self.inner.evaluate(entry):
                return True
        return False


@dataclass
class Not(FilterNode):
    child: FilterNode

    def evaluate(self, resource: dict[str, Any]) -> bool:
        return not self.child.evaluate(resource)


@dataclass
class And(FilterNode):
    left: FilterNode
    right: FilterNode

    def evaluate(self, resource: dict[str, Any]) -> bool:
        return self.left.evaluate(resource) and self.right.evaluate(resource)


@dataclass
class Or(FilterNode):
    left: FilterNode
    right: FilterNode

    def evaluate(self, resource: dict[str, Any]) -> bool:
        return self.left.evaluate(resource) or self.right.evaluate(resource)


# --------------------------------------------------------------------------
# Parser (recursive descent; precedence: or < and < not < primary)
# --------------------------------------------------------------------------
class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> _Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _next(self) -> _Token:
        token = self._peek()
        if token is None:
            raise ScimError.invalid_filter("Unexpected end of filter.")
        self.pos += 1
        return token

    def _is_keyword(self, word: str) -> bool:
        token = self._peek()
        return (
            token is not None
            and token.kind == "word"
            and token.value.lower() == word
        )

    def parse(self) -> FilterNode:
        node = self._parse_or()
        if self._peek() is not None:
            raise ScimError.invalid_filter("Trailing tokens in filter.")
        return node

    def _parse_or(self) -> FilterNode:
        node = self._parse_and()
        while self._is_keyword("or"):
            self._next()
            node = Or(node, self._parse_and())
        return node

    def _parse_and(self) -> FilterNode:
        node = self._parse_not()
        while self._is_keyword("and"):
            self._next()
            node = And(node, self._parse_not())
        return node

    def _parse_not(self) -> FilterNode:
        if self._is_keyword("not"):
            self._next()
            if self._peek() is None or self._peek().kind != "lparen":  # type: ignore[union-attr]
                raise ScimError.invalid_filter("'not' must be followed by '('.")
            self._next()  # consume '('
            node = self._parse_or()
            self._expect("rparen")
            return Not(node)
        return self._parse_primary()

    def _parse_primary(self) -> FilterNode:
        token = self._peek()
        if token is None:
            raise ScimError.invalid_filter("Unexpected end of filter.")
        if token.kind == "lparen":
            self._next()
            node = self._parse_or()
            self._expect("rparen")
            return node
        if token.kind == "word":
            return self._parse_attr_exp()
        raise ScimError.invalid_filter(f"Unexpected token: {token.value!r}")

    def _parse_attr_exp(self) -> FilterNode:
        attr = self._next().value  # attribute path word
        token = self._peek()

        # value-path: attr[ inner ]
        if token is not None and token.kind == "lbracket":
            self._next()
            inner = self._parse_or()
            self._expect("rbracket")
            return ValuePath(attr, inner)

        # unary presence: attr pr
        if self._is_keyword("pr"):
            self._next()
            return Comparison(attr, "pr", None)

        # binary comparison: attr <op> value
        op_token = self._next()
        if op_token.kind != "word" or op_token.value.lower() not in _COMPARATORS:
            raise ScimError.invalid_filter(
                f"Expected a comparison operator, got {op_token.value!r}"
            )
        value = self._parse_value()
        return Comparison(attr, op_token.value.lower(), value)

    def _parse_value(self) -> Any:
        token = self._next()
        if token.kind == "string":
            return _unquote(token.value)
        if token.kind == "number":
            return float(token.value) if "." in token.value else int(token.value)
        if token.kind == "word":
            lowered = token.value.lower()
            if lowered == "true":
                return True
            if lowered == "false":
                return False
            if lowered == "null":
                return None
            return token.value
        raise ScimError.invalid_filter(f"Invalid comparison value: {token.value!r}")

    def _expect(self, kind: str) -> _Token:
        token = self._next()
        if token.kind != kind:
            raise ScimError.invalid_filter(f"Expected {kind}, got {token.value!r}")
        return token


def parse_filter(text: str) -> FilterNode:
    """Parse a SCIM filter string into an AST (raises ScimError on failure)."""
    tokens = _tokenize(text)
    if not tokens:
        raise ScimError.invalid_filter("Empty filter.")
    return _Parser(tokens).parse()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _unquote(quoted: str) -> str:
    return quoted[1:-1].replace('\\"', '"').replace("\\\\", "\\")


def _resolve_path(resource: dict[str, Any], attr_path: str) -> list[Any]:
    """Resolve a (possibly dotted) attribute path to a flat list of values.

    Attribute name matching is case-insensitive. Multi-valued attributes fan out
    so a comparison can match "any entry".
    """
    current: list[Any] = [resource]
    for segment in attr_path.split("."):
        nxt: list[Any] = []
        for item in current:
            if not isinstance(item, dict):
                continue
            value = _get_ci(item, segment)
            if isinstance(value, list):
                nxt.extend(value)
            elif value is not None:
                nxt.append(value)
        current = nxt
    return current


def _get_ci(mapping: dict[str, Any], key: str) -> Any:
    if key in mapping:
        return mapping[key]
    lowered = key.lower()
    for existing_key, value in mapping.items():
        if existing_key.lower() == lowered:
            return value
    return None


def _compare(actual: Any, op: str, expected: Any) -> bool:
    if op == "eq":
        return _eq(actual, expected)
    if op == "ne":
        return not _eq(actual, expected)

    # String-oriented operators
    if op in ("co", "sw", "ew"):
        if actual is None or expected is None:
            return False
        actual_s, expected_s = str(actual).lower(), str(expected).lower()
        if op == "co":
            return expected_s in actual_s
        if op == "sw":
            return actual_s.startswith(expected_s)
        return actual_s.endswith(expected_s)

    # Ordering operators
    if op in ("gt", "ge", "lt", "le"):
        try:
            if op == "gt":
                return actual > expected
            if op == "ge":
                return actual >= expected
            if op == "lt":
                return actual < expected
            return actual <= expected
        except TypeError:
            actual_s, expected_s = str(actual), str(expected)
            if op == "gt":
                return actual_s > expected_s
            if op == "ge":
                return actual_s >= expected_s
            if op == "lt":
                return actual_s < expected_s
            return actual_s <= expected_s

    raise ScimError.invalid_filter(f"Unsupported operator: {op}")


def _eq(actual: Any, expected: Any) -> bool:
    if isinstance(actual, bool) or isinstance(expected, bool):
        return actual == expected
    if isinstance(actual, str) and isinstance(expected, str):
        # SCIM string comparison is case-insensitive unless caseExact.
        return actual.lower() == expected.lower()
    return actual == expected
