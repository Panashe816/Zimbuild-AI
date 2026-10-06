import os

from fastapi import APIRouter, HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from pydantic import BaseModel


router = APIRouter(prefix="/auth", tags=["Authentication"])


class GoogleCredentialRequest(BaseModel):
    credential: str


@router.post("/google")
def sign_in_with_google(payload: GoogleCredentialRequest):
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
    if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
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

    return {
        "status": "authenticated",
        "user": {
            "id": subject,
            "email": email,
            "name": google_user.get("name") or email.split("@")[0],
            "picture": google_user.get("picture"),
            "email_verified": bool(google_user.get("email_verified")),
        },
    }
