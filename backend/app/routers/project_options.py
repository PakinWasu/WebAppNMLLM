from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel

from ..db.mongo import db
from ..dependencies.auth import get_current_user, check_project_access, check_project_manager_or_admin

router = APIRouter(prefix="/projects/{project_id}/options", tags=["project-options"])


class ProjectOptionCreate(BaseModel):
    field: str  # 'what', 'where', 'when', 'why'
    value: str


@router.get("")
async def get_project_options(project_id: str, user=Depends(get_current_user)):
    """Get project-specific dropdown options"""
    await check_project_access(project_id, user)
    
    options_doc = await db()["project_options"].find_one({"project_id": project_id})
    if not options_doc:
        return {"what": [], "where": [], "when": [], "why": []}
    
    return {
        "what": options_doc.get("what", []),
        "where": options_doc.get("where", []),
        "when": options_doc.get("when", []),
        "why": options_doc.get("why", [])
    }


@router.post("")
async def save_project_option(
    project_id: str,
    body: ProjectOptionCreate,
    user=Depends(get_current_user)
):
    """Save a custom dropdown option for a project. Only admin or project manager can do this."""
    await check_project_manager_or_admin(project_id, user)
    
    if body.field not in ["what", "where", "when", "why"]:
        raise HTTPException(status_code=400, detail="Invalid field. Must be one of: what, where, when, why")
    
    # Get existing options
    options_doc = await db()["project_options"].find_one({"project_id": project_id})
    
    if not options_doc:
        # Create new document
        new_options = {
            "project_id": project_id,
            "what": [],
            "where": [],
            "when": [],
            "why": []
        }
        new_options[body.field] = [body.value]
        await db()["project_options"].insert_one(new_options)
    else:
        # Update existing document
        field_options = options_doc.get(body.field, [])
        if body.value not in field_options:
            field_options.append(body.value)
            await db()["project_options"].update_one(
                {"project_id": project_id},
                {"$set": {body.field: field_options}}
            )
    
    return {"message": "Option saved successfully"}

