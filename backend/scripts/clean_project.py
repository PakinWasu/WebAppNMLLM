"""Script to clean all data for a specific project"""

import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.settings import settings

async def clean_project(project_id: str):
    """Delete all data for a specific project"""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]
    
    print(f"⚠️  WARNING: This will delete ALL data for project: {project_id}")
    print(f"Database: {settings.MONGODB_DB_NAME}")
    
    # Check if project exists
    project = await db["projects"].find_one({"project_id": project_id})
    if not project:
        print(f"❌ Project {project_id} not found!")
        client.close()
        return
    
    print(f"Project name: {project.get('name', 'N/A')}")
    
    # Delete all data related to this project
    results = {}
    
    # 1. Delete project members
    result = await db["project_members"].delete_many({"project_id": project_id})
    results["members"] = result.deleted_count
    print(f"✅ Deleted {result.deleted_count} project members")
    
    # 2. Delete all documents
    result = await db["documents"].delete_many({"project_id": project_id})
    results["documents"] = result.deleted_count
    print(f"✅ Deleted {result.deleted_count} documents")
    
    # 3. Delete parsed_configs
    try:
        result = await db["parsed_configs"].delete_many({"project_id": project_id})
        results["parsed_configs"] = result.deleted_count
        print(f"✅ Deleted {result.deleted_count} parsed configs")
    except Exception as e:
        print(f"⚠️  Could not delete from parsed_configs: {e}")
        results["parsed_configs"] = 0
    
    # 4. Delete project options
    try:
        result = await db["project_options"].delete_many({"project_id": project_id})
        results["options"] = result.deleted_count
        print(f"✅ Deleted {result.deleted_count} project options")
    except Exception as e:
        print(f"⚠️  Could not delete from project_options: {e}")
        results["options"] = 0
    
    # 5. Delete the project itself
    result = await db["projects"].delete_one({"project_id": project_id})
    results["project"] = result.deleted_count
    print(f"✅ Deleted {result.deleted_count} project")
    
    print(f"\n✅ Project {project_id} cleaned!")
    print(f"Total deleted: {sum(results.values())} documents")
    
    client.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python clean_project.py <project_id>")
        sys.exit(1)
    
    project_id = sys.argv[1]
    asyncio.run(clean_project(project_id))

