"""REST API call tool."""

import requests
from typing import Dict, Any


def rest_call(url: str, method: str = 'GET', timeout: int = 10) -> Dict[str, Any]:
    """Make a REST API call.
    
    Args:
        url: Target URL
        method: HTTP method (GET, POST, etc.)
        timeout: Request timeout in seconds
    
    Returns:
        dict: Response status and text
    """
    try:
        resp = requests.request(method, url, timeout=timeout)
        return {
            "url": url,
            "method": method,
            "status_code": resp.status_code,
            "text": resp.text[:500]  # Truncate for brevity
        }
    except Exception as e:
        return {
            "url": url,
            "error": str(e)
        }


if __name__ == '__main__':
    result = rest_call('https://httpbin.org/get')
    print(result)

