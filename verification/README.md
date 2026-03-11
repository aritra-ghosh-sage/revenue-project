# Bill-Generation Verification

This folder contains a small verification harness to run end-to-end bill generation, parse generated PDFs, and compare key fields against the request payload.

Usage (local):

1. Install dependencies:

```bash
python -m pip install -r verification/requirements.txt
```

2. Run a verification against a locally-running FastAPI server:

```bash
python -m verification.runner --mode api --payload verification/tests/fixtures/sample_bill_request.json --out reports/run.json
```

The runner will POST to `/generate-bill`, parse produced PDFs, and write a JSON report.

Verification is intended to be invoked via the MCP tool `verify_bills` (LLM or MCP client flows).
