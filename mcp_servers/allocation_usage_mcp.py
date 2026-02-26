"""MCP Server for Allocation Usage Data

This server provides tools to query allocation SKU records from the revenue system.
The allocation SKU records represent billable allocations that meet specific criteria:
- Non-contract allocations (contract = False)
- Flagged for billing (flag = True)
- Active allocations (allocations > 0)
- Recently processed (last_run within last 12 months)

Uses stdio transport for local communication with MCP clients.
Connects to FastAPI backend on port 8001 for data retrieval.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path to import api module
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from mcp.server import FastMCP

# Initialize the FastMCP server
mcp = FastMCP("allocation-usage-server")

# Base URL for the FastAPI allocation metrics service
BASE_URL = "http://localhost:8000"


@mcp.tool()
async def get_allocation_sku_records() -> str:
    """Retrieve allocation SKU records matching specific billing criteria.

    This tool queries allocation records that are eligible for SKU-based billing.
    The records returned meet the following criteria:
    - contract = False (non-contract allocations)
    - flag = True (flagged for billing)
    - allocations > 0 (has active allocations)
    - last_run within last 12 months (recently processed, rolling window)

    Returns:
        JSON string containing list of allocation SKU records with fields:
        - sfdc_link: Salesforce link status (bool)
        - cny: Company identifier/CNY code (str)
        - company_id: Company name/identifier (str)
        - intacct_cid: Intacct customer ID (str)
        - parent: Parent company/organization name (str)
        - link: Link type/category (str)
        - intacct: Intacct integration status (bool)
        - contract: Contract status (bool)
        - flag: Billing flag status (bool)
        - contract_link: Contract link status (bool)
        - subscribed: Subscription date (ISO date string)
        - allocations: Number of allocations (int)
        - last_gl: Last general ledger date (ISO date string)
        - last_run: Last processing run date (ISO date string)

    Example usage:
        Use this tool to identify companies with billable allocations that need
        to be processed for revenue recognition. The results can be used for:
        - Monthly billing cycles
        - Revenue forecasting
        - Allocation usage tracking
        - Identifying active non-contract customers
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/allocation-sku")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


async def main():
    """Run the MCP server using stdio transport."""
    await mcp.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())
