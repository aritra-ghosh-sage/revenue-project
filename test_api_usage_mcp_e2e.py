"""End-to-end tests for mcp_servers/api_usage_mcp.py

Covers:
  Happy paths   — successful round-trips through every MCP tool.
  Sad paths     — validation failures, empty results, non-list inputs.
  Exception paths — httpx.ConnectError, httpx.TimeoutException,
                    httpx.HTTPStatusError (4xx / 5xx), json.JSONDecodeError,
                    and generic unexpected exceptions.

asyncio_mode = "auto" is set in pyproject.toml, so @pytest.mark.asyncio
decorators are not required.
"""

import json
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure verification.runner is loaded so patch() can address it directly.
import verification.runner  # noqa: F401

from mcp_servers.api_usage_mcp import (
    BillUsageRecord,
    generate_bill,
    get_usage_by_period,
    get_usage_by_contract,
    get_usage_by_company,
    get_usage_by_account_name,
    get_usage_by_account_owner,
    get_usage_by_channel,
    get_usage_by_partner,
    get_usage_by_total_usage,
    get_usage_by_over_usage,
    get_usage_by_estimated_dollars,
    get_usage_by_api_usage,
    get_usage_by_api_over,
    get_usage_by_api_estimated_dollars,
    get_usage_by_apa_usage,
    get_usage_by_apa_over,
    get_usage_by_apa_estimated_dollars,
    get_usage_by_das_usage,
    get_usage_by_das_over,
    verify_bills,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ctx():
    """Minimal MCP Context mock that satisfies awaitable ctx.error() calls."""
    ctx = AsyncMock()
    ctx.error = AsyncMock()
    return ctx


@pytest.fixture
def sample_bill():
    return BillUsageRecord(
        tenant="FusionSite Services, LLC",
        period="January 2026",
        usage_details={
            "API Calls": 224796,
            "API Overage": 124796,
            "Estimated Dollars": 2121.0,
        },
    )


@pytest.fixture
def sample_bills(sample_bill):
    return [sample_bill]


# ---------------------------------------------------------------------------
# HTTP mock factory
# ---------------------------------------------------------------------------

_SAMPLE_USAGE_RECORD = {
    "contract_id": "C20506",
    "order_id": "C20506",
    "account_name": "FusionSite Services, LLC",
    "account_owner": "Monica Lopez",
    "channel": "Direct",
    "partner": None,
    "period": "January 2026",
    "api_usage": 224796,
    "api_over": 124796,
    "api_est_dollars": "2121",
    "apa_usage": 4140,
    "apa_over": 2140,
    "apa_est_dollars": "1070",
    "das_usage": 0,
    "das_over": 0,
}


def _make_mock_async_client(
    response_data=None,
    post_side_effect=None,
    get_side_effect=None,
):
    """Return (mock_class, mock_response, mock_client) for patching httpx.AsyncClient.

    Pass post_side_effect or get_side_effect to raise exceptions on those calls.
    Modify mock_response (e.g. raise_for_status.side_effect) after the call for
    fine-grained control.
    """
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = response_data if response_data is not None else []

    mock_client = AsyncMock()
    if post_side_effect is not None:
        mock_client.post.side_effect = post_side_effect
    else:
        mock_client.post.return_value = mock_response

    if get_side_effect is not None:
        mock_client.get.side_effect = get_side_effect
    else:
        mock_client.get.return_value = mock_response

    # Replaces the httpx.AsyncClient class so that:
    #   async with httpx.AsyncClient(...) as client  →  client is mock_client
    mock_class = MagicMock()
    mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_class.return_value.__aexit__ = AsyncMock(return_value=False)

    return mock_class, mock_response, mock_client


# ===========================================================================
# generate_bill
# ===========================================================================


class TestGenerateBill:
    # -----------------------------------------------------------------------
    # Happy paths
    # -----------------------------------------------------------------------

    async def test_single_valid_bill_returns_pdf_path(self, mock_ctx, sample_bill):
        """Happy: one valid BillUsageRecord → backend called → PDF path list returned."""
        expected_path = "bills/bill_FusionSite_Services_abc12345.pdf"
        mock_class, _, _ = _make_mock_async_client(response_data=[expected_path])

        with patch("mcp_servers.api_usage_mcp.httpx.AsyncClient", mock_class):
            result = await generate_bill(bills=[sample_bill], ctx=mock_ctx)

        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert parsed[0] == expected_path

    async def test_maximum_four_bills_all_returned(self, mock_ctx):
        """Happy: exactly 4 bills → all 4 PDF paths returned."""
        pdf_paths = [f"bills/bill_tenant{i}_xxxxxxxx.pdf" for i in range(4)]
        bills = [
            BillUsageRecord(
                tenant=f"Tenant {i}",
                period="January 2026",
                usage_details={"Estimated Dollars": float(100 * (i + 1))},
            )
            for i in range(4)
        ]
        mock_class, _, _ = _make_mock_async_client(response_data=pdf_paths)

        with patch("mcp_servers.api_usage_mcp.httpx.AsyncClient", mock_class):
            result = await generate_bill(bills=bills, ctx=mock_ctx)

        parsed = json.loads(result)
        assert len(parsed) == 4
        assert parsed == pdf_paths

    # -----------------------------------------------------------------------
    # Sad paths
    # -----------------------------------------------------------------------

    async def test_empty_bills_list_returns_validation_error(self, mock_ctx):
        """Sad: empty bills list → Validation Error, no HTTP request made."""
        result = await generate_bill(bills=[], ctx=mock_ctx)

        parsed = json.loads(result)
        assert parsed["error"] == "Validation Error"
        assert "empty" in parsed["details"].lower()

    async def test_more_than_four_bills_returns_validation_error(self, mock_ctx):
        """Sad: 5 bills → Validation Error before any HTTP call."""
        bills = [
            BillUsageRecord(
                tenant=f"T{i}",
                period="January 2026",
                usage_details={"Estimated Dollars": 1.0},
            )
            for i in range(5)
        ]
        result = await generate_bill(bills=bills, ctx=mock_ctx)

        parsed = json.loads(result)
        assert parsed["error"] == "Validation Error"
        assert "4" in parsed["details"]

    async def test_dict_bill_blank_tenant_returns_validation_error(self, mock_ctx):
        """Sad: dict bill with blank tenant → Validation Error, ctx.error called once."""
        invalid_bills = [
            {"tenant": "", "period": "January 2026", "usage_details": {"Estimated Dollars": 50.0}}
        ]
        result = await generate_bill(bills=invalid_bills, ctx=mock_ctx)

        parsed = json.loads(result)
        assert parsed["error"] == "Validation Error"
        assert "tenant" in parsed["extra"]["details"].lower()
        mock_ctx.error.assert_awaited_once()

    async def test_dict_bill_blank_period_returns_validation_error(self, mock_ctx):
        """Sad: dict bill with blank period → Validation Error, ctx.error called once."""
        invalid_bills = [
            {"tenant": "Acme Corp", "period": "", "usage_details": {"Estimated Dollars": 50.0}}
        ]
        result = await generate_bill(bills=invalid_bills, ctx=mock_ctx)

        parsed = json.loads(result)
        assert parsed["error"] == "Validation Error"
        assert "period" in parsed["extra"]["details"].lower()
        mock_ctx.error.assert_awaited_once()

    async def test_dict_bill_empty_usage_details_returns_validation_error(self, mock_ctx):
        """Sad: dict bill with empty usage_details → Validation Error, ctx.error called once."""
        invalid_bills = [
            {"tenant": "Acme Corp", "period": "January 2026", "usage_details": {}}
        ]
        result = await generate_bill(bills=invalid_bills, ctx=mock_ctx)

        parsed = json.loads(result)
        assert parsed["error"] == "Validation Error"
        assert "usage_details" in parsed["extra"]["details"].lower()
        mock_ctx.error.assert_awaited_once()

    # -----------------------------------------------------------------------
    # Exception paths
    # -----------------------------------------------------------------------

    async def test_connect_error_returns_connection_failed_json(self, mock_ctx, sample_bills):
        """Exception: httpx.ConnectError → 'Connection Failed' error JSON, ctx.error called."""
        mock_class, _, _ = _make_mock_async_client(
            post_side_effect=httpx.ConnectError("Connection refused")
        )

        with patch("mcp_servers.api_usage_mcp.httpx.AsyncClient", mock_class):
            result = await generate_bill(bills=sample_bills, ctx=mock_ctx)

        parsed = json.loads(result)
        assert parsed["error"] == "Connection Failed"
        assert "port 8000" in parsed["message"].lower() or "connect" in parsed["message"].lower()
        mock_ctx.error.assert_awaited_once()

    async def test_timeout_exception_returns_request_timeout_json(self, mock_ctx, sample_bills):
        """Exception: httpx.TimeoutException → 'Request Timeout' error JSON, ctx.error called."""
        mock_class, _, _ = _make_mock_async_client(
            post_side_effect=httpx.TimeoutException("Request timed out")
        )

        with patch("mcp_servers.api_usage_mcp.httpx.AsyncClient", mock_class):
            result = await generate_bill(bills=sample_bills, ctx=mock_ctx)

        parsed = json.loads(result)
        assert parsed["error"] == "Request Timeout"
        mock_ctx.error.assert_awaited_once()

    async def test_http_4xx_status_error_returns_http_status_json(self, mock_ctx, sample_bills):
        """Exception: HTTPStatusError 400 → 'HTTP 400' error JSON, ctx.error called."""
        fake_response = MagicMock()
        fake_response.status_code = 400
        fake_response.text = "Bad Request"

        mock_class, mock_resp, _ = _make_mock_async_client()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Client Error", request=MagicMock(), response=fake_response
        )

        with patch("mcp_servers.api_usage_mcp.httpx.AsyncClient", mock_class):
            result = await generate_bill(bills=sample_bills, ctx=mock_ctx)

        parsed = json.loads(result)
        assert parsed["error"] == "HTTP 400"
        assert "server error" in parsed["message"].lower()
        mock_ctx.error.assert_awaited_once()

    async def test_http_5xx_status_error_returns_http_status_json(self, mock_ctx, sample_bills):
        """Exception: HTTPStatusError 500 → 'HTTP 500' error JSON, ctx.error called."""
        fake_response = MagicMock()
        fake_response.status_code = 500
        fake_response.text = "Internal Server Error"

        mock_class, mock_resp, _ = _make_mock_async_client()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=fake_response
        )

        with patch("mcp_servers.api_usage_mcp.httpx.AsyncClient", mock_class):
            result = await generate_bill(bills=sample_bills, ctx=mock_ctx)

        parsed = json.loads(result)
        assert parsed["error"] == "HTTP 500"
        mock_ctx.error.assert_awaited_once()

    async def test_json_decode_error_returns_invalid_response_json(self, mock_ctx, sample_bills):
        """Exception: response.json() raises JSONDecodeError → 'Invalid Response', ctx.error called."""
        mock_class, mock_resp, _ = _make_mock_async_client()
        mock_resp.json.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)

        with patch("mcp_servers.api_usage_mcp.httpx.AsyncClient", mock_class):
            result = await generate_bill(bills=sample_bills, ctx=mock_ctx)

        parsed = json.loads(result)
        assert parsed["error"] == "Invalid Response"
        assert "invalid response" in parsed["message"].lower()
        mock_ctx.error.assert_awaited_once()

    async def test_generic_exception_returns_unexpected_error_json(self, mock_ctx, sample_bills):
        """Exception: RuntimeError from client.post → 'Unexpected Error' JSON, ctx.error called."""
        mock_class, _, mock_client = _make_mock_async_client()
        mock_client.post.side_effect = RuntimeError("Catastrophic failure")

        with patch("mcp_servers.api_usage_mcp.httpx.AsyncClient", mock_class):
            result = await generate_bill(bills=sample_bills, ctx=mock_ctx)

        parsed = json.loads(result)
        assert parsed["error"] == "Unexpected Error"
        assert "Catastrophic failure" in parsed["details"]
        mock_ctx.error.assert_awaited_once()


