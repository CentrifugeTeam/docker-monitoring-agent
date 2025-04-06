import asyncio
import docker
import logging

class DockerCollector:
    def __init__(self, api_auth=None):
        self.client = docker.DockerClient(base_url='unix:///Users/germanmironchuc/.docker/run/docker.sock')
        self.api_auth = api_auth
        # Список стандартных сетей для исключения
        self.default_networks = ['host', 'none', 'bridge']

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    async def collect(self):
        try:
            result = {
                "networks": [],
                "containers": []
            }

            networks = await asyncio.to_thread(self.client.networks.list)
            containers = await asyncio.to_thread(self.client.containers.list)

            # Сопоставим network.id с индексом для дальнейшего использования
            network_id_map = {}
            for i, network in enumerate(networks):
                # обработка для overlay сети
                network_type = network.attrs.get('Driver', 'unknown')
                if network_type == "overlay":
                    await self.api_auth.get_or_create_overlay_network()


                self.logger.debug(f"network_type: {network_type}")

                # Пропускаем стандартные сети
                if network.name not in self.default_networks:
                    network_id_map[network.id] = network.id  # Сохраняем настоящий id сети
                    result["networks"].append({
                        "name": network.name,
                        "network_id": network.id  # Используем настоящий ID сети
                    })

            for container in containers:
                container_networks = container.attrs['NetworkSettings']['Networks']
                network_ids = [
                    network_id_map[network.id]  # Теперь собираем настоящий ID сети
                    for network in networks
                    if network.name in container_networks and network.name not in self.default_networks
                ]

                container_ip = ""
                for net_info in container_networks.values():
                    if net_info.get("IPAddress"):
                        container_ip = net_info["IPAddress"]
                        break

                result["containers"].append({
                    "name": container.name,
                    "image": container.attrs['Config']['Image'],
                    "container_id": container.short_id,
                    "status": container.status,
                    "ip": container_ip,
                    "created_at": container.attrs['Created'],
                    "network_ids": network_ids  # Теперь в этом поле будут только ID сетей
                })

            # self.logger.debug(f"Collected metrics: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Ошибка при сборе метрик: {e}")
            return {
                "networks": [],
                "containers": []
            }
