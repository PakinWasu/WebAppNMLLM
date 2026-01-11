from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from ..db.mongo import db
from ..dependencies.auth import require_admin
from ..core.security import hash_password, encrypt_temp_password, decrypt_temp_password
from ..models.user import UserCreate, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

@router.get("", dependencies=[Depends(require_admin)])
async def list_users():
    """List all users (without password_hash and role - roles are per project)"""
    users = []
    async for u in db()["users"].find({}, {"_id": 0, "password_hash": 0}):
        # Remove role from response - roles are assigned per project
        user_data = {k: v for k, v in u.items() if k != "role"}
        
        # Decrypt temp_password_encrypted if it exists
        if "temp_password_encrypted" in user_data:
            temp_password = decrypt_temp_password(user_data["temp_password_encrypted"])
            user_data["temp_password"] = temp_password
            # Remove encrypted field from response
            del user_data["temp_password_encrypted"]
        else:
            user_data["temp_password"] = None
        
        users.append(user_data)
    return users

@router.post("", dependencies=[Depends(require_admin)])
async def create_user(body: UserCreate):
    """Create a new user. Only admin can do this."""
    # Check if username exists (username must be unique)
    exists = await db()["users"].find_one({"username": body.username})
    if exists:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Email can be duplicated, so no need to check for email uniqueness

    temp_pw = body.temp_password or "123456"
    doc = {
        "username": body.username,
        "email": body.email,
        "phone_number": body.phone_number,
        "password_hash": hash_password(temp_pw),
        "temp_password_encrypted": encrypt_temp_password(temp_pw),
        # role removed - roles are assigned per project via project_members
        "created_at": datetime.now(timezone.utc),
        "last_login_at": None,
    }
    
    try:
        await db()["users"].insert_one(doc)
        return {"message": "User created", "temp_password": temp_pw}
    except DuplicateKeyError as e:
        # Handle duplicate key errors from MongoDB
        # Only username should be unique, email can be duplicated
        error_msg = str(e)
        if "username" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Username already exists")
        else:
            # This should not happen for email since we removed unique constraint
            raise HTTPException(status_code=400, detail="Duplicate key error")
    except Exception as e:
        # Handle other errors
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@router.get("/{username}")
async def get_user(username: str, user=Depends(require_admin)):
    """Get user details. Only admin can do this."""
    u = await db()["users"].find_one({"username": username}, {"_id": 0, "password_hash": 0})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    # Remove role if exists (roles are per project)
    user_data = {k: v for k, v in u.items() if k != "role"}
    return user_data

@router.put("/{username}")
async def update_user(username: str, body: UserUpdate, user=Depends(require_admin)):
    """Update user details. Only admin can do this."""
    existing = await db()["users"].find_one({"username": username})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if new username conflicts (if changed)
    if body.username != username:
        conflict = await db()["users"].find_one({"username": body.username})
        if conflict:
            raise HTTPException(status_code=400, detail="Username already exists")
    
    # Email can be duplicated, so no need to check for email conflicts
    
    update_data = {
        "username": body.username,
        "email": body.email,
        "updated_at": datetime.now(timezone.utc),
    }
    
    # Update password if provided
    if body.temp_password:
        update_data["password_hash"] = hash_password(body.temp_password)
    
    # Update phone_number if provided
    if body.phone_number is not None:
        update_data["phone_number"] = body.phone_number
    
    try:
        await db()["users"].update_one(
            {"username": username},
            {"$set": update_data}
        )
    except DuplicateKeyError as e:
        # Handle duplicate key errors from MongoDB
        # Only username should be unique, email can be duplicated
        error_msg = str(e)
        if "username" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Username already exists")
        else:
            # This should not happen for email since we removed unique constraint
            raise HTTPException(status_code=400, detail="Duplicate key error")
    except Exception as e:
        # Handle other errors
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")
    
    updated = await db()["users"].find_one({"username": body.username}, {"_id": 0, "password_hash": 0})
    user_data = {k: v for k, v in updated.items() if k != "role"}
    return user_data

@router.delete("/{username}")
async def delete_user(username: str, user=Depends(require_admin)):
    """Delete a user. Only admin can do this. Cannot delete admin user."""
    existing = await db()["users"].find_one({"username": username})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting admin user
    if existing.get("role") == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin user")
    
    # Delete user and all their project memberships
    await db()["users"].delete_one({"username": username})
    await db()["project_members"].delete_many({"username": username})
    
    return {"message": "User deleted"}

