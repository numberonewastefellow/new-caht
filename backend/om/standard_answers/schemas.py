"""Pydantic DTOs for the standard-answers API.

Field names/shapes are the **frozen frontend contract** (the admin UI + query API
already speak these), so they are preserved exactly even though the implementation
behind them is clean-room. Owned by WS-D; supersedes the DTOs that lived in
``om/server/manage/models.py``.
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from om.db.models import StandardAnswer as StandardAnswerModel
from om.db.models import StandardAnswerCategory as StandardAnswerCategoryModel


# --- categories -----------------------------------------------------------------


class StandardAnswerCategoryCreationRequest(BaseModel):
    name: str


class StandardAnswerCategory(BaseModel):
    id: int
    name: str

    @classmethod
    def from_model(
        cls, model: StandardAnswerCategoryModel
    ) -> "StandardAnswerCategory":
        return cls(id=model.id, name=model.name)


# --- answers --------------------------------------------------------------------


class StandardAnswer(BaseModel):
    id: int
    keyword: str
    answer: str
    categories: list[StandardAnswerCategory]
    match_regex: bool
    match_any_keywords: bool

    @classmethod
    def from_model(cls, model: StandardAnswerModel) -> "StandardAnswer":
        return cls(
            id=model.id,
            keyword=model.keyword,
            answer=model.answer,
            categories=[
                StandardAnswerCategory.from_model(c) for c in model.categories
            ],
            match_regex=model.match_regex,
            match_any_keywords=model.match_any_keywords,
        )


class StandardAnswerCreationRequest(BaseModel):
    keyword: str
    answer: str
    categories: list[int]
    match_regex: bool
    match_any_keywords: bool

    @field_validator("categories")
    @classmethod
    def _require_at_least_one_category(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("At least one category must be attached to a standard answer.")
        return value


# --- per-tenant config ----------------------------------------------------------


class StandardAnswerConfigResponse(BaseModel):
    enabled: bool
    max_matches_per_message: int
    match_input_char_limit: int


class StandardAnswerConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    max_matches_per_message: int | None = Field(default=None, ge=1, le=25)
    match_input_char_limit: int | None = Field(default=None, ge=100, le=100_000)


# --- stateless query endpoint ---------------------------------------------------


class StandardAnswerQueryRequest(BaseModel):
    message: str
    slack_bot_categories: list[str]


class StandardAnswerQueryResponse(BaseModel):
    standard_answers: list[StandardAnswer] = Field(default_factory=list)
