# Revenue Project

A comprehensive system for managing and querying API usage data across multiple billing periods and services, with an MCP (Model Context Protocol) server interface.

## Project Structure

```
revenue-project/
├── api/
│   ├── models.py                      # Data models and filtering logic
│   ├── metrics.py                     # FastAPI server for usage data (port 8000)
│   └── allocation_metrics.py          # FastAPI server for allocation data (port 8001)
├── mcp_servers/
│   ├── api_usage_mcp.py               # MCP server for usage data (18 tools)
│   ├── allocation_usage_mcp.py        # MCP server for allocation data (1 tool)
│   └── README.md                      # MCP server documentation
├── mcp_clients/
│   └── api_usage_mcp_client.py        # MCP client with LLM integration
├── END_TO_END_FLOW_VERIFICATION.md    # Complete test report
└── pyproject.toml                     # Project configuration
```

## Features

### API Models (`api/models.py`)
- **UsageData**: Comprehensive dataclass for tracking API, AP Automation, and DAS service usage
- **SKU**: Representation of SKU information for tracking products
- Extensive filtering methods for querying usage data by various criteria
- Mock data with 10 real sample accounts for testing

### FastAPI Endpoints (`api/metrics.py`)
- RESTful endpoints for retrieving usage data by various filters
- Period, channel, partner, and service-specific queries
- JSON serialization with proper Decimal handling

### MCP Server (`mcp_servers/api_usage_mcp.py`)
A Model Context Protocol server that exposes 18 tools for querying usage data. The MCP server connects to the FastAPI backend via HTTP.

**Architecture:**
```
MCP Client → MCP Server → FastAPI Server → Data Model
  (stdio)     (httpx)       (port 8000)
```

**Running the System:**
```bash
# Step 1: Start FastAPI server (required)
uvicorn api.metrics:app --reload

# Step 2: Run MCP tests
uv run python test_direct_mcp_flow.py
```

**Key Features:**
- ✅ 18 comprehensive query tools
- ✅ Async HTTP integration with FastAPI backend
- ✅ Stdio transport for MCP communication 
- ✅ Proper error handling and JSON serialization
- ✅ 100% test success rate (10/10 tests passing)

See [END_TO_END_FLOW_VERIFICATION.md](END_TO_END_FLOW_VERIFICATION.md) for complete test results.

### Allocation MCP Server (`mcp_servers/allocation_usage_mcp.py`)
A Model Context Protocol server that provides tools for querying allocation SKU records. The server connects to the allocation FastAPI backend via HTTP.

**Architecture:**
```
MCP Client → Allocation MCP Server → Allocation FastAPI → AllocationUsage Model
  (stdio)          (httpx)              (port 8001)
```

**Running the System:**
```bash
# Start Allocation FastAPI server
uvicorn api.allocation_metrics:app --port 8001 --reload

# Run the MCP server
python -m mcp_servers.allocation_usage_mcp
```

**Key Features:**
- ✅ Query allocation SKU records for billing
- ✅ Filters non-contract allocations (contract = False)
- ✅ Returns flagged allocations (flag = True)
- ✅ Active allocations only (allocations > 0)
- ✅ Rolling 12-month window (last_run within last year)
- ✅ Async HTTP integration with FastAPI backend
- ✅ Comprehensive field documentation for LLM understanding

## Available Tools (MCP Servers)

### API Usage MCP Server Tools

#### Query by Time Period
- `get_usage_by_period(period)` - e.g., "January 2026"

#### Query by Organization
- `get_usage_by_contract(contract_id)` - e.g., "C20506"
- `get_usage_by_company(company_id)` - e.g., "C1922"
- `get_usage_by_account_name(account_name)` - Partial match support
- `get_usage_by_account_owner(account_owner)` - Partial match support

#### Query by Channel & Partner
- `get_usage_by_channel(channel)` - e.g., "Direct", "VAR"
- `get_usage_by_partner(partner)` - Partner name lookup

#### Query by Usage Metrics
- `get_usage_by_total_usage(usage)` - Total across all services
- `get_usage_by_over_usage(over_usage)` - Total overage
- `get_usage_by_estimated_dollars(estimated_dollars)` - Total revenue

#### Service-Specific Queries
- **API Service**: `get_usage_by_api_usage`, `get_usage_by_api_over`, `get_usage_by_api_estimated_dollars`
- **AP Automation Service**: `get_usage_by_apa_usage`, `get_usage_by_apa_over`, `get_usage_by_apa_estimated_dollars`
- **DAS Service**: `get_usage_by_das_usage`, `get_usage_by_das_over`

