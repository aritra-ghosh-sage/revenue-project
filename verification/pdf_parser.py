import re
from typing import Dict, Any
import pdfplumber


def _find_field(text: str, label: str) -> str | None:
    m = re.search(rf"{re.escape(label)}:\s*(.+)", text)
    return m.group(1).strip() if m else None


def parse_pdf(path: str) -> Dict[str, Any]:
    """Parse the bill PDF produced by the service and return structured fields.

    Expected output keys: tenant, period, items (list), total (float)
    """
    full_text = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            full_text.append(t)
    text = "\n".join(full_text)

    tenant = _find_field(text, "Billed Tenant")
    period = _find_field(text, "Billing Period")

    # Extract total billed amount
    total = None
    m = re.search(r"Total Billed Amount:\s*\$?([0-9,\.]+)", text)
    if m:
        total = float(m.group(1).replace(",", ""))

    # Extract usage details block
    items = []
    usage_block = None
    block_match = re.search(r"Usage Details:\s*(.*?)Total Billed Amount:", text, re.S)
    if block_match:
        usage_block = block_match.group(1)
        for line in usage_block.splitlines():
            line = line.strip()
            if not line:
                continue
            # Heuristic: last whitespace-separated token is likely the numeric value
            parts = line.split()
            if len(parts) >= 2:
                value = parts[-1].strip()
                name = " ".join(parts[:-1]).strip()
                try:
                    value_num = float(value.replace(',', ''))
                except Exception:
                    value_num = None
                items.append({"service": name, "value": value_num, "raw": line})

    return {"tenant": tenant, "period": period, "items": items, "total": total}
