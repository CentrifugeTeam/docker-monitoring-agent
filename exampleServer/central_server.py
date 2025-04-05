from fastapi import FastAPI
import redis.asyncio as aioredis
import asyncpg
import logging
from pydantic import BaseModel
import asyncio
import gzip
import base64
import json
from io import BytesIO
from datetime import datetime

app = FastAPI()
logging.basicConfig(level=logging.INFO)

redis_pool = None
postgres_pool = None

class AgentData(BaseModel):
    agent_id: str
    docker: dict
    connections: dict
    timestamp: int

# Подключение к Redis при старте приложения
@app.on_event("startup")
async def startup():
    global redis_pool, postgres_pool
    try:
        logging.info("Starting Redis connection...")
        redis_pool = await aioredis.from_url("redis://localhost")
        app.state.redis = redis_pool
        logging.info("✅ Successfully connected to Redis.")

        logging.info("Starting PostgreSQL connection...")
        postgres_pool = await asyncpg.create_pool(
            user="postgres", password="S100is100",
            database="docker_monitor", host="localhost"
        )
        app.state.pool = postgres_pool
        logging.info("✅ Successfully connected to PostgreSQL.")

        # Проверка соединения с PostgreSQL
        async with app.state.pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                logging.info("✅ PostgreSQL connection test passed.")
            else:
                logging.error("❌ PostgreSQL connection test failed.")
                raise Exception("PostgreSQL connection test failed.")

        # Создание базы данных
        await create_db_schema()

        # Запуск фонового прослушивания Redis Stream
        asyncio.create_task(listen_to_redis_stream())
        logging.info("✅ Background task started.")
    except Exception as e:
        logging.error(f"❌ Failed to initialize application resources: {e}")
        raise

# Очистка ресурсов при завершении работы приложения
@app.on_event("shutdown")
async def shutdown():
    try:
        if redis_pool:
            await redis_pool.close()
            logging.info("✅ Redis connection closed.")
        if postgres_pool:
            await postgres_pool.close()
            logging.info("✅ PostgreSQL connection closed.")
    except Exception as e:
        logging.error(f"❌ Failed to clean up resources: {e}")

# Обработчик для получения данных
@app.post("/receive_data")
async def receive_data(data: dict):
    # Декодируем и распаковываем данные из Gzip и Base64
    try:
        base64_data = data['data']  # Предполагается, что данные приходят в поле "data"
        # Декодируем base64
        compressed_data = base64.b64decode(base64_data)
        # Распаковываем Gzip
        with gzip.GzipFile(fileobj=BytesIO(compressed_data), mode='rb') as f:
            json_data = f.read().decode('utf-8')

        # Десериализуем JSON
        agent_data = json.loads(json_data)

        # Валидируем данные с помощью Pydantic модели
        agent_data_model = AgentData(**agent_data)

        logging.info(f"✅ Data received and processed: {agent_data_model}")
        return {"status": "received", "message": "Data successfully processed."}

    except Exception as e:
        logging.error(f"❌ Failed to process data: {e}")
        return {"status": "error", "message": f"Failed to process data: {e}"}

async def listen_to_redis_stream():
    while True:
        try:
            # Читаем данные из Redis Stream
            stream_data = await app.state.redis.xread({"agent_data": "$"}, count=1, block=0)
            for _, messages in stream_data:
                for message_id, message in messages:
                    data_json = message[b"data"].decode("utf-8")
                    try:
                        # Попытка распаковки сжатых данных
                        compressed_data = base64.b64decode(data_json)
                        with gzip.GzipFile(fileobj=BytesIO(compressed_data), mode='rb') as f:
                            json_data = f.read().decode('utf-8')

                        # Десериализуем JSON
                        agent_data = json.loads(json_data)

                        # Валидируем данные с помощью Pydantic модели
                        data = AgentData(**agent_data)
                        await process_agent_data(data)

                    except Exception as e:
                        logging.error(f"Error processing message: {e}")
                        continue
        except Exception as e:
            logging.error(f"Error reading from Redis stream: {e}")
            await asyncio.sleep(5)

async def process_agent_data(data: AgentData):
    try:
        async with app.state.pool.acquire() as conn:
            machine_id = await conn.fetchval('''
                INSERT INTO machines (agent_id, ip_address, last_seen)
                VALUES ($1, $2, NOW())
                ON CONFLICT (agent_id) DO UPDATE SET last_seen = NOW()
                RETURNING id
            ''', data.agent_id, data.connections.get('local_ip'))

            for project, containers in data.docker.items():
                for name, container in containers.items():
                    # Преобразуем список портов в строку
                    ports_str = ",".join(container['ports']) if isinstance(container['ports'], list) else container['ports']

                    # Преобразуем строку времени в datetime
                    try:
                        last_started = datetime.strptime(container['last_started'], "%Y-%m-%dT%H:%M:%S.%fZ")
                    except ValueError:
                        last_started = None  # В случае ошибки можно установить None

                    container_id = await conn.fetchval('''
                        INSERT INTO containers
                        (machine_id, container_id, name, image, ports, last_started)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (machine_id, container_id) DO UPDATE SET
                        name = $3, image = $4, ports = $5, last_started = $6
                        RETURNING id
                    ''', machine_id, container['container_id'], name,
                       container['image'], ports_str, last_started)  # Передаём datetime

                    for conn_info in data.connections.get('outbound', []):
                        await conn.execute('''
                            INSERT INTO connections
                            (source_container, target_container, direction,
                             protocol, bytes_sent, bytes_received, timestamp)
                            VALUES ($1, $2, $3, $4, $5, $6, NOW())
                        ''', container_id, resolve_target(conn_info), 'outbound',
                           conn_info['protocol'], conn_info['bytes'], 0)
    except Exception as e:
        logging.error(f"❌ Failed to process agent data: {e}")


def resolve_target(connection_info):
    return connection_info['remote']

async def create_db_schema():
    try:
        async with app.state.pool.acquire() as conn:
            # Создание таблицы machines
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id SERIAL PRIMARY KEY,
                agent_id TEXT UNIQUE,
                ip_address TEXT,
                last_seen TIMESTAMP
            )''')
            logging.info("✅ machines table created.")

            # Добавление уникального индекса на agent_id
            await conn.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_id ON machines(agent_id);
            ''')

            # Создание таблицы containers
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS containers (
                id SERIAL PRIMARY KEY,
                machine_id INTEGER REFERENCES machines(id),
                container_id TEXT,
                name TEXT,
                image TEXT,
                ports TEXT,
                last_started TIMESTAMP
            )''')
            logging.info("✅ containers table created.")

            # Добавление уникального индекса на machine_id и container_id
            await conn.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_machine_container ON containers(machine_id, container_id);
            ''')

            # Создание таблицы connections
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS connections (
                id SERIAL PRIMARY KEY,
                source_container INTEGER REFERENCES containers(id),
                target_container INTEGER REFERENCES containers(id),
                direction TEXT,
                protocol TEXT,
                bytes_sent BIGINT,
                bytes_received BIGINT,
                timestamp TIMESTAMP
            )''')
            logging.info("✅ connections table created.")

            # Добавление уникального индекса на source_container и target_container
            await conn.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_source_target_container ON connections(source_container, target_container);
            ''')

    except Exception as e:
        logging.error(f"❌ Error creating database schema: {e}")
        raise
