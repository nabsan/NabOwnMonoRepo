from fastmcp import tool

@tool
def hello(name: str = "world"):
    """Simple hello tool"""
    return {"message": f"hello {name}"}
