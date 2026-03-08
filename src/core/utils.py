from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_handler import AuthHandler
from src.core.database import get_async_session
from src.cruds.authentication import AuthenticationCrud
from src.models.authentication import Authentication


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    access_token: Annotated[str | None, Cookie()] = None,
    db_session: AsyncSession = Depends(get_async_session),
) -> Authentication:

    token = None
    if credentials:
        token = credentials.credentials
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token required for this endpoint",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = AuthHandler.decode_token(token, "access_token")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user: Authentication | None = await AuthenticationCrud().get(
        db_session,
        email=email,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user is not active.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
