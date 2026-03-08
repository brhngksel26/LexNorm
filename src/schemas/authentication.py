from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponseSchema(BaseModel):
    """Response schema for User - excludes sensitive fields like password."""

    id: int
    email: str
    created_date: datetime
    updated_date: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreateSchema(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")


class UserLoginSchema(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserUpdateSchema(BaseModel):
    email: EmailStr | None = Field(None, description="New email address")
    password: str | None = Field(
        None, min_length=8, description="New password (min 8 characters)"
    )


class JWTResponseSchema(BaseModel):
    success: bool = Field(True, description="Login success status")
    message: str = Field(
        default="JWT tokens generated successfully", description="Success message"
    )
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")
    user: UserResponseSchema = Field(..., description="User information")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Login timestamp",
    )

    model_config = ConfigDict(from_attributes=True)
