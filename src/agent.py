import asyncio
import logging
import socket
import psutil
from .collectors.docker import DockerCollector
from .processors.compressor import GzipCompressor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class DockerAgent:
    def __init__(self, agent_id, redis_host='localhost'):
        self.logger = logging.getLogger(__name__)
        self.interval = 60
        self.agent_id = agent_id
        self.collector = DockerCollector(agent_id, redis_host)
        self.compressor = GzipCompressor()
        self.local_ip = socket.gethostbyname(socket.gethostname())
        self.hostname = socket.gethostname()

    async def run(self):
        await self.collector.init_redis()

        # Initial data collection
        initial_report = await self._collect_data()
        initial_report.update({
            "event_type": "agent_start",
            "status": "initialized"
        })
        await self._send_report(initial_report)

        while True:
            try:
                start_time = asyncio.get_event_loop().time()
                report = await self._collect_data()
                report["event_type"] = "periodic_update"
                await self._send_report(report)

                elapsed = asyncio.get_event_loop().time() - start_time
                await asyncio.sleep(max(0, self.interval - elapsed))

            except asyncio.CancelledError:
                self.logger.info("Agent stopped by cancel")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")

    async def _collect_data(self):
        try:
            report = await self.collector.collect()

            # Network IO
            net_io = psutil.net_io_counters()
            report.update({
                "network": {
                    "in": {"bytes": net_io.bytes_recv, "packets": net_io.packets_recv},
                    "out": {"bytes": net_io.bytes_sent, "packets": net_io.packets_sent}
                },
                "host": {"hostname": self.hostname, "ip": self.local_ip}
            })

            return report

        except Exception as e:
            self.logger.error(f"Error collecting data: {e}")
            return {}

    async def _send_report(self, report):
        try:
            compressed = self.compressor.compress(report)
            await self.collector.redis.xadd(
                "agent_data",
                {"agent_id": self.agent_id, "data": compressed, "timestamp": int(asyncio.get_event_loop().time())}
            )
        except Exception as e:
            self.logger.error(f"Send failed: {e}")
