from fastmcp import tool
import psutil
import platform
import os

@tool
"""Host and system status tools."""

import psutil
import platform
import os
from typing import Dict, Any


def get_os_name() -> Dict[str, str]:
    """Get OS and platform information."""
    return {
        "hostname": platform.node(),
        "os": platform.platform(),
        "python": platform.python_version(),
    }


def get_system_resources() -> Dict[str, Any]:
    """Get CPU, memory, and load information."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "total": psutil.virtual_memory().total,
            "used": psutil.virtual_memory().used,
            "percent": psutil.virtual_memory().percent,
        },
        "loadavg": os.getloadavg(),
    }


def get_disk_usage(path: str = "/") -> Dict[str, Any]:
    """Get disk usage for a given path."""
    disk_info = psutil.disk_usage(path)
    return {
        "path": path,
        "total": disk_info.total,
        "used": disk_info.used,
        "free": disk_info.free,
        "percent": disk_info.percent,
    }


def check_disk_space_warning(path: str = "/") -> Dict[str, Any]:
    """Check disk space and return warning if usage is high."""
    disk_info = psutil.disk_usage(path)
    warning = "" if disk_info.percent < 80 else f"WARNING: Disk {path} is {disk_info.percent}% full!"
    return {
        "path": path,
        "percent": disk_info.percent,
        "warning": warning,
    }


def get_process_info() -> Dict[str, Any]:
    """Get list of running processes."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
        try:
            processes.append({
                "pid": proc.info['pid'],
                "name": proc.info['name'],
                "memory_percent": proc.info['memory_percent'],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return {"processes": processes[:10]}  # Return top 10

