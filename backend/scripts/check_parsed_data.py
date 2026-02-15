#!/usr/bin/env python3
"""Check parsed data in database. Usage: python check_parsed_data.py [project_id]"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.mongo import db, connect, close


def _safe_str(v, max_len=80):
    s = str(v) if v is not None else ""
    return (s[: max_len] + "…") if len(s) > max_len else s


async def check_parsed_data(project_id_filter=None):
    """Check what parsed data exists in database. If project_id_filter is set, only that project."""
    await connect()

    try:
        if project_id_filter:
            projects = [project_id_filter]
            # Verify project exists
            p = await db()["projects"].find_one({"project_id": project_id_filter})
            if not p:
                print(f"❌ Project not found: {project_id_filter!r}")
                return
        else:
            projects = []
            async for project in db()["projects"].find({}):
                projects.append(project["project_id"])
            print(f"📁 Found {len(projects)} project(s)")

        for project_id in projects:
            print(f"\n{'='*60}")
            print(f"Project: {project_id!r}")
            print(f"{'='*60}")

            # Parsed configs (used by topology first)
            parsed_count = await db()["parsed_configs"].count_documents({"project_id": project_id})
            print(f"\n📊 parsed_configs (project_id={project_id!r}): {parsed_count} doc(s)")

            if parsed_count > 0:
                async for doc in db()["parsed_configs"].find({"project_id": project_id}).limit(5):
                    device_name = doc.get("device_name", "N/A")
                    overview = doc.get("device_overview", {})
                    interfaces = doc.get("interfaces", [])
                    vlans = doc.get("vlans", {})
                    print(f"\n  device_name={device_name!r}")
                    print(f"    device_overview keys: {list(overview.keys())[:12]}")
                    print(f"    interfaces: {len(interfaces)}, vlans: {vlans.get('total_vlan_count', len(vlans.get('vlan_list', [])))}")

            # Documents with parsed_config (topology fallback = same as Summary)
            query_docs = {
                "project_id": project_id,
                "is_latest": True,
                "parsed_config": {"$exists": True},
            }
            doc_count = await db()["documents"].count_documents(query_docs)
            print(f"\n📄 documents (is_latest=True, parsed_config exists): {doc_count} doc(s)")

            if doc_count > 0:
                async for doc in db()["documents"].find(query_docs).limit(10):
                    filename = doc.get("filename", "N/A")
                    folder_id = doc.get("folder_id")
                    pc = doc.get("parsed_config") or {}
                    device_name = pc.get("device_name")
                    overview = pc.get("device_overview") or {}
                    interfaces = pc.get("interfaces") or []
                    neighbors = pc.get("neighbors") or []
                    print(f"\n  filename={filename!r} folder_id={folder_id!r}")
                    print(f"    parsed_config.device_name={device_name!r}")
                    print(f"    parsed_config keys: {list(pc.keys())}")
                    print(f"    device_overview keys: {list(overview.keys())[:10]}")
                    print(f"    interfaces: {len(interfaces)}, neighbors: {len(neighbors)}")
            else:
                # Show why: any docs in project at all? with folder_id Config?
                total_in_project = await db()["documents"].count_documents({"project_id": project_id, "is_latest": True})
                config_folder = await db()["documents"].count_documents({
                    "project_id": project_id,
                    "is_latest": True,
                    "folder_id": "Config",
                })
                any_parsed = await db()["documents"].count_documents({
                    "project_id": project_id,
                    "parsed_config": {"$exists": True},
                })
                print(f"  (is_latest docs in project: {total_in_project}, folder_id=Config: {config_folder}, any doc with parsed_config: {any_parsed})")

    finally:
        await close()


if __name__ == "__main__":
    filter_id = sys.argv[1].strip() if len(sys.argv) > 1 else None
    asyncio.run(check_parsed_data(filter_id))
