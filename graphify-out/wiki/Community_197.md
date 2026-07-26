# Community 197

> 66 nodes · cohesion 0.05

## Key Concepts

- **get_image_generation_provider()** (13 connections) — `backend/om/image_gen/factory.py`
- **AzureImageGenerationProvider** (10 connections) — `backend/om/image_gen/providers/azure_img_gen.py`
- **OpenAIImageGenerationProvider** (10 connections) — `backend/om/image_gen/providers/openai_img_gen.py`
- **VertexImageGenerationProvider** (10 connections) — `backend/om/image_gen/providers/vertex_img_gen.py`
- **MockImageGenerationProvider** (9 connections) — `backend/tests/external_dependency_unit/mock_image_provider.py`
- **test_provider_building.py** (9 connections) — `backend/tests/unit/om/image_gen/test_provider_building.py`
- **_get_default_image_gen_creds()** (9 connections) — `backend/tests/unit/om/image_gen/test_provider_building.py`
- **ImageGenerationProviderName** (7 connections) — `backend/om/image_gen/factory.py`
- **_parse_to_vertex_credentials()** (6 connections) — `backend/om/image_gen/providers/vertex_img_gen.py`
- **ImageGenerationProvider** (5 connections) — `backend/om/image_gen/factory.py`
- **ImageGenerationProviderCredentials** (5 connections) — `backend/om/image_gen/factory.py`
- **mock_image_provider.py** (5 connections) — `backend/tests/external_dependency_unit/mock_image_provider.py`
- **use_mock_image_generation_provider()** (5 connections) — `backend/tests/external_dependency_unit/mock_image_provider.py`
- **factory.py** (5 connections) — `backend/om/image_gen/factory.py`
- **_get_provider_cls()** (5 connections) — `backend/om/image_gen/factory.py`
- **ImageGenerationProvider** (5 connections)
- **ImageGenerationProviderCredentials** (4 connections) — `backend/tests/unit/om/image_gen/test_provider_building.py`
- **_create_mock_image_generation_llm_config()** (4 connections) — `backend/tests/external_dependency_unit/mock_image_provider.py`
- **ImageGenerationProviderController** (4 connections) — `backend/tests/external_dependency_unit/mock_image_provider.py`
- **ImageProviderCredentialsError** (4 connections) — `backend/om/image_gen/exceptions.py`
- **vertex_img_gen.py** (4 connections) — `backend/om/image_gen/providers/vertex_img_gen.py`
- **VertexCredentials** (4 connections) — `backend/om/image_gen/providers/vertex_img_gen.py`
- **ImageGenerationProviderCredentials** (3 connections) — `backend/om/image_gen/providers/vertex_img_gen.py`
- **._build_from_credentials()** (3 connections) — `backend/tests/external_dependency_unit/mock_image_provider.py`
- **.generate_image()** (3 connections) — `backend/tests/external_dependency_unit/mock_image_provider.py`
- *... and 41 more nodes in this community*

## Relationships

- [[Community 72]] (3 shared connections)
- [[Community 106]] (2 shared connections)
- [[Agent Tracing Processor]] (1 shared connections)
- [[Community 115]] (1 shared connections)
- [[Community 1079]] (1 shared connections)
- [[Community 260]] (1 shared connections)
- [[Community 267]] (1 shared connections)
- [[Agent Chat Packets & Citations]] (1 shared connections)
- [[Analytics & Usage Models (WS-H)]] (1 shared connections)

## Source Files

- `backend/om/image_gen/exceptions.py`
- `backend/om/image_gen/factory.py`
- `backend/om/image_gen/providers/azure_img_gen.py`
- `backend/om/image_gen/providers/openai_img_gen.py`
- `backend/om/image_gen/providers/vertex_img_gen.py`
- `backend/tests/external_dependency_unit/mock_image_provider.py`
- `backend/tests/unit/om/image_gen/test_provider_building.py`

## Audit Trail

- EXTRACTED: 186 (81%)
- INFERRED: 44 (19%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*