"""
Email Service for sending OTP codes for password reset.
Uses SMTP to send emails.
"""
import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import logging

from ..db.mongo import db

logger = logging.getLogger(__name__)

# Email configuration from environment
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Network Project Platform")

# OTP settings
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 15
MAX_OTP_ATTEMPTS = 5


def generate_otp(length: int = OTP_LENGTH) -> str:
    """Generate a random numeric OTP code."""
    return ''.join(random.choices(string.digits, k=length))


async def create_otp_record(email: str, username: str) -> Tuple[str, datetime]:
    """
    Create and store an OTP record in database.
    Returns (otp_code, expiry_time).
    """
    otp_code = generate_otp()
    expiry_time = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
    
    # Delete any existing OTP for this email
    await db()["password_reset_otps"].delete_many({"email": email})
    
    # Create new OTP record
    await db()["password_reset_otps"].insert_one({
        "email": email,
        "username": username,
        "otp_code": otp_code,
        "created_at": datetime.now(timezone.utc),
        "expires_at": expiry_time,
        "attempts": 0,
        "verified": False,
    })
    
    return otp_code, expiry_time


async def verify_otp(email: str, otp_code: str) -> Tuple[bool, str, Optional[str]]:
    """
    Verify OTP code for email.
    Returns (success, message, username if success).
    """
    record = await db()["password_reset_otps"].find_one({"email": email})
    
    if not record:
        return False, "No OTP request found. Please request a new code.", None
    
    # Check if already verified
    if record.get("verified"):
        return False, "This OTP has already been used. Please request a new code.", None
    
    # Check expiry - handle both naive and aware datetimes from MongoDB
    expires_at = record["expires_at"]
    now = datetime.now(timezone.utc)
    # Make expires_at timezone-aware if it's naive
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        await db()["password_reset_otps"].delete_one({"email": email})
        return False, "OTP has expired. Please request a new code.", None
    
    # Check attempts
    if record["attempts"] >= MAX_OTP_ATTEMPTS:
        await db()["password_reset_otps"].delete_one({"email": email})
        return False, "Too many failed attempts. Please request a new code.", None
    
    # Verify code
    if record["otp_code"] != otp_code:
        await db()["password_reset_otps"].update_one(
            {"email": email},
            {"$inc": {"attempts": 1}}
        )
        remaining = MAX_OTP_ATTEMPTS - record["attempts"] - 1
        return False, f"Invalid OTP code. {remaining} attempts remaining.", None
    
    # Mark as verified
    await db()["password_reset_otps"].update_one(
        {"email": email},
        {"$set": {"verified": True}}
    )
    
    return True, "OTP verified successfully.", record["username"]


async def get_verified_otp_record(email: str) -> Optional[dict]:
    """Get verified OTP record for password reset."""
    record = await db()["password_reset_otps"].find_one({
        "email": email,
        "verified": True
    })
    
    if not record:
        return None
    
    # Check if still within expiry (allow extra 5 minutes for password reset)
    expires_at = record["expires_at"]
    # Make expires_at timezone-aware if it's naive
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    extended_expiry = expires_at + timedelta(minutes=5)
    if extended_expiry < datetime.now(timezone.utc):
        await db()["password_reset_otps"].delete_one({"email": email})
        return None
    
    return record


async def delete_otp_record(email: str):
    """Delete OTP record after password reset."""
    await db()["password_reset_otps"].delete_one({"email": email})


def send_otp_email(to_email: str, otp_code: str, username: str) -> Tuple[bool, str]:
    """
    Send OTP code via email.
    Returns (success, message).
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP not configured. OTP: %s for %s", otp_code, to_email)
        return True, "Email sending simulated (SMTP not configured). Check server logs for OTP."
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Password Reset Code - {otp_code}"
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        
        # Plain text version
        text_content = f"""
Hello {username},

Your password reset verification code is:

{otp_code}

This code will expire in {OTP_EXPIRY_MINUTES} minutes.

If you did not request this code, please ignore this email.

Best regards,
Network Project Platform Team
"""
        
        # HTML version
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }}
        .otp-code {{ font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #4f46e5; text-align: center; padding: 20px; background: white; border-radius: 8px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #6b7280; font-size: 12px; padding: 20px; }}
        .warning {{ color: #dc2626; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset</h1>
        </div>
        <div class="content">
            <p>Hello <strong>{username}</strong>,</p>
            <p>You have requested to reset your password. Use the verification code below:</p>
            <div class="otp-code">{otp_code}</div>
            <p>This code will expire in <strong>{OTP_EXPIRY_MINUTES} minutes</strong>.</p>
            <p class="warning">If you did not request this code, please ignore this email and ensure your account is secure.</p>
        </div>
        <div class="footer">
            <p>Network Project Platform</p>
        </div>
    </div>
</body>
</html>
"""
        
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())
        
        logger.info("OTP email sent successfully to %s", to_email)
        return True, "Verification code sent to your email."
    
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed")
        return False, "Email service configuration error. Please contact administrator."
    except smtplib.SMTPException as e:
        logger.error("SMTP error: %s", str(e))
        return False, f"Failed to send email: {str(e)}"
    except Exception as e:
        logger.exception("Unexpected error sending email")
        return False, f"Failed to send email: {str(e)}"
