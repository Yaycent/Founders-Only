"""Python API for Founders-Only authentication and per-user account data."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
import uvicorn
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse


BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent


def load_backend_env() -> None:
    """Load backend/.env without requiring a separate dotenv dependency."""
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_backend_env()
JWT_SECRET = os.environ.get("JWT_SECRET", "")
if len(JWT_SECRET) < 32:
    raise RuntimeError("Set JWT_SECRET in backend/.env to a private value of at least 32 characters.")

DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", BACKEND_DIR / "data" / "founders_only.sqlite3"))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = (ROOT_DIR / DATABASE_PATH).resolve()
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

SESSION_COOKIE = "founders_session"
SESSION_SECONDS = 7 * 24 * 60 * 60
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@contextmanager
def database_connection():
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    with database_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                _id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                passwordHash TEXT NOT NULL,
                createdAt TEXT NOT NULL,
                updatedAt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS account_data (
                userId TEXT PRIMARY KEY NOT NULL REFERENCES users(_id) ON DELETE CASCADE,
                profile TEXT NOT NULL DEFAULT '{}',
                preferences TEXT NOT NULL DEFAULT '{}',
                updatedAt TEXT NOT NULL
            );
            """
        )


initialize_database()
app = FastAPI(title="Founders-Only API", docs_url=None, redoc_url=None)


class Credentials(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=72)
    confirmPassword: str | None = None


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    profile: dict | None = None
    preferences: dict | None = None


def public_user(row: sqlite3.Row) -> dict:
    return {"id": row["_id"], "email": row["email"], "createdAt": row["createdAt"]}


def set_session_cookie(response: Response, user_id: str) -> None:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": user_id, "iat": now, "exp": now + timedelta(seconds=SESSION_SECONDS)},
        JWT_SECRET,
        algorithm="HS256",
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=os.environ.get("NODE_ENV") == "production",
        samesite="strict",
        path="/",
    )


def current_user_id(founders_session: str | None = Cookie(default=None)) -> str:
    if not founders_session:
        raise HTTPException(status_code=401, detail="Please log in to continue.")
    try:
        claims = jwt.decode(founders_session, JWT_SECRET, algorithms=["HS256"])
        user_id = claims.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise jwt.InvalidTokenError("Invalid subject")
        return user_id
    except jwt.PyJWTError as error:
        raise HTTPException(status_code=401, detail="Your session has expired. Please log in again.") from error


@app.middleware("http")
async def no_store(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(HTTPException)
async def handle_http_error(_request: Request, error: HTTPException):
    message = error.detail if isinstance(error.detail, str) else "The request could not be completed."
    return JSONResponse(status_code=error.status_code, content={"error": message}, headers=error.headers)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request: Request, _error: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Check that all required fields are valid."})


@app.get("/api/health")
def health():
    return {"status": "ok", "database": "sqlite", "persistent": True}


@app.post("/api/auth/register", status_code=201)
def register(credentials: Credentials, response: Response):
    email = credentials.email.strip().lower()
    password = credentials.password
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if len(password) < 8 or len(password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters and no more than 72 UTF-8 bytes.")
    if password != credentials.confirmPassword:
        raise HTTPException(status_code=400, detail="Your passwords do not match.")

    now = datetime.now(timezone.utc).isoformat()
    user_id = uuid.uuid4().hex
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")
    try:
        with database_connection() as connection:
            connection.execute(
                "INSERT INTO users (_id,email,passwordHash,createdAt,updatedAt) VALUES (?,?,?,?,?)",
                (user_id, email, password_hash, now, now),
            )
            connection.execute(
                "INSERT INTO account_data (userId,profile,preferences,updatedAt) VALUES (?,?,?,?)",
                (user_id, "{}", "{}", now),
            )
            user = connection.execute(
                "SELECT _id,email,createdAt FROM users WHERE _id=?", (user_id,)
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from error

    set_session_cookie(response, user_id)
    return {"user": public_user(user)}


@app.post("/api/auth/login")
def login(credentials: Credentials, response: Response):
    email = credentials.email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=400, detail="Enter your email and password.")
    if len(credentials.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=401, detail="The email or password is incorrect.")

    with database_connection() as connection:
        user = connection.execute(
            "SELECT _id,email,passwordHash,createdAt FROM users WHERE email=? COLLATE NOCASE",
            (email,),
        ).fetchone()
    if user is None or not bcrypt.checkpw(credentials.password.encode("utf-8"), user["passwordHash"].encode("ascii")):
        raise HTTPException(status_code=401, detail="The email or password is incorrect.")

    set_session_cookie(response, user["_id"])
    return {"user": public_user(user)}


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        secure=os.environ.get("NODE_ENV") == "production",
        samesite="strict",
        path="/",
    )
    return {"message": "You have been logged out."}


@app.get("/api/auth/me")
def me(user_id: str = Depends(current_user_id)):
    with database_connection() as connection:
        user = connection.execute(
            "SELECT _id,email,createdAt FROM users WHERE _id=?", (user_id,)
        ).fetchone()
    if user is None:
        raise HTTPException(status_code=401, detail="This account is no longer available.")
    return {"user": public_user(user)}


@app.get("/api/account")
def get_account(user_id: str = Depends(current_user_id)):
    with database_connection() as connection:
        account = connection.execute(
            "SELECT profile,preferences FROM account_data WHERE userId=?", (user_id,)
        ).fetchone()
    if account is None:
        raise HTTPException(status_code=404, detail="Account data was not found.")
    return {"profile": json.loads(account["profile"]), "preferences": json.loads(account["preferences"])}


@app.patch("/api/account")
def update_account(update: AccountUpdate, user_id: str = Depends(current_user_id)):
    fields = {}
    if update.profile is not None:
        fields["profile"] = json.dumps(update.profile, ensure_ascii=False)
    if update.preferences is not None:
        fields["preferences"] = json.dumps(update.preferences, ensure_ascii=False)
    if not fields:
        raise HTTPException(status_code=400, detail="Provide profile or preferences to update.")

    assignments = ", ".join(f"{name}=?" for name in fields)
    values = [*fields.values(), datetime.now(timezone.utc).isoformat(), user_id]
    with database_connection() as connection:
        result = connection.execute(
            f"UPDATE account_data SET {assignments}, updatedAt=? WHERE userId=?", values
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Account data was not found.")
        account = connection.execute(
            "SELECT profile,preferences FROM account_data WHERE userId=?", (user_id,)
        ).fetchone()
    return {"profile": json.loads(account["profile"]), "preferences": json.loads(account["preferences"])}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "4000")))
