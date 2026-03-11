import argparse
import json
import os
import time
from typing import List

import httpx

from verification.pdf_parser import parse_pdf
from verification.comparator import compare
from verification.reporting import write_report, summary_text
# Note: redaction removed — reports are returned unmodified
import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def post_generate_bill(api_url: str, payload: dict) -> List[str]:
    url = api_url.rstrip("/") + "/generate-bill"
    resp = httpx.post(url, json=payload, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


def find_existing_files(prefix: str = "bills/"):
    if not os.path.isdir(prefix):
        return []
    files = [os.path.join(prefix, f) for f in os.listdir(prefix) if f.lower().endswith('.pdf')]
    files.sort(key=lambda p: os.path.getmtime(p))
    return files


def run_api_flow(payload_path: str, api_url: str) -> dict:
    with open(payload_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # snapshot existing files
    before = set(find_existing_files())

    pdf_paths = post_generate_bill(api_url, payload)

    # allow some time for file writes if needed
    time.sleep(0.5)

    results = []
    for idx, pdf in enumerate(pdf_paths):
        parsed = parse_pdf(pdf)
        bill_req = payload.get("bills", [])[idx] if idx < len(payload.get("bills", [])) else {}
        diff = compare(bill_req, parsed)
        # Also compare against canonical UsageData aggregates when possible
        try:
            from verification.comparator import compare_with_usage_data

            usage_diff = compare_with_usage_data(bill_req, parsed)
        except Exception:
            usage_diff = {"passed": False, "reason": "compare_with_usage_data_failed"}

        results.append({"pdf": pdf, "bill": bill_req, "parsed": parsed, "diff": diff, "usage_diff": usage_diff})

    report = {"run_id": int(time.time()), "mode": "api", "api_url": api_url, "results": results}
    return report


def _run_api_flow_payload(payload: dict, api_url: str) -> dict:
    """Internal: Run the API-mode verification given an in-memory payload dict.

    This is intentionally a private API; verification should be invoked via MCP tool.
    """
    pdf_paths = post_generate_bill(api_url, payload)

    # allow some time for file writes if needed
    time.sleep(0.5)

    results = []
    for idx, pdf in enumerate(pdf_paths):
        parsed = parse_pdf(pdf)
        bill_req = payload.get("bills", [])[idx] if idx < len(payload.get("bills", [])) else {}
        diff = compare(bill_req, parsed)
        try:
            from verification.comparator import compare_with_usage_data

            usage_diff = compare_with_usage_data(bill_req, parsed)
        except Exception:
            usage_diff = {"passed": False, "reason": "compare_with_usage_data_failed"}

        results.append({"pdf": pdf, "bill": bill_req, "parsed": parsed, "diff": diff, "usage_diff": usage_diff})

    report = {"run_id": int(time.time()), "mode": "api", "api_url": api_url, "results": results}
    return report


def _run_verification_payload(payload: dict, api_url: str = "http://localhost:8000") -> dict:
    """Private wrapper used by MCP tool to run verification in-process.

    External callers should use the MCP tool `verify_bills` instead of calling
    this function directly.
    """
    return _run_api_flow_payload(payload, api_url)


async def run_mcp_flow_async(payload_path: str, server_script_path: str) -> dict:
    """Start MCP server as a subprocess via stdio client and call generate_bill tool."""
    with open(payload_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    exit_stack = AsyncExitStack()
    await exit_stack.__aenter__()
    try:
        stdio_ctx = await exit_stack.enter_async_context(
            stdio_client(StdioServerParameters(command="uv", args=["run", "python", server_script_path], env=None))
        )
        stdio, write = stdio_ctx

        session = await exit_stack.enter_async_context(ClientSession(stdio, write))
        await session.initialize()

        # Call the generate_bill tool directly
        try:
            tool_result = await session.call_tool("generate_bill", {"bills": payload.get("bills", [])})
        except Exception as e:
            await exit_stack.aclose()
            return {"run_id": int(time.time()), "mode": "mcp", "error": str(e), "results": []}

        # Extract text from tool_result
        tool_text = ""
        try:
            if hasattr(tool_result, "content"):
                for c in tool_result.content:
                    if hasattr(c, "text") and c.text:
                        tool_text += c.text
                    elif isinstance(c, str):
                        tool_text += c
            elif isinstance(tool_result, str):
                tool_text = tool_result
        except Exception:
            tool_text = str(tool_result)

        # tool_text expected to be JSON list of pdf paths or error object
        try:
            pdf_paths = json.loads(tool_text)
        except Exception:
            # if parsing failed, attempt to find file paths substrings
            pdf_paths = []
            for line in tool_text.splitlines():
                line = line.strip().strip('"')
                if line.lower().endswith('.pdf'):
                    pdf_paths.append(line)

        results = []
        for idx, pdf in enumerate(pdf_paths):
            parsed = parse_pdf(pdf)
            bill_req = payload.get("bills", [])[idx] if idx < len(payload.get("bills", [])) else {}
            diff = compare(bill_req, parsed)
            try:
                from verification.comparator import compare_with_usage_data
                usage_diff = compare_with_usage_data(bill_req, parsed)
            except Exception:
                usage_diff = {"passed": False, "reason": "compare_with_usage_data_failed"}

            results.append({"pdf": pdf, "bill": bill_req, "parsed": parsed, "diff": diff, "usage_diff": usage_diff})

        report = {"run_id": int(time.time()), "mode": "mcp", "server_script": server_script_path, "results": results}
        await exit_stack.aclose()
        return report
    finally:
        try:
            await exit_stack.aclose()
        except Exception:
            pass


def run_mcp_flow(payload_path: str, server_script_path: str) -> dict:
    return asyncio.run(run_mcp_flow_async(payload_path, server_script_path))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["api","mcp"], default="api")
    p.add_argument("--payload", required=True)
    p.add_argument("--api-url", default="http://localhost:8000")
    p.add_argument("--server-script", default="mcp_servers/api_usage_mcp.py", help="Path to MCP server script for stdio launch")
    p.add_argument("--out", default="verification_report.json")
    args = p.parse_args()

    if args.mode == "api":
        report = run_api_flow(args.payload, args.api_url)
        write_report(report, args.out)
        print(summary_text(report))
    elif args.mode == "mcp":
        # run mcp flow (this wrapper is synchronous)
        report = run_mcp_flow(args.payload, args.server_script)
        write_report(report, args.out)
        print(summary_text(report))
    else:
        raise NotImplementedError("Only 'api' mode is implemented in MVP")


if __name__ == "__main__":
    main()
