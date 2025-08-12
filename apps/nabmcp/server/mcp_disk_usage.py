#!/usr/bin/env python3
"""
MCP server for disk usage information
"""

import shutil
import os
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("disk-usage-server")

@mcp.tool()
def get_disk_usage(path: str = "/") -> str:
    """
    Get disk usage information for the specified path.
    
    Args:
        path (str): Path to check (default: "/")
    
    Returns:
        str: Disk usage information
    """
    try:
        # Get disk usage
        total, used, free = shutil.disk_usage(path)
        
        # Convert bytes to GB
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        free_gb = free / (1024**3)
        
        # Calculate usage percentage
        usage_percent = (used / total) * 100
        
        result = f"""Disk Usage Information (Path: {path})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Total Space:    {total_gb:.2f} GB
💾 Used Space:     {used_gb:.2f} GB ({usage_percent:.1f}%)
💿 Free Space:     {free_gb:.2f} GB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return result
        
    except Exception as e:
        return f"Error: Failed to get disk usage information: {str(e)}"

@mcp.tool()
def get_multiple_disk_usage() -> str:
    """
    Get disk usage information for multiple major paths (/, /tmp, /home, etc.).
    
    Returns:
        str: Multiple paths disk usage information
    """
    paths_to_check = ["/", "/tmp", "/home", "/var"]
    results = []
    
    for path in paths_to_check:
        if os.path.exists(path):
            try:
                total, used, free = shutil.disk_usage(path)
                total_gb = total / (1024**3)
                used_gb = used / (1024**3)
                free_gb = free / (1024**3)
                usage_percent = (used / total) * 100
                
                results.append(f"{path:<10} | {total_gb:>8.1f}GB | {used_gb:>8.1f}GB | {free_gb:>8.1f}GB | {usage_percent:>5.1f}%")
            except Exception as e:
                results.append(f"{path:<10} | Error: {str(e)}")
    
    header = """Multiple Paths Disk Usage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Path       | Total     | Used      | Free      | Usage%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    return header + "\n" + "\n".join(results) + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

@mcp.tool()
def check_disk_space_warning(path: str = "/", threshold: float = 80.0) -> str:
    """
    Check if disk usage exceeds the threshold.
    
    Args:
        path (str): Path to check (default: "/")
        threshold (float): Usage percentage threshold for warning (default: 80.0%)
    
    Returns:
        str: Warning information
    """
    try:
        total, used, free = shutil.disk_usage(path)
        usage_percent = (used / total) * 100
        
        if usage_percent >= threshold:
            status = "🚨 WARNING"
            message = f"Disk usage exceeds {threshold}%!"
        elif usage_percent >= threshold - 10:
            status = "⚠️  CAUTION"
            message = f"Disk usage exceeds {threshold-10}%."
        else:
            status = "✅ NORMAL"
            message = "Disk usage is within normal range."
        
        return f"""{status} - {path}
{message}
Current usage: {usage_percent:.1f}%
Threshold: {threshold}%"""
        
    except Exception as e:
        return f"Error: Failed to check disk usage: {str(e)}"

if __name__ == "__main__":
    # Start MCP server
    mcp.run()