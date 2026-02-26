# API Usage MCP Server

This is a Model Context Protocol (MCP) server that provides tools to query API usage data from the revenue system using the FastMCP framework.

## Features

- **Async-first design**: All tools are implemented as async functions using `asyncio.to_thread()` for non-blocking operations
- **Comprehensive filtering**: 18 different query tools covering all aspects of usage data
- **Stdio transport**: Uses standard input/output for local MCP communication
- **JSON serialization**: Returns clean JSON-formatted results with Decimal support

## Tools Available

### Period and Time-based Queries
- `get_usage_by_period(period)` - Get usage data for a specific billing period (e.g., "January 2026")

### Account and Organization Queries
- `get_usage_by_contract(contract_id)` - Filter by contract ID (e.g., "C20506")
- `get_usage_by_company(company_id)` - Filter by company/order ID (e.g., "C1922")
- `get_usage_by_account_name(account_name)` - Filter by account name (partial match)
- `get_usage_by_account_owner(account_owner)` - Filter by account owner (partial match)

### Channel and Partner Queries
- `get_usage_by_channel(channel)` - Filter by sales channel (e.g., "Direct", "VAR")
- `get_usage_by_partner(partner)` - Filter by partner name

### Usage Metrics Queries
- `get_usage_by_total_usage(usage)` - Filter by total usage across all services
- `get_usage_by_over_usage(over_usage)` - Filter by total overage usage
- `get_usage_by_estimated_dollars(estimated_dollars)` - Filter by total estimated revenue

### Service-Specific Queries

#### API Service
- `get_usage_by_api_usage(api_usage)` - Filter by API usage
- `get_usage_by_api_over(api_over)` - Filter by API overage
- `get_usage_by_api_estimated_dollars(api_est_dollars)` - Filter by API estimated dollars

#### AP Automation Service
- `get_usage_by_apa_usage(apa_usage)` - Filter by AP Automation usage
- `get_usage_by_apa_over(apa_over)` - Filter by AP Automation overage
- `get_usage_by_apa_estimated_dollars(apa_est_dollars)` - Filter by AP Automation estimated dollars

#### DAS Service
- `get_usage_by_das_usage(das_usage)` - Filter by DAS usage
- `get_usage_by_das_over(das_over)` - Filter by DAS overage

## Running the Server

### Stdio Transport (Local)
```bash
python -m mcp_servers.api_usage_mcp
```

This will start the server listening on stdin/stdout for MCP protocol messages.

### Configuration in client (e.g., Claude Desktop)

Add to your MCP server configuration:

```json
{
  "mcpServers": {
    "api-usage": {
      "command": "python",
      "args": ["-m", "mcp_servers.api_usage_mcp"],
      "cwd": "/path/to/revenue-project"
    }
  }
}
```

## Implementation Details

- **FastMCP**: Uses FastMCP for simplified async tool definitions
- **Async Operations**: All database queries are run in thread pools via `asyncio.to_thread()` to avoid blocking the async loop
- **Data Serialization**: Decimal values are automatically serialized to strings for JSON compatibility
- **Error Handling**: Returns error results with descriptive messages when queries fail

## Examples

### Query by period
```
Tool: get_usage_by_period
Parameters: {"period": "January 2026"}
```

### Query by channel
```
Tool: get_usage_by_channel
Parameters: {"channel": "Direct"}
```

### Query by partner
```
Tool: get_usage_by_partner
Parameters: {"partner": "Baker Tilly Advisory Group"}
```

## Return Format

All tools return JSON-formatted strings with a list of usage records:

```json
[
  {
    "contract_id": "C20506",
    "order_id": "C20506",
    "account_name": "FusionSite Services, LLC",
    "account_owner": "Monica Lopez",
    "channel": "Direct",
    "partner": null,
    "period": "January 2026",
    "api_usage": 224796,
    "api_over": 124796,
    "api_est_dollars": "2121",
    "apa_usage": 4140,
    "apa_over": 2140,
    "apa_est_dollars": "1070",
    "das_usage": 0,
    "das_over": 0,
    "sku_name": null
  }
]
```
