# API Usage MCP Server

MCP server that exposes usage and billing-related tools via stdin/stdout for local testing.

Quick facts:

- Starts with: `python -m mcp_servers.api_usage_mcp`
- Exposes query tools (time, account, partner, metric filters) plus `generate_bill`
- Tools return JSON-formatted strings; the `generate_bill` tool posts to the FastAPI `/generate-bill` endpoint

Run notes:

1. Ensure the FastAPI backend is running: `uvicorn api.metrics:app --reload` (port 8000)
2. Start the MCP server: `python -m mcp_servers.api_usage_mcp`
3. Use the repository test scripts to exercise tools: `uv run python test_mcp_query.py`, `uv run python test_bill_generation_mcp.py`

Relevant files:

- `mcp_servers/api_usage_mcp.py` — main tool definitions and `generate_bill`
- `mcp_servers/allocation_usage_mcp.py` — allocation-specific tool(s)
- `mcp_clients/api_usage_mcp_client.py` — example client showing LLM tool calling loop

Updated: 2026-03-11
