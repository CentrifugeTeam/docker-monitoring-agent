import time
import logging
import socket
import psutil
from .collectors.docker import DockerCollector
from .processors.compressor import GzipCompressor

class DockerAgent:
    def __init__(self, agent_id, redis_host='localhost'):
        self.logger = logging.getLogger(__name__)
        self.interval = 60
        self.agent_id = agent_id
        self.collector = DockerCollector(agent_id, redis_host)
        self.compressor = GzipCompressor()

        # Получаем локальный IP
        self.local_ip = socket.gethostbyname(socket.gethostname())
        self.hostname = socket.gethostname()

    def run(self):
        self.logger.info("Starting Docker Agent on %s (%s)", self.hostname, self.local_ip)

        # Первый сбор данных
        initial_report = self._collect_data()
        initial_report.update({
            "event_type": "agent_start",
            "status": "initialized"
        })

        self._send_report(initial_report)

        while True:
            start_time = time.time()

            try:
                report = self._collect_data()
                report["event_type"] = "periodic_update"
                self._send_report(report)

            except KeyboardInterrupt:
                self.logger.info("Agent stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")

            elapsed = time.time() - start_time
            time.sleep(max(0, self.interval - elapsed))

    def _collect_data(self):
        """Собирает все метрики и возвращает отчет"""
        report = self.collector.collect()

        # Добавляем сетевую статистику
        net_io = psutil.net_io_counters()
        report.update({
            "network": {
                "in": {
                    "bytes": net_io.bytes_recv,
                    "packets": net_io.packets_recv
                },
                "out": {
                    "bytes": net_io.bytes_sent,
                    "packets": net_io.packets_sent
                }
            },
            "host": {
                "hostname": self.hostname,
                "ip": self.local_ip
            }
        })

        return report

    def _send_report(self, report):
        """Отправляет отчет на сервер через Redis Stream"""
        try:
            compressed = self.compressor.compress(report)
            self.collector.redis.xadd(
                "agent_data",
                {
                    "agent_id": self.agent_id,
                    "data": compressed,
                    "timestamp": int(time.time())
                }
            )
            self.logger.debug("Report sent successfully")
        except Exception as e:
            self.logger.error(f"Failed to send report: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    agent = DockerAgent(agent_id=1, redis_host='central_server')
    agent.run()
