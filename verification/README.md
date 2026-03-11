# Bill-Generation Verification

Small harness to POST a `generate-bill` request, parse the produced PDFs, and compare key fields back to the request.

Quick start:

1. Activate virtual environment and install verification deps:

```powershell
& .venv\Scripts\Activate.ps1
python -m pip install -r verification/requirements.txt
```

2. Run the verification runner (FastAPI must be running):

```powershell
python -m verification.runner --mode api --payload verification/tests/fixtures/sample_bill_request.json --out verification/reports/run.json
```

Outputs:

- Generated PDFs are saved under `bills/` by the FastAPI endpoint
- The runner writes a JSON report under `verification/reports/`

Tip: The verification runner is called by MCP tool flows in tests; run it directly for focused PDF validation.

Updated: 2026-03-11
