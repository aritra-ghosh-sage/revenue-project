"""MCP Server for API Usage Data

This server provides tools to query usage data from the revenue system.
Uses stdio transport for local communication.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field

# Add parent directory to path to import api module
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from mcp.server import FastMCP

# Initialize the FastMCP server
mcp = FastMCP("api-usage-server")

# Base URL for the FastAPI metrics service
BASE_URL = "http://localhost:8000"


class BillUsageRecord(BaseModel):
    """A single bill record with tenant name, billing period, and usage details."""

    tenant: str = Field(
        ..., description="Tenant or account name (e.g., 'Baker Tilly Advisory Group')"
    )
    period: str = Field(
        ..., description="Billing period (e.g., '2026-01' or 'January 2026')"
    )
    usage_details: Dict[str, Any] = Field(
        ...,
        description="Usage details as key-value pairs. Example: {'API Calls': 1200, 'Storage (GB)': 50, 'Estimated Dollars': 123.45}",
    )


@mcp.tool(
    name="generate_bill",
    description="Generate up to 4 PDF bills for tenants and return file paths to the generated PDFs.",
)
async def generate_bill(bills: List[BillUsageRecord]) -> str:
    """Generate up to 4 PDF bills for tenants. Returns file paths to the generated PDFs.

    Args:
        bills: List of up to 4 bill records, each with:
            - tenant (str): Tenant or account name
            - period (str): Billing period (e.g., '2026-01' or 'January 2026')
            - usage_details (dict): Usage metrics with keys like 'API Calls', 'Storage (GB)', 'Estimated Dollars', etc.

    Returns:
        JSON string containing a list of file paths to the generated PDF bills or error message.
        Success example: ['bills/bill_Baker_Tilly_Advisory_Group_xxxxxxxx.pdf']
        Error example: {"error": "Connection Failed", "message": "...", "details": "..."}
    """
    import json

    import httpx

    try:
        # Validate input
        if not bills:
            error_msg = {
                "error": "Validation Error",
                "message": "Bill generation failed due to missing required fields.",
                "details": "Bills list is empty. Please provide at least one bill record with tenant, period, and usage_details.",
            }
            return json.dumps(error_msg, indent=2)

        if len(bills) > 4:
            error_msg = {
                "error": "Validation Error",
                "message": "Too many bills provided. Maximum is 4 bills per request.",
                "details": f"Provided {len(bills)} bills but maximum is 4.",
            }
            return json.dumps(error_msg, indent=2)

        # Convert Pydantic models to dictionaries
        bills_data = []
        for bill in bills:
            try:
                if isinstance(bill, BillUsageRecord):
                    bill_dict = bill.model_dump()
                elif isinstance(bill, dict):
                    bill_dict = bill
                else:
                    bill_dict = bill if isinstance(bill, dict) else bill.__dict__

                # Validate required fields
                if "tenant" not in bill_dict or not bill_dict["tenant"]:
                    raise ValueError("Missing required field: 'tenant'")
                if "period" not in bill_dict or not bill_dict["period"]:
                    raise ValueError("Missing required field: 'period'")
                if "usage_details" not in bill_dict or not bill_dict["usage_details"]:
                    raise ValueError("Missing required field: 'usage_details'")

                bills_data.append(bill_dict)
            except ValueError as ve:
                error_msg = {
                    "error": "Validation Error",
                    "message": "Bill generation failed due to missing required fields.",
                    "details": f"Invalid bill record: {str(ve)}. Each bill must have: tenant, period, usage_details",
                }
                return json.dumps(error_msg, indent=2)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/generate-bill", json={"bills": bills_data}
            )
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)
    except httpx.ConnectError as e:
        error_msg = {
            "error": "Connection Failed",
            "message": "Unable to connect to the bill generation service. Please ensure the FastAPI server is running on port 8000.",
            "details": str(e),
        }
        return json.dumps(error_msg, indent=2)
    except httpx.TimeoutException as e:
        error_msg = {
            "error": "Request Timeout",
            "message": "Bill generation request timed out. The server may be overloaded or unresponsive.",
            "details": str(e),
        }
        return json.dumps(error_msg, indent=2)
    except httpx.HTTPStatusError as e:
        error_msg = {
            "error": f"HTTP {e.response.status_code}",
            "message": "Bill generation failed due to a server error.",
            "details": e.response.text if e.response.text else str(e),
        }
        return json.dumps(error_msg, indent=2)
    except json.JSONDecodeError as e:
        error_msg = {
            "error": "Invalid Response",
            "message": "Received an invalid response from the bill generation service.",
            "details": str(e),
        }
        return json.dumps(error_msg, indent=2)
    except Exception as e:
        error_msg = {
            "error": "Unexpected Error",
            "message": "An unexpected error occurred during bill generation.",
            "details": f"{type(e).__name__}: {str(e)}",
        }
        return json.dumps(error_msg, indent=2)


@mcp.tool()
async def get_usage_by_period(period: str) -> str:
    """Retrieve usage data for a specific billing period.

    Args:
        period: Billing period identifier (e.g., "January 2026", "2026-01")

    Returns:
        JSON list of usage records, each with fields:
        - account_name: Tenant/account name
        - period: Billing period
        - api_usage, api_over, api_est_dollars: API service metrics
        - apa_usage, apa_over, apa_est_dollars: AP Automation metrics
        - das_usage, das_over: DAS service metrics
        Use these fields to construct bill usage_details when calling generate_bill.
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
        account_name: Account name identifier (supports partial matching)

    Returns:
        JSON list of usage records for matching accounts, each with fields:
        - account_name: Tenant/account name (use this as 'tenant' in generate_bill)
        - period: Billing period (use this as 'period' in generate_bill)
        - api_usage, api_over, api_est_dollars: API service metrics
        - apa_usage, apa_over, apa_est_dollars: AP Automation metrics
        - das_usage, das_over: DAS service metrics
        Format these fields into a usage_details dict when calling generate_bill.
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


@mcp.tool(
    name="verify_bills",
    description="Run bill-generation verification for provided bills and return a JSON report.",
)
async def verify_bills(bills: List[BillUsageRecord]) -> str:
    """Run the verification harness against the provided bills.

    This tool invokes the in-repo verification runner directly (no subprocess)
    and returns the redacted JSON report as a string.
    """
    try:
        # Convert to plain dict payload
        if isinstance(bills, list):
            bills_data = []
            for b in bills:
                if isinstance(b, BillUsageRecord):
                    bills_data.append(b.model_dump())
                else:
                    bills_data.append(b if isinstance(b, dict) else dict(b))
        else:
            return json.dumps(
                {"error": "Invalid input", "message": "bills must be a list"}
            )

        payload = {"bills": bills_data}

        # Import the private runner entrypoint and call it
        from verification.runner import _run_verification_payload

        report = _run_verification_payload(payload, api_url=BASE_URL)
        return json.dumps(report, indent=2)
    except Exception as e:
        return json.dumps({"error": "Unexpected Error", "message": str(e)})


async def main():
    await mcp.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())
