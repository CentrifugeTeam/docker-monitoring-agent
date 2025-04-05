import asyncio
import docker
import logging
from datetime import datetime
import redis.asyncio as aioredis

class DockerCollector:
    def __init__(self, agent_id, redis_host):
        self.client = docker.DockerClient(base_url='unix:///Users/germanmironchuc/.docker/run/docker.sock')
        self.agent_id = agent_id
        self.local_ip = "127.0.0.1"
        self.redis = None
        self.redis_host = redis_host

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    async def init_redis(self):
        """Инициализация Redis соединения"""
        try:
            self.redis = await aioredis.from_url(f"redis://{self.redis_host}")
        except Exception as e:
            raise

    async def collect(self):
        try:
            metrics = {
                "docker": {},
                "agent_id": self.agent_id,
                "connections": {
                    "local_ip": self.local_ip,
                    "outbound": await self._get_outbound_connections(),
                    "inter_container": await self._get_inter_container_connections()
                },
                "timestamp": int(datetime.now().timestamp())
            }

            # Получаем все сети Docker
            networks = await asyncio.to_thread(self.client.networks.list)

            containers = await asyncio.to_thread(self.client.containers.list)

            # Сбор данных о контейнерах
            for container in containers:
                project = container.labels.get('com.docker.compose.project', 'standalone')
                if project not in metrics["docker"]:
                    metrics["docker"][project] = {}

                metrics["docker"][project][container.name] = {
                    "container_id": container.short_id,
                    "image": container.attrs['Config']['Image'],
                    "status": container.status,
                    "state": container.attrs['State']['Status'],
                    "last_started": container.attrs['State']['StartedAt'],
                    "networks": list(container.attrs['NetworkSettings']['Networks'].keys())
                }

            # Сбор сетевых соединений через docker network inspect
            for network in networks:
                network_data = await asyncio.to_thread(self.client.api.inspect_network, network.id)
                containers_in_network = network_data.get("Containers", {})

                for container_id, container_info in containers_in_network.items():
                    container_name = container_info["Name"]
                    container_ip = container_info["IPv4Address"]

                    if container_name not in metrics["docker"][project]:
                        metrics["docker"][project][container_name] = {}

                    metrics["docker"][project][container_name]["network_info"] = {
                        "ip": container_ip,
                        "network": network.name
                    }

                    # Собираем информацию о соединениях между контейнерами в этой сети
                    await self._analyze_container_connections(container_name, container_info, network, containers_in_network)

            self.logger.debug(f"metrics: {metrics}")
            return metrics
        except Exception as e:
            return {}

    async def _analyze_container_connections(self, container_name, container_info, network, containers_in_network):
        """
        Сбор информации о соединениях между контейнерами внутри сети
        """
        try:
            connections = []
            container_ip = container_info["IPv4Address"]

            # Проходим по всем контейнерам в этой сети
            for other_container_id, other_container_info in containers_in_network.items():
                other_container_name = other_container_info["Name"]
                other_container_ip = other_container_info["IPv4Address"]

                if container_name != other_container_name and container_ip and other_container_ip:
                    # Если IP-адреса есть, создаем запись о соединении
                    connections.append({
                        "source": container_name,
                        "target": other_container_name,
                        "network": network.name,
                        "connection": f"{container_ip} <-> {other_container_ip}"
                    })

            return connections
        except Exception as e:
            return []

    async def _get_outbound_connections(self):
        """
        Сбор информации о внешних соединениях контейнеров
        """
        try:
            connections = []
            containers = await asyncio.to_thread(self.client.containers.list)

            for container in containers:
                # Получаем информацию о сетевых соединениях контейнера
                network_settings = container.attrs['NetworkSettings']
                container_ip = network_settings['Networks'].get('bridge', {}).get('IPAddress', '')
                if container_ip:
                    # Мы можем использовать netstat, ss или другую утилиту для получения внешних соединений
                    # В качестве примера используем сетевые соединения в сети "bridge"
                    connections.append({
                        "container": container.name,
                        "ip": container_ip,
                        "type": "outbound"
                    })

            return connections
        except Exception as e:
            return []

    async def _get_inter_container_connections(self):
        """
        Сбор информации о межконтейнерных соединениях
        """
        try:
            connections = []
            containers = await asyncio.to_thread(self.client.containers.list)

            for container in containers:
                networks = container.attrs['NetworkSettings']['Networks']
                for network_name, network_info in networks.items():
                    container_ip = network_info.get('IPAddress', '')
                    if container_ip:
                        # Здесь можно использовать дополнительные утилиты или сетевые запросы для определения соединений между контейнерами
                        connections.append({
                            "source": container.name,
                            "target": "other_container_name",  # Это нужно будет заполнять на основе дополнительной логики
                            "network": network_name,
                            "connection": f"{container_ip} -> some_target_ip"
                        })
            return connections
        except Exception as e:
            return []
