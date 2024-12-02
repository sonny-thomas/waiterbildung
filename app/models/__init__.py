from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from app.core.database import db


class BaseModel(BaseModel):
    __collection_name__: str

    id: str = Field(default_factory=lambda: str(ObjectId()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(self, *args, **kwargs):
        if "_id" in kwargs:
            kwargs["id"] = str(kwargs.pop("_id"))

        if "id" not in kwargs:
            kwargs["id"] = str(ObjectId())

        super().__init__(*args, **kwargs)

    @classmethod
    async def list(
        cls,
        page: int = 1,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = {},
        sort: Optional[List[tuple]] = None,
    ) -> List[Any]:
        """
        List documents with pagination and optional filtering/sorting

        :param page: Page number for pagination
        :param limit: Number of items per page
        :param filter: Dictionary of filter conditions
        :param sort: List of tuples for sorting (field, direction)
        :return: List of serialized documents
        """
        collection = db.get_collection(cls.__collection_name__)
        skip = (page - 1) * limit

        cursor = collection.find(filters).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)

        documents = await cursor.to_list(length=limit)
        return [cls(**doc) for doc in documents]

    @classmethod
    async def get(cls, id: Optional[str] = None, **kwargs) -> Optional[Any]:
        """
        Retrieve a single document by ID

        :param id: Document ID
        :param kwargs: Additional filter parameters
        :return: Class instance of the document or None
        """
        collection = db.get_collection(cls.__collection_name__)
        filter_params = {**kwargs}

        if id:
            try:
                filter_params["_id"] = ObjectId(id)
            except Exception as e:
                raise ValueError(f"Invalid ObjectId: {id}") from e
        doc = await collection.find_one(filter_params)

        return cls(**doc) if doc else None

    async def save(self) -> Dict[str, Any]:
        """
        Save the current instance to the database

        :param include: Set of fields to include in the saved document
        :return: Serialized saved document
        """
        collection = db.get_collection(self.__collection_name__)

        self.updated_at = datetime.now(timezone.utc)
        doc = self.model_dump(mode="json")

        if self.hashed_password:
            doc["hashed_password"] = self.hashed_password

        doc["_id"] = ObjectId(doc.pop("id", None))
        await collection.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
        doc["id"] = str(doc.pop("_id", None))

        return self.__class__(**doc) if doc else None

    async def delete(self) -> bool:
        """
        Delete the current instance from the database

        :return: Whether deletion was successful
        """
        collection = db.get_collection(self.__collection_name__)
        result = await collection.delete_one({"id": self.id})
        return result.deleted_count > 0
