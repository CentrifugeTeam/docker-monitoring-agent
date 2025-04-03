import docker
import redis
import json
import socket
from datetime import datetime
import psutil

class DockerCollector:
    def __init__(self, agent_id, redis_host):
        self.client = docker.from_env()
        self.redis = redis.Redis(host=redis_host, port=6379)
        self.agent_id = agent_id
        self.local_ip = socket.gethostbyname(socket.gethostname())
        self.hostname = socket.gethostname()

    def collect(self):
        metrics = {
            "docker": {},
            "agent_id": self.agent_id,
            "connections": {
                "local_ip": self.local_ip,
                "outbound": self._get_outbound_connections(),
                "inter_container": self._get_inter_container_connections()
            },
            "timestamp": int(datetime.now().timestamp())
        }

        # Собираем информацию о контейнерах
        for container in self.client.containers.list():
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

        return metrics

    def _get_ports(self, container):
        ports = []
        for port, bindings in container.attrs['HostConfig']['PortBindings'].items():
            if bindings:
                for binding in bindings:
                    ports.append(f"{binding['HostPort']}:{port}")
        return ports

    def _get_outbound_connections(self):
        connections = []
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'ESTABLISHED' and conn.raddr:
                connections.append({
                    "local": f"{conn.laddr.ip}:{conn.laddr.port}",
                    "remote": f"{conn.raddr.ip}:{conn.raddr.port}",
                    "status": conn.status
                })
        return connections

    def _get_inter_container_connections(self):
        """Анализирует соединения между контейнерами в одной сети"""
        connections = []
        containers = self.client.containers.list()

        for container in containers:
            networks = container.attrs['NetworkSettings']['Networks']
            for net_name, net_info in networks.items():
                ip = net_info['IPAddress']
                if not ip:
                    continue

                # Получаем соединения для этого контейнера
                try:
                    # Используем nsenter для анализа соединений внутри контейнера
                    cmd = f"nsenter -t {container.attrs['State']['Pid']} -n netstat -tunp 2>/dev/null"
                    result = container.exec_run(cmd)

                    for line in result.output.decode().split('\n'):
                        if 'ESTABLISHED' in line:
                            parts = line.split()
                            local = parts[3]
                            remote = parts[4]

                            # Проверяем, является ли удаленный IP контейнером в той же сети
                            for target in containers:
                                target_networks = target.attrs['NetworkSettings']['Networks']
                                if net_name in target_networks and target_networks[net_name]['IPAddress'] in remote:
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
