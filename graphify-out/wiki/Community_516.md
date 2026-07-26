# Community 516

> 30 nodes · cohesion 0.09

## Key Concepts

- **parse_litellm_model_name()** (14 connections) — `backend/om/llm/model_name_parser.py`
- **model_name_parser.py** (10 connections) — `backend/om/llm/model_name_parser.py`
- **test_model_name_parser.py** (5 connections) — `backend/tests/unit/om/llm/test_model_name_parser.py`
- **_generate_provider_display_name()** (4 connections) — `backend/om/llm/model_name_parser.py`
- **ParsedModelName** (4 connections) — `backend/om/llm/model_name_parser.py`
- **_extract_provider()** (3 connections) — `backend/om/llm/model_name_parser.py`
- **_extract_region()** (3 connections) — `backend/om/llm/model_name_parser.py`
- **_format_name()** (3 connections) — `backend/om/llm/model_name_parser.py`
- **_generate_display_name_from_model()** (3 connections) — `backend/om/llm/model_name_parser.py`
- **_get_model_info()** (3 connections) — `backend/om/llm/model_name_parser.py`
- **_infer_vendor_from_model_name()** (3 connections) — `backend/om/llm/model_name_parser.py`
- **test_bedrock_model_with_enrichment()** (3 connections) — `backend/tests/unit/om/llm/test_model_name_parser.py`
- **test_direct_provider_inference()** (3 connections) — `backend/tests/unit/om/llm/test_model_name_parser.py`
- **test_region_extraction()** (3 connections) — `backend/tests/unit/om/llm/test_model_name_parser.py`
- **test_unknown_model_fallback()** (3 connections) — `backend/tests/unit/om/llm/test_model_name_parser.py`
- **LiteLLM Model Name Parser  Parses LiteLLM model strings and returns structured m** (1 connections) — `backend/om/llm/model_name_parser.py`
- **Generate a human-friendly display name from a model identifier.      Used as fal** (1 connections) — `backend/om/llm/model_name_parser.py`
- **Generate provider display name with model brand and vendor info.      Examples:** (1 connections) — `backend/om/llm/model_name_parser.py`
- **Parse a LiteLLM model string into structured data.      Metadata comes from enri** (1 connections) — `backend/om/llm/model_name_parser.py`
- **Structured representation of a parsed LiteLLM model name.** (1 connections) — `backend/om/llm/model_name_parser.py`
- **Get model info from litellm.model_cost.** (1 connections) — `backend/om/llm/model_name_parser.py`
- **Extract provider from model key prefix.** (1 connections) — `backend/om/llm/model_name_parser.py`
- **Extract region from model key (e.g., us., eu., apac. prefix).** (1 connections) — `backend/om/llm/model_name_parser.py`
- **Format provider or vendor name with proper capitalization.** (1 connections) — `backend/om/llm/model_name_parser.py`
- **Infer vendor from model name patterns when enrichment data is missing.      Uses** (1 connections) — `backend/om/llm/model_name_parser.py`
- *... and 5 more nodes in this community*

## Relationships

- [[Community 155]] (1 shared connections)
- [[Analytics & Usage Models (WS-H)]] (1 shared connections)

## Source Files

- `backend/om/llm/model_name_parser.py`
- `backend/tests/unit/om/llm/test_model_name_parser.py`

## Audit Trail

- EXTRACTED: 73 (89%)
- INFERRED: 9 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*