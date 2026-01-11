from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone

from ..db.mongo import db
from ..dependencies.auth import get_current_user, check_project_access, check_project_manager_or_admin

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
    
    # Return folders list, exclude deleted ones
    folders = folders_doc.get("folders", [])
    active_folders = [f for f in folders if not f.get("deleted", False)]
    
    return {"folders": active_folders}


@router.post("")
async def create_folder(
    project_id: str,
    body: FolderCreate,
    user=Depends(get_current_user)
):
    """Create a new custom folder. Only admin or project manager can do this."""
    await check_project_manager_or_admin(project_id, user)
    
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
    """Update a custom folder. Only admin or project manager can do this."""
    await check_project_manager_or_admin(project_id, user)
    
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
    parent_id_clean = body.parent_id if body.parent_id and body.parent_id.strip() else None
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
    """Delete a custom folder (soft delete). Only admin or project manager can do this."""
    await check_project_manager_or_admin(project_id, user)
    
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
    
    # Check if folder has documents
    docs_count = await db()["documents"].count_documents({
        "project_id": project_id,
        "folder_id": folder_id,
        "is_latest": True
    })
    
    if docs_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete folder: {docs_count} document(s) still in this folder. Please move or delete documents first."
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

