
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from pydantic import BaseModel, EmailStr


router = APIRouter(prefix="/auth", tags=["Authentication"])

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8


class GoogleCredentialRequest(BaseModel):
    credential: str


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


def create_access_token(user_id: str, email: str, role: str) -> str:
    """
    Create a signed access token for an authenticated user.
    The signing secret must be configured in Render.
    """
    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        raise HTTPException(
            status_code=500,
            detail="Authentication is not configured on the server.",
        )

    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    }

    return jwt.encode(
        payload,
        secret_key,
        algorithm=JWT_ALGORITHM,
    )


@router.post("/google")
def sign_in_with_google(payload: GoogleCredentialRequest):
    """
    Authenticate an ordinary user using Google Sign-In.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")

    if not client_id:
        raise HTTPException(
            status_code=500,
            detail="Google authentication is not configured on the server.",
        )

    if not payload.credential:
        raise HTTPException(
            status_code=400,
            detail="Google credential is required.",
        )

    try:
        google_user = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            client_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired Google credential.",
        ) from exc

    issuer = google_user.get("iss")

    if issuer not in {
        "accounts.google.com",
        "https://accounts.google.com",
    }:
        raise HTTPException(
            status_code=401,
            detail="Invalid Google credential issuer.",
        )

    subject = google_user.get("sub")
    email = google_user.get("email")

    if not subject or not email:
        raise HTTPException(
            status_code=401,
            detail="Google account information is incomplete.",
        )

    if not google_user.get("email_verified", False):
        raise HTTPException(
            status_code=401,
            detail="Please use a verified Google account.",
        )

    email = email.strip().lower()

    token = create_access_token(
        user_id=subject,
        email=email,
        role="user",
    )

    return {
        "status": "authenticated",
        "token": token,
        "user": {
            "id": subject,
            "email": email,
            "name": google_user.get("name") or email.split("@")[0],
            "picture": google_user.get("picture"),
            "email_verified": True,
            "role": "user",
        },
    }


@router.post("/admin/login")
def sign_in_as_admin(payload: AdminLoginRequest):
    """
    Authenticate the configured administrator using credentials
    stored in server environment variables, never in frontend code.
    """
    configured_email = os.getenv("ADMIN_EMAIL")
    configured_password = os.getenv("ADMIN_PASSWORD")

    if not configured_email or not configured_password:
        raise HTTPException(
            status_code=503,
            detail=(
                "Administrator authentication is not configured. "
                "Please configure ADMIN_EMAIL and ADMIN_PASSWORD "
                "in the backend environment."
            ),
        )

    submitted_email = str(payload.email).strip().lower()
    expected_email = configured_email.strip().lower()

    email_matches = secrets.compare_digest(
        submitted_email,
        expected_email,
    )

    password_matches = secrets.compare_digest(
        payload.password,
        configured_password,
    )

    if not email_matches or not password_matches:
        raise HTTPException(
            status_code=401,
            detail="Invalid administrator email or password.",
        )

    token = create_access_token(
        user_id=expected_email,
        email=expected_email,
        role="admin",
    )

    return {
        "status": "authenticated",
        "token": token,
        "user": {
            "id": expected_email,
            "email": expected_email,
            "name": "ZimBuild AI Administrator",
            "role": "admin",
        },
    }
