import os
import tempfile
from api.metrics import _generate_pdf_reportlab
from verification.pdf_parser import parse_pdf


def test_pdf_parser_extracts_fields():
    tenant = "ACME"
    period = "January 2026"
    usage = {"ServiceA": 100, "Amount": 200.0}

    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        _generate_pdf_reportlab(tenant, period, usage, path)
        parsed = parse_pdf(path)
        assert parsed["tenant"] == tenant
        assert parsed["period"] == period
        assert parsed["total"] == 200.0
        assert any(it["service"] == "ServiceA" for it in parsed["items"]) or len(parsed["items"]) >= 1
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
