from __future__ import annotations

import os
from typing import Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.database import engine
from backend.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Sign-in is required.")

    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise HTTPException(status_code=503, detail="Authentication is not configured.")

    try:
        return jwt.decode(
            credentials.credentials,
            secret_key,
            algorithms=["HS256"],
            options={"require": ["sub", "email", "role", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=401,
            detail="Your session is invalid or expired. Please sign in again.",
        ) from exc


def get_current_user(claims: dict[str, Any] = Depends(get_token_claims)) -> User:
    if claims.get("role") != "user":
        raise HTTPException(status_code=403, detail="A user account is required.")

    with Session(engine) as db:
        user = db.query(User).filter(User.google_id == str(claims["sub"])).one_or_none()
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="User account was not found. Please sign in again.",
            )
        db.expunge(user)
        return user


def get_admin_claims(claims: dict[str, Any] = Depends(get_token_claims)) -> dict[str, Any]:
    if claims.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    return claims
