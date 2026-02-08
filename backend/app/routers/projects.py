from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
import uuid
from ..db.mongo import db
from ..dependencies.auth import get_current_user, check_project_manager_or_admin
from ..models.project import ProjectCreate, ProjectUpdate
from ..models.membership import MemberAdd

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("")
async def list_projects(user=Depends(get_current_user)):
    """List projects - admin sees all, others see only projects they're members of"""
    projects = []
    if user.get("role") == "admin":
        async for p in db()["projects"].find({}, {"_id": 0}):
            projects.append(p)
    else:
        # Get project IDs where user is a member
        memberships = []
        async for m in db()["project_members"].find({"username": user["username"]}, {"_id": 0, "project_id": 1}):
            memberships.append(m["project_id"])
        
        if memberships:
            async for p in db()["projects"].find({"project_id": {"$in": memberships}}, {"_id": 0}):
                projects.append(p)
    
    # Convert datetime objects to ISO strings
    for p in projects:
        if "created_at" in p and isinstance(p["created_at"], datetime):
            p["created_at"] = p["created_at"].isoformat()
        if "updated_at" in p and isinstance(p["updated_at"], datetime):
            p["updated_at"] = p["updated_at"].isoformat()
    
    return projects

@router.post("")
async def create_project(body: ProjectCreate, user=Depends(get_current_user)):
    """Create a new project. Only admin can create projects."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create projects")
    
    pid = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    doc = {
        "project_id": pid,
        "name": body.name,
        "description": body.description,
        "topo_url": body.topo_url,
        "visibility": body.visibility or "Private",
        "backup_interval": body.backup_interval or "Daily",
        "created_at": created_at,
        "created_by": user["username"],
    }
    await db()["projects"].insert_one(doc)

    # Admin who creates is automatically admin in the project (not manager)
    await db()["project_members"].insert_one({
        "project_id": pid,
        "username": user["username"],
        "role": "admin",
        "joined_at": datetime.now(timezone.utc),
    })
    
    # Return document without _id and convert datetime to ISO string
    result = {
        "project_id": pid,
        "name": body.name,
        "description": body.description,
        "topo_url": body.topo_url,
        "visibility": body.visibility or "Private",
        "backup_interval": body.backup_interval or "Daily",
        "created_at": created_at.isoformat(),
        "created_by": user["username"],
    }
    return result

@router.get("/{project_id}")
async def get_project(project_id: str, user=Depends(get_current_user)):
    """Get project details"""
    project = await db()["projects"].find_one({"project_id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check access: admin can see all, others must be members
    if user.get("role") != "admin":
        membership = await db()["project_members"].find_one(
            {"project_id": project_id, "username": user["username"]}
        )
        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this project")
    
    # Convert datetime objects to ISO strings
    if "created_at" in project and isinstance(project["created_at"], datetime):
        project["created_at"] = project["created_at"].isoformat()
    if "updated_at" in project and isinstance(project["updated_at"], datetime):
        project["updated_at"] = project["updated_at"].isoformat()
    
    return project

@router.get("/{project_id}/members")
async def list_project_members(project_id: str, user=Depends(get_current_user)):
    """List members of a project"""
    # Check access
    if user.get("role") != "admin":
        membership = await db()["project_members"].find_one(
            {"project_id": project_id, "username": user["username"]}
        )
        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this project")
    
    members = []
    async for m in db()["project_members"].find({"project_id": project_id}, {"_id": 0}):
        # Convert datetime objects to ISO strings
        if "joined_at" in m and isinstance(m["joined_at"], datetime):
            m["joined_at"] = m["joined_at"].isoformat()
        members.append(m)
    return members

@router.post("/{project_id}/members")
async def add_member(project_id: str, body: MemberAdd, user=Depends(get_current_user)):
    """Add or update a member in a project. Only admin or project manager can do this."""
    # Check if project exists
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permission - manager has same permissions as admin
    await check_project_manager_or_admin(project_id, user)

    # Check if user exists
    u = await db()["users"].find_one({"username": body.username})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    # Add or update member
    result = await db()["project_members"].update_one(
        {"project_id": project_id, "username": body.username},
        {"$setOnInsert": {"joined_at": datetime.now(timezone.utc)},
         "$set": {"role": body.role}},
        upsert=True
    )
    return {"message": "Member added/updated", "upserted": result.upserted_id is not None}

@router.put("/{project_id}/members/{username}")
async def update_member_role(project_id: str, username: str, body: MemberAdd, user=Depends(get_current_user)):
    """Update a member's role in a project. Only admin or project manager can do this."""
    # Check if project exists
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permission - manager has same permissions as admin
    await check_project_manager_or_admin(project_id, user)
    
    # Check if member exists
    member = await db()["project_members"].find_one({"project_id": project_id, "username": username})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found in this project")
    
    # Update role
    await db()["project_members"].update_one(
        {"project_id": project_id, "username": username},
        {"$set": {"role": body.role}}
    )
    return {"message": "Member role updated"}

