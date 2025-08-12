#!/usr/bin/env python3
"""
MCP server for OS information
"""

import platform
import os
import subprocess
import psutil
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("os-info-server")

@mcp.tool()
def get_os_name() -> str:
    """
    Get basic operating system information.
    
    Returns:
        str: OS name and basic information
    """
    try:
        os_info = f"""Operating System Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🖥️  System:          {platform.system()}
📋 Platform:         {platform.platform()}
🏷️  Release:          {platform.release()}
🔢 Version:          {platform.version()}
🏗️  Architecture:     {platform.architecture()[0]}
💻 Machine Type:     {platform.machine()}
🌐 Network Name:     {platform.node()}
🐍 Python Version:   {platform.python_version()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return os_info
        
    except Exception as e:
        return f"Error: Failed to get OS information: {str(e)}"

@mcp.tool()
def get_system_resources() -> str:
    """
    Get system resource usage (CPU, Memory).
    
    Returns:
        str: System resource information
    """
    try:
        # CPU information
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # Memory information
        memory = psutil.virtual_memory()
        memory_total_gb = memory.total / (1024**3)
        memory_used_gb = memory.used / (1024**3)
        memory_available_gb = memory.available / (1024**3)
        
        # Swap information
        swap = psutil.swap_memory()
        swap_total_gb = swap.total / (1024**3)
        swap_used_gb = swap.used / (1024**3)
        
        # Boot time
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        resource_info = f"""System Resource Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💾 CPU Information:
   Usage:            {cpu_percent}%
   Cores:            {cpu_count}
   Frequency:        {cpu_freq.current:.2f} MHz (Max: {cpu_freq.max:.2f} MHz)

🧠 Memory Information:
   Total:            {memory_total_gb:.2f} GB
   Used:             {memory_used_gb:.2f} GB ({memory.percent}%)
   Available:        {memory_available_gb:.2f} GB

💿 Swap Information:
   Total:            {swap_total_gb:.2f} GB
   Used:             {swap_used_gb:.2f} GB ({swap.percent}%)

⏰ System Uptime:
   Boot Time:        {boot_time.strftime('%Y-%m-%d %H:%M:%S')}
   Uptime:           {str(uptime).split('.')[0]}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return resource_info
        
    except Exception as e:
        return f"Error: Failed to get system resource information: {str(e)}"

@mcp.tool()
def get_rhel_version() -> str:
    """
    Get RHEL (Red Hat Enterprise Linux) version information.
    
    Returns:
        str: RHEL version information
    """
    try:
        rhel_info = []
        
        # Check /etc/redhat-release file
        if os.path.exists("/etc/redhat-release"):
            with open("/etc/redhat-release", "r") as f:
                rhel_info.append(f"Red Hat Release: {f.read().strip()}")
        
        # Check /etc/os-release file
        if os.path.exists("/etc/os-release"):
            os_release_info = {}
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        os_release_info[key] = value.strip('"')
            
            rhel_info.extend([
                f"Name: {os_release_info.get('NAME', 'Unknown')}",
                f"Version: {os_release_info.get('VERSION', 'Unknown')}",
                f"ID: {os_release_info.get('ID', 'Unknown')}",
                f"Version ID: {os_release_info.get('VERSION_ID', 'Unknown')}",
                f"Pretty Name: {os_release_info.get('PRETTY_NAME', 'Unknown')}"
            ])
        
        # Kernel information
        kernel_info = platform.release()
        rhel_info.append(f"Kernel: {kernel_info}")
        
        # Hostname
        hostname = platform.node()
        rhel_info.append(f"Hostname: {hostname}")
        
        result = f"""RHEL System Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🐧 {chr(10).join(rhel_info)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return result
        
    except Exception as e:
        return f"Error: Failed to get RHEL information: {str(e)}"

@mcp.tool()
def get_process_info(limit: int = 10) -> str:
    """
    Get information about running processes.
    
    Args:
        limit (int): Number of processes to display (default: 10)
    
    Returns:
        str: Process information
    """
    try:
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
        
        result = f"""Running Processes (sorted by CPU usage, top {limit})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PID     | Process Name          | CPU%  | MEM%  | User
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        for proc in processes[:limit]:
            pid = proc['pid']
            name = (proc['name'] or 'Unknown')[:20]
            cpu = proc['cpu_percent'] or 0
            mem = proc['memory_percent'] or 0
            user = (proc['username'] or 'Unknown')[:10]
            
            result += f"\n{pid:<8} | {name:<21} | {cpu:>5.1f} | {mem:>5.1f} | {user}"
        
        result += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        return result
        
    except Exception as e:
        return f"Error: Failed to get process information: {str(e)}"

if __name__ == "__main__":
    # Start MCP server
    mcp.run()