# ===========================================================================
# get_usage_by_* tools
#
# All 18 query tools share the same HTTP-GET + raise_for_status() + json()
# pattern and have no internal exception handler (exceptions propagate).
# Each is exercised with 4 scenarios via parametrize.
# ===========================================================================

# (test_id, async_fn, kwargs_to_pass)
_GET_USAGE_CASES = [
    ("period",           get_usage_by_period,           {"period": "January 2026"}),
    ("contract",         get_usage_by_contract,         {"contract_id": "C20506"}),
    ("company",          get_usage_by_company,          {"company_id": "C1922"}),
    ("account_name",     get_usage_by_account_name,     {"account_name": "FusionSite"}),
    ("account_owner",    get_usage_by_account_owner,    {"account_owner": "Monica Lopez"}),
    ("channel",          get_usage_by_channel,          {"channel": "Direct"}),
    ("partner",          get_usage_by_partner,          {"partner": "Intellitec"}),
    ("total_usage",      get_usage_by_total_usage,      {"usage": "50000"}),
    ("over_usage",       get_usage_by_over_usage,       {"over_usage": "10000"}),
    ("estimated_dollars", get_usage_by_estimated_dollars, {"estimated_dollars": "500"}),
    ("api_usage",        get_usage_by_api_usage,        {"api_usage": "100000"}),
    ("api_over",         get_usage_by_api_over,         {"api_over": "20000"}),
    ("api_est_dollars",  get_usage_by_api_estimated_dollars, {"api_est_dollars": "1000"}),
    ("apa_usage",        get_usage_by_apa_usage,        {"apa_usage": "5000"}),
    ("apa_over",         get_usage_by_apa_over,         {"apa_over": "1000"}),
    ("apa_est_dollars",  get_usage_by_apa_estimated_dollars, {"apa_est_dollars": "500"}),
    ("das_usage",        get_usage_by_das_usage,        {"das_usage": "100000"}),
    ("das_over",         get_usage_by_das_over,         {"das_over": "10000"}),
]


