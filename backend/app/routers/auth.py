from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from ..db.mongo import db
from ..core.security import verify_password, create_access_token, hash_password, encrypt_temp_password
from ..dependencies.auth import get_current_user
from ..services.email_service import (
    create_otp_record, verify_otp, get_verified_otp_record, 
    delete_otp_record, send_otp_email
)

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

class ForgotPasswordBody(BaseModel):
    email: EmailStr

class VerifyOTPBody(BaseModel):
    email: EmailStr
    otp_code: str

class ResetPasswordBody(BaseModel):
    email: EmailStr
    new_password: str

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
        # Check if email is already used by another user
        email_lower = body.email.lower().strip()
        existing = await db()["users"].find_one({
            "email": {"$regex": f"^{email_lower}$", "$options": "i"},
            "username": {"$ne": user["username"]}
        })
        if existing:
            raise HTTPException(status_code=400, detail=f"Email '{body.email}' is already used by another user")
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


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordBody):
    """
    Request password reset OTP. Sends verification code to email.
    """
    email = body.email.lower().strip()
    
    # Find user by email
    user = await db()["users"].find_one({"email": email})
    if not user:
        # Don't reveal if email exists - return success anyway for security
        return {"message": "If this email is registered, you will receive a verification code."}
    
    # Create OTP and send email
    otp_code, expiry_time = await create_otp_record(email, user["username"])
    success, message = send_otp_email(email, otp_code, user["username"])
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
    
    return {
        "message": "Verification code sent to your email.",
        "expires_in_minutes": 15
    }


@router.post("/verify-otp")
async def verify_otp_endpoint(body: VerifyOTPBody):
    """
    Verify OTP code for password reset.
    """
    email = body.email.lower().strip()
    otp_code = body.otp_code.strip()
    
    success, message, username = await verify_otp(email, otp_code)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "username": username,
        "can_reset_password": True
    }


@router.post("/reset-password")
async def reset_password(body: ResetPasswordBody):
    """
    Reset password after OTP verification.
    """
    email = body.email.lower().strip()
    
    # Check if OTP was verified
    otp_record = await get_verified_otp_record(email)
    if not otp_record:
        raise HTTPException(
            status_code=400, 
            detail="No verified OTP found. Please verify your code first."
        )
    
    # Validate new password
    if len(body.new_password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")
    
    # Update password
    username = otp_record["username"]
    await db()["users"].update_one(
        {"username": username},
        {
            "$set": {
                "password_hash": hash_password(body.new_password),
                "temp_password_encrypted": encrypt_temp_password(body.new_password),
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    # Delete OTP record
    await delete_otp_record(email)
    
    return {"message": "Password reset successfully. You can now login with your new password."}
