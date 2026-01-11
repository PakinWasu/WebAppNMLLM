#!/usr/bin/env python3
"""
Seed script to create initial admin user.
Run with: python -m scripts.seed_admin
"""
import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.settings import settings
from app.core.security import hash_password

ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@net.app"
ADMIN_PASSWORD = "admin123"


async def main():
    print(f"Connecting to MongoDB at {settings.MONGODB_URI}...")
    client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client[settings.MONGODB_DB_NAME]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("MongoDB connected successfully!")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        client.close()
        return
    
    # Check if admin exists
    existing = await db["users"].find_one({"username": ADMIN_USERNAME})
    if existing:
        print(f"Admin user '{ADMIN_USERNAME}' already exists. Skipping.")
        client.close()
        return
    
    # Create admin user
    doc = {
        "username": ADMIN_USERNAME,
        "email": ADMIN_EMAIL,
        "password_hash": hash_password(ADMIN_PASSWORD),
        "role": "admin",
        "created_at": datetime.now(timezone.utc),
        "last_login_at": None,
    }
    await db["users"].insert_one(doc)
    print(f"Admin user created: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
