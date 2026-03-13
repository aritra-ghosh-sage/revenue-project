import os
import asyncio
import sys
import json
from logging import info
from typing import Optional
from pathlib import Path
from contextlib import AsyncExitStack
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionToolParam

# Load environment variables from .env file
load_dotenv()

class MCPClient:
    def __init__(self) -> None:
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.endpoint = "https://models.github.ai/inference"
        self.model = "openai/gpt-4.1"
        self.token = os.environ["GITHUB_TOKEN_GPT_4_1"]
        self.available_tools = []

    async def connect_to_server(self, server_script_path: str) -> None:
        """Connect to the MCP server using stdio transport."""
        # Ensure server_script_path is absolute
        if not Path(server_script_path).is_absolute():
            server_script_path = str(Path(server_script_path).resolve())
        
        stdio_context = await self.exit_stack.enter_async_context(
            stdio_client(
                StdioServerParameters(
                    command="uv",
                    args=["run", "python", server_script_path],
                    env=None
                )
            )
        )
        self.stdio, self.write = stdio_context
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools

        # Store tool definitions in the format expected by OpenAI
        self.available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in tools]

        # Initialize AsyncOpenAI client
        self.client = AsyncOpenAI(
            base_url=self.endpoint,
            api_key=self.token
        )
        
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query by using the LLM to call MCP tools."""
        if (self.session is None):
            raise RuntimeError("MCP session is not initialized. Call connect_to_server() first.")
        
        # Convert tool definitions to ChatCompletionToolParam format
        formatted_tools = [
            ChatCompletionToolParam(
                type="function",
                function={
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            )
            for tool in self.available_tools
        ]

        # Build the initial messages
        messages = [
            {"content": (
            "You are a helpful assistant that answers questions about Sage Intacct's services usage details. "
            "It can be XML API, REST API, DAS (Or DDS Service), or AP Automation API usage details. "
            "Additional Intacct SKU based information can also be provided, "
            "e.g. Allocation SKU based tenant usage and consumption details. "
            "\n\n"
            "HOW TO FIND USAGE DATA: "
            "The system contains both ACCOUNT NAMES and PARTNER NAMES. When searching: "
            "- Try get_usage_by_account_name first if given an account/company name; "
            "- Try get_usage_by_partner if given a partner/vendor name like 'Baker Tilly', 'Sage', etc.; "
            "- Use get_usage_by_period to search by date period like 'January 2026'; "
            "- If one search returns no results, try an alternative query. "
            "\n\n"
            "IMPORTANT INSTRUCTIONS FOR BILL GENERATION: "
            "When asked to generate a bill, you MUST: "
            "1. First retrieve usage data using appropriate get_usage_* tools matching the query; "
            "2. From the retrieved data, extract account_name and all usage metrics (api_usage, apa_usage, das_usage, api_est_dollars, etc.); "
            "3. If multiple records are returned, create a bill for each unique account; "
            "4. Format each bill as: {'tenant': account_name, 'period': period, 'usage_details': {metric_key: metric_value, ...}}; "
            "5. Pass the list of properly formatted bills to generate_bill. "
            "\n"
            "CRITICAL: Each bill MUST have EXACTLY these three keys: 'tenant', 'period', 'usage_details'. "
            "\n"
            "Example of CORRECT format: "
            "generate_bill([{'tenant': 'McCarthy Management Group', 'period': 'January 2026', 'usage_details': {'api_usage': 0, 'apa_usage': 5900, 'das_usage': 0}}])"
            "\n"
            "Provide concise and accurate answers based on the available data. Keep responses brief and to the point. "
            "If you do not know the answer, say I do not know."
            ), "role":"system"},
            {"content":query, "role":"user"},
        ]

        # Agentic loop: keep calling the model and executing tools until we get a final response
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            try:
                response = await self.client.chat.completions.create(
                    messages=messages, # pyright: ignore[reportArgumentType]
                    temperature=0.3,
                    top_p=0.1,
                    max_tokens=32768,
                    model=self.model,
                    tools=formatted_tools
                )
            except Exception as api_error:
                return f"Error calling LLM API: {str(api_error)}"
            
            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            
            # If the model generated text without tool calls, return it
            if finish_reason == "stop" and message.content:
                return message.content
            
            # If the model wants to call tools, execute them
            if finish_reason == "tool_calls" and message.tool_calls:
                # Add the assistant's response (with tool calls) to messages
                messages.append({"role": "assistant", "content": message.content or "", "tool_calls": message.tool_calls}) # pyright: ignore[reportArgumentType]
                
                # Execute each tool call and collect results
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name # pyright: ignore[reportAttributeAccessIssue]
                    tool_args = json.loads(tool_call.function.arguments) # pyright: ignore[reportAttributeAccessIssue]
                    
                    try:
                        # Call the MCP tool
                        result = await self.session.call_tool(tool_name, tool_args)
                        
                        # Extract the text content from the result
                        tool_result_text = ""
                        if result.content:
                            for content in result.content:
                                if hasattr(content, 'text'):
                                    tool_result_text = content.text # pyright: ignore[reportAttributeAccessIssue]
                        
                        # Add tool result message (Using correct format for OpenAI)
                        # Each tool call result needs its own "tool" message
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result_text
                        })
                    except Exception as tool_error:
                        # Add error result
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error calling tool {tool_name}: {str(tool_error)}"
                        })
                
                # Continue the loop to get the final response
                continue
            
            # If we get here without a tool call or text, check if there's content
            if message.content:
                return message.content
            
            # If no content and no tool calls, break
            break
        
        return "Unable to generate a response."
    
    
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python api_usage_mcp.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])

        await client.chat_loop()
    finally:
        await client.exit_stack.aclose()

if __name__ == "__main__":
    info("Starting MCP Client...")
    asyncio.run(main())