import asyncio
import docker
import logging
from datetime import datetime, timezone, timedelta

class DockerCollector:
    def __init__(self, api_auth=None, excluded_containers=None):
        self.client = docker.DockerClient(base_url='unix:///Users/germanmironchuc/.docker/run/docker.sock')
        self.api_auth = api_auth
        self.known_containers = []
        self.known_networks = []
        self.excluded_containers = excluded_containers or []
        self.default_networks = ['host', 'none', 'bridge']
        self.last_stats_check_time = datetime.now(tz=timezone.utc)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    async def collect(self):
        try:
            now = datetime.now(tz=timezone.utc)
            should_check_stats = (now - self.last_stats_check_time) >= timedelta(hours=1)
            if should_check_stats:
                self.last_stats_check_time = now

            result = {
                "networks": [],
                "containers": [],
                "known_networks": self.known_networks,
                "known_containers": self.known_containers
            }

            networks = await asyncio.to_thread(self.client.networks.list)
            containers = await asyncio.to_thread(self.client.containers.list)

            network_id_map = {}
            for network in networks:
                network_type = network.attrs.get('Driver', 'unknown')
                if network_type == "overlay":
                    try:
                        import json
                        from subprocess import PIPE, run

                        # Используем docker inspect для получения полной информации о сети
                        inspect_result = run(["docker", "network", "inspect", network.id], stdout=PIPE, stderr=PIPE, text=True)
                        if inspect_result.returncode == 0:
                            network_info = json.loads(inspect_result.stdout)[0]
                            peers = []

                            # Получаем IP всех узлов (Peers) overlay-сети
                            for peer in network_info.get('Peers', []):
                                ip = peer.get("IP")
                                if ip:
                                    peers.append(ip)

                            await self.api_auth.get_or_create_overlay_network(
                                id_network=network.id,
                                name_network=network.name,
                                peers=peers
                            )
                        else:
                            self.logger.error(f"docker inspect error: {inspect_result.stderr}")
                    except Exception as e:
                        self.logger.error(f"Error while inspecting overlay network {network.id}: {e}")

                if network.name in self.default_networks or self._is_known_network(network.id):
                    continue
                network_id_map[network.id] = network.id
                result["networks"].append({
                    "name": network.name,
                    "network_id": network.id
                })

            for container in containers:
                if container.name in self.excluded_containers or container.short_id in self.excluded_containers:
                    continue

                container_id = container.short_id
                container_name = container.name

                if self._is_known_container(container_id):
                    known = next(c for c in self.known_containers if c["container_id"] == container_id)
                else:
                    created_at = datetime.fromisoformat(container.attrs['Created'].replace("Z", "+00:00"))
                    known = {
                        "container_id": container_id,
                        "last_rx": 0,
                        "last_tx": 0,
                        "last_active": created_at.isoformat(timespec='milliseconds').replace("+00:00", "Z"),
                        "id": None  # добавляем, чтобы потом обновить из API
                    }
                    self.known_containers.append(known)

                if should_check_stats:
                    try:
                        stats = await asyncio.to_thread(container.stats, stream=False)
                        networks_stats = stats.get("networks", {})

                        rx = sum(int(i.get("rx_bytes", 0)) for i in networks_stats.values())
                        tx = sum(int(i.get("tx_bytes", 0)) for i in networks_stats.values())

                        if rx > known.get("last_rx", 0) or tx > known.get("last_tx", 0):
                            known["last_active"] = now.isoformat(timespec='milliseconds').replace("+00:00", "Z")

                        known["last_rx"] = rx
                        known["last_tx"] = tx

                        is_alive = (now - datetime.fromisoformat(known["last_active"].replace("Z", "+00:00"))) <= timedelta(minutes=2)
                        status = "running" if is_alive else "exited"

                        global_container_id = known.get("id")
                        if global_container_id:
                            payload = {
                                "status": status,
                                "created_at": datetime.fromisoformat(container.attrs['Created'].replace("Z", "+00:00")).isoformat(timespec='milliseconds').replace("+00:00", "Z"),
                                "last_active": known["last_active"],
                                "id": global_container_id
                            }

                            await self.api_auth.change_container_data(data=payload, id=global_container_id)

                            if self.api_auth.redis_stream_manager:
                                await self.api_auth.redis_stream_manager.send_message(payload)

                    except Exception as e:
                        self.logger.warning(f"Не удалось получить stats для {container_name}: {e}")

                container_networks = container.attrs['NetworkSettings']['Networks']
                network_ids = [
                    network_id_map[network.id]
                    for network in networks
                    if network.name in container_networks and network.name not in self.default_networks and network.id in network_id_map
                ]

                container_ip = ""
                for net_info in container_networks.values():
                    if net_info.get("IPAddress"):
                        container_ip = net_info["IPAddress"]
                        break

                created_at = datetime.fromisoformat(container.attrs['Created'].replace("Z", "+00:00"))
                result["containers"].append({
                    "name": container.name,
                    "image": container.attrs['Config']['Image'],
                    "container_id": container.short_id,
                    "status": container.status,
                    "ip": container_ip,
                    "created_at": created_at.isoformat(timespec='milliseconds').replace("+00:00", "Z"),
                    "network_ids": network_ids,
                    "last_active": known["last_active"]
                })

            if result:
                return result

        except Exception as e:
            self.logger.error(f"Ошибка при сборе метрик: {e}")
            return {
                "networks": [],
                "containers": [],
                "known_networks": [],
                "known_containers": []
            }

    def _is_known_container(self, container_id):
        return any(c["container_id"] == container_id for c in self.known_containers)

    def _is_known_network(self, network_id):
        return any(n["network_id"] == network_id for n in self.known_networks)
