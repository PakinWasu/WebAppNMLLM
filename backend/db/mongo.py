from motor.motor_asyncio import AsyncIOMotorClient
from ..core.settings import settings

client: AsyncIOMotorClient | None = None

async def connect():
    global client
    client = AsyncIOMotorClient(settings.MONGO_URL)

def db():
    assert client is not None
    return client[settings.DB_NAME]

async def close():
    global client
    if client:
        client.close()
        client = None
