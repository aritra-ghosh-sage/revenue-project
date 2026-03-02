"""Test MCP client with the exact query that's failing."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_clients.api_usage_mcp_client import MCPClient


async def main():
    """Test the exact failing query."""
    client = MCPClient()
    try:
        server_script = str(Path(__file__).parent / "mcp_servers" / "api_usage_mcp.py")
        await client.connect_to_server(server_script)

        # The exact query that's failing
        query = "get all usages for baker tilly in the month of Jan 2026 and generate a bill"
        
        print("\n" + "=" * 70)
        print(f"QUERY: {query}")
        print("=" * 70 + "\n")
        
        response = await client.process_query(query)
        print("\n" + "=" * 70)
        print("RESPONSE:")
        print("=" * 70)
        print(response)
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n[ERROR] {str(e)}\n")
        import traceback
        traceback.print_exc()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
