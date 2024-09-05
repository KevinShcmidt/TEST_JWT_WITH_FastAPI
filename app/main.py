from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import secrets
from fastapi.security import OAuth2PasswordBearer
from .db import database
from .models import users, UserCreate, User, UserOut, Login
from fastapi.middleware.cors import CORSMiddleware

SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()
origins = [
    "http://localhost:3000",  # Remplacez par l'URL de votre frontend
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Dependency
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # Asynchrone n'a pas besoin de cela

async def get_db():
    async with database.connection() as connection:
        yield connection

# Create tables
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Hash the password
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Verify password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Create JWT Token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Register User
@app.post("/register", response_model=UserOut)
async def register_user(user:UserCreate, db: AsyncSession = Depends(get_db)):
    hashed_password = hash_password(user.password)
    query = users.insert().values(
        name=user.name,
        first_name=user.first_name,
        role=user.role,
        email=user.email,
        hashed_password=hashed_password
    )
    user_id = await db.execute(query)
    # Créez un objet UserOut pour la réponse
    new_user = UserOut(
        id=user_id,
        name=user.name,
        first_name=user.first_name,
        role=user.role,
        email=user.email
    )
    return new_user
# Authenticate User
@app.post("/token")
async def login_for_access_token(form_data: Login, db: AsyncSession = Depends(get_db)):
    query = users.select().where(users.c.email == form_data.email)
    user = await db.fetch_one(query)
    if not user or not verify_password(form_data.password, user['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email ou mots de pass",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Déterminez la durée de vie du token en fonction de "rememberMe"
    expires_delta = timedelta(days=30) if form_data.rememberMe else timedelta(minutes=15)
    access_token = create_access_token(data={"sub": user['email']}, expires_delta=expires_delta)
    return {"access_token": access_token, "token_type": "bearer", "user" : user, "rememberMe" : form_data.rememberMe}

# Define oauth2_scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Protected Route
@app.get("/users/me", response_model=User)
async def read_users_me(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    query = users.select().where(users.c.email == email)
    user = await db.fetch_one(query)
    if user is None:
        raise credentials_exception
    return User(id=user['id'], email=user['email'])
