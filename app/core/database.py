import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


class Database:
    client: AsyncIOMotorClient = None

    @staticmethod
    async def connect():
        if not Database.is_connected():
            Database.client = AsyncIOMotorClient(settings.MONGODB_URL)

    @staticmethod
    async def close():
        if Database.client:
            Database.client.close()

    @staticmethod
    def get_database():
        return Database.client[settings.DATABASE_NAME]

    @staticmethod
    def get_collection(collection_name: str):
        return Database.client[settings.DATABASE_NAME][collection_name]

    @staticmethod
    async def aggregate(collection_name: str, pipeline: list):
        """
        Perform aggregation on a specified collection.

        :param collection_name: Name of the MongoDB collection.
        :param pipeline: Aggregation pipeline (list of stages).
        :return: List of aggregation results.
        """
        collection = Database.get_collection(collection_name)
        results = await collection.aggregate(pipeline).to_list(length=5)

        return results

    @staticmethod
    def is_connected() -> bool:
        return Database.client is not None and Database.client is not None


db = Database()
asyncio.run(db.connect())
user_collection = db.get_collection("users")
chat_collection = db.get_collection("chats")
institution_collection = db.get_collection("institutions")
course_collection = db.get_collection("courses")
scraper_collection = db.get_collection("scrapers")
