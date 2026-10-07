from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=200)
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=4, max_length=128)


class ProfileUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=4, max_length=128)
