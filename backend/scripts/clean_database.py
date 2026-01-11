"""Script to clean all data from the database for testing"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.settings import settings

async def clean_database():
    """Delete all data from all collections"""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]
    
    print("⚠️  WARNING: This will delete ALL data from the database!")
    print(f"Database: {settings.MONGODB_DB_NAME}")
    print(f"URI: {settings.MONGODB_URI}")
    
    # List all collections
    collections = await db.list_collection_names()
    print(f"\nCollections found: {collections}")
    
    # Delete all documents from each collection
    results = {}
    for collection_name in collections:
        collection = db[collection_name]
        result = await collection.delete_many({})
        results[collection_name] = result.deleted_count
        print(f"✅ Deleted {result.deleted_count} documents from {collection_name}")
    
    # Also try to delete from parsed_configs if it exists
    try:
        parsed_configs_result = await db["parsed_configs"].delete_many({})
        results["parsed_configs"] = parsed_configs_result.deleted_count
        print(f"✅ Deleted {parsed_configs_result.deleted_count} documents from parsed_configs")
    except Exception as e:
        print(f"⚠️  Could not delete from parsed_configs: {e}")
    
    print("\n✅ Database cleaned!")
    print(f"Total deleted: {sum(results.values())} documents")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(clean_database())

