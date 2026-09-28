from pydantic import BaseModel, Field


class MaxAuthRequest(BaseModel):
    init_data: str = Field(min_length=1, max_length=16384)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminLoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)
