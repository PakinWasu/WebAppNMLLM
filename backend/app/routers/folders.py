from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone
import zipfile
import io
import os

from ..db.mongo import db
from ..dependencies.auth import get_current_user, check_project_access, check_project_editor_or_admin

router = APIRouter(prefix="/projects/{project_id}/folders", tags=["folders"])


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None


class FolderUpdate(BaseModel):
    name: str
    parent_id: Optional[str] = None


@router.get("")
async def get_folders(project_id: str, user=Depends(get_current_user)):
    """Get all custom folders for a project"""
    await check_project_access(project_id, user)
    
    folders_doc = await db()["project_folders"].find_one({"project_id": project_id})
    if not folders_doc:
        return {"folders": []}
    
    # Return folders list, exclude deleted ones; normalize parent_id "root" -> null
    folders = folders_doc.get("folders", [])
    active_folders = []
    for f in folders:
        if f.get("deleted", False):
            continue
        fcopy = dict(f)
        if fcopy.get("parent_id") == "root":
            fcopy["parent_id"] = None
        active_folders.append(fcopy)
    return {"folders": active_folders}


@router.post("")
async def create_folder(
    project_id: str,
    body: FolderCreate,
    user=Depends(get_current_user)
):
    """Create a new custom folder. Admin, manager, or engineer can do this."""
    await check_project_editor_or_admin(project_id, user)
    
    # Validate folder name
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="Folder name cannot be empty")
    
    # Prevent creating folder with name "Config"
    if body.name.strip() == "Config":
        raise HTTPException(status_code=400, detail="Cannot create folder named 'Config'")
    
    # Generate folder ID
    import uuid
    folder_id = str(uuid.uuid4())
    
    # Get or create folders document
    folders_doc = await db()["project_folders"].find_one({"project_id": project_id})
    
    new_folder = {
        "id": folder_id,
        "name": body.name.strip(),
        "parent_id": body.parent_id if body.parent_id and body.parent_id.strip() else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["username"],
        "deleted": False
    }
    
    if not folders_doc:
        # Create new document
        await db()["project_folders"].insert_one({
            "project_id": project_id,
            "folders": [new_folder]
        })
    else:
        # Check if folder name already exists at the same level
        existing_folders = folders_doc.get("folders", [])
        parent_id_clean = body.parent_id if body.parent_id and body.parent_id.strip() else None
        
        for folder in existing_folders:
            if (not folder.get("deleted", False) and 
                folder.get("name") == body.name.strip() and 
                folder.get("parent_id") == parent_id_clean):
                raise HTTPException(status_code=400, detail="Folder with this name already exists at this level")
        
        # Add new folder
        existing_folders.append(new_folder)
        await db()["project_folders"].update_one(
            {"project_id": project_id},
            {"$set": {"folders": existing_folders}}
        )
    
    return {"message": "Folder created successfully", "folder": new_folder}


@router.put("/{folder_id}")
async def update_folder(
    project_id: str,
    folder_id: str,
    body: FolderUpdate,
    user=Depends(get_current_user)
):
    """Update a custom folder. Admin, manager, or engineer can do this."""
    await check_project_editor_or_admin(project_id, user)
    
    # Prevent editing Config folder
    if folder_id == "Config":
        raise HTTPException(status_code=400, detail="Cannot edit Config folder")
    
    # Validate folder name
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="Folder name cannot be empty")
    
    # Prevent renaming to "Config"
    if body.name.strip() == "Config":
        raise HTTPException(status_code=400, detail="Cannot rename folder to 'Config'")
    
    folders_doc = await db()["project_folders"].find_one({"project_id": project_id})
    if not folders_doc:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    folders = folders_doc.get("folders", [])
    folder_index = None
    
    for i, folder in enumerate(folders):
        if folder.get("id") == folder_id and not folder.get("deleted", False):
            folder_index = i
            break
    
    if folder_index is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Check if new name conflicts with existing folder at same level
    # Normalize "root" to None so root folders are stored correctly
    parent_id_clean = body.parent_id if body.parent_id and str(body.parent_id).strip() else None
    if parent_id_clean == "root":
        parent_id_clean = None
    for folder in folders:
        if (folder.get("id") != folder_id and 
            not folder.get("deleted", False) and
            folder.get("name") == body.name.strip() and 
            folder.get("parent_id") == parent_id_clean):
            raise HTTPException(status_code=400, detail="Folder with this name already exists at this level")
    
    # Update folder
    folders[folder_index]["name"] = body.name.strip()
    folders[folder_index]["parent_id"] = parent_id_clean
    folders[folder_index]["updated_at"] = datetime.now(timezone.utc).isoformat()
    folders[folder_index]["updated_by"] = user["username"]
    
    await db()["project_folders"].update_one(
        {"project_id": project_id},
        {"$set": {"folders": folders}}
    )
    
    return {"message": "Folder updated successfully", "folder": folders[folder_index]}


