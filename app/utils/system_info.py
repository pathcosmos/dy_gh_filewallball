"""
System Information Utility Module

This module provides functions to gather real-time system information
including CPU, memory, disk usage, network information, and process details.
"""

import os
import socket
import platform
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Store the start time when the module is first imported
START_TIME = datetime.now()


def get_uptime() -> str:
    """Calculate and format the application uptime."""
    uptime_delta = datetime.now() - START_TIME
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

    return ", ".join(parts)


def get_memory_info() -> Dict[str, Any]:
    """Get memory usage information."""
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "memory_usage_mb": round(memory.used / (1024 * 1024), 2),
        "memory_total_mb": round(memory.total / (1024 * 1024), 2),
        "memory_percent": memory.percent,
        "memory_available_mb": round(memory.available / (1024 * 1024), 2),
        "swap_usage_mb": round(swap.used / (1024 * 1024), 2),
        "swap_total_mb": round(swap.total / (1024 * 1024), 2),
        "swap_percent": swap.percent
    }


def get_disk_info(path: str = "/") -> Dict[str, Any]:
    """Get disk usage information for a specific path."""
    try:
        disk = psutil.disk_usage(path)
        return {
            "disk_usage_gb": round(disk.used / (1024 * 1024 * 1024), 2),
            "disk_total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
            "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
            "disk_percent": disk.percent,
            "disk_path": path
        }
    except Exception as e:
        return {
            "disk_error": str(e),
            "disk_path": path
        }


def get_cpu_info() -> Dict[str, Any]:
    """Get CPU usage and information."""
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    cpu_count_logical = psutil.cpu_count(logical=True)

    # Get load average (Unix-like systems only)
    load_avg = None
    try:
        load_avg = os.getloadavg()
        load_avg = [round(x, 2) for x in load_avg]
    except (AttributeError, OSError):
        pass

    return {
        "cpu_percent": cpu_percent,
        "cpu_count_physical": cpu_count,
        "cpu_count_logical": cpu_count_logical,
        "load_average": load_avg
    }


def get_network_info() -> Dict[str, Any]:
    """Get network information."""
    hostname = socket.gethostname()

    # Get IP addresses
    try:
        # Get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    # Get all network interfaces
    interfaces = []
    try:
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    interfaces.append({
                        "interface": interface,
                        "ip": addr.address,
                        "netmask": addr.netmask
                    })
    except Exception:
        pass

    # Get network IO stats
    net_io = psutil.net_io_counters()

    return {
        "hostname": hostname,
        "local_ip": local_ip,
        "interfaces": interfaces,
        "bytes_sent_mb": round(net_io.bytes_sent / (1024 * 1024), 2),
        "bytes_recv_mb": round(net_io.bytes_recv / (1024 * 1024), 2),
        "packets_sent": net_io.packets_sent,
        "packets_recv": net_io.packets_recv
    }


def get_system_info() -> Dict[str, Any]:
    """Get general system information."""
    return {
        "platform": platform.platform(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "platform_machine": platform.machine(),
        "platform_processor": platform.processor() or "Unknown",
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation()
    }


def get_process_info() -> Dict[str, Any]:
    """Get information about the current process."""
    process = psutil.Process(os.getpid())

    # Get process memory info
    mem_info = process.memory_info()

    # Get process CPU info
    cpu_times = process.cpu_times()

    # Get open file descriptors count (Unix-like systems)
    try:
        num_fds = process.num_fds()
    except AttributeError:
        num_fds = None

    # Get number of threads
    num_threads = process.num_threads()

    # Get connections
    try:
        connections = len(process.connections())
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        connections = 0

    return {
        "pid": process.pid,
        "process_memory_mb": round(mem_info.rss / (1024 * 1024), 2),
        "process_memory_percent": round(process.memory_percent(), 2),
        "process_cpu_percent": round(process.cpu_percent(), 2),
        "process_cpu_time_user": round(cpu_times.user, 2),
        "process_cpu_time_system": round(cpu_times.system, 2),
        "process_num_threads": num_threads,
        "process_num_fds": num_fds,
        "process_num_connections": connections
    }


def get_docker_info() -> Optional[Dict[str, Any]]:
    """Get Docker container information if running in Docker."""
    docker_info = {}

    # Check if running in Docker
    if os.path.exists('/.dockerenv'):
        docker_info["in_docker"] = True

        # Try to get container ID
        try:
            with open('/proc/self/cgroup', 'r') as f:
                for line in f:
                    if 'docker' in line:
                        container_id = line.split('/')[-1].strip()[:12]
                        docker_info["container_id"] = container_id
                        break
        except Exception:
            pass

        # Get container hostname (usually the container ID)
        docker_info["container_hostname"] = socket.gethostname()

    else:
        docker_info["in_docker"] = False

    return docker_info


def get_all_system_info() -> Dict[str, Any]:
    """
    Gather all system information into a single dictionary.
    """
    info = {
        "timestamp": datetime.now().isoformat(),
        "uptime": get_uptime(),
        **get_system_info(),
        **get_memory_info(),
        **get_disk_info(),
        **get_cpu_info(),
        **get_network_info(),
        **get_process_info(),
        **get_docker_info()
    }

    # Format some values for better readability
    info["memory_usage"] = f"{info['memory_usage_mb']} MB / {info['memory_total_mb']} MB ({info['memory_percent']}%)"
    info["disk_usage"] = f"{info['disk_usage_gb']} GB / {info['disk_total_gb']} GB ({info['disk_percent']}%)"
    info["cpu_usage"] = f"{info['cpu_percent']}% ({info['cpu_count_logical']} cores)"

    return info


def get_health_status(db_connected: bool = True) -> str:
    """
    Determine overall health status based on system metrics.

    Args:
        db_connected: Whether database is connected

    Returns:
        Health status: "healthy", "degraded", or "critical"
    """
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Define thresholds
        critical_conditions = [
            memory.percent > 95,  # Memory usage above 95%
            disk.percent > 95,    # Disk usage above 95%
            cpu_percent > 90,      # CPU usage above 90%
            not db_connected       # Database not connected
        ]

        degraded_conditions = [
            memory.percent > 85,  # Memory usage above 85%
            disk.percent > 85,    # Disk usage above 85%
            cpu_percent > 80,      # CPU usage above 80%
        ]

        if any(critical_conditions):
            return "critical"
        elif any(degraded_conditions):
            return "degraded"
        else:
            return "healthy"

    except Exception:
        return "unknown"