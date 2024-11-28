from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from app.core.database import Database

db = Database()


class BaseModel(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Class attribute for collection name (not persisted)
    _collection_name: str = None

    @classmethod
    def _get_collection(cls):
        """
        Internal method to get the collection name.
        Subclasses should override this with their specific collection name.
        """
        if cls._collection_name is None:
            raise ValueError(f"Collection name not set for {cls.__name__}")
        return str(cls._collection_name.default)

    @classmethod
    async def list(
        cls,
        page: int = 1,
        limit: int = 10,
        filter: Optional[Dict[str, Any]] = None,
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
        filter = filter or {}
        collection = db.get_collection(cls._get_collection())
        skip = (page - 1) * limit

        # Apply sorting if provided
        cursor = collection.find(filter).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)

        # Convert raw documents to model instances and serialize
        documents = await cursor.to_list(length=limit)
        return await cls.serialize(documents)

    @classmethod
    async def get(cls, id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single document by ID

        :param id: Document ID
        :return: Serialized document or None
        """
        collection = db.get_collection(cls._get_collection())
        doc = await collection.find_one({"_id": ObjectId(id)})

        if not doc:
            return None

        return await cls.serialize(doc)

    @classmethod
    def create(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new document

        :param data: Document data
        :return: Serialized created document
        """
        collection = db.get_collection(cls._get_collection())

        # Ensure default fields are set
        if "id" not in data:
            data["id"] = str(ObjectId())
        data["created_at"] = datetime.now(timezone.utc())
        data["updated_at"] = datetime.now(timezone.utc())

        # Create model instance and validate
        model_instance = cls.model_validate(data)

        # Insert validated data
        collection.insert_one(model_instance.model_dump())

        return model_instance.model_dump()

    @classmethod
    def update(cls, id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing document

        :param id: Document ID
        :param data: Update data
        :return: Serialized updated document
        """
        collection = db.get_collection(cls._get_collection())

        # Retrieve existing document first
        existing_doc = collection.find_one({"id": id})
        if not existing_doc:
            return None

        # Merge existing data with update data
        merged_data = {**existing_doc, **data}
        merged_data["updated_at"] = datetime.now(timezone.utc())

        # Validate merged data
        model_instance = cls.model_validate(merged_data)

        # Update with validated data
        collection.update_one({"id": id}, {"$set": model_instance.model_dump()})

        return model_instance.model_dump()

    @classmethod
    def delete(cls, id: str) -> bool:
        """
        Delete a document by ID

        :param id: Document ID
        :return: Whether deletion was successful
        """
        collection = db.get_collection(cls._get_collection())
        result = collection.delete_one({"id": id})
        return result.deleted_count > 0

    def save(self) -> Dict[str, Any]:
        """
        Save the current instance to the database

        :return: Serialized saved document
        """
        collection = db.get_collection(self._get_collection())

        # Ensure timestamps are set
        self.updated_at = datetime.now(timezone.utc())

        # Generate ID if not exists
        if not self.id:
            self.id = str(ObjectId())
            self.created_at = self.updated_at

        # Convert to dictionary and save
        data = self.model_dump(exclude_unset=True)
        data.pop("_collection_name", None)

        collection.update_one({"id": self.id}, {"$set": data}, upsert=True)

        return data

    @classmethod
    async def serialize(cls, documents: Any) -> Any:
        """
        Serialize a document or a list of documents, excluding internal attributes

        :param documents: A raw document or a list of raw documents
        :return: Serialized document or list of serialized documents
        """

        def _serialize(doc):
            doc["id"] = str(doc.pop("_id", None))
            for key, value in doc.items():
                if isinstance(value, ObjectId):
                    doc[key] = str(value)
            model_instance = cls.model_validate(doc)
            serialized = model_instance.model_dump(mode="json")
            return serialized

        if isinstance(documents, list):
            return [_serialize(doc) for doc in documents]
        return _serialize(documents)
