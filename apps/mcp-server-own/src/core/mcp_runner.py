from fastmcp import FastMCP
from core.tool_loader import load_tools

TOOLS = load_tools("scripts")

mcp = FastMCP(
    name="mcp-server-own",
    tools=TOOLS,
)

def call_tool(tool_name: str, args: dict):
    return mcp.call_tool(tool_name, args)

def list_tools():
    return [
        {
            "name": t.__name__,
            "doc": t.__doc__ or "",
            "params": list(t.__annotations__.keys()),
        }
        for t in TOOLS
    ]
