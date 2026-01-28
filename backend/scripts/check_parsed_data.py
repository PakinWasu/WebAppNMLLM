#!/usr/bin/env python3
"""Check parsed data in database"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.mongo import db, connect, close

async def check_parsed_data():
    """Check what parsed data exists in database"""
    await connect()
    
    try:
        # Get all projects
        projects = []
        async for project in db()["projects"].find({}):
            projects.append(project["project_id"])
        
        print(f"📁 Found {len(projects)} project(s)")
        
        for project_id in projects:
            print(f"\n{'='*60}")
            print(f"Project: {project_id}")
            print(f"{'='*60}")
            
            # Check parsed_configs collection
            parsed_count = await db()["parsed_configs"].count_documents({"project_id": project_id})
            print(f"\n📊 Parsed Configs Collection: {parsed_count} device(s)")
            
            if parsed_count > 0:
                async for doc in db()["parsed_configs"].find({"project_id": project_id}).limit(5):
                    device_name = doc.get("device_name", "N/A")
                    overview = doc.get("device_overview", {})
                    interfaces = doc.get("interfaces", [])
                    vlans = doc.get("vlans", {})
                    
                    print(f"\n  Device: {device_name}")
                    print(f"    Hostname: {overview.get('hostname', 'N/A')}")
                    print(f"    Model: {overview.get('model', 'N/A')}")
                    print(f"    OS Version: {overview.get('os_version', 'N/A')}")
                    print(f"    Management IP: {overview.get('management_ip', 'N/A')}")
                    print(f"    Interfaces: {len(interfaces)}")
                    print(f"    VLANs: {vlans.get('total_vlan_count', 0)}")
            
            # Check documents collection with parsed_config
            doc_count = await db()["documents"].count_documents({
                "project_id": project_id,
                "is_latest": True,
                "parsed_config": {"$exists": True}
            })
            print(f"\n📄 Documents with parsed_config: {doc_count} document(s)")
            
            if doc_count > 0:
                async for doc in db()["documents"].find({
                    "project_id": project_id,
                    "is_latest": True,
                    "parsed_config": {"$exists": True}
                }).limit(5):
                    filename = doc.get("filename", "N/A")
                    parsed_config = doc.get("parsed_config", {})
                    device_name = parsed_config.get("device_name", "N/A")
                    overview = parsed_config.get("device_overview", {})
                    
                    print(f"\n  File: {filename}")
                    print(f"    Device: {device_name}")
                    print(f"    Hostname: {overview.get('hostname', 'N/A')}")
                    print(f"    Model: {overview.get('model', 'N/A')}")
    
    finally:
        await close()

if __name__ == "__main__":
    asyncio.run(check_parsed_data())
