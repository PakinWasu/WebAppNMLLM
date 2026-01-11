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
    """Check if user is admin or project manager. Manager has same permissions as admin in the project."""
    if user.get("role") == "admin":
        return
    
    # Check if user is a manager in the project
    membership = await db()["project_members"].find_one(
        {"project_id": project_id, "username": user["username"]}
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")
    
    if membership.get("role") != "manager":
        raise HTTPException(status_code=403, detail="Only admin or project manager can perform this action")

