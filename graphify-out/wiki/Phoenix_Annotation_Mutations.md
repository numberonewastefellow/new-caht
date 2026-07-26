# Phoenix Annotation Mutations

> 261 nodes · cohesion 0.03

## Key Concepts

- **User** (248 connections) — `phoenix/src/phoenix/server/api/types/User.py`
- **SpanAnnotation** (132 connections) — `phoenix/src/phoenix/server/api/types/SpanAnnotation.py`
- **from_global_id_with_expected_type()** (123 connections) — `phoenix/src/phoenix/server/api/types/node.py`
- **AnnotationSource** (99 connections) — `phoenix/src/phoenix/server/api/types/AnnotationSource.py`
- **AnnotatorKind** (67 connections) — `phoenix/src/phoenix/server/api/types/AnnotatorKind.py`
- **ProjectSessionAnnotation** (61 connections) — `phoenix/src/phoenix/server/api/types/ProjectSessionAnnotation.py`
- **Annotation** (43 connections) — `phoenix/src/phoenix/server/api/types/Annotation.py`
- **PatchAnnotationInput** (25 connections) — `phoenix/src/phoenix/server/api/input_types/PatchAnnotationInput.py`
- **annotations.py** (24 connections) — `phoenix/src/phoenix/server/api/routers/v1/annotations.py`
- **DeleteAnnotationsInput** (23 connections) — `phoenix/src/phoenix/server/api/input_types/DeleteAnnotationsInput.py`
- **.exists()** (22 connections) — `backend/om/server/rate_limits/cache.py`
- **Context** (18 connections) — `phoenix/src/phoenix/server/api/types/DocumentAnnotation.py`
- **Info** (18 connections) — `phoenix/src/phoenix/server/api/types/DocumentAnnotation.py`
- **Context** (18 connections) — `phoenix/src/phoenix/server/api/types/SpanAnnotation.py`
- **Info** (18 connections) — `phoenix/src/phoenix/server/api/types/SpanAnnotation.py`
- **SpanAnnotationMutationMixin** (17 connections) — `phoenix/src/phoenix/server/api/mutations/span_annotations_mutations.py`
- **get_project_by_identifier()** (17 connections) — `phoenix/src/phoenix/server/api/routers/v1/utils.py`
- **SpanAnnotationMutationPayload** (16 connections) — `phoenix/src/phoenix/server/api/mutations/span_annotations_mutations.py`
- **Context** (16 connections) — `phoenix/src/phoenix/server/api/types/ProjectSessionAnnotation.py`
- **Info** (16 connections) — `phoenix/src/phoenix/server/api/types/ProjectSessionAnnotation.py`
- **DocumentAnnotationInsertEvent** (16 connections) — `phoenix/src/phoenix/server/dml_event.py`
- **User.py** (16 connections) — `phoenix/src/phoenix/server/api/types/User.py`
- **DocumentAnnotationMutationMixin** (15 connections) — `phoenix/src/phoenix/server/api/mutations/document_annotations_mutations.py`
- **Context** (15 connections) — `phoenix/src/phoenix/server/api/mutations/span_annotations_mutations.py`
- **Info** (15 connections) — `phoenix/src/phoenix/server/api/mutations/span_annotations_mutations.py`
- *... and 236 more nodes in this community*

## Relationships

- [[Phoenix Experiment Comparison Queries]] (221 shared connections)
- [[Phoenix Experiment Queries]] (125 shared connections)
- [[Phoenix Dataset Events]] (121 shared connections)
- [[Community 110]] (37 shared connections)
- [[Community 101]] (33 shared connections)
- [[Community 131]] (29 shared connections)
- [[Community 247]] (26 shared connections)
- [[Phoenix Model Store Tests]] (14 shared connections)
- [[Phoenix GraphQL DataLoaders]] (14 shared connections)
- [[Community 97]] (10 shared connections)
- [[Community 765]] (9 shared connections)
- [[Community 66]] (7 shared connections)

## Source Files

- `backend/om/server/rate_limits/cache.py`
- `phoenix/src/phoenix/server/api/helpers/annotations.py`
- `phoenix/src/phoenix/server/api/input_types/CreateDocumentAnnotationInput.py`
- `phoenix/src/phoenix/server/api/input_types/CreateProjectSessionAnnotationInput.py`
- `phoenix/src/phoenix/server/api/input_types/CreateSpanAnnotationInput.py`
- `phoenix/src/phoenix/server/api/input_types/CreateTraceAnnotationInput.py`
- `phoenix/src/phoenix/server/api/input_types/DeleteAnnotationsInput.py`
- `phoenix/src/phoenix/server/api/input_types/PatchAnnotationInput.py`
- `phoenix/src/phoenix/server/api/input_types/UpdateAnnotationInput.py`
- `phoenix/src/phoenix/server/api/mutations/document_annotations_mutations.py`
- `phoenix/src/phoenix/server/api/mutations/project_session_annotations_mutations.py`
- `phoenix/src/phoenix/server/api/mutations/span_annotations_mutations.py`
- `phoenix/src/phoenix/server/api/mutations/trace_annotations_mutations.py`
- `phoenix/src/phoenix/server/api/routers/v1/annotations.py`
- `phoenix/src/phoenix/server/api/routers/v1/utils.py`
- `phoenix/src/phoenix/server/api/types/Annotation.py`
- `phoenix/src/phoenix/server/api/types/AnnotationSource.py`
- `phoenix/src/phoenix/server/api/types/AnnotatorKind.py`
- `phoenix/src/phoenix/server/api/types/DocumentAnnotation.py`
- `phoenix/src/phoenix/server/api/types/ProjectSession.py`

## Audit Trail

- EXTRACTED: 993 (40%)
- INFERRED: 1480 (60%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*