"""
Unified MCP Gateway Server
Analyzes prompts with @keywords and routes to appropriate tools
"""
import re
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Any
from core.mcp_runner import get_mcp_server

app = FastAPI(title="mcp-server-own", description="Unified MCP Gateway")
mcp = get_mcp_server()


class PromptRequest(BaseModel):
    prompt: str
    params: dict = {}


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    method: str
    params: Optional[dict] = None


def parse_keyword(prompt: str) -> tuple[str, str]:
    """
    Extract @keyword from prompt
    Returns: (keyword, cleaned_prompt)
    """
    match = re.search(r'@(\w+)', prompt)
    if match:
        keyword = match.group(1).lower()
        cleaned_prompt = re.sub(r'@\w+\s*', '', prompt).strip()
        return keyword, cleaned_prompt
    return None, prompt


KEYWORD_TOOL_MAP = {
    "psql": "postgres_query",
    "vertica": "vertica_query",
    "osname": "get_os_name",
    "sysinfo": "get_system_resources",
    "diskusage": "get_disk_usage",
    "diskcheck": "check_disk_space_warning",
    "process": "get_process_info",
    "rest": "rest_call",
    "hello": "hello",
}


@app.get("/")
def root():
    return {
        "service": "mcp-server-own",
        "description": "Unified MCP Gateway with @keyword routing",
        "keywords": list(KEYWORD_TOOL_MAP.keys()),
    }


@app.get("/mcp/tools")
def list_tools():
    """List all available tools"""
    # Access the internal tool manager to get tools
    from core.mcp_runner import TOOLS
    
    tools_info = []
    for name, func in TOOLS.items():
        tools_info.append({
            "name": name,
            "description": func.__doc__ or "No description",
            "params": list(func.__annotations__.keys()) if hasattr(func, '__annotations__') else []
        })
    
    return {
        "count": len(tools_info),
        "tools": tools_info,
        "keywords": KEYWORD_TOOL_MAP,
    }


@app.post("/mcp/query")
async def query_with_prompt(request: PromptRequest):
    """
    Main entry point - analyzes prompt and routes to appropriate tool
    Example: {"prompt": "@osname show system info"}
    """
    keyword, cleaned_prompt = parse_keyword(request.prompt)
    
    if not keyword:
        raise HTTPException(
            status_code=400,
            detail="No @keyword found. Available: " + ", ".join(KEYWORD_TOOL_MAP.keys())
        )
    
    tool_name = KEYWORD_TOOL_MAP.get(keyword)
    if not tool_name:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown keyword '@{keyword}'. Available: " + ", ".join(KEYWORD_TOOL_MAP.keys())
        )
    
    try:
        # Get the actual tool function from TOOLS dict
        from core.mcp_runner import TOOLS
        
        if tool_name not in TOOLS:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found in TOOLS registry"
            )
        
        tool_func = TOOLS[tool_name]
        
        # Route-specific argument mapping
        try:
            if keyword in ["psql", "vertica"]:
                # SQL queries
                result = tool_func(sql=cleaned_prompt)
            elif keyword == "hello":
                # Greeting - pass message
                result = tool_func(message=cleaned_prompt)
            elif keyword == "rest":
                # REST calls - pass URL
                result = tool_func(url=cleaned_prompt)
            elif keyword in ["diskusage", "diskcheck"]:
                # Disk tools - pass path if provided
                if cleaned_prompt and cleaned_prompt.strip():
                    result = tool_func(path=cleaned_prompt.strip())
                else:
                    result = tool_func()  # Use default path
            else:
                # No-argument tools (osname, sysinfo, process)
                result = tool_func()
        except TypeError as e:
            # If argument mismatch, try calling with no args
            result = tool_func()
        
        return {
            "keyword": keyword,
            "tool": tool_name,
            "prompt": cleaned_prompt,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/{tool_name}")
def call_tool_direct(tool_name: str, request: Request):
    """Direct tool call without @keyword routing"""
    try:
        from core.mcp_runner import TOOLS
        
        if tool_name not in TOOLS:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found. Available tools: {list(TOOLS.keys())}"
            )
        
        tool_func = TOOLS[tool_name]
        # Get query parameters as dict
        kwargs = dict(request.query_params)
        result = tool_func(**kwargs)
        return {"tool": tool_name, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp")
async def mcp_jsonrpc(request: MCPRequest):
    """
    MCP JSON-RPC endpoint for GitHub Copilot HTTP integration
    Handles tools/list and tools/call methods
    """
    from core.mcp_runner import TOOLS
    
    try:
        if request.method == "tools/list":
            # Return list of available tools
            tools = []
            for name, func in TOOLS.items():
                tools.append({
                    "name": name,
                    "description": func.__doc__ or "No description",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "Prompt with @keyword"},
                            "params": {"type": "object", "description": "Additional parameters"}
                        }
                    }
                })
            
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {"tools": tools}
            }
        
        elif request.method == "tools/call":
            # Call a tool
            params = request.params or {}
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            # Extract prompt
            prompt = arguments.get("prompt", "")
            tool_params = arguments.get("params", {})
            
            # Parse keyword from prompt
            keyword, cleaned_prompt = parse_keyword(prompt)
            
            if not keyword:
                return {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "error": {
                        "code": -32602,
                        "message": f"No @keyword found. Available: {', '.join(KEYWORD_TOOL_MAP.keys())}"
                    }
                }
            
            tool_func_name = KEYWORD_TOOL_MAP.get(keyword)
            if not tool_func_name or tool_func_name not in TOOLS:
                return {
                    "jsonrpc": "2.0",
                    "id": request.id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown keyword '@{keyword}'"
                    }
                }
            
            tool_func = TOOLS[tool_func_name]
            
            # Prepare arguments
            args = tool_params.copy()
            
            # Route based on keyword
            if keyword in ["psql", "vertica"]:
                args["sql"] = cleaned_prompt
            elif keyword == "hello":
                args["message"] = cleaned_prompt
            elif keyword == "rest":
                args["url"] = cleaned_prompt
            elif keyword in ["diskusage", "diskcheck"]:
                if cleaned_prompt and cleaned_prompt.strip():
                    args["path"] = cleaned_prompt.strip()
            
            # Execute tool
            result = tool_func(**args)
            
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": str(result)
                        }
                    ]
                }
            }
        
        elif request.method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "mcp-server-own",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                }
            }
    
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }
        
