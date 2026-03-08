from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth_handler import AuthHandler
from src.core.database import get_async_session
from src.cruds.authentication import AuthenticationCrud
from src.schemas.authentication import (
    JWTResponseSchema,
    UserLoginSchema,
    UserResponseSchema,
)

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=JWTResponseSchema)
async def login_jwt(
    response: Response,
    login_data: UserLoginSchema,
    db_session: AsyncSession = Depends(get_async_session),
) -> JWTResponseSchema:
    user = await AuthenticationCrud().get(db_session, email=login_data.email)
    if not user or not user.check_password(login_data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = AuthHandler.encode_token(
        user.email, scope="access_token", ttl={"days": 30}
    )
    refresh_token = AuthHandler.encode_token(
        user.email, scope="refresh_token", ttl={"days": 60}
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="none",
        secure=True,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="none",
        secure=True,
    )

    user_data = UserResponseSchema(
        id=user.id,
        email=user.email,
        created_date=user.created_date,
        updated_date=user.updated_date,
    )

    return JWTResponseSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=60 * 60 * 24 * 30,  # 30 days in seconds
        user=user_data,
    )
