from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from datetime import datetime, timezone
from ..core.settings import settings

_client: AsyncIOMotorClient | None = None
_db = None


async def connect(max_retries: int = 10, delay: float = 2.0):
    """Connect to MongoDB on startup with retry logic and create indexes."""
    global _client, _db
    
    for attempt in range(max_retries):
        try:
            _client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000
            )
            # Actually test the connection with a ping
            await _client.admin.command('ping')
            _db = _client[settings.MONGODB_DB_NAME]
            print("Connected to MongoDB")
            
            # Create indexes for better performance
            await create_indexes()
            
            return
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"MongoDB connection attempt {attempt + 1} failed, retrying in {delay}s... ({e})")
                await asyncio.sleep(delay)
            else:
                print(f"Failed to connect to MongoDB after {max_retries} attempts: {e}")
                raise


async def create_indexes():
    """Create database indexes for better query performance."""
    try:
        # Users collection indexes
        # Username must be unique, but email can be duplicated
        await _db["users"].create_index("username", unique=True)
        # Email index without unique constraint - allow duplicate emails
        await _db["users"].create_index("email")
        
        # Projects collection indexes
        await _db["projects"].create_index("project_id", unique=True)
        await _db["projects"].create_index("created_by")
        
        # Project members collection indexes
        await _db["project_members"].create_index([("project_id", 1), ("username", 1)], unique=True)
        await _db["project_members"].create_index("project_id")
        await _db["project_members"].create_index("username")
        
        # Documents collection indexes
        await _db["documents"].create_index("document_id")
        await _db["documents"].create_index("project_id")
        await _db["documents"].create_index("uploader")
        await _db["documents"].create_index("created_at")
        await _db["documents"].create_index("upload_batch_id")
        await _db["documents"].create_index("parent_document_id")
        await _db["documents"].create_index([("project_id", 1), ("filename", 1)])
        await _db["documents"].create_index([("project_id", 1), ("is_latest", 1)])
        await _db["documents"].create_index([("document_id", 1), ("version", 1)], unique=True)
        
        # Project folders collection indexes
        await _db["project_folders"].create_index("project_id", unique=True)
        
        # Parsed configs collection - create collection and indexes
        # Create collection explicitly to avoid permission issues
        try:
            collection_names = await _db.list_collection_names()
            if "parsed_configs" not in collection_names:
                # Create collection by inserting and immediately deleting a dummy document
                # This ensures the collection exists with proper permissions
                try:
                    dummy_doc = {
                        "_temp": True,
                        "created_at": datetime.now(timezone.utc)
                    }
                    result = await _db["parsed_configs"].insert_one(dummy_doc)
                    if result.inserted_id:
                        await _db["parsed_configs"].delete_one({"_id": result.inserted_id})
                        print("✅ Created parsed_configs collection")
                except Exception as create_err:
                    print(f"⚠️ Could not pre-create parsed_configs collection: {create_err}")
                    print("Collection will be created on first write")
            
            # Create indexes (whether collection existed or was just created)
            try:
                # MongoDB 4.4.18 compatible: iterate through cursor
                index_names = []
                async for idx in _db["parsed_configs"].list_indexes():
                    index_names.append(idx["name"])
                
                if "project_id_1" not in index_names:
                    await _db["parsed_configs"].create_index("project_id", background=True)
                    print("✅ Created project_id index for parsed_configs")
                if "device_name_1" not in index_names:
                    await _db["parsed_configs"].create_index("device_name", background=True)
                    print("✅ Created device_name index for parsed_configs")
                if "upload_timestamp_1" not in index_names:
                    await _db["parsed_configs"].create_index("upload_timestamp", background=True)
                    print("✅ Created upload_timestamp index for parsed_configs")
                if "project_id_1_device_name_1" not in index_names:
                    await _db["parsed_configs"].create_index([("project_id", 1), ("device_name", 1)], background=True)
                    print("✅ Created compound index (project_id, device_name) for parsed_configs")
                
                print("✅ Parsed configs indexes created/verified")
            except Exception as idx_err:
                print(f"⚠️ Could not create all parsed_configs indexes: {idx_err}")
        except Exception as e:
            # Non-critical - indexes can be created later
            print(f"⚠️ Info: Could not setup parsed_configs collection at startup: {e}")
            print("Collection and indexes will be created on first write")
        
        print("MongoDB indexes created")
    except Exception as e:
        print(f"Warning: Could not create indexes: {e}")


async def close():
    """Close MongoDB connection on shutdown."""
    global _client
    if _client:
        _client.close()
        print("MongoDB connection closed")


def db():
    """Return the database instance. Call after connect()."""
    if _db is None:
        raise RuntimeError("Database not connected. Call connect() first.")
    return _db

