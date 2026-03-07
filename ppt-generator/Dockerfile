FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir office-powerpoint-mcp-server

# Create directories for templates and output
RUN mkdir -p /app/templates /app/output

ENV PPT_TEMPLATE_PATH=/app/templates

EXPOSE 8100

# Run MCP server in HTTP (streamable-http) mode
# The entry point script doesn't pass CLI args to main(), so we invoke the module directly.
# We patch the host to 0.0.0.0 so it's accessible from outside the container.
CMD ["python", "-c", "from ppt_mcp_server import app; app.settings.port = 8100; app.settings.host = '0.0.0.0'; app.settings.transport_security.enable_dns_rebinding_protection = False; app.run(transport='streamable-http')"]
