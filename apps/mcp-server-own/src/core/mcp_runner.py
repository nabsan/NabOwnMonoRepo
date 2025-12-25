"""MCP Runner Gateway - FastMCP-based tool orchestration.

Loads tool functions from src/scripts and exposes them via FastMCP.
The @keyword router in main.py routes prompts to specific tools.
"""

from fastmcp import FastMCP
from typing import Any, Dict

# Import tool functions
from scripts.hello import hello
from scripts.host_status import (
    get_os_name, 
    get_system_resources, 
    get_disk_usage, 
    check_disk_space_warning, 
    get_process_info
)
from scripts.vertica_query import vertica_query
from scripts.postgres_query import postgres_query
from scripts.rest_call import rest_call


# Initialize FastMCP gateway
mcp = FastMCP(name="mcp-server-own", description="@keyword gateway for tool routing")


# Register tool functions
@mcp.tool()
def hello_tool(message: str = "world") -> Dict[str, Any]:
    """Respond to greetings"""
    return hello(message)


@mcp.tool()
def get_os_name_tool() -> Dict[str, str]:
    """Get OS and platform information"""
    return get_os_name()


@mcp.tool()
def get_system_resources_tool() -> Dict[str, Any]:
    """Get CPU, memory, and load information"""
    return get_system_resources()


@mcp.tool()
def get_disk_usage_tool(path: str = "/") -> Dict[str, Any]:
    """Get disk usage for a path"""
    return get_disk_usage(path)


@mcp.tool()
def check_disk_space_warning_tool(path: str = "/") -> Dict[str, Any]:
    """Check disk space and return warning if high"""
    return check_disk_space_warning(path)


@mcp.tool()
def get_process_info_tool() -> Dict[str, Any]:
    """Get list of running processes"""
    return get_process_info()


@mcp.tool()
def vertica_query_tool(sql: str, limit: int = 100) -> Dict[str, Any]:
    """Execute query on Vertica"""
    return vertica_query(sql, limit)


@mcp.tool()
def postgres_query_tool(sql: str, limit: int = 100) -> Dict[str, Any]:
    """Execute query on PostgreSQL"""
    return postgres_query(sql, limit)


@mcp.tool()
def rest_call_tool(url: str, method: str = 'GET', timeout: int = 10) -> Dict[str, Any]:
    """Make REST API call"""
    return rest_call(url, method, timeout)


# Tool registry for @keyword mapping
TOOLS = {
    "hello": hello_tool,
    "get_os_name": get_os_name_tool,
    "get_system_resources": get_system_resources_tool,
    "get_disk_usage": get_disk_usage_tool,
    "check_disk_space_warning": check_disk_space_warning_tool,
    "get_process_info": get_process_info_tool,
    "vertica_query": vertica_query_tool,
    "postgres_query": postgres_query_tool,
    "rest_call": rest_call_tool,
}


def get_mcp_server():
    """Return FastMCP gateway instance"""
    return mcp
