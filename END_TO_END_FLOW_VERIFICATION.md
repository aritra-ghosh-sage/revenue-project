### Allocation Usage FastAPI Server
# End-to-End Flow Verification (summary)

Snapshot: local verification notes and how to run end-to-end checks for the MCP + FastAPI flows.

What this repo contains:

- FastAPI backends in `api/` (usage and allocation)
- MCP servers in `mcp_servers/` exposing query tools and a `generate_bill` tool
- Test and verification scripts at repository root (e.g., `test_all_mcp_flows.py`, `test_bill_generation_mcp.py`)
- PDF verification tools and runner in `verification/`

How to run verification locally:

1. Activate virtual environment and install deps (if needed):

```powershell
& .venv\Scripts\Activate.ps1
uv sync
```

2. Start API servers:

```powershell
uvicorn api.metrics:app --reload
uvicorn api.allocation_metrics:app --port 8001 --reload
```

3. Start MCP servers (separate terminals):

```powershell
python -m mcp_servers.api_usage_mcp
python -m mcp_servers.allocation_usage_mcp
```

4. Run the test runner or individual tests:

```powershell
uv run python test_all_mcp_flows.py
uv run python test_bill_generation_mcp.py
pytest
```

Files to check after running flows:

- `reports/` under `verification/` for PDF parsing output
- `bills/` for generated PDF bill artifacts

If you see failures, inspect the FastAPI logs (terminal running `uvicorn`) and the MCP server STDOUT for tool-call traces.

Updated: 2026-03-11
