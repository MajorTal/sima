"""
Heartbeat Sense - CPU utilization as an interoceptive signal.

Maps CPU usage to a heartbeat metaphor:
- Low CPU = calm, resting
- High CPU = racing, stressed

Sampling: Every tick (fast sense)
Source: /proc/stat for local, AWS CloudWatch for ECS
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _read_proc_stat_cpu() -> float | None:
    """
    Read CPU utilization from /proc/stat (Linux only).

    Returns CPU usage percentage or None if unavailable.
    """
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()

        # Format: cpu user nice system idle iowait irq softirq steal guest guest_nice
        parts = line.split()
        if parts[0] != "cpu":
            return None

        # Sum all non-idle times
        user = int(parts[1])
        nice = int(parts[2])
        system = int(parts[3])
        idle = int(parts[4])
        iowait = int(parts[5]) if len(parts) > 5 else 0
        irq = int(parts[6]) if len(parts) > 6 else 0
        softirq = int(parts[7]) if len(parts) > 7 else 0
        steal = int(parts[8]) if len(parts) > 8 else 0

        # Total and idle times
        total = user + nice + system + idle + iowait + irq + softirq + steal
        idle_total = idle + iowait

        if total == 0:
            return 0.0

        # Calculate usage percentage
        usage = ((total - idle_total) / total) * 100
        return round(usage, 1)

    except FileNotFoundError:
        logger.debug("/proc/stat not found (not Linux)")
        return None
    except (ValueError, IndexError) as e:
        logger.warning(f"Failed to parse /proc/stat: {e}")
        return None


def _read_container_cpu() -> float | None:
    """
    Read CPU utilization from container cgroup (for Docker/ECS).

    Returns CPU usage percentage or None if unavailable.
    """
    # cgroup v2 path
    cpu_stat_path = "/sys/fs/cgroup/cpu.stat"
    cpu_max_path = "/sys/fs/cgroup/cpu.max"

    try:
        # Read usage_usec from cpu.stat
        usage_usec = None
        with open(cpu_stat_path, "r") as f:
            for line in f:
                if line.startswith("usage_usec"):
                    usage_usec = int(line.split()[1])
                    break

        if usage_usec is None:
            return None

        # Read cpu.max for quota (format: "max period" or "quota period")
        with open(cpu_max_path, "r") as f:
            parts = f.read().strip().split()
            if parts[0] == "max":
                # No limit set, fall back to system CPU count
                return _read_proc_stat_cpu()
            quota = int(parts[0])
            period = int(parts[1])

        # Calculate CPU percentage based on quota
        # This is a snapshot, not a differential, so it's an approximation
        cpu_count = os.cpu_count() or 1
        max_usec = quota * cpu_count

        if max_usec == 0:
            return 0.0

        # This gives us an approximation of current CPU usage
        usage_pct = (usage_usec % (period * 1000)) / (period * 10)
        return round(min(usage_pct, 100.0), 1)

    except FileNotFoundError:
        logger.debug("cgroup v2 cpu files not found")
        return None
    except (ValueError, IndexError) as e:
        logger.warning(f"Failed to parse cgroup cpu stats: {e}")
        return None


class HeartbeatSense:
    """
    Collects CPU utilization as a "heartbeat rate" interoceptive sense.

    Interpretation guide (for Sima, not enforced):
    - 0-30%: Calm, resting
    - 30-60%: Active, engaged
    - 60-80%: Working hard
    - 80-100%: Racing, stressed
    """

    def __init__(self):
        self._last_reading: float | None = None

    async def collect(self) -> dict[str, Any]:
        """
        Collect current CPU utilization.

        Returns:
            Heartbeat rate data structure with value, unit, and description.
        """
        # Try container cgroup first (for ECS/Docker), then fall back to /proc/stat
        value = _read_container_cpu()
        if value is None:
            value = _read_proc_stat_cpu()

        # If still None, use a fallback value
        if value is None:
            # On non-Linux systems or in tests, provide a neutral value
            value = 25.0
            logger.debug("Using fallback CPU value (non-Linux environment)")

        self._last_reading = value

        return {
            "value": value,
            "unit": "percent",
            "description": "CPU utilization of The Brain container",
        }

    @property
    def last_reading(self) -> float | None:
        """Return the last collected CPU reading."""
        return self._last_reading
