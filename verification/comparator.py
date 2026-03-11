from typing import Dict, Any
from decimal import Decimal
from api.models import UsageData


def _sum_numeric_usage(usage_details: Dict[str, Any]) -> float:
    total = 0.0
    for k, v in usage_details.items():
        if isinstance(v, (int, float)):
            # follow same heuristic as generator: keys with 'dollar' or 'amount' count as billed amounts
            if "dollar" in k.lower() or "amount" in k.lower() or "$" in k:
                total += float(v)
        else:
            try:
                total += float(v)
            except Exception:
                continue
    return total


def compare(bill_request_record: Dict[str, Any], parsed_pdf: Dict[str, Any]) -> Dict[str, Any]:
    """Compare a single bill request record to the parsed PDF dict and return a diff object."""
    expected_total = _sum_numeric_usage(bill_request_record.get("usage_details", {}))
    parsed_total = parsed_pdf.get("total")

    diff = {"expected_total": expected_total, "parsed_total": parsed_total}
    passed = False
    if parsed_total is None:
        diff["reason"] = "parsed_total_missing"
    else:
        delta = abs(expected_total - parsed_total)
        diff["delta"] = delta
        passed = delta <= 0.01
    diff["passed"] = passed
    diff["tenant_match"] = (
        (bill_request_record.get("tenant") or "") == (parsed_pdf.get("tenant") or "")
    )
    diff["period_match"] = (
        (bill_request_record.get("period") or "") == (parsed_pdf.get("period") or "")
    )
    return diff


def compare_with_usage_data(bill_request_record: Dict[str, Any], parsed_pdf: Dict[str, Any]) -> Dict[str, Any]:
    """Compare parsed PDF against canonical UsageData aggregates.

    Strategy: find UsageData rows matching account_name (partial) and period if provided,
    then sum `api_est_dollars + apa_est_dollars` as the expected billed amount.
    """
    tenant = bill_request_record.get("tenant")
    period = bill_request_record.get("period")

    if not tenant:
        return {"passed": False, "reason": "no_tenant_in_request"}

    # Query UsageData by account name (partial match)
    matches = UsageData.get_billing_by_account_name(tenant)
    if period:
        matches = [m for m in matches if (m.period or "") == period]

    expected_total = Decimal(0)
    for m in matches:
        try:
            expected_total += (m.api_est_dollars or Decimal(0)) + (m.apa_est_dollars or Decimal(0))
        except Exception:
            continue

    parsed_total = parsed_pdf.get("total")
    parsed_total_dec = None
    if parsed_total is not None:
        try:
            parsed_total_dec = Decimal(str(parsed_total))
        except Exception:
            parsed_total_dec = None

    diff = {"expected_total": float(expected_total) if expected_total is not None else None, "parsed_total": parsed_total}
    if parsed_total_dec is None:
        diff["passed"] = False
        diff["reason"] = "parsed_total_missing_or_invalid"
    else:
        delta = abs(expected_total - parsed_total_dec)
        diff["delta"] = float(delta)
        diff["passed"] = delta <= Decimal("0.01")

    diff["matched_rows"] = len(matches)
    return diff
