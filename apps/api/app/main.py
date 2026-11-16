
from contextlib import asynccontextmanager

import redis
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.app.auth_dependencies import get_current_user
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
    hash_password,
    verify_password,
)

# ============================================================
# Register ORM models before database initialization
# ============================================================

from apps.api.rag import models as rag_models  # noqa: F401
from apps.api.agents import audit_models  # noqa: F401
from apps.api.agents import investigation_report_models  # noqa: F401
from apps.api.agents import investigation_review_models  # noqa: F401

# Phase 7.7: Report export audit models
from apps.api.agents import report_export_models  # noqa: F401

from apps.api.app import settings_models  # noqa: F401


# ============================================================
# API Routers
# ============================================================

from apps.api.routes.chat import router as chat_router
from apps.api.routes.documents import router as documents_router
from apps.api.routes.retrieval import router as retrieval_router
from apps.api.routes.rag_chat import router as rag_chat_router

from apps.api.routes.investigations import (
    router as investigations_router,
)

from apps.api.routes.settings import (
    router as settings_router,
)

from apps.api.routes.reviews import (
    router as reviews_router,
)

# Phase 7.7: Secure report exports
from apps.api.routes.reports import (
    router as reports_router,
)


# ============================================================
# Application Lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize database tables on application startup.

    Development only:
    Use Alembic migrations for production deployments.
    """
    Base.metadata.create_all(bind=engine)
    yield


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="SecureAgent AI API",
    description=(
        "SecureAgent AI is a secure AI-powered "
        "cybersecurity research and investigation platform."
    ),
    version="0.3.0",
    lifespan=lifespan,
)


# ============================================================
# CORS Configuration
# ============================================================

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=[
        "Authorization",
        "Content-Type",
    ],
)


# ============================================================
# Health Check
# ============================================================

@app.get("/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "service": "secureagent-api",
    }


# ============================================================
# Readiness Check
# ============================================================

@app.get("/ready", tags=["System"])
def ready(
    db: Session = Depends(get_db),
):
    """
    Check PostgreSQL and Redis connectivity.
    """
    try:
        db.execute(text("SELECT 1"))

        client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
        )

        client.ping()
        client.close()

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Dependency unavailable",
        ) from None

    return {
        "status": "ready",
        "database": "ok",
        "redis": "ok",
    }


# ============================================================
# User Registration
# ============================================================

@app.post(
    "/auth/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
)
def register(
    data: Credentials,
    db: Session = Depends(get_db),
):
    """
    Register a new user.
    """
    user = User(
        email=str(data.email).lower(),
        password_hash=hash_password(data.password),
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Account already exists",
        ) from None

    return user


# ============================================================
# User Login
# ============================================================

@app.post(
    "/auth/login",
    response_model=TokenOut,
    tags=["Authentication"],
)
def login(
    data: LoginCredentials,
    db: Session = Depends(get_db),
):
    """
    Authenticate a user and return a JWT token.
    """
    user = db.scalar(
        select(User).where(
            User.email == str(data.email).lower()
        )
    )

    if user is None or not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    return TokenOut(
        access_token=create_token(user.id)
    )


# ============================================================
# Current Authenticated User
# ============================================================

@app.get(
    "/auth/me",
    response_model=UserOut,
    tags=["Authentication"],
)
def me(
    user: User = Depends(get_current_user),
):
    """
    Return the authenticated user's information.
    """
    return user


# ============================================================
# Register API Routers
# ============================================================

# AI chat
app.include_router(chat_router)

# Document management
app.include_router(documents_router)

# RAG retrieval and chat
app.include_router(retrieval_router)
app.include_router(rag_chat_router)

# Agentic cybersecurity investigations
app.include_router(investigations_router)

# User configuration
app.include_router(settings_router)

# Human investigation reviews
app.include_router(reviews_router)

# Phase 7.7: Secure PDF and JSON report exports
app.include_router(reports_router)
