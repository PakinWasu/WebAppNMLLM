from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from ..db.mongo import db
from ..core.security import verify_password, create_access_token, hash_password, encrypt_temp_password
from ..dependencies.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginBody(BaseModel):
    username: str
    password: str

class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str

@router.post("/login")
async def login(body: LoginBody):
    user = await db()["users"].find_one({"username": body.username})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username/password")

    await db()["users"].update_one(
        {"username": body.username},
        {"$set": {"last_login_at": datetime.now(timezone.utc)}}
    )

    token = create_access_token({"sub": body.username})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {
        "username": user["username"],
        "email": user["email"],
        "role": user.get("role", "viewer"),
        "created_at": user.get("created_at"),
        "last_login_at": user.get("last_login_at"),
    }

@router.post("/change-password")
async def change_password(body: ChangePasswordBody, user=Depends(get_current_user)):
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Wrong current password")

    await db()["users"].update_one(
        {"username": user["username"]},
        {
            "$set": {
                "password_hash": hash_password(body.new_password),
                "temp_password_encrypted": encrypt_temp_password(body.new_password)  # Store new password so admin can see it
            }
        }
    )
    return {"message": "Password updated"}
