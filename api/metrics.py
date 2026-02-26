from dataclasses import asdict
from decimal import Decimal

from fastapi import FastAPI

from api.models import UsageData

app = FastAPI()


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
