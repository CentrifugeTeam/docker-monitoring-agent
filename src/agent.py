import asyncio
import logging
import socket
import psutil
from config.settings import settings
from .senders.api_auth import Api
from .collectors.docker_get_topology import DockerCollector
from  datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class DockerAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.hostname = socket.gethostname()
        self.local_ip = "127.0.0.1"
        self.interval = settings.INTERVAL
        self.api_auth = Api(self.hostname, self.local_ip)
        self.collector = DockerCollector(
            api_auth=self.api_auth,
            excluded_containers=settings.EXCLUDED_CONTAINERS
        )

    async def run(self):
        await self._register_agent()

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
        """Отправка топологии данных через API"""
        # response = await self.api_auth.send_compressed_data(report)

        # if response:
        #     new_known_networks = response.get("networks", [])
        #     new_known_containers = response.get("containers", [])

        #     self.collector.known_networks = new_known_networks

        #     for new in new_known_containers:
        #         found = False
        #         for existing in self.collector.known_containers:
        #             if existing["container_id"] == new["container_id"]:
        #                 existing["id"] = new["id"]
        #                 found = True
        #                 break
        #         if not found:
        #             self.collector.known_containers.append({
        #                 "container_id": new["container_id"],
        #                 "id": new["id"],
        #                 "last_rx": 0,
        #                 "last_tx": 0,
        #                 "last_active": datetime.now(tz=timezone.utc).isoformat(timespec='milliseconds').replace("+00:00", "Z")
        #             })

    async def _register_agent(self):
        """Регистрация агента через API"""
        # await self.api_auth.register_agent()