@router.delete("/{project_id}/members/{username}")
async def remove_member(project_id: str, username: str, user=Depends(get_current_user)):
    """Remove a member from a project. Only admin or project manager can do this."""
    # Check if project exists
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permission - manager has same permissions as admin
    await check_project_manager_or_admin(project_id, user)
    
    # Check if member exists
    member = await db()["project_members"].find_one({"project_id": project_id, "username": username})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found in this project")
    
    # Remove member
    result = await db()["project_members"].delete_one({"project_id": project_id, "username": username})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    
    return {"message": "Member removed"}

@router.put("/{project_id}")
async def update_project(project_id: str, body: ProjectUpdate, user=Depends(get_current_user)):
    """Update project details. Only admin or project manager can do this."""
    # Check if project exists
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permission - manager has same permissions as admin
    await check_project_manager_or_admin(project_id, user)
    
    # Update project
    updated_at = datetime.now(timezone.utc)
    update_data = {
        "name": body.name,
        "description": body.description,
        "updated_at": updated_at,
        "updated_by": user["username"]
    }
    if body.topo_url is not None:
        update_data["topo_url"] = body.topo_url
    if body.visibility is not None:
        update_data["visibility"] = body.visibility
    if body.backup_interval is not None:
        update_data["backup_interval"] = body.backup_interval
    
    await db()["projects"].update_one(
        {"project_id": project_id},
        {"$set": update_data}
    )
    
    updated = await db()["projects"].find_one({"project_id": project_id}, {"_id": 0})
    # Convert datetime objects to ISO strings
    if updated:
        if "created_at" in updated and isinstance(updated["created_at"], datetime):
            updated["created_at"] = updated["created_at"].isoformat()
        if "updated_at" in updated and isinstance(updated["updated_at"], datetime):
            updated["updated_at"] = updated["updated_at"].isoformat()
    return updated

@router.delete("/{project_id}")
async def delete_project(project_id: str, user=Depends(get_current_user)):
    """Delete a project and all its data. Only admin or project manager can do this."""
    from ..dependencies.auth import check_project_manager_or_admin
    await check_project_manager_or_admin(project_id, user)
    
    # Check if project exists
    project = await db()["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Delete all data related to this project
    # 1. Delete project members
    members_result = await db()["project_members"].delete_many({"project_id": project_id})
    
    # 2. Delete all documents (including parsed_configs stored in documents)
    documents_result = await db()["documents"].delete_many({"project_id": project_id})
    
    # 3. Delete parsed_configs collection data (if exists)
    try:
        parsed_configs_result = await db()["parsed_configs"].delete_many({"project_id": project_id})
    except Exception:
        # Collection might not exist or be inaccessible
        parsed_configs_result = None
    
    # 4. Delete project options
    try:
        options_result = await db()["project_options"].delete_many({"project_id": project_id})
    except Exception:
        options_result = None
    
    # 5. Delete project folders
    try:
        folders_result = await db()["project_folders"].delete_many({"project_id": project_id})
    except Exception:
        folders_result = None

    # 6. Delete LLM results for this project (device overview, recommendations, topology, etc.)
    try:
        llm_results_deleted = await db()["llm_results"].delete_many({"project_id": project_id})
        llm_results_count = llm_results_deleted.deleted_count
    except Exception:
        llm_results_count = 0

    # 7. Delete the project itself (includes device_images, topoPositions, etc. in the doc)
    project_result = await db()["projects"].delete_one({"project_id": project_id})

    # TODO: Also delete files from storage directory
    # Storage path: storage/{project_id}/

    return {
        "message": "Project and all related data deleted",
        "deleted": {
            "project": project_result.deleted_count,
            "members": members_result.deleted_count,
            "documents": documents_result.deleted_count,
            "parsed_configs": parsed_configs_result.deleted_count if parsed_configs_result else 0,
            "options": options_result.deleted_count if options_result else 0,
            "folders": folders_result.deleted_count if folders_result else 0,
            "llm_results": llm_results_count,
        }
    }
