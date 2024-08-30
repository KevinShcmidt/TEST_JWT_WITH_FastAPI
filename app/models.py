from sqlalchemy import Table, Column, Integer, String
from pydantic import BaseModel

from .db import metadata

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("name", String, index=True),
    Column("first_name", String, index=True),
    Column("role", String, index=True),
    Column("email", String, unique=True, index=True),
    Column("hashed_password", String),
)

# Pydantic Models
class UserCreate(BaseModel):
    name: str
    first_name: str
    role: str
    email: str
    password: str

class Login(BaseModel):
    email: str
    password: str
    rememberMe: bool = False

class User(BaseModel):
    id: int
    name: str
    first_name: str
    role: str
    email: str
class UserOut(BaseModel):
    id: int
    name: str
    first_name: str
    role: str
    email: str

    class Config:
        orm_mode = True