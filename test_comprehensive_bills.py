"""Comprehensive test of bill generation with multiple query variations."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_clients.api_usage_mcp_client import MCPClient


async def run_query(query: str, test_name: str):
    """Test a single query."""
    print("\n" + "=" * 70)
    print(f"TEST: {test_name}")
    print(f"QUERY: {query}")
    print("=" * 70 + "\n")
    
    client = MCPClient()
    try:
        server_script = str(Path(__file__).parent / "mcp_servers" / "api_usage_mcp.py")
        await client.connect_to_server(server_script)
        
        response = await client.process_query(query)
        print(response)
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
    finally:
        await client.cleanup()


async def main():
    """Run multiple test queries."""
    tests = [
        ("get all usages for baker tilly in the month of Jan 2026 and generate a bill", 
         "Original failing query - Baker Tilly partner query"),
        
        ("Get usage data for January 2026 and generate a bill for CCHS",
         "Query by account name 'CCHS' for January 2026"),
         
        ("Show me usage for Signature Dental Partners in January 2026 and create a bill",
         "Query by exact account name"),
    ]
    
    for query, test_name in tests:
        await run_query(query, test_name)
        await asyncio.sleep(2)  # Brief delay between tests
    
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