@pytest.mark.parametrize("label,fn,kwargs", _GET_USAGE_CASES)
class TestGetUsageTools:
    async def test_happy_returns_usage_record_list(self, label, fn, kwargs):
        """Happy: server returns one matching record → parsed JSON list with that record."""
        mock_class, _, _ = _make_mock_async_client(response_data=[_SAMPLE_USAGE_RECORD])

        with patch("mcp_servers.api_usage_mcp.httpx.AsyncClient", mock_class):
            result = await fn(**kwargs)

        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["account_name"] == "FusionSite Services, LLC"

    async def test_sad_empty_result_returns_empty_json_array(self, label, fn, kwargs):
        """Sad: server finds no matching records → tool returns JSON empty array."""
        mock_class, _, _ = _make_mock_async_client(response_data=[])

        with patch("mcp_servers.api_usage_mcp.httpx.AsyncClient", mock_class):
            result = await fn(**kwargs)

        assert json.loads(result) == []

    async def test_exception_connect_error_propagates(self, label, fn, kwargs):
        """Exception: httpx.ConnectError propagates (no handler in query tools)."""
        mock_class, _, _ = _make_mock_async_client(
            get_side_effect=httpx.ConnectError("Connection refused")
        )

        with patch("mcp_servers.api_usage_mcp.httpx.AsyncClient", mock_class):
            with pytest.raises(httpx.ConnectError):
                await fn(**kwargs)

    async def test_exception_http_status_error_propagates(self, label, fn, kwargs):
        """Exception: HTTPStatusError from raise_for_status() propagates."""
        fake_response = MagicMock()
        fake_response.status_code = 404
        fake_response.text = "Not Found"

        mock_class, mock_resp, _ = _make_mock_async_client()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=fake_response
        )

        with patch("mcp_servers.api_usage_mcp.httpx.AsyncClient", mock_class):
            with pytest.raises(httpx.HTTPStatusError):
                await fn(**kwargs)


