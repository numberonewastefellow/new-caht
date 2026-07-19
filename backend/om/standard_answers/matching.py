"""Keyword / regex matching engine for standard answers (pure, persistence-free).

Operates on :class:`AnswerRule` value objects so it is fully decoupled from the ORM
and trivially unit-testable. The service layer maps persisted rows to ``AnswerRule``
and calls :meth:`StandardAnswerMatcher.find_matches`.

Matching model (see module README):
- **regex mode** (``match_regex=True``): the ``keyword`` field is a regular
  expression, matched with :class:`~om.standard_answers.safe_regex.SafeRegex`
  (ReDoS-guarded, case-insensitive, length-capped).
- **keyword mode** (``match_regex=False``): the ``keyword`` field is a list of
  whitespace/comma-separated tokens. Each token is matched case-insensitively on a
  word boundary. ``match_any_keywords=True`` → match if ANY token is present
  (One-Match); ``False`` → match only if EVERY token is present (All-Match).

A rule with no usable trigger tokens never matches (fail-closed).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field

from om.standard_answers.safe_regex import SafeRegex
from om.standard_answers.safe_regex import UnsafeRegexError

# Split a keyword field into tokens on whitespace and commas.
_TOKEN_SPLIT = re.compile(r"[\s,]+")


@dataclass(frozen=True, slots=True)
class AnswerRule:
    """Persistence-free view of a standard answer, sufficient to match a message."""

    id: int
    keyword: str
    answer: str
    match_regex: bool
    match_any_keywords: bool
    category_ids: frozenset[int] = field(default_factory=frozenset)


def tokenize_keywords(keyword: str) -> list[str]:
    """Split a keyword-mode trigger string into individual, non-empty tokens."""

    if not keyword:
        return []
    return [tok for tok in _TOKEN_SPLIT.split(keyword.strip()) if tok]


class StandardAnswerMatcher:
    """Matches messages against standard-answer rules.

    Compiled regexes and per-token word-boundary matchers are memoised for the life
    of the instance, so create one matcher per handling pass and reuse it across the
    channel's candidate rules.
    """

    def __init__(self) -> None:
        self._regex_cache: dict[str, SafeRegex | None] = {}
        self._token_cache: dict[str, re.Pattern[str]] = {}

    # -- public API --------------------------------------------------------------

    def matches(self, rule: AnswerRule, message: str) -> bool:
        """True if ``message`` triggers ``rule`` under the rule's match mode."""

        if not message:
            return False
        if rule.match_regex:
            return self._regex_matches(rule.keyword, message)
        return self._keyword_matches(rule, message)

    def find_matches(
        self, rules: list[AnswerRule], message: str
    ) -> list[AnswerRule]:
        """Return every rule triggered by ``message``, preserving input order."""

        return [rule for rule in rules if self.matches(rule, message)]

    # -- regex mode --------------------------------------------------------------

    def _regex_matches(self, pattern: str, message: str) -> bool:
        compiled = self._compiled_regex(pattern)
        if compiled is None:
            return False
        return compiled.search(message)

    def _compiled_regex(self, pattern: str) -> SafeRegex | None:
        if pattern not in self._regex_cache:
            try:
                self._regex_cache[pattern] = SafeRegex.compile(pattern)
            except UnsafeRegexError:
                # A rule that fails validation at match time (e.g. legacy data) is
                # treated as non-matching rather than raising into the hot path.
                self._regex_cache[pattern] = None
        return self._regex_cache[pattern]

    # -- keyword mode ------------------------------------------------------------

    def _keyword_matches(self, rule: AnswerRule, message: str) -> bool:
        tokens = tokenize_keywords(rule.keyword)
        if not tokens:
            return False
        present = (self._token_present(tok, message) for tok in tokens)
        if rule.match_any_keywords:
            return any(present)
        return all(present)

    def _token_present(self, token: str, message: str) -> bool:
        return self._token_matcher(token).search(message) is not None

    def _token_matcher(self, token: str) -> re.Pattern[str]:
        if token not in self._token_cache:
            # re.escape ⇒ the token is a literal (no user quantifiers → ReDoS-safe).
            # Lookarounds anchor on "not adjacent to a word char", so "api" does not
            # match inside "capitalize" yet punctuation tokens (e.g. "c++") still work
            # where a plain \b would fail on the trailing non-word char.
            self._token_cache[token] = re.compile(
                rf"(?<!\w){re.escape(token)}(?!\w)", re.IGNORECASE
            )
        return self._token_cache[token]
