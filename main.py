from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Boolean, select, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()  # загружает переменные из файла .env

# --- Конфигурация ---
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-for-development")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- База данных ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:S3crtKfiJ4@localhost:5432/postgres")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# --- Хэширование паролей ---
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# --- Security ---
security = HTTPBearer()


# --- Модели базы данных ---
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    tasks = relationship("TaskDB", back_populates="owner")


class TaskDB(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, default="", nullable=False)
    completed = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("UserDB", back_populates="tasks")


# --- Pydantic модели ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str


class TaskCreate(BaseModel):
    title: str
    description: str = ""


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    completed: bool


class Token(BaseModel):
    access_token: str
    token_type: str


# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ База данных готова")
    yield
    await engine.dispose()
    print("🛑 Соединение закрыто")


app = FastAPI(lifespan=lifespan, title="Task Manager with JWT")


# --- Вспомогательные функции ---
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(UserDB).where(UserDB.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, password: str):
    hashed = get_password_hash(password)
    user = UserDB(email=email, hashed_password=hashed)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(UserDB).where(UserDB.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

# --- Auth endpoints ---
@app.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await create_user(db, user.email, user.password)
    return new_user


@app.post("/auth/login", response_model=Token)
async def login(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_email(db, user.email)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


# --- Protected task endpoints ---
@app.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskCreate, current_user: UserDB = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    db_task = TaskDB(title=task.title, description=task.description, owner_id=current_user.id)
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(current_user: UserDB = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskDB).where(TaskDB.owner_id == current_user.id))
    tasks = result.scalars().all()
    return tasks


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, current_user: UserDB = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskDB).where(TaskDB.id == task_id, TaskDB.owner_id == current_user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int, current_user: UserDB = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskDB).where(TaskDB.id == task_id, TaskDB.owner_id == current_user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()
    return {"message": "Task deleted"}


# --- Health check ---
@app.get("/health")
async def health():
    return {"status": "alive"}

@app.get("/about")
async def about():
    return {"version": 1.0, "author": "NemesisYN"}