### Allocation MCP Server Tools

#### Allocation SKU Queries
- `get_allocation_sku_records()` - Retrieve billable allocation records
  - Returns non-contract allocations (contract = False)
  - Only flagged for billing (flag = True)
  - Active allocations only (allocations > 0)
  - Recently processed within last 12 months (rolling window)
  - Useful for monthly billing cycles and revenue forecasting

## Installation & Setup

### Prerequisites
- Python 3.13+
- uv (for dependency management)

### Install Dependencies
```bash
uv sync
```

### Configure MCP Server
For use with Claude Desktop or other MCP clients, add to your configuration:

```json
{
  "mcpServers": {
    "api-usage": {
      "command": "python",
      "args": ["-m", "mcp_servers.api_usage_mcp"],
      "cwd": "/path/to/revenue-project"
    },
    "allocation-usage": {
      "command": "python",
      "args": ["-m", "mcp_servers.allocation_usage_mcp"],
      "cwd": "/path/to/revenue-project"
    }
  }
}
```

## Development

### Running the System
```bash
# Terminal 1: Start FastAPI server for usage data
uvicorn api.metrics:app --reload

# Terminal 2: Start FastAPI server for allocation data
uvicorn api.allocation_metrics:app --port 8001 --reload

# Terminal 3: Run MCP tests
uv run python test_direct_mcp_flow.py
uv run python test_additional_queries.py
```

### Running Tests
```bash
# Unit tests
pytest test_billing_queries.py
pytest test_endpoints.py

# MCP end-to-end tests
uv run python test_direct_mcp_flow.py
```

## Data Model

### UsageData
```python
@dataclass
class UsageData:
    contract_id: str
    order_id: str
    account_name: str
    account_owner: str
    channel: str                    # "Direct" or "VAR"
    partner: Optional[str]          # Partner name if applicable
    period: str                     # e.g., "January 2026"
    
    api_usage: int = 0
    api_over: int = 0
    api_est_dollars: Decimal = Decimal("0")
    
    apa_usage: int = 0
    apa_over: int = 0
    apa_est_dollars: Decimal = Decimal("0")
    
    das_usage: int = 0
    das_over: int = 0
```

### AllocationUsage
```python
@dataclass
class AllocationUsage:
    sfdc_link: bool                 # Salesforce link status
    cny: str                        # Company identifier/CNY code
    company_id: str                 # Company name/identifier
    intacct_cid: str                # Intacct customer ID
    parent: str                     # Parent company/organization
    link: str                       # Link type/category
    intacct: bool                   # Intacct integration status
    contract: bool                  # Contract status
    flag: bool                      # Billing flag status
    contract_link: bool             # Contract link status
    subscribed: date                # Subscription date
    allocations: int                # Number of allocations
    last_gl: date                   # Last general ledger date
    last_run: date                  # Last processing run date
```

## Technology Stack

- **FastAPI**: REST API server (port 8000)
- **FastMCP**: MCP server framework with stdio transport
- **httpx**: Async HTTP client for MCP → FastAPI communication
- **MCP SDK**: Model Context Protocol implementation
- **pytest**: Testing framework
- **uv**: Package manager and Python environment manager

## Test Results

**Status:** ✅ All tests passing (10/10, 100% success rate)

The system has been verified end-to-end with comprehensive tests covering:
- Period-based queries
- Entity queries (contract, company, account)
- Channel and partner queries
- Metric-based queries (API, APA, DAS usage)

See [END_TO_END_FLOW_VERIFICATION.md](END_TO_END_FLOW_VERIFICATION.md) for detailed results.

## Sample Data

The system includes 10 sample accounts with real usage data for January 2026:

- Acme Corporation (Direct, Allied Solutions Group)
- Zenith Solutions Group (Direct, Tech Partners Inc)
- Apex Financial Services (TSA)
- Momentum Healthcare Systems (Direct, Global Advisory Partners)
- Riverstone Consulting (TSA)
- Prism Dental Solutions (Direct, Strategic Innovations Ltd)
- Nexus Enterprises (TSA)
- Catalyst Medical Group (TSA)
- Sterling Services LLC (Direct, Enterprise Partners)
- Horizon Holdings Corp (TSA)

## License

Proprietary - Revenue Project
