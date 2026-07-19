"""Unit tests for the keyword/regex matching engine."""

from om.standard_answers.matching import AnswerRule
from om.standard_answers.matching import StandardAnswerMatcher
from om.standard_answers.matching import tokenize_keywords


def _rule(
    keyword: str,
    *,
    match_regex: bool = False,
    match_any_keywords: bool = False,
    rule_id: int = 1,
) -> AnswerRule:
    return AnswerRule(
        id=rule_id,
        keyword=keyword,
        answer="canned answer",
        match_regex=match_regex,
        match_any_keywords=match_any_keywords,
    )


class TestTokenize:
    def test_splits_on_whitespace_and_commas(self) -> None:
        assert tokenize_keywords("reset, password  vpn") == ["reset", "password", "vpn"]

    def test_empty(self) -> None:
        assert tokenize_keywords("") == []
        assert tokenize_keywords("   ") == []


class TestKeywordMatchingAny:
    def test_matches_if_any_token_present(self) -> None:
        m = StandardAnswerMatcher()
        rule = _rule("vpn wifi network", match_any_keywords=True)
        assert m.matches(rule, "my wifi keeps dropping") is True

    def test_no_token_present(self) -> None:
        m = StandardAnswerMatcher()
        rule = _rule("vpn wifi network", match_any_keywords=True)
        assert m.matches(rule, "how do I reset my password") is False


class TestKeywordMatchingAll:
    def test_requires_every_token(self) -> None:
        m = StandardAnswerMatcher()
        rule = _rule("reset password", match_any_keywords=False)
        assert m.matches(rule, "how do I reset my password today") is True
        assert m.matches(rule, "how do I reset my account") is False


class TestWordBoundaries:
    def test_token_matches_on_word_boundary_only(self) -> None:
        m = StandardAnswerMatcher()
        rule = _rule("api", match_any_keywords=True)
        assert m.matches(rule, "the API is down") is True
        # "api" must not match inside "capitalize"
        assert m.matches(rule, "please capitalize the title") is False

    def test_case_insensitive(self) -> None:
        m = StandardAnswerMatcher()
        rule = _rule("Refund", match_any_keywords=True)
        assert m.matches(rule, "i want a REFUND") is True


class TestRegexMatching:
    def test_regex_match(self) -> None:
        m = StandardAnswerMatcher()
        rule = _rule(r"error code \d{3}", match_regex=True)
        assert m.matches(rule, "I got error code 502 today") is True
        assert m.matches(rule, "I got an error") is False

    def test_unsafe_regex_treated_as_non_matching(self) -> None:
        # A catastrophic pattern that slipped past write-time validation (e.g. legacy
        # data) must fail closed, not raise or hang.
        m = StandardAnswerMatcher()
        rule = _rule(r"(a+)+$", match_regex=True)
        assert m.matches(rule, "a" * 40 + "!") is False


class TestEdgeCases:
    def test_empty_message_never_matches(self) -> None:
        m = StandardAnswerMatcher()
        assert m.matches(_rule("hello", match_any_keywords=True), "") is False

    def test_empty_keyword_never_matches(self) -> None:
        m = StandardAnswerMatcher()
        assert m.matches(_rule("", match_any_keywords=True), "hello world") is False
        assert m.matches(_rule("   ", match_any_keywords=False), "hello world") is False

    def test_find_matches_preserves_order_and_filters(self) -> None:
        m = StandardAnswerMatcher()
        rules = [
            _rule("vpn", match_any_keywords=True, rule_id=1),
            _rule("refund", match_any_keywords=True, rule_id=2),
            _rule("password", match_any_keywords=True, rule_id=3),
        ]
        matched = m.find_matches(rules, "my vpn needs a new password")
        assert [r.id for r in matched] == [1, 3]
