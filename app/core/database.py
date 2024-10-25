from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings


class Database:
    client: AsyncIOMotorClient = None

    @staticmethod
    async def connect_db():
        Database.client = AsyncIOMotorClient(settings.MONGODB_URL)

    @staticmethod
    async def close_db():
        if Database.client:
            Database.client.close()

    @staticmethod
    def get_collection(collection_name: str):
        return Database.client[settings.DATABASE_NAME][collection_name]
