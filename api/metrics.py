from dataclasses import asdict
from decimal import Decimal
from api.models import UsageData
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import uuid
import asyncio

app = FastAPI()


class BillUsageRecord(BaseModel):
    tenant: str = Field(..., description="Tenant name")
    period: str = Field(..., description="Billing period")
    usage_details: Dict[str, Any] = Field(
        ..., description="Usage details for the tenant"
    )


class BillRequest(BaseModel):
    bills: List[BillUsageRecord]


# Remove the HTML template and Jinja2 logic
def _generate_pdf_reportlab(tenant: str, period: str, usage_details: dict, pdf_path: str):
    """Generate a PDF bill using ReportLab.
    
    Raises:
        OSError: If unable to write to the file path
        Exception: For any reportlab-related errors
    """
    try:
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        y = height - 40
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, y, "Sage Intacct - Usage Bill")
        y -= 30
        c.setFont("Helvetica", 12)
        c.drawString(40, y, f"Billed Tenant: {tenant}")
        y -= 20
        c.drawString(40, y, f"Billing Period: {period}")
        y -= 30
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Usage Details:")
        y -= 20
        c.setFont("Helvetica-Bold", 11)
        c.drawString(60, y, "Service")
        c.drawString(200, y, "Usage")
        y -= 15
        c.setFont("Helvetica", 11)
        total_billed = 0.0
        for key, value in usage_details.items():
            c.drawString(60, y, str(key))
            c.drawString(200, y, str(value))
            # If the key is a dollar amount, add to total_billed
            if isinstance(value, (int, float)) and ("dollar" in key.lower() or "$" in key or "amount" in key.lower()):
                total_billed += float(value)
            y -= 15
            if y < 60:
                c.showPage()
                y = height - 40
        # Draw total billed amount at the bottom
        y -= 10
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, f"Total Billed Amount: ${total_billed:,.2f}")
        c.save()
    except OSError as e:
        raise OSError(f"Unable to write PDF to {pdf_path}: {str(e)}")
    except Exception as e:
        raise Exception(f"PDF generation error: {str(e)}")

async def _generate_pdf_async(tenant: str, period: str, usage_details: dict, pdf_path: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: _generate_pdf_reportlab(tenant, period, usage_details, pdf_path))


@app.post(
    "/generate-bill",
    summary="Generate up to 4 PDF bills for tenants",
    response_model=List[str],
)
async def generate_bill(
    request: BillRequest, background_tasks: BackgroundTasks
) -> List[str]:
    """Generate up to 4 PDF bills for tenants. Returns file paths. Bills are not deleted after generation."""
    from fastapi import HTTPException
    
    try:
        bills = request.bills[:4]  # Enforce max 4 bills
        pdf_paths = []
        
        # Ensure bills directory exists
        try:
            os.makedirs("bills", exist_ok=True)
        except OSError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create bills directory: {str(e)}"
            )
        
        # Generate each PDF
        for bill in bills:
            try:
                filename = f"bills/bill_{bill.tenant}_{uuid.uuid4().hex[:8]}.pdf"
                await _generate_pdf_async(bill.tenant, bill.period, bill.usage_details, filename)
                pdf_paths.append(filename)
            except Exception as e:
                # If one bill fails, log it but continue with others
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate PDF for tenant {bill.tenant}: {str(e)}"
                )
        
        return pdf_paths
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Bill generation failed: {str(e)}"
        )


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}


def _serialize_usage(row: UsageData) -> dict:
    payload = asdict(row)
    for key, value in payload.items():
        if isinstance(value, Decimal):
            payload[key] = str(value)
    return payload


@app.get("/usage/period/{period}")
async def get_usage_by_period(period: str) -> list[dict]:
    """Retrieve usage data for a specific billing period.

    Args:
        period: Billing period identifier (e.g., "January 2026")

    Returns:
        List of usage records matching the specified period
    """
    return [_serialize_usage(row) for row in UsageData.get_billing_by_period(period)]


@app.get("/usage/channel/{channel}")
async def get_usage_by_channel(channel: str) -> list[dict]:
    """Retrieve usage data filtered by sales channel.

    Args:
        channel: Sales channel identifier (e.g., "Direct", "VAR")

    Returns:
        List of usage records matching the specified channel
    """
    return [_serialize_usage(row) for row in UsageData.get_billing_by_channel(channel)]


@app.get("/usage/partner/{partner}")
async def get_usage_by_partner(partner: str) -> list[dict]:
    """Retrieve usage data filtered by partner name.

    Args:
        partner: Partner name identifier

    Returns:
        List of usage records for the specified partner
    """
    return [_serialize_usage(row) for row in UsageData.get_billing_by_partner(partner)]


@app.get("/usage/over-usage/{over_usage}")
async def get_usage_by_over_usage(over_usage: str) -> list[dict]:
    """Retrieve usage data filtered by total overage usage across all services.

    Args:
        over_usage: Minimum total overage usage value (returns records >= this value)

    Returns:
        List of usage records with total overage >= specified value
    """
    return [
        _serialize_usage(row) for row in UsageData.get_billing_by_over_usage(over_usage)
    ]


@app.get("/usage/account/{account_name}")
async def get_usage_by_account_name(account_name: str) -> list[dict]:
    """Retrieve usage data filtered by account name (partial match).

    Args:
        account_name: Account name identifier (supports partial matching)

    Returns:
        List of usage records for accounts matching the specified name
    """
    return [
        _serialize_usage(row)
        for row in UsageData.get_billing_by_account_name(account_name)
    ]


