from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
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

class VerifyPasswordBody(BaseModel):
    current_password: str

class UpdateMyProfileBody(BaseModel):
    email: EmailStr | None = None
    phone_number: str | None = None

@router.post("/login")
async def login(body: LoginBody):
    login_id = body.username.strip()
    # Accept username or email: find by username first, then by email
    user = await db()["users"].find_one({"username": login_id})
    if not user and "@" in login_id:
        user = await db()["users"].find_one({"email": login_id})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username/password")

    await db()["users"].update_one(
        {"username": user["username"]},
        {"$set": {"last_login_at": datetime.now(timezone.utc)}}
    )

    token = create_access_token({"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {
        "username": user["username"],
        "email": user.get("email", ""),
        "phone_number": user.get("phone_number"),
        "role": user.get("role", "viewer"),
        "created_at": user.get("created_at"),
        "last_login_at": user.get("last_login_at"),
    }

@router.patch("/me")
async def update_my_profile(body: UpdateMyProfileBody, user=Depends(get_current_user)):
    """Update current user's email and phone_number. Username cannot be changed."""
    update_data = {}
    if body.email is not None:
        update_data["email"] = body.email
    if body.phone_number is not None:
        update_data["phone_number"] = body.phone_number
    if not update_data:
        return {"message": "Nothing to update"}
    update_data["updated_at"] = datetime.now(timezone.utc)
    await db()["users"].update_one(
        {"username": user["username"]},
        {"$set": update_data}
    )
    return {"message": "Profile updated"}

@router.post("/verify-password")
async def verify_password_route(body: VerifyPasswordBody, user=Depends(get_current_user)):
    """Verify current password without changing it. Used when updating profile without changing password."""
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Wrong current password")
    return {"message": "Password verified"}

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
