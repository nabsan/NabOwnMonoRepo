from fastapi import FastAPI, HTTPException, Request
from core.mcp_runner import call_tool, list_tools

app = FastAPI(title="mcp-server-own")

@app.get("/mcp/tools")
def get_tools():
    tools = list_tools()
    return {
        "count": len(tools),
        "tools": tools,
    }

@app.get("/mcp/{tool_name}")
async def run_tool_get(tool_name: str, request: Request):
    try:
        params = dict(request.query_params)
        return call_tool(tool_name, params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/{tool_name}")
def run_tool_post(tool_name: str, payload: dict):
    try:
        return call_tool(tool_name, payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
