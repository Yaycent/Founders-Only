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
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse


BACKEND_DIR = Path(__file__).resolve().parent


def load_backend_env() -> None:
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
    raise RuntimeError("Set JWT_SECRET to a private value of at least 32 characters in backend/.env")

DATA_PATH = Path(os.environ.get("DATABASE_PATH", BACKEND_DIR / "data" / "founders_only.sqlite3"))
if not DATA_PATH.is_absolute():
    DATA_PATH = (Path.cwd() / DATA_PATH).resolve()
DATA_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def connect_db():
    conn = sqlite3.connect(DATA_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database() -> None:
    with connect_db() as conn:
        conn.executescript("""
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
        """)


initialize_database()
app = FastAPI(title="Founders-Only API", docs_url=None, redoc_url=None)
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
COOKIE_NAME = "founders_session"
COOKIE_MAX_AGE = 7 * 24 * 60 * 60


@app.exception_handler(StarletteHTTPException)
async def api_http_error(_request: Request, exc: StarletteHTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
    return JSONResponse(status_code=exc.status_code, content={"error": message}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def api_validation_error(_request: Request, _exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "Check that all required fields are valid."})


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


def session_cookie(response: Response, user_id: str) -> None:
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": user_id, "iat": now, "exp": now + timedelta(seconds=COOKIE_MAX_AGE)}, JWT_SECRET, algorithm="HS256")
    response.set_cookie(
        COOKIE_NAME, token, max_age=COOKIE_MAX_AGE, httponly=True,
        secure=os.environ.get("NODE_ENV") == "production", samesite="strict", path="/",
    )


def authenticated_user(founders_session: str | None = Cookie(default=None)) -> str:
    if not founders_session:
        raise HTTPException(status_code=401, detail="Please log in to continue.")
    try:
        payload = jwt.decode(founders_session, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise jwt.InvalidTokenError("Missing subject")
        return user_id
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Your session has expired. Please log in again.") from exc


@app.middleware("http")
async def no_store(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health():
    return {"status": "ok", "database": "sqlite", "persistent": True}


@app.post("/api/auth/register", status_code=201)
def register(payload: Credentials, response: Response):
    email = payload.email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if len(payload.password) < 8 or len(payload.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters and no more than 72 UTF-8 bytes.")
    if payload.password != payload.confirmPassword:
        raise HTTPException(status_code=400, detail="Your passwords do not match.")

    now = datetime.now(timezone.utc).isoformat()
    user_id = uuid.uuid4().hex
    password_hash = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")
    try:
        with connect_db() as conn:
            conn.execute("INSERT INTO users (_id,email,passwordHash,createdAt,updatedAt) VALUES (?,?,?,?,?)", (user_id, email, password_hash, now, now))
            conn.execute("INSERT INTO account_data (userId,profile,preferences,updatedAt) VALUES (?,?,?,?)", (user_id, "{}", "{}", now))
            row = conn.execute("SELECT _id,email,createdAt FROM users WHERE _id=?", (user_id,)).fetchone()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
    session_cookie(response, user_id)
    return {"user": public_user(row)}


@app.post("/api/auth/login")
def login(payload: Credentials, response: Response):
    email = payload.email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=400, detail="Enter your email and password.")
    if len(payload.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=401, detail="The email or password is incorrect.")
    with connect_db() as conn:
        row = conn.execute("SELECT _id,email,passwordHash,createdAt FROM users WHERE email=? COLLATE NOCASE", (email,)).fetchone()
    if row is None or not bcrypt.checkpw(payload.password.encode("utf-8"), row["passwordHash"].encode("ascii")):
        raise HTTPException(status_code=401, detail="The email or password is incorrect.")
    session_cookie(response, row["_id"])
    return {"user": public_user(row)}


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, httponly=True, secure=os.environ.get("NODE_ENV") == "production", samesite="strict", path="/")
    return {"message": "You have been logged out."}


@app.get("/api/auth/me")
def me(user_id: str = Depends(authenticated_user)):
    with connect_db() as conn:
        row = conn.execute("SELECT _id,email,createdAt FROM users WHERE _id=?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="This account is no longer available.")
    return {"user": public_user(row)}


@app.get("/api/account")
def get_account(user_id: str = Depends(authenticated_user)):
    with connect_db() as conn:
        row = conn.execute("SELECT profile,preferences FROM account_data WHERE userId=?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Account data was not found.")
    return {"profile": json.loads(row["profile"]), "preferences": json.loads(row["preferences"])}


@app.patch("/api/account")
def update_account(payload: AccountUpdate, user_id: str = Depends(authenticated_user)):
    updates = {}
    if payload.profile is not None:
        updates["profile"] = json.dumps(payload.profile, ensure_ascii=False)
    if payload.preferences is not None:
        updates["preferences"] = json.dumps(payload.preferences, ensure_ascii=False)
    if not updates:
        raise HTTPException(status_code=400, detail="Provide profile or preferences to update.")
    assignments = ",".join(f"{column}=?" for column in updates)
    values = [*updates.values(), datetime.now(timezone.utc).isoformat(), user_id]
    with connect_db() as conn:
        cursor = conn.execute(f"UPDATE account_data SET {assignments},updatedAt=? WHERE userId=?", values)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Account data was not found.")
        row = conn.execute("SELECT profile,preferences FROM account_data WHERE userId=?", (user_id,)).fetchone()
    return {"profile": json.loads(row["profile"]), "preferences": json.loads(row["preferences"])}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "4000")), log_level="info")
