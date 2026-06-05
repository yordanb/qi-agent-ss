from pydantic import BaseModel
from typing import Optional, List, Any


class LoginRequest(BaseModel):
    nrp: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict


class ChangePasswordRequest(BaseModel):
    nrp: str
    old_password: str
    new_password: str
