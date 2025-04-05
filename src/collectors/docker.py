import asyncio  # Импортируем asyncio
import docker
import socket
import psutil
import redis.asyncio as aioredis
from datetime import datetime

class DockerCollector:
    def __init__(self, agent_id, redis_host):
        self.client = docker.DockerClient(base_url='unix:///Users/germanmironchuc/.docker/run/docker.sock')
        self.agent_id = agent_id
        self.local_ip = self.local_ip = "127.0.0.1"
        self.hostname = socket.gethostname()
        self.redis = None
        self.redis_host = redis_host

    async def init_redis(self):
        self.redis = await aioredis.from_url(f"redis://{self.redis_host}")

    async def collect(self):
        if not self.redis:
            await self.init_redis()

        metrics = {
            "docker": {},
            "agent_id": self.agent_id,
            "connections": {
                "local_ip": self.local_ip,
                # "outbound": await self._get_outbound_connections(),  # асинхронный вызов
                "inter_container": await self._get_inter_container_connections()  # асинхронный вызов
            },
            "timestamp": int(datetime.now().timestamp())
        }
        print('kfasldj', metrics)

        containers = await asyncio.to_thread(self.client.containers.list)  # асинхронный вызов через asyncio.to_thread()

        for container in containers:
            project = container.labels.get('com.docker.compose.project', 'standalone')
            if project not in metrics["docker"]:
                metrics["docker"][project] = {}

            metrics["docker"][project][container.name] = {
                "container_id": container.short_id,
                "image": container.attrs['Config']['Image'],
                "ports": self._get_ports(container),
                "status": container.status,
                "state": container.attrs['State']['Status'],
                "last_started": container.attrs['State']['StartedAt'],
                "networks": list(container.attrs['NetworkSettings']['Networks'].keys())
            }
        print(metrics)
        return metrics

    def _get_ports(self, container):
        ports = []
        port_bindings = container.attrs['HostConfig'].get('PortBindings', {})
        for port, bindings in port_bindings.items():
            if bindings:
                for binding in bindings:
                    ports.append(f"{binding.get('HostPort', '')}:{port}")
        return ports

    # async def _get_outbound_connections(self):
    #     # Асинхронный метод для получения соединений
    #     print(conn.laddr.ip)
    #     return [
    #         {
    #             "local": f"{conn.laddr.ip}:{conn.laddr.port}",
    #             "remote": f"{conn.raddr.ip}:{conn.raddr.port}",
    #             "status": conn.status
    #         }
    #         for conn in psutil.net_connections(kind='inet')
    #         if conn.status == 'ESTABLISHED' and conn.raddr
    #     ]

    async def _get_inter_container_connections(self):
        connections = []
        containers = await asyncio.to_thread(self.client.containers.list)  # асинхронный вызов через asyncio.to_thread()

        for container in containers:
            networks = container.attrs['NetworkSettings']['Networks']
            for net_name, net_info in networks.items():
                ip = net_info['IPAddress']
                if not ip:
                    continue

                try:
                    cmd = f"nsenter -t {container.attrs['State']['Pid']} -n netstat -tunp 2>/dev/null"
                    result = await asyncio.to_thread(container.exec_run, cmd)  # асинхронный запуск команды

                    for line in result.output.decode().split('\n'):
                        if 'ESTABLISHED' in line:
                            parts = line.split()
                            local, remote = parts[3], parts[4]

                            for target in containers:
                                target_ip = target.attrs['NetworkSettings']['Networks'].get(net_name, {}).get("IPAddress", "")
                                if target_ip and target_ip in remote:
                                    connections.append({
                                        "source": container.name,
                                        "target": target.name,
                                        "network": net_name,
                                        "connection": f"{local} -> {remote}",
                                        "protocol": parts[0]
                                    })
                except:
                    continue

        return connections
