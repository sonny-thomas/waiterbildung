import os
import json
import asyncio
from tqdm.asyncio import tqdm
from app.core.config import settings
from app.core.database import Database
from app.services.utils import generate_embedding_openai
from pymongo.operations import SearchIndexModel
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

# Remove embedding field from collection
async def remove_embedding_field():
    await Database.connect_db()
    collection = Database.get_collection("courses")
    response = await collection.update_many(
        {"embedding": {"$exists": True}},  # Filter documents with "embedding" field
        {"$unset": {"embedding": ""}}     # Remove "embedding" field
    )
    # Extract the required information
    modified_count = response.modified_count
    print(f"Modified Documents: {modified_count}")
    await Database.close_db()
    return {"Modified Documents": modified_count}
    
# Create Vector embedding in course courses
async def insert_vector_embedding():
    # Insert vector embedding from course collection in db
    await Database.connect_db()

    collection = Database.get_collection("courses")
    cursor = collection.find({"embedding": {"$eq": None}})

    # found documents count
    total_documents = await collection.count_documents({"embedding": {"$eq": None}})
    print(f"Found {total_documents} documents without embedding")
    
    success_count = 0
    failure_count = 0
    async def process_document(document):
        nonlocal success_count, failure_count
        doc_id = document["_id"]
        embedding_data = {
            "title": document.get("program_name", ""),
            "description": document.get("description", ""),
            "key_data" : document.get("key_data")
        }
        result = await generate_embedding_openai(json.dumps(embedding_data))
        
        if isinstance(result, str):
            failure_count += 1
            print(f"Failed to generate embedding for document {doc_id}: {result}")
            return
        else:
            embedding = result
        try:
            result = await collection.update_one(
                {"_id": doc_id},
                {"$set": {"embedding": embedding}}
            )
            success_count += 1
            print(f"Updated document {doc_id}")
        except Exception as e:
            failure_count += 1
            print(f"Failed to update document {doc_id}: {e}")

    tasks = [process_document(document) async for document in cursor]
    await asyncio.gather(*tasks)
    print("Completed processing all documents successfully")
    await Database.close_db()
    return {"success_count": success_count, "failure_count": failure_count}

# Create Index from Course Collection
async def create_vector_index():
    await Database.connect_db()
    collection = Database.get_collection("courses")
    search_index_model = SearchIndexModel(
        definition={
            "fields": [
                {
                    "type": "vector",
                    "numDimensions": settings.OPENAI_EMBEDDING_DIMENSION,
                    "path": "embedding",
                    "similarity": "cosine" # euclidean | cosine | dotProduct
                },
            ]
        },
        name="vector_index",
        type="vectorSearch",
    )
    
    result = await collection.create_search_index(model=search_index_model)
    await Database.close_db()
    
    return result


# Get Relevant courses from index
# async def get_relevant_courses(query, index):
#     await Database.connect_db()
#     courses = await Database.get_collection("courses").find().to_list(None)
#     return courses