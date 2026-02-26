from dataclasses import asdict
from datetime import date

from fastapi import FastAPI

from api.models import AllocationUsage

app = FastAPI()


def _serialize_allocation(row: AllocationUsage) -> dict:
    """Serialize AllocationUsage record to JSON-compatible format."""
    payload = asdict(row)
    for key, value in payload.items():
        if isinstance(value, date):
            payload[key] = value.isoformat()
    return payload


@app.get("/allocation-sku")
async def get_allocation_sku_records() -> list[dict]:
    """Retrieve allocation SKU records matching criteria:
    - contract = False
    - flag = True
    - allocations > 0
    - last_run within last 12 months (rolling)

    Returns:
        List of allocation SKU records matching the specified criteria
    """
    return [
        _serialize_allocation(row)
        for row in AllocationUsage.get_allocation_sku_records()
    ]
