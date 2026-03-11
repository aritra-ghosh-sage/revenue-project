import json
from typing import Any, Dict


def write_report(report: Dict[str, Any], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def summary_text(report: Dict[str, Any]) -> str:
    runs = report.get("results", [])
    total = len(runs)
    passed = sum(1 for r in runs if r.get("diff", {}).get("passed"))
    lines = [f"Verification run: {report.get('run_id', 'unknown')}", f"{passed}/{total} bills passed"]
    for idx, r in enumerate(runs, 1):
        tenant = r.get("bill", {}).get("tenant")
        p = r.get("diff", {})
        status = "PASSED" if p.get("passed") else "FAILED"
        lines.append(f"{idx}. {tenant or 'unknown'} — {status} (delta={p.get('delta')})")
    return "\n".join(lines)
