import asyncio
import logging
import httpx
from config.settings import settings
from .redis_streams import RedisStreamManager

logger = logging.getLogger(__name__)

class Api:
    def __init__(self, hostname: str, ip: str):
        self.hostname = hostname
        self.ip = ip
        self.token = settings.TOKEN
        self.redis_stream_manager = RedisStreamManager()
        asyncio.create_task(self.redis_stream_manager.connect())

    async def register_agent(self):
        """Асинхронная регистрация агента и обновление токена"""
        url = f"{settings.API_URL}/auth"
        payload = {
            "host": {
                "hostname": self.hostname,
                "ip": self.ip
            },
            "token": self.token
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    new_token = data.get("token")
                    if new_token:
                        self.token = new_token
                    else:
                        logger.warning("⚠️ Новый токен не получен")
                else:
                    logger.error(f"❌ Ошибка регистрации: {response.status_code} — {response.text}")
        except httpx.HTTPError as e:
            logger.error(f"📡 HTTP ошибка: {e}")
        except Exception as e:
            logger.error(f"💥 Неизвестная ошибка: {e}")

    async def send_compressed_data(self, data: dict):
        """отправка топологию сетей и контейнеров"""
        try:
            networks = data["networks"]
            containers = data["containers"]

            data = {
                "networks": networks,
                "containers": containers
            }
            url = f"{settings.API_URL}/containers/batch"
            headers = {"Authorization": f"Bearer {self.token}"}

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers)
                if response.status_code == 200 or response.status_code == 204:
                    logger.info("✅ Сжатые данные успешно отправлены")
                    if response.content:
                        return response.json()
                else:
                    logger.error(f"❌ Ошибка отправки данных: {response.status_code} — {response.text}")

        except Exception as e:
            logger.error(f"💥 Ошибка при отправке сжатых данных: {e}")

    async def get_or_create_overlay_network(self, id_network: str, name_network: str, peers: list[str]):
        try:
            url = f"{settings.API_URL}/networks"
            data = [
                {
                    "name": name_network,
                    "network_id": id_network,
                    "peers": peers
                }
            ]
            headers = {"Authorization": f"Bearer {self.token}"}
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers)
        except Exception as e:
            logger.error(f"💥 Ошибка при создание или получение id overlay сети: {e}")

    async def change_container_data(self, data: dict, id: int):
        try:
            url = f"{settings.API_URL}/containers/{id}"
            logger.error(f"data: {data}")
            headers = {"Authorization": f"Bearer {self.token}"}
            async with httpx.AsyncClient() as client:
                response = await client.patch(url, json=data, headers=headers)
                logger.error(f"response: {response}")
        except Exception as e:
            logger.error(f"💥 Ошибка при измении данных о контейнере: {e}")
