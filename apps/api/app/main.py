from contextlib import asynccontextmanager
import jwt
import redis
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from apps.api.app.config import get_settings
from apps.api.app.database import Base, engine, get_db
from apps.api.app.models import User
from apps.api.app.schemas import (
    Credentials,
    LoginCredentials,
    TokenOut,
    UserOut,
)
from apps.api.app.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 1 only: use Alembic migrations before any production deployment.
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="SecureAgent AI API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins.split(","), allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])
bearer = HTTPBearer()

@app.get("/health")
def health():
    return {"status": "ok", "service": "secureagent-api"}

@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        client = redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
    except Exception:
        raise HTTPException(status_code=503, detail="Dependency unavailable") from None
    return {"status": "ready", "database": "ok", "redis": "ok"}

@app.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: Credentials, db: Session = Depends(get_db)):
    user = User(email=str(data.email).lower(), password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Account already exists") from None
    return user

@app.post("/auth/login", response_model=TokenOut)
def login(data: LoginCredentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenOut(access_token=create_token(user.id))

@app.get("/auth/me", response_model=UserOut)
def me(auth: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    try:
        user_id = decode_token(auth.credentials)
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid token") from None
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user