# ===========================================================================
# verify_bills
# ===========================================================================


class TestVerifyBills:
    async def test_happy_valid_bills_returns_report_json(self):
        """Happy: valid BillUsageRecord list → _run_verification_payload called → JSON report."""
        bills = [
            BillUsageRecord(
                tenant="FusionSite Services, LLC",
                period="January 2026",
                usage_details={"API Calls": 224796, "Estimated Dollars": 2121.0},
            )
        ]
        expected_report = {
            "run_id": 1744000000,
            "mode": "api",
            "results": [
                {
                    "pdf": "bills/bill_FusionSite_abc12345.pdf",
                    "diff": {"passed": True, "delta": 0.0},
                }
            ],
        }

        with patch(
            "verification.runner._run_verification_payload",
            return_value=expected_report,
        ):
            result = await verify_bills(bills=bills)

        parsed = json.loads(result)
        assert parsed["mode"] == "api"
        assert parsed["results"][0]["diff"]["passed"] is True

    async def test_happy_multiple_bills_payload_forwarded(self):
        """Happy: multiple bills are all included in the payload forwarded to the runner."""
        bills = [
            BillUsageRecord(
                tenant=f"Org {i}",
                period="January 2026",
                usage_details={"Estimated Dollars": float(i * 100)},
            )
            for i in range(3)
        ]
        expected_report = {"run_id": 1744000001, "mode": "api", "results": []}

        captured = {}

        def fake_runner(payload, api_url):
            captured["payload"] = payload
            return expected_report

        with patch("verification.runner._run_verification_payload", side_effect=fake_runner):
            await verify_bills(bills=bills)

        assert len(captured["payload"]["bills"]) == 3
        assert captured["payload"]["bills"][0]["tenant"] == "Org 0"

    async def test_sad_non_list_input_returns_invalid_input_error(self):
        """Sad: passing a non-list value → 'Invalid input' error JSON, no runner call."""
        result = await verify_bills(bills="not-a-list")  # type: ignore[arg-type]

        parsed = json.loads(result)
        assert parsed["error"] == "Invalid input"
        assert "list" in parsed["message"].lower()

    async def test_sad_none_input_returns_invalid_input_error(self):
        """Sad: None as bills → 'Invalid input' error JSON."""
        result = await verify_bills(bills=None)  # type: ignore[arg-type]

        parsed = json.loads(result)
        assert parsed["error"] == "Invalid input"

    async def test_exception_runner_raises_returns_unexpected_error_json(self):
        """Exception: _run_verification_payload raises → caught, 'Unexpected Error' JSON returned."""
        bills = [
            BillUsageRecord(
                tenant="Acme Corp",
                period="January 2026",
                usage_details={"Estimated Dollars": 99.0},
            )
        ]

        with patch(
            "verification.runner._run_verification_payload",
            side_effect=RuntimeError("Database connection unavailable"),
        ):
            result = await verify_bills(bills=bills)

        parsed = json.loads(result)
        assert parsed["error"] == "Unexpected Error"
        assert "Database connection unavailable" in parsed["message"]

    async def test_exception_import_error_in_runner_returns_unexpected_error_json(self):
        """Exception: ImportError from runner module → caught, 'Unexpected Error' JSON returned."""
        bills = [
            BillUsageRecord(
                tenant="Tide Health Group LLC",
                period="January 2026",
                usage_details={"Estimated Dollars": 976.0},
            )
        ]

        with patch(
            "verification.runner._run_verification_payload",
            side_effect=ImportError("No module named 'missing_dep'"),
        ):
            result = await verify_bills(bills=bills)

        parsed = json.loads(result)
        assert parsed["error"] == "Unexpected Error"
        assert "missing_dep" in parsed["message"]
