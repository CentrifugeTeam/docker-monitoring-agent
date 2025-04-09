import asyncio
import logging
from typing import Dict, Any, Optional
from redis.asyncio import Redis

class RedisStreamManager:
  def __init__(
      self,
      stream_name: str = "graph",
      max_stream_length: Optional[int] = None,
  ):
      """
      Асинхронный менеджер для работы с Redis Streams

      :param stream_name: Название стрима
      :param max_stream_length: Максимальная длина стрима (обрезание по достижению)
      """
      self.stream_name = stream_name
      self.max_stream_length = max_stream_length
      self.redis: Optional[Redis] = None
      self.logger = logging.getLogger(self.__class__.__name__)

  async def connect(self):
    """Установка соединения с Redis"""
    try:
      self.redis = Redis(host='158.160.47.155', port='6379', db=0, decode_responses=True)
      # await self.redis.ping()  # Проверка соединения
      self.logger.info("Connected to Redis successfully")
    except Exception as e:
      self.logger.error(f"Redis connection error: {e}")
      raise

  async def disconnect(self):
    """Закрытие соединения с Redis"""
    if self.redis:
      await self.redis.close()
      self.logger.info("Disconnected from Redis")

  async def send_message(self, data: Dict[str, Any]) -> str:
    """
    Отправка сообщения в стрим

    :param data: Данные для отправки (словарь)
    :return: ID добавленного сообщения
    """
    if not self.redis:
      raise RuntimeError("Redis connection not established")

    try:
      # Добавляем сообщение и обрезаем стрим если нужно
      message_id = await self.redis.xadd(
        name=self.stream_name,
        fields=data,
        maxlen=self.max_stream_length,
        approximate=True
      )
      self.logger.debug(f"Message sent to {self.stream_name}, ID: {message_id}")
      return message_id
    except Exception as e:
      self.logger.error(f"Error sending message to Redis Stream: {e}")
      raise

  async def read_messages(
    self,
    count: int = 10,
    block_ms: int = 5000,
    last_id: str = "$",
  ):
    """
    Чтение сообщений из стрима

    :param count: Максимальное количество сообщений
    :param block_ms: Время блокировки в миллисекундах
    :param last_id: ID с которого начинать чтение ("$" - новые сообщения)
    :return: Список сообщений
    """
    if not self.redis:
      raise RuntimeError("Redis connection not established")

    try:
      messages = await self.redis.xread(
        streams={self.stream_name: last_id},
        count=count,
        block=block_ms,
      )

      if messages:
        self.logger.debug(f"Received {len(messages[0][1])} messages")
        return messages[0][1]  # Возвращаем только сообщения из нашего стрима
      return []
    except Exception as e:
      self.logger.error(f"Error reading messages from Redis Stream: {e}")
      raise
