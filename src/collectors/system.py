import psutil
import logging
from datetime import datetime

class SystemCollector:
  def __init__(self):
    self.logger = logging.getLogger(__name__)

  def collect(self):
    """Сбор системных метрик: CPU, память, диск, сеть"""
    try:
      return {
        "system": {
          "cpu": self._get_cpu_stats(),
          "memory": self._get_memory_stats(),
          "disk": self._get_disk_stats(),
          "network": self._get_network_stats(),
          "timestamp": datetime.utcnow().isoformat()
        }
      }
    except Exception as e:
      self.logger.error(f"System collection error: {e}")
      return {"system": {}}

  def _get_cpu_stats(self):
    return {
      "percent": psutil.cpu_percent(interval=1),
      "cores": psutil.cpu_count(logical=False),
      "threads": psutil.cpu_count(logical=True)
    }

  def _get_memory_stats(self):
    mem = psutil.virtual_memory()
    return {
      "total": mem.total,
      "available": mem.available,
      "used": mem.used,
      "percent": mem.percent
    }

  def _get_disk_stats(self):
    return {
      mount: psutil.disk_usage(mount)._asdict()
      for mount in [partition.mountpoint for partition in psutil.disk_partitions()]
    }

  def _get_network_stats(self):
    net = psutil.net_io_counters()
    return {
      "bytes_sent": net.bytes_sent,
      "bytes_recv": net.bytes_recv
    }
