"""Search result DTO shared by the orchestrator, packets, and API layer.

``SearchDocWithContent`` is the on-the-wire result document. It is exactly the
MIT ``SearchDoc`` plus an optional ``content`` field (populated only when the
caller requests ``include_content``), matching the frontend
``SearchDocWithContent`` interface field-for-field.
"""

from om.context.search.models import InferenceSection
from om.context.search.models import SearchDoc


class SearchDocWithContent(SearchDoc):
    content: str | None = None

    @classmethod
    def from_section(
        cls, section: InferenceSection, include_content: bool = False
    ) -> "SearchDocWithContent":
        base = SearchDoc.from_chunks_or_sections([section])
        if not base:
            # Fall back to the center chunk if conversion produced nothing.
            base = SearchDoc.from_chunks_or_sections([section.center_chunk])
        payload = base[0].model_dump()
        return cls(
            **payload,
            content=section.combined_content if include_content else None,
        )

    @classmethod
    def from_sections(
        cls, sections: list[InferenceSection], include_content: bool = False
    ) -> list["SearchDocWithContent"]:
        return [cls.from_section(section, include_content) for section in sections]
