from fastmcp import tool
import requests

@tool
def rest_call(url: str, method: str = "GET", timeout: int = 10):
    """Call external REST API"""
    r = requests.request(method, url, timeout=timeout)
    return {
        "status_code": r.status_code,
        "headers": dict(r.headers),
        "body": r.text[:5000],
    }

