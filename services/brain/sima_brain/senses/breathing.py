"""
Breathing Sense - Memory utilization as an interoceptive signal.

Maps memory usage to a breathing metaphor:
- Low memory = easy breathing, relaxed
- High memory = heavy breathing, strained

Sampling: Every tick (fast sense)
Source: /proc/meminfo for local, AWS CloudWatch for ECS
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _read_proc_meminfo() -> float | None:
    """
    Read memory utilization from /proc/meminfo (Linux only).

    Returns memory usage percentage or None if unavailable.
    """
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    # Values are in kB
                    key = parts[0].rstrip(":")
                    meminfo[key] = int(parts[1])

        total = meminfo.get("MemTotal", 0)
        available = meminfo.get("MemAvailable")

        if available is None:
            # Fallback for older kernels without MemAvailable
            free = meminfo.get("MemFree", 0)
            buffers = meminfo.get("Buffers", 0)
            cached = meminfo.get("Cached", 0)
            available = free + buffers + cached

        if total == 0:
            return 0.0

        used = total - available
        usage = (used / total) * 100
        return round(usage, 1)

    except FileNotFoundError:
        logger.debug("/proc/meminfo not found (not Linux)")
        return None
    except (ValueError, KeyError) as e:
        logger.warning(f"Failed to parse /proc/meminfo: {e}")
        return None


def _read_container_memory() -> float | None:
    """
    Read memory utilization from container cgroup (for Docker/ECS).

    Returns memory usage percentage or None if unavailable.
    """
    # cgroup v2 paths
    memory_current_path = "/sys/fs/cgroup/memory.current"
    memory_max_path = "/sys/fs/cgroup/memory.max"

    try:
        # Read current memory usage
        with open(memory_current_path, "r") as f:
            current = int(f.read().strip())

        # Read memory limit
        with open(memory_max_path, "r") as f:
            max_str = f.read().strip()
            if max_str == "max":
                # No limit set, use system memory
                return _read_proc_meminfo()
            max_bytes = int(max_str)

        if max_bytes == 0:
            return 0.0

        usage = (current / max_bytes) * 100
        return round(usage, 1)

    except FileNotFoundError:
        logger.debug("cgroup v2 memory files not found")
        return None
    except (ValueError, IndexError) as e:
        logger.warning(f"Failed to parse cgroup memory stats: {e}")
        return None


class BreathingSense:
    """
    Collects memory utilization as a "breathing rate" interoceptive sense.

    Interpretation guide (for Sima, not enforced):
    - 0-50%: Easy breathing, relaxed
    - 50-75%: Normal exertion
    - 75-90%: Heavy breathing, strained
    - 90-100%: Gasping, critical
    """

    def __init__(self):
        self._last_reading: float | None = None

    async def collect(self) -> dict[str, Any]:
        """
        Collect current memory utilization.

        Returns:
            Breathing rate data structure with value, unit, and description.
        """
        # Try container cgroup first (for ECS/Docker), then fall back to /proc/meminfo
        value = _read_container_memory()
        if value is None:
            value = _read_proc_meminfo()

        # If still None, use a fallback value
        if value is None:
            # On non-Linux systems or in tests, provide a neutral value
            value = 40.0
            logger.debug("Using fallback memory value (non-Linux environment)")

        self._last_reading = value

        return {
            "value": value,
            "unit": "percent",
            "description": "Memory utilization of The Brain container",
        }

    @property
    def last_reading(self) -> float | None:
        """Return the last collected memory reading."""
        return self._last_reading
