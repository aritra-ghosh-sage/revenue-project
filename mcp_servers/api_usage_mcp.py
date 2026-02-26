"""MCP Server for API Usage Data

This server provides tools to query usage data from the revenue system.
Uses stdio transport for local communication.
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
mcp = FastMCP("api-usage-server")

# Base URL for the FastAPI metrics service
BASE_URL = "http://localhost:8000"


@mcp.tool()
async def get_usage_by_period(period: str) -> str:
    """Retrieve usage data for a specific billing period.

    Args:
        period: Billing period identifier (e.g., "January 2026")

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/period/{period}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_contract(contract_id: str) -> str:
    """Retrieve usage data filtered by contract ID.

    Args:
        contract_id: Contract identifier (e.g., "C20506")

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/contract/{contract_id}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_company(company_id: str) -> str:
    """Retrieve usage data filtered by company/order ID.

    Args:
        company_id: Company or order identifier (e.g., "C1922")

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/company/{company_id}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_account_name(account_name: str) -> str:
    """Retrieve usage data filtered by account name (partial match).

    Args:
        account_name: Account name identifier

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/account/{account_name}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_account_owner(account_owner: str) -> str:
    """Retrieve usage data filtered by account owner (partial match).

    Args:
        account_owner: Account owner name

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/account-owner/{account_owner}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_channel(channel: str) -> str:
    """Retrieve usage data filtered by sales channel.

    Args:
        channel: Sales channel identifier (e.g., "Direct", "VAR")

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/channel/{channel}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_partner(partner: str) -> str:
    """Retrieve usage data filtered by partner name.

    Args:
        partner: Partner name identifier

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/partner/{partner}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_total_usage(usage: str) -> str:
    """Retrieve usage data filtered by total usage (>= comparison).

    Args:
        usage: Minimum total usage value (returns records >= this value)

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/total-usage/{usage}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_over_usage(over_usage: str) -> str:
    """Retrieve usage data filtered by total overage usage (>= comparison).

    Args:
        over_usage: Minimum total overage value (returns records >= this value)

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/over-usage/{over_usage}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_estimated_dollars(estimated_dollars: str) -> str:
    """Retrieve usage data filtered by total estimated revenue (>= comparison).

    Args:
        estimated_dollars: Minimum total estimated dollar value (returns records >= this value)

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/usage/estimated-dollars/{estimated_dollars}"
        )
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_api_usage(api_usage: str) -> str:
    """Retrieve usage data filtered by API usage (>= comparison).

    Args:
        api_usage: Minimum API usage value (returns records >= this value)

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/api-usage/{api_usage}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_api_over(api_over: str) -> str:
    """Retrieve usage data filtered by API overage (>= comparison).

    Args:
        api_over: Minimum API overage value (returns records >= this value)

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/api-over/{api_over}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_api_estimated_dollars(api_est_dollars: str) -> str:
    """Retrieve usage data filtered by API estimated dollars (>= comparison).

    Args:
        api_est_dollars: Minimum API estimated dollars value (returns records >= this value)

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/usage/api-estimated-dollars/{api_est_dollars}"
        )
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_apa_usage(apa_usage: str) -> str:
    """Retrieve usage data filtered by AP Automation usage (>= comparison).

    Args:
        apa_usage: Minimum AP Automation usage value (returns records >= this value)

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/apa-usage/{apa_usage}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_apa_over(apa_over: str) -> str:
    """Retrieve usage data filtered by AP Automation overage (>= comparison).

    Args:
        apa_over: Minimum AP Automation overage value (returns records >= this value)

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/apa-over/{apa_over}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_apa_estimated_dollars(apa_est_dollars: str) -> str:
    """Retrieve usage data filtered by AP Automation estimated dollars (>= comparison).

    Args:
        apa_est_dollars: Minimum AP Automation estimated dollars value (returns records >= this value)

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/usage/apa-estimated-dollars/{apa_est_dollars}"
        )
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_das_usage(das_usage: str) -> str:
    """Retrieve usage data filtered by DAS usage (>= comparison).

    Args:
        das_usage: Minimum DAS usage value (returns records >= this value)

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/das-usage/{das_usage}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


@mcp.tool()
async def get_usage_by_das_over(das_over: str) -> str:
    """Retrieve usage data filtered by DAS overage (>= comparison).

    Args:
        das_over: Minimum DAS overage value (returns records >= this value)

    Returns:
        JSON string containing list of usage records
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/usage/das-over/{das_over}")
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


async def main():
    await mcp.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())
