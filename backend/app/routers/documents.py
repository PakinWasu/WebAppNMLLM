from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Body
from fastapi.responses import FileResponse, StreamingResponse, PlainTextResponse
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path
import io
import os
import re
import json
import hashlib
from pydantic import BaseModel

from ..db.mongo import db
from ..dependencies.auth import get_current_user, check_project_access
from ..models.document import DocumentCreate, DocumentMetadata, DocumentPublic, DocumentVersionInfo
from ..services.document_storage import upload_documents, get_document_file_path, read_document_file
from ..services.preview import generate_preview
from ..services.config_parser import ConfigParser

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


# check_project_access is now imported from dependencies.auth


async def check_upload_permission(project_id: str, user: dict):
    """Check if user can upload documents (engineer, manager, or admin)"""
    if user.get("role") == "admin":
        return
    
    membership = await db()["project_members"].find_one(
        {"project_id": project_id, "username": user["username"]}
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")
    
    role = membership.get("role")
    if role not in ["engineer", "manager"]:
        raise HTTPException(status_code=403, detail="Only engineer, manager, or admin can upload documents")


@router.post("")
async def upload_documents_endpoint(
    project_id: str,
    files: List[UploadFile] = File(...),
    who: str = Form(..., description="Responsible user"),
    what: str = Form(..., description="Activity type"),
    where: Optional[str] = Form(None, description="Site"),
    when: Optional[str] = Form(None, description="Operational timing"),
    why: Optional[str] = Form(None, description="Purpose"),
    description: Optional[str] = Form(None, description="Description"),
    folder_id: Optional[str] = Form(None, description="Folder ID"),
    user=Depends(get_current_user)
):
    """Upload multiple documents in a single batch with shared metadata"""
    # Check project access
    await check_project_access(project_id, user)
    
    # Check upload permission
    await check_upload_permission(project_id, user)
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Create metadata
    metadata = DocumentMetadata(
        who=who,
        what=what,
        where=where,
        when=when,
        why=why,
        description=description
    )
    
    try:
        # Upload documents
        # Convert empty string to None for folder_id
        folder_id_clean = folder_id if folder_id and folder_id.strip() else None
        
        # Validate folder_id if provided (except for "Config" which is special)
        if folder_id_clean and folder_id_clean != "Config":
            # Check if folder exists in project_folders
            folders_doc = await db()["project_folders"].find_one({"project_id": project_id})
            if folders_doc:
                folders = folders_doc.get("folders", [])
                folder_exists = any(
                    f.get("id") == folder_id_clean and not f.get("deleted", False)
                    for f in folders
                )
                if not folder_exists:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Folder '{folder_id_clean}' does not exist. Please select a valid folder or leave empty for root."
                    )
            else:
                # No folders document means no custom folders exist
                raise HTTPException(
                    status_code=400,
                    detail=f"Folder '{folder_id_clean}' does not exist. Please select a valid folder or leave empty for root."
                )
        
        # Prevent uploading to "Other" folder (it's a virtual folder, not real)
        if folder_id_clean == "Other":
            raise HTTPException(
                status_code=400,
                detail="Cannot upload to 'Other' folder. It is a virtual folder for files with invalid folder_id. Please select a valid folder or leave empty for root."
            )
        
        uploaded = await upload_documents(
            project_id=project_id,
            files=files,
            uploader=user["username"],
            metadata=metadata,
            folder_id=folder_id_clean
        )
        
        # If uploaded to Config folder, trigger parser
        if folder_id_clean == "Config":
            parser = ConfigParser()
            for doc in uploaded:
                try:
                    # Read file content
                    file_path = await get_document_file_path(project_id, doc["document_id"])
                    if file_path and file_path.exists():
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # Parse config
                        parsed_data = parser.parse_config(content, doc["filename"])
                        if parsed_data:
                            device_name = parser.extract_device_name(content, doc["filename"])
                            
                            # Get device overview for summary fields
                            overview = parsed_data.get("device_overview", {})
                            interfaces = parsed_data.get("interfaces", [])
                            vlans = parsed_data.get("vlans", {})
                            stp = parsed_data.get("stp", {})
                            routing = parsed_data.get("routing", {})
                            
                            # Calculate interface stats
                            total_ifaces = len(interfaces)
                            up_ifaces = sum(1 for i in interfaces if i.get("oper_status") == "up")
                            down_ifaces = sum(1 for i in interfaces if i.get("oper_status") == "down")
                            admin_down = sum(1 for i in interfaces if i.get("admin_status") == "down")
                            
                            # Count access and trunk ports
                            access_ports = sum(1 for i in interfaces if i.get("port_mode") == "access")
                            trunk_ports = sum(1 for i in interfaces if i.get("port_mode") == "trunk")
                            
                            # Prepare parsed config document
                            # Note: Removed duplicate fields (model, os_version, serial_number, mgmt_ip, uptime, cpu_util, mem_util)
                            # These are now only stored in device_overview to avoid duplication
                            
                            # Create a copy of parsed data for hash calculation (without timestamps and IDs)
                            hash_data = {
                                "device_name": device_name,
                                "vendor": parsed_data.get("vendor", "unknown"),
                                "device_overview": overview,
                                "interfaces": interfaces,
                                "vlans": vlans,
                                "stp": stp,
                                "routing": routing,
                                "neighbors": parsed_data.get("neighbors", []),
                                "mac_arp": parsed_data.get("mac_arp", {}),
                                "security": parsed_data.get("security", {}),
                                "ha": parsed_data.get("ha", {}),
                            }
                            
                            # Calculate hash of parsed data (for duplicate detection)
                            # Sort keys to ensure consistent hashing
                            hash_str = json.dumps(hash_data, sort_keys=True, default=str)
                            config_hash = hashlib.sha256(hash_str.encode('utf-8')).hexdigest()
                            
                            # Get next version number for this device
                            collection = db()["parsed_configs"]
                            try:
                                # Find latest version for this device
                                latest_version_doc = await collection.find_one(
                                    {"project_id": project_id, "device_name": device_name},
                                    sort=[("version", -1)]
                                )
                                next_version = (latest_version_doc.get("version", 0) + 1) if latest_version_doc else 1
                            except Exception:
                                # If collection doesn't exist or query fails, start with version 1
                                next_version = 1
                            
                            parsed_doc = {
                                "project_id": project_id,
                                "document_id": doc["document_id"],
                                "device_name": device_name,
                                "vendor": parsed_data.get("vendor", "unknown"),
                                "version": next_version,
                                "config_hash": config_hash,
                                "upload_timestamp": datetime.now(timezone.utc),
                                "original_content": content,  # Store original file content
                                "device_overview": overview,
                                "interfaces": interfaces,
                                "vlans": vlans,
                                "stp": stp,
                                "routing": routing,
                                "neighbors": parsed_data.get("neighbors", []),
                                "mac_arp": parsed_data.get("mac_arp", {}),
                                "security": parsed_data.get("security", {}),
                                "ha": parsed_data.get("ha", {}),
                                "created_at": datetime.now(timezone.utc),
                                "updated_at": datetime.now(timezone.utc),
                            }
                            
                            # Save to parsed_configs collection (check if exists, then insert or update)
                            # Log parsed data structure for debugging
                            print(f"\n=== Parsing result for {device_name} ===")
                            print(f"Device name: {device_name}")
                            print(f"Vendor: {parsed_data.get('vendor', 'unknown')}")
                            print(f"Model: {overview.get('model', 'N/A')}")
                            print(f"OS Version: {overview.get('os_version', 'N/A')}")
                            print(f"Interfaces count: {len(interfaces) if interfaces else 0}")
                            print(f"VLANs count: {len(vlans) if vlans else 0}")
                            print(f"STP mode: {stp.get('mode', 'N/A') if stp else 'N/A'}")
                            print(f"Routing protocols: {list(routing.keys()) if routing else []}")
                            print(f"Neighbors count: {len(parsed_data.get('neighbors', []))}")
                            print(f"==========================================\n")
                            
                            # Note: Due to MongoDB permission issues with creating new collections,
                            # we store parsed config data in the documents collection as metadata.
                            # This allows us to view parsed data while avoiding permission errors.
                            # Try to save to parsed_configs collection first (preferred method)
                            collection = db()["parsed_configs"]
                            save_success = False
                            
                            try:
                                # First, check if collection exists and is accessible
                                try:
                                    # Try to count documents to verify collection exists
                                    await collection.count_documents({}, limit=1)
                                except Exception:
                                    # Collection might not exist, try to create it by inserting a dummy doc
                                    try:
                                        dummy_doc = {
                                            "_temp": True,
                                            "created_at": datetime.now(timezone.utc),
                                            "project_id": project_id,
                                            "device_name": "_temp"
                                        }
                                        await collection.insert_one(dummy_doc)
                                        await collection.delete_one({"_temp": True})
                                        print(f"✅ Created parsed_configs collection")
                                    except Exception as create_err:
                                        # Can't create collection, will fallback to documents
                                        raise create_err
                                
                                # Check for duplicate config (strict check - same hash means same config)
                                existing_doc = await collection.find_one(
                                    {
                                        "project_id": project_id,
                                        "device_name": device_name,
                                        "config_hash": config_hash
                                    }
                                )
                                
                                if existing_doc:
                                    print(f"⚠️ Duplicate config detected for {device_name} (hash: {config_hash[:8]}...). Skipping insert (strict duplicate check).")
                                    print(f"   Existing version: {existing_doc.get('version', 'N/A')}, timestamp: {existing_doc.get('upload_timestamp', 'N/A')}")
                                    save_success = True  # Consider duplicate detection as success
                                else:
                                    # Insert new version (versioning system - keep all versions)
                                    result = await collection.insert_one(parsed_doc)
                                    
                                    if result.inserted_id:
                                        print(f"✅ Successfully inserted parsed config for {device_name} version {next_version} in parsed_configs collection (ID: {result.inserted_id})")
                                        save_success = True
                                        # Create indexes after successful insert
                                        try:
                                            await collection.create_index("project_id", background=True)
                                            await collection.create_index("device_name", background=True)
                                            await collection.create_index("version", background=True)
                                            await collection.create_index("config_hash", background=True)
                                            await collection.create_index("upload_timestamp", background=True)
                                            await collection.create_index([("project_id", 1), ("device_name", 1)], background=True)
                                            await collection.create_index([("project_id", 1), ("device_name", 1), ("version", -1)], background=True)
                                            print(f"✅ Created indexes for parsed_configs collection")
                                        except Exception as idx_err:
                                            print(f"⚠️ Index creation warning (may already exist): {idx_err}")
                                    else:
                                        print(f"⚠️ Insert operation completed but no ID returned for {device_name}")
                            except Exception as parsed_configs_err:
                                # If parsed_configs write fails, fallback to documents collection
                                error_msg = str(parsed_configs_err)
                                if "Operation not permitted" in error_msg or "not permitted" in error_msg.lower():
                                    print(f"⚠️ parsed_configs collection unavailable (permission issue), using documents collection for {device_name}")
                                    print(f"   Note: Data will be stored in documents.parsed_config field instead")
                                else:
                                    print(f"⚠️ parsed_configs collection write failed for {device_name}: {error_msg}")
                                    print(f"⚠️ Falling back to documents collection for {device_name}")
                                
                                # Fallback: Store as metadata in documents collection (with versioning)
                                try:
                                    # Check for duplicate in documents collection
                                    existing_doc = await db()["documents"].find_one(
                                        {
                                            "project_id": project_id,
                                            "parsed_config.device_name": device_name,
                                            "parsed_config.config_hash": config_hash
                                        }
                                    )
                                    
                                    if existing_doc:
                                        print(f"⚠️ Duplicate config detected for {device_name} in documents collection (hash: {config_hash[:8]}...). Skipping insert (strict duplicate check).")
                                        save_success = True
                                    else:
                                        # Store as metadata with version info
                                        result = await db()["documents"].update_many(
                                            {"document_id": doc["document_id"], "project_id": project_id, "is_latest": True},
                                            {"$set": {"parsed_config": parsed_doc}}
                                        )
                                        
                                        # If no match, try without is_latest filter
                                        if result.matched_count == 0:
                                            result = await db()["documents"].update_many(
                                                {"document_id": doc["document_id"], "project_id": project_id},
                                                {"$set": {"parsed_config": parsed_doc}}
                                            )
                                        
                                        if result.matched_count > 0:
                                            print(f"✅ Successfully stored parsed config for {device_name} version {next_version} as metadata in documents collection (parsed_configs unavailable) - matched {result.matched_count}, modified {result.modified_count}")
                                            save_success = True
                                        else:
                                            print(f"⚠️ Warning: Could not find document to update for {device_name} (document_id: {doc['document_id']})")
                                            # Try to verify document exists
                                            check_doc = await db()["documents"].find_one({"document_id": doc["document_id"], "project_id": project_id})
                                            if check_doc:
                                                print(f"Document exists but update didn't match - trying with is_latest filter")
                                                result2 = await db()["documents"].update_many(
                                                    {"document_id": doc["document_id"], "project_id": project_id, "is_latest": True},
                                                    {"$set": {"parsed_config": parsed_doc}}
                                                )
                                                if result2.matched_count > 0:
                                                    print(f"✅ Successfully stored parsed config for {device_name} version {next_version} using is_latest filter")
                                                    save_success = True
                                            else:
                                                print(f"❌ Document not found in database")
                                except Exception as fallback_err:
                                    print(f"❌ Error: Could not store parsed config for {device_name} in either collection: {fallback_err}")
                                    import traceback
                                    print(f"Traceback: {traceback.format_exc()}")
                                    # Continue anyway - parsing succeeded even if storage failed
                                
                            except Exception as db_error:
                                # Log error but don't fail upload
                                print(f"Error saving parsed config for {device_name}: {db_error}")
                                import traceback
                                print(f"Traceback: {traceback.format_exc()}")
                except Exception as parse_error:
                    # Log error but don't fail upload
                    import traceback
                    error_details = traceback.format_exc()
                    print(f"Error parsing config for {doc.get('filename')}: {parse_error}")
                    print(f"Full traceback:\n{error_details}")
        
        return {
            "message": f"Successfully uploaded {len(uploaded)} document(s)",
            "batch_id": uploaded[0]["upload_batch_id"] if uploaded else None,
            "documents": uploaded
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        # Extract error message properly
        error_msg = str(e)
        if "Operation not permitted" in error_msg or "Permission denied" in error_msg:
            error_msg = f"Storage permission error: {error_msg}. Please check storage directory permissions in Docker."
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("")
async def list_documents(
    project_id: str,
    folder_id: Optional[str] = Query(None, description="Filter by folder"),
    uploader: Optional[str] = Query(None, description="Filter by uploader"),
    search: Optional[str] = Query(None, description="Search in filename"),
    user=Depends(get_current_user)
):
    """List documents in a project with optional filters"""
    await check_project_access(project_id, user)
    
    # Build base query
    base_conditions = {"project_id": project_id, "is_latest": True}
    
    # Handle folder_id filter - support both null/None and specific folder_id
    folder_condition = None
    if folder_id is not None:
        # If folder_id is explicitly provided (even if empty string), filter by it
        folder_id_clean = folder_id.strip() if folder_id else None
        if folder_id_clean:
            # Filter by specific folder
            folder_condition = {"folder_id": folder_id_clean}
        else:
            # Filter for documents with folder_id = null or missing
            # MongoDB: use $or to match both null and missing fields
            folder_condition = {
                "$or": [
                    {"folder_id": None},
                    {"folder_id": {"$exists": False}}
                ]
            }
    
    # Combine all conditions
    if folder_condition:
        # If we have folder condition, use $and to combine with base conditions
        query = {
            "$and": [
                base_conditions,
                folder_condition
            ]
        }
    else:
        # No folder filter, just use base conditions
        query = base_conditions
    
    # Add other filters
    if uploader:
        if "$and" in query:
            query["$and"].append({"uploader": uploader})
        else:
            query["uploader"] = uploader
    if search:
        search_condition = {"filename": {"$regex": search, "$options": "i"}}
        if "$and" in query:
            query["$and"].append(search_condition)
        else:
            query["filename"] = search_condition
    
    documents = []
    async for doc in db()["documents"].find(query, sort=[("created_at", -1)]):
        # Convert datetime objects to ISO strings
        if "created_at" in doc and isinstance(doc["created_at"], datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        if "updated_at" in doc and isinstance(doc["updated_at"], datetime):
            doc["updated_at"] = doc["updated_at"].isoformat()
        
        # Remove _id and convert any ObjectId fields to strings
        doc.pop("_id", None)
        
        # Handle parsed_config if it exists (might contain ObjectId references)
        if "parsed_config" in doc and isinstance(doc["parsed_config"], dict):
            # Recursively clean ObjectId from parsed_config
            def clean_objectid(obj):
                from bson import ObjectId
                if isinstance(obj, ObjectId):
                    return str(obj)
                elif isinstance(obj, dict):
                    return {k: clean_objectid(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_objectid(item) for item in obj]
                elif isinstance(obj, datetime):
                    return obj.isoformat()
                return obj
            doc["parsed_config"] = clean_objectid(doc["parsed_config"])
        
        documents.append(doc)
    
    return {"documents": documents, "count": len(documents)}


@router.get("/{document_id}")
async def get_document(
    project_id: str,
    document_id: str,
    user=Depends(get_current_user)
):
    """Get document metadata"""
    await check_project_access(project_id, user)
    
    doc = await db()["documents"].find_one(
        {"document_id": document_id, "project_id": project_id, "is_latest": True},
        {"_id": 0}
    )
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Convert datetime objects to ISO strings
    if "created_at" in doc and isinstance(doc["created_at"], datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    if "updated_at" in doc and isinstance(doc["updated_at"], datetime):
        doc["updated_at"] = doc["updated_at"].isoformat()
    
    return doc


@router.get("/{document_id}/download")
async def download_document(
    project_id: str,
    document_id: str,
    version: Optional[int] = Query(None, description="Specific version, or latest if not provided"),
    user=Depends(get_current_user)
):
    """Download document file"""
    await check_project_access(project_id, user)
    
    file_path = await get_document_file_path(project_id, document_id, version)
    if not file_path:
        raise HTTPException(status_code=404, detail="Document file not found")
    
    # Get document metadata for filename
    query = {"document_id": document_id, "project_id": project_id}
    if version:
        query["version"] = version
    else:
        query["is_latest"] = True
    
    doc = await db()["documents"].find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get filename and sanitize it for download (remove any path components)
    filename = doc["filename"]
    # Remove any path components (in case filename contains slashes)
    filename = os.path.basename(filename)
    # Extract extension
    name, ext = os.path.splitext(filename)
    # Sanitize name part - keep only alphanumeric, dots, hyphens, and underscores
    # This preserves the original filename structure while removing problematic characters
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    # Reconstruct filename with extension
    safe_filename = safe_name + ext if ext else safe_name
    
    # For PDF files, set Content-Disposition to inline so they can be viewed in iframe
    headers = {}
    if doc.get("content_type") == "application/pdf":
        headers["Content-Disposition"] = f'inline; filename="{safe_filename}"'
    else:
        headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
    
    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type=doc.get("content_type", "application/octet-stream"),
        headers=headers
    )


@router.get("/{document_id}/preview")
async def get_document_preview(
    project_id: str,
    document_id: str,
    version: Optional[int] = Query(None, description="Specific version, or latest if not provided"),
    user=Depends(get_current_user)
):
    """Get document preview (for supported types: PDF, images, text)"""
    await check_project_access(project_id, user)
    
    # Get document metadata
    query = {"document_id": document_id, "project_id": project_id}
    if version:
        query["version"] = version
    else:
        query["is_latest"] = True
    
    doc = await db()["documents"].find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = await get_document_file_path(project_id, document_id, version)
    if not file_path:
        raise HTTPException(status_code=404, detail="Document file not found")
    
    # Generate preview
    preview = await generate_preview(file_path, doc.get("content_type", "application/octet-stream"))
    
    return preview


@router.get("/{document_id}/content")
async def get_document_content(
    project_id: str,
    document_id: str,
    version: Optional[int] = Query(None, description="Specific version, or latest if not provided"),
    user=Depends(get_current_user)
):
    """Get raw text content of a document (for config compare / diff). Returns plain text."""
    await check_project_access(project_id, user)
    content_bytes = await read_document_file(project_id, document_id, version)
    if not content_bytes:
        raise HTTPException(status_code=404, detail="Document file not found")
    try:
        text = content_bytes.decode("utf-8", errors="replace")
    except Exception:
        text = content_bytes.decode("latin-1", errors="replace")
    return PlainTextResponse(content=text, media_type="text/plain; charset=utf-8")


@router.get("/{document_id}/versions")
async def list_document_versions(
    project_id: str,
    document_id: str,
    user=Depends(get_current_user)
):
    """List all versions of a document"""
    await check_project_access(project_id, user)
    
    # Get all versions
    versions = []
    async for doc in db()["documents"].find(
        {"document_id": document_id, "project_id": project_id},
        sort=[("version", -1)]
    ):
        versions.append({
            "document_id": doc["document_id"],
            "version": doc["version"],
            "filename": doc["filename"],
            "size": doc["size"],
            "uploader": doc["uploader"],
            "created_at": doc["created_at"].isoformat() if isinstance(doc["created_at"], datetime) else doc["created_at"],
            "is_latest": doc["is_latest"],
            "file_hash": doc["file_hash"]
        })
    
    if not versions:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"document_id": document_id, "filename": versions[0]["filename"], "versions": versions}


@router.post("/{document_id}/upload-version")
async def upload_new_version(
    project_id: str,
    document_id: str,
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """Upload a new version of an existing document"""
    await check_project_access(project_id, user)
    await check_upload_permission(project_id, user)
    
    # Get original document to reuse metadata
    original = await db()["documents"].find_one(
        {"document_id": document_id, "project_id": project_id, "is_latest": True}
    )
    if not original:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Create metadata from original
    metadata = DocumentMetadata(
        who=original["metadata"].get("who", user["username"]),
        what=original["metadata"].get("what", ""),
        where=original["metadata"].get("where"),
        when=original["metadata"].get("when"),
        why=original["metadata"].get("why"),
        description=original["metadata"].get("description")
    )
    
    try:
        # Upload new version (reuse same filename and folder_id)
        # Preserve folder_id from original document, even if it's None
        original_folder_id = original.get("folder_id")
        # Explicitly pass None if folder_id is None to maintain folder location
        uploaded = await upload_documents(
            project_id=project_id,
            files=[file],
            uploader=user["username"],
            metadata=metadata,
            folder_id=original_folder_id  # Keep same folder_id (can be None)
        )
        
        return {
            "message": "New version uploaded successfully",
            "document": uploaded[0] if uploaded else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


class MoveFolderRequest(BaseModel):
    folder_id: Optional[str] = None

@router.patch("/{document_id}/folder")
async def move_document_folder(
    project_id: str,
    document_id: str,
    request: MoveFolderRequest = Body(...),
    user=Depends(get_current_user)
):
    """Move document to a different folder"""
    await check_project_access(project_id, user)
    await check_upload_permission(project_id, user)  # Same permission as upload
    
    # Get document
    doc = await db()["documents"].find_one(
        {"document_id": document_id, "project_id": project_id, "is_latest": True}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Convert empty string to None
    folder_id_clean = request.folder_id if request.folder_id and request.folder_id.strip() else None
    
    # Update all versions of this document to the new folder
    result = await db()["documents"].update_many(
        {"document_id": document_id, "project_id": project_id},
        {"$set": {"folder_id": folder_id_clean, "updated_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": f"Moved {result.matched_count} version(s) to folder", "folder_id": folder_id_clean}


class RenameFileRequest(BaseModel):
    filename: str

@router.patch("/{document_id}/filename")
async def rename_document(
    project_id: str,
    document_id: str,
    request: RenameFileRequest = Body(...),
    user=Depends(get_current_user)
):
    """Rename document filename"""
    await check_project_access(project_id, user)
    await check_upload_permission(project_id, user)  # Same permission as upload
    
    # Validate filename
    if not request.filename or not request.filename.strip():
        raise HTTPException(status_code=400, detail="Filename cannot be empty")
    
    new_filename = request.filename.strip()
    
    # Get document
    doc = await db()["documents"].find_one(
        {"document_id": document_id, "project_id": project_id, "is_latest": True}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Prevent renaming files in Config folder
    if doc.get("folder_id") == "Config":
        raise HTTPException(status_code=403, detail="Cannot rename files in Config folder")
    
    # Check if new filename conflicts with existing file in the same folder
    folder_id = doc.get("folder_id")
    existing_doc = await db()["documents"].find_one(
        {
            "project_id": project_id,
            "folder_id": folder_id,
            "filename": new_filename,
            "is_latest": True,
            "document_id": {"$ne": document_id}  # Exclude current document
        }
    )
    if existing_doc:
        raise HTTPException(status_code=400, detail="A file with this name already exists in this folder")
    
    # Update all versions of this document with the new filename
    result = await db()["documents"].update_many(
        {"document_id": document_id, "project_id": project_id},
        {"$set": {"filename": new_filename, "updated_at": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": f"Renamed {result.matched_count} version(s)", "filename": new_filename}


@router.delete("/{document_id}")
async def delete_document(
    project_id: str,
    document_id: str,
    delete_all_versions: bool = Query(False, description="Delete all versions"),
    user=Depends(get_current_user)
):
    """Delete document (soft delete by default, or hard delete all versions)"""
    await check_project_access(project_id, user)
    
    # Check if document exists and get its folder_id
    doc = await db()["documents"].find_one(
        {"document_id": document_id, "project_id": project_id, "is_latest": True}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Prevent deletion of files in Config folder
    if doc.get("folder_id") == "Config":
        raise HTTPException(status_code=403, detail="Cannot delete files from Config folder")
    
    # Only admin or project manager can delete
    from ..dependencies.auth import check_project_manager_or_admin
    await check_project_manager_or_admin(project_id, user)
    
    if delete_all_versions:
        # Delete all versions
        result = await db()["documents"].delete_many(
            {"document_id": document_id, "project_id": project_id}
        )
        # TODO: Also delete files from storage
        return {"message": f"Deleted {result.deleted_count} version(s)"}
    else:
        # Soft delete: mark as deleted (or just delete latest version)
        result = await db()["documents"].delete_one(
            {"document_id": document_id, "project_id": project_id, "is_latest": True}
        )
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"message": "Document deleted"}