@router.delete("/{folder_id}")
async def delete_folder(
    project_id: str,
    folder_id: str,
    user=Depends(get_current_user)
):
    """Delete a custom folder (soft delete). Admin, manager, or engineer can do this."""
    await check_project_editor_or_admin(project_id, user)
    
    # Prevent deleting Config folder
    if folder_id == "Config":
        raise HTTPException(status_code=400, detail="Cannot delete Config folder")
    
    folders_doc = await db()["project_folders"].find_one({"project_id": project_id})
    if not folders_doc:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    folders = folders_doc.get("folders", [])
    folder_index = None
    
    for i, folder in enumerate(folders):
        if folder.get("id") == folder_id and not folder.get("deleted", False):
            folder_index = i
            break
    
    if folder_index is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Delete all documents in this folder first
    await db()["documents"].update_many(
        {
            "project_id": project_id,
            "folder_id": folder_id,
            "is_latest": True
        },
        {
            "$set": {
                "deleted": True,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "deleted_by": user["username"]
            }
        }
    )
    
    # Soft delete: mark as deleted
    folders[folder_index]["deleted"] = True
    folders[folder_index]["deleted_at"] = datetime.now(timezone.utc).isoformat()
    folders[folder_index]["deleted_by"] = user["username"]
    
    await db()["project_folders"].update_one(
        {"project_id": project_id},
        {"$set": {"folders": folders}}
    )
    
    return {"message": "Folder deleted successfully"}


@router.get("/{folder_id}/download")
async def download_folder(
    project_id: str,
    folder_id: str,
    user=Depends(get_current_user)
):
    """Download folder and all its contents as ZIP file"""
    await check_project_access(project_id, user)
    
    # Prevent downloading Config folder
    if folder_id == "Config":
        raise HTTPException(status_code=400, detail="Cannot download Config folder")
    
    # Get folder information
    folders_doc = await db()["project_folders"].find_one({"project_id": project_id})
    if not folders_doc:
        raise HTTPException(status_code=404, detail="No folders found for this project")
    
    folders = folders_doc.get("folders", [])
    target_folder = None
    
    for folder in folders:
        if folder.get("id") == folder_id and not folder.get("deleted", False):
            target_folder = folder
            break
    
    if not target_folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Get all folders to build hierarchy
    all_folders = folders_doc.get("folders", [])
    
    # Build folder hierarchy - get all subfolders recursively
    def get_all_subfolders(folder_id):
        subfolders = []
        for folder in all_folders:
            if (folder.get("parent_id") == folder_id and 
                not folder.get("deleted", False)):
                subfolders.append(folder)
                # Recursively get subfolders
                subfolders.extend(get_all_subfolders(folder["id"]))
        return subfolders
    
    # Get target folder and all its subfolders
    folder_hierarchy = [target_folder] + get_all_subfolders(folder_id)
    folder_ids = [f["id"] for f in folder_hierarchy]
    
    # Get all documents in this folder and all subfolders
    documents = []
    cursor = db()["documents"].find({
        "project_id": project_id,
        "folder_id": {"$in": folder_ids},
        "is_latest": True,
        "deleted": {"$ne": True}
    })
    
    async for doc in cursor:
        documents.append(doc)
    
    if not documents:
        raise HTTPException(status_code=404, detail="No documents found in this folder")
    
    # Create folder path mapping
    def get_folder_path(doc_folder_id):
        # Build full path from target folder to document's folder
        path_parts = []
        current_id = doc_folder_id
        
        while current_id:
            folder = next((f for f in all_folders if f["id"] == current_id), None)
            if not folder:
                break
                
            folder_name = folder["name"].replace(" ", "_").replace("/", "_")
            path_parts.insert(0, folder_name)
            current_id = folder.get("parent_id")
            
            # Stop when we reach the target folder
            if folder["id"] == folder_id:
                break
        
        return "/".join(path_parts) if path_parts else ""
    
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for doc in documents:
            try:
                # Get file path
                from ..services.document_storage import get_document_file_path
                file_path = await get_document_file_path(project_id, doc["document_id"])
                
                # Read file content
                if os.path.exists(file_path):
                    # Sanitize filename for ZIP
                    filename = doc["filename"]
                    safe_filename = os.path.basename(filename)
                    
                    # Get folder path for this document
                    folder_path = get_folder_path(doc["folder_id"])
                    zip_path = f"{folder_path}/{safe_filename}" if folder_path else safe_filename
                    
                    # Add file to ZIP with folder structure
                    zip_file.write(file_path, zip_path)
                    
            except Exception as e:
                # Skip files that can't be read
                print(f"Error adding file {doc.get('filename', 'unknown')} to ZIP: {e}")
                continue
    
    zip_buffer.seek(0)
    
    # Generate ZIP filename
    folder_name = target_folder["name"].replace(" ", "_").replace("/", "_")
    zip_filename = f"{folder_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    return StreamingResponse(
        io.BytesIO(zip_buffer.read()),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
    )

