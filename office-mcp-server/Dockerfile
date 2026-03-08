FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    office-powerpoint-mcp-server \
    office-word-mcp-server

# Create directories for templates, output, and documents
RUN mkdir -p /app/templates /app/output /app/documents

COPY server.py /app/server.py

ENV PPT_TEMPLATE_PATH=/app/templates

EXPOSE 8100

CMD ["python", "/app/server.py"]
