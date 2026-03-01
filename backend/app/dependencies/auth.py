from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ..core.security import decode_token
from ..db.mongo import db

bearer = HTTPBearer()

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    token = creds.credentials
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if not username:
            raise ValueError("no sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await db()["users"].find_one({"username": username})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user

async def check_project_access(project_id: str, user: dict):
    """Check if user has access to a project (admin or member)"""
    if user.get("role") == "admin":
        return
    
    # Check if user is a member of the project
    membership = await db()["project_members"].find_one(
        {"project_id": project_id, "username": user["username"]}
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")

async def check_project_manager_or_admin(project_id: str, user: dict):
    """Check if user is admin or project manager. Only they can access project settings (members, project update, options)."""
    if user.get("role") == "admin":
        return

    membership = await db()["project_members"].find_one(
        {"project_id": project_id, "username": user["username"]}
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")

    if membership.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Only admin or project manager can perform this action")


async def check_project_editor_or_admin(project_id: str, user: dict):
    """Check if user can write project content: admin, manager, or engineer. Viewer is read-only."""
    if user.get("role") == "admin":
        return

    membership = await db()["project_members"].find_one(
        {"project_id": project_id, "username": user["username"]}
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")

    role = membership.get("role")
    if role not in ("manager", "engineer"):
        raise HTTPException(status_code=403, detail="Only admin, manager, or engineer can perform this action")


async def check_project_download_permission(project_id: str, user: dict):
    if user.get("role") == "admin":
        return

    membership = await db()["project_members"].find_one(
        {"project_id": project_id, "username": user["username"]}
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")

    if membership.get("role") == "viewer":
        raise HTTPException(status_code=403, detail="Viewer cannot download files")


async def check_project_delete_permission(project_id: str, user: dict):
    if user.get("role") == "admin":
        return

    membership = await db()["project_members"].find_one(
        {"project_id": project_id, "username": user["username"]}
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")

    role = membership.get("role")
    if role not in ("manager", "engineer"):
        raise HTTPException(status_code=403, detail="Only admin, manager, or engineer can delete documents")


async def check_project_llm_permission(project_id: str, user: dict):
    if user.get("role") == "admin":
        return

    membership = await db()["project_members"].find_one(
        {"project_id": project_id, "username": user["username"]}
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")

    role = membership.get("role")
    if role not in ("manager", "engineer"):
        raise HTTPException(status_code=403, detail="Only admin, manager, or engineer can run AI/LLM tasks")
