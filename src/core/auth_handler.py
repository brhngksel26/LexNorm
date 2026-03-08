from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext

from src.core.config import settings


class AuthHandler:
    security = HTTPBearer()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    secret = settings.JWT_ACCESS_SECRET_KEY

    @classmethod
    def get_password_hash(cls, password):
        return cls.pwd_context.hash(password)

    @classmethod
    def verify_password(cls, plain_password, hashed_password):
        return cls.pwd_context.verify(plain_password, hashed_password)

    @classmethod
    def encode_token(cls, email, scope, ttl):
        exp = datetime.now(timezone.utc) + timedelta(**ttl)
        try:
            payload = {
                "exp": exp,
                "iat": datetime.now(timezone.utc),
                "scope": scope,
                "sub": email,
            }
            return jwt.encode(
                payload, cls.secret, algorithm=settings.ENCRYPTION_ALGORITHM
            )
        except Exception as exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            ) from exception

    @classmethod
    def decode_token(cls, token, scope):
        try:
            payload = jwt.decode(
                token, cls.secret, algorithms=[settings.ENCRYPTION_ALGORITHM]
            )
            if payload["scope"] != scope:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid scope for token",
                )
            return payload["sub"]
        except ExpiredSignatureError as exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            ) from exception
        except InvalidTokenError as exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid access token {exception}",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exception

    @classmethod
    def refresh_token(cls, refresh_token):
        email = cls.decode_token(refresh_token, "refresh_token")
        return cls.encode_token(email, "access_token", {"days": 0, "hours": 2})
