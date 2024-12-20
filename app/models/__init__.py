from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional, Tuple, Union

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, Field

from app.core import db

PyObjectId = Annotated[str, BeforeValidator(str)]


class BaseModel(BaseModel):
    __collection_name__: str
    id: PyObjectId = Field(
        alias="_id", default_factory=lambda: str(ObjectId())
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __init__(self, **data: Any):
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            )
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(
                data["updated_at"].replace("Z", "+00:00")
            )
        super().__init__(**data)
        self.id = data.get("id", self.id)
        self.created_at = data.get("created_at", self.created_at)
        self.updated_at = data.get("updated_at", self.updated_at)

    @classmethod
    async def list(
        cls,
        page: int = 1,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = {},
        sort: Optional[List[tuple]] = None,
    ) -> Tuple[List[Any], int]:
        """
        List documents with pagination and optional filtering/sorting

        :param page: Page number for pagination
        :param limit: Number of items per page
        :param filter: Dictionary of filter conditions
        :param sort: List of tuples for sorting (field, direction)
        :return: Tuple of list of instances and total count
        """
        collection = db.get_collection(cls.__collection_name__)
        skip = (page - 1) * limit

        cursor = collection.find(filters).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)

        documents = await cursor.to_list(length=limit)
        total = await collection.count_documents(filters)

        instances = []
        for doc in documents:
            instance = cls(**doc)

            for field_name, field in cls.model_fields.items():
                if (
                    field.annotation
                    and hasattr(field.annotation, "__origin__")
                    and field.annotation.__origin__ is Union
                    and PyObjectId in field.annotation.__args__
                ):
                    for model_type in field.annotation.__args__:
                        if (
                            model_type is not PyObjectId
                            and model_type is not type(None)
                        ):
                            if doc.get(field_name):
                                expanded_model = await model_type.get(
                                    doc[field_name]
                                )
                                if expanded_model:
                                    setattr(
                                        instance,
                                        field_name,
                                        expanded_model,
                                    )

            instances.append(instance)

        return instances, total

    @classmethod
    async def get(cls, id: Optional[str] = None, **kwargs) -> Optional[Any]:
        """
        Retrieve a single document by ID and expand Union[PyObjectId, Model] fields

        :param id: Document ID
        :param kwargs: Additional filter parameters
        :return: Class instance of the document or None
        """
        collection = db.get_collection(cls.__collection_name__)
        filters = {"_id": id} if id else {}
        filters.update(kwargs)
        doc = await collection.find_one(filters)
        if not doc:
            return None

        instance = cls(**doc)

        for field_name, field in cls.model_fields.items():
            if (
                field.annotation
                and hasattr(field.annotation, "__origin__")
                and field.annotation.__origin__ is Union
                and PyObjectId in field.annotation.__args__
            ):
                for model_type in field.annotation.__args__:
                    if (
                        model_type is not PyObjectId
                        and model_type is not type(None)
                    ):
                        if doc.get(field_name):
                            expanded_model = await model_type.get(
                                doc[field_name]
                            )
                            if expanded_model:
                                setattr(instance, field_name, expanded_model)

        return instance

    async def save(self) -> Dict[str, Any]:
        """
        Save the current instance to the database and return expanded object

        :return: Serialized saved document with expanded references
        """
        collection = db.get_collection(self.__collection_name__)
        self.updated_at = datetime.now(timezone.utc)

        # Store original objects before converting to IDs
        original_values = {}

        # Convert expanded models to IDs for saving
        for field_name, field in self.model_fields.items():
            if (
                field.annotation
                and hasattr(field.annotation, "__origin__")
                and field.annotation.__origin__ is Union
                and PyObjectId in field.annotation.__args__
            ):
                value = getattr(self, field_name)
                if value and hasattr(value, "id"):
                    original_values[field_name] = value
                    setattr(self, field_name, value.id)

        doc = self.model_dump(by_alias=True, mode="json")

        if self.__class__.__name__ == "User" and hasattr(
            self, "hashed_password"
        ):
            doc["hashed_password"] = self.hashed_password

        await collection.update_one(
            {"_id": doc["_id"]}, {"$set": doc}, upsert=True
        )

        # Restore original objects
        for field_name, value in original_values.items():
            setattr(self, field_name, value)

        return self

    async def delete(self) -> bool:
        """
        Delete the current instance from the database

        :return: Whether deletion was successful
        """
        collection = db.get_collection(self.__collection_name__)
        result = await collection.delete_one({"_id": self.id})
        return result.deleted_count > 0
