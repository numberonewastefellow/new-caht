"""RAG benchmark: scored retrieval + answer-quality runs over a fixed corpus.

Sibling of the tool-assertion eval in ``om.evals``. It talks to a running
(scratch) stack over HTTP only; nothing here is imported by the server.
Entry point: ``python -m om.evals.rag_benchmark.benchmark_cli``.
"""
