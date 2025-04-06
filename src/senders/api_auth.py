import logging
import httpx
from config.settings import settings

logger = logging.getLogger(__name__)

class Api:
    def __init__(self, hostname: str, ip: str):
        self.hostname = hostname
        self.ip = ip
        self.token = settings.TOKEN

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
                    logger.info("✅ Агент успешно зарегистрирован")
                    logger.info(f"📦 Ответ сервера: {data}")

                    new_token = data.get("token")
                    if new_token:
                        self.token = new_token
                        logger.info("🔑 Токен обновлён")
                    else:
                        logger.warning("⚠️ Новый токен не получен")
                else:
                    logger.error(f"❌ Ошибка регистрации: {response.status_code} — {response.text}")
        except httpx.HTTPError as e:
            logger.error(f"📡 HTTP ошибка: {e}")
        except Exception as e:
            logger.error(f"💥 Неизвестная ошибка: {e}")

    async def send_compressed_data(self, data: dict):
        """Сжимает данные и отправляет их через защищённый запрос"""
        try:
            url = f"{settings.API_URL}/containers/batch"
            headers = {"Authorization": f"Bearer {self.token}"}

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    logger.info("✅ Сжатые данные успешно отправлены")
                else:
                    logger.error(f"❌ Ошибка отправки данных: {response.status_code} — {response.text}")

        except Exception as e:
            logger.error(f"💥 Ошибка при отправке сжатых данных: {e}")

    async def get_or_create_overlay_network(self, id_network: str, name_network: str):
        try:
            url = f"{settings.API_URL}/networks"
            headers = {"Authorization": f"Bearer {self.token}"}

            async with httpx.AsyncClient() as client:
                pass
                # response = await client.post(url, json=data, headers=headers)
        except Exception as e:
            logger.error(f"💥 Ошибка при создание или получение id overlay сети: {e}")