@app.get("/usage/contract/{contract_id}")
async def get_usage_by_contract(contract_id: str) -> list[dict]:
    """Retrieve usage data filtered by contract ID.

    Args:
        contract_id: Contract identifier (e.g., "C20506")

    Returns:
        List of usage records for the specified contract
    """
    return [
        _serialize_usage(row)
        for row in UsageData.get_billing_by_contract_id(contract_id)
    ]


@app.get("/usage/company/{company_id}")
async def get_usage_by_company(company_id: str) -> list[dict]:
    """Retrieve usage data filtered by company/order ID.

    Args:
        company_id: Company or order identifier (e.g., "C1922")

    Returns:
        List of usage records for the specified company
    """
    return [
        _serialize_usage(row) for row in UsageData.get_billing_by_order_id(company_id)
    ]


@app.get("/usage/estimated-dollars/{estimated_dollars}")
async def get_usage_by_estimated_dollars(estimated_dollars: str) -> list[dict]:
    """Retrieve usage data filtered by total estimated revenue across all services.

    Args:
        estimated_dollars: Minimum total estimated dollar value (returns records >= this value)

    Returns:
        List of usage records with total estimated dollars >= specified value
    """
    return [
        _serialize_usage(row)
        for row in UsageData.get_billing_by_estimated_dollars(estimated_dollars)
    ]


@app.get("/usage/account-owner/{account_owner}")
async def get_usage_by_account_owner(account_owner: str) -> list[dict]:
    """Retrieve usage data filtered by account owner (partial match).

    Args:
        account_owner: Account owner name

    Returns:
        List of usage records for the specified account owner
    """
    return [
        _serialize_usage(row)
        for row in UsageData.get_billing_by_account_owner(account_owner)
    ]


@app.get("/usage/total-usage/{total_usage}")
async def get_usage_by_total_usage(total_usage: str) -> list[dict]:
    """Retrieve usage data filtered by total usage.

    Args:
        total_usage: Minimum total usage value (returns records >= this value)

    Returns:
        List of usage records with total usage >= specified value
    """
    return [
        _serialize_usage(row) for row in UsageData.get_billing_by_usage(total_usage)
    ]


@app.get("/usage/api-usage/{api_usage}")
async def get_usage_by_api_usage(api_usage: str) -> list[dict]:
    """Retrieve usage data filtered by API usage.

    Args:
        api_usage: Minimum API usage value (returns records >= this value)

    Returns:
        List of usage records with API usage >= specified value
    """
    return [
        _serialize_usage(row) for row in UsageData.get_billing_by_api_usage(api_usage)
    ]


@app.get("/usage/api-over/{api_over}")
async def get_usage_by_api_over(api_over: str) -> list[dict]:
    """Retrieve usage data filtered by API overage.

    Args:
        api_over: Minimum API overage value (returns records >= this value)

    Returns:
        List of usage records with API overage >= specified value
    """
    return [
        _serialize_usage(row) for row in UsageData.get_billing_by_api_over(api_over)
    ]


@app.get("/usage/api-estimated-dollars/{api_est_dollars}")
async def get_usage_by_api_estimated_dollars(api_est_dollars: str) -> list[dict]:
    """Retrieve usage data filtered by API estimated dollars.

    Args:
        api_est_dollars: Minimum API estimated dollars value (returns records >= this value)

    Returns:
        List of usage records with API estimated dollars >= specified value
    """
    return [
        _serialize_usage(row)
        for row in UsageData.get_billing_by_api_est_dollars(api_est_dollars)
    ]


@app.get("/usage/apa-usage/{apa_usage}")
async def get_usage_by_apa_usage(apa_usage: str) -> list[dict]:
    """Retrieve usage data filtered by AP Automation usage.

    Args:
        apa_usage: Minimum AP Automation usage value (returns records >= this value)

    Returns:
        List of usage records with AP Automation usage >= specified value
    """
    return [
        _serialize_usage(row) for row in UsageData.get_billing_by_apa_usage(apa_usage)
    ]


@app.get("/usage/apa-over/{apa_over}")
async def get_usage_by_apa_over(apa_over: str) -> list[dict]:
    """Retrieve usage data filtered by AP Automation overage.

    Args:
        apa_over: Minimum AP Automation overage value (returns records >= this value)

    Returns:
        List of usage records with AP Automation overage >= specified value
    """
    return [
        _serialize_usage(row) for row in UsageData.get_billing_by_apa_over(apa_over)
    ]


@app.get("/usage/apa-estimated-dollars/{apa_est_dollars}")
async def get_usage_by_apa_estimated_dollars(apa_est_dollars: str) -> list[dict]:
    """Retrieve usage data filtered by AP Automation estimated dollars.

    Args:
        apa_est_dollars: Minimum AP Automation estimated dollars value (returns records >= this value)

    Returns:
        List of usage records with AP Automation estimated dollars >= specified value
    """
    return [
        _serialize_usage(row)
        for row in UsageData.get_billing_by_apa_est_dollars(apa_est_dollars)
    ]


@app.get("/usage/das-usage/{das_usage}")
async def get_usage_by_das_usage(das_usage: str) -> list[dict]:
    """Retrieve usage data filtered by DAS usage.

    Args:
        das_usage: Minimum DAS usage value (returns records >= this value)

    Returns:
        List of usage records with DAS usage >= specified value
    """
    return [
        _serialize_usage(row) for row in UsageData.get_billing_by_das_usage(das_usage)
    ]


@app.get("/usage/das-over/{das_over}")
async def get_usage_by_das_over(das_over: str) -> list[dict]:
    """Retrieve usage data filtered by DAS overage.

    Args:
        das_over: Minimum DAS overage value (returns records >= this value)

    Returns:
        List of usage records with DAS overage >= specified value
    """
    return [
        _serialize_usage(row) for row in UsageData.get_billing_by_das_over(das_over)
    ]
