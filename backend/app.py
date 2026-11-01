"""
Python API for Founders-Only authentication and autonomous Agentboxd workflow.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
import uvicorn
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse

# 引入 Agentboxd 与 AI 服务能力
from agentboxd import get_emails, reply_to_email
try:
    from agentboxd import send_email
except ImportError:
    send_email = None

from ai_service import generate_reply
try:
    from ai_service import generate_schedule
except ImportError:
    generate_schedule = None


BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent


def load_backend_env() -> None:
    """自动加载 backend/.env 配置"""
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

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# LARP 全局高管档案与人设状态
# ============================================================
MODE_MAPPING = {
    "arrogant_founder": "unicorn_gatekeeper",
    "toxic_hacker": "reverse_recruiter",
    "bureaucrat": "infinite_bureaucrat",
}

current_executive_profile = {
    "name": "Alexander Sterling",
    "title": "Managing Partner & Chief Architect",
    "company": "Sterling Capital Group",
    "industry": "Autonomous Intelligence & Frontier Tech",
    "valuation": "$42.0B",
    "netWorth": "$1.24B",
    "bio": "Building what comes next. My time is denominated in millions per second.",
    "persona_preset": "arrogant_founder",
}

def get_current_identity_str() -> str:
    return f"""
Name: {current_executive_profile.get('name')}
Title: {current_executive_profile.get('title')}
Company: {current_executive_profile.get('company')}
Industry: {current_executive_profile.get('industry')}
Valuation: {current_executive_profile.get('valuation')}
Net Worth: {current_executive_profile.get('netWorth')}
Bio: {current_executive_profile.get('bio')}
"""

# ============================================================
# 用户认证与原有数据模型
# ============================================================
class Credentials(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=72)
    confirmPassword: str | None = None

class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    profile: dict | None = None
    preferences: dict | None = None

class PersonaUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str | None = None
    title: str | None = None
    company: str | None = None
    industry: str | None = None
    valuation: str | None = None
    netWorth: str | None = None
    bio: str | None = None
    persona_preset: str | None = None

class ScheduleDispatch(BaseModel):
    email: str
    request_type: str = "hyper_elite"

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

# ============================================================
# API 路由：人设同步与日程投递
# ============================================================

@app.get("/api/persona")
def get_persona():
    return current_executive_profile

@app.post("/api/persona")
def update_persona(data: PersonaUpdate):
    """前端切换人设时，实时更新内存中用于生成邮件的 Prompt"""
    global current_executive_profile
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    current_executive_profile.update(updates)
    print(f"\n🎭 [人设已同步] 切换姿态为: {current_executive_profile.get('persona_preset')} | 身价: {current_executive_profile.get('netWorth')}")
    return {"status": "success", "profile": current_executive_profile}

@app.post("/api/send-larp-schedule")
def send_larp_schedule(req: ScheduleDispatch):
    """一键向外部邮箱投递离谱高管日程"""
    if not send_email:
        raise HTTPException(status_code=500, detail="send_email not implemented in agentboxd.py")

    identity_str = get_current_identity_str()
    schedule_text = ""
    if generate_schedule:
        schedule_text = generate_schedule(
            schedule_type=req.request_type,
            identity_data=current_executive_profile,  # 直接传字典！
        )
    else:
        schedule_text = f"""CONFIDENTIAL EXECUTIVE ITINERARY (Alexander Sterling)
03:45 AM - Sub-zero cryo-chamber meditation synchronized with Ethereum block generation.
04:30 AM - Espresso & 18 nootropic supplements. Contemplating AGI endgame.
06:15 AM - Centering a div in raw x86 assembly.
09:00 AM - Board emergency conference: Rejected Google takeover bid.
11:30 AM - Pickleball match with Sovereign Wealth Fund ($50M SAFE closed on court).
02:00 PM - Demanding hiring teams overrule candidate rejections.
11:30 PM - Sleep protocol activated."""

    subject = "📅 [STRICTLY CONFIDENTIAL] Your 24-Hour Executive Schedule is Synced"
    send_email(req.email, subject, schedule_text)
    print(f"✅ 日程已通过 Agentboxd 发送至: {req.email}")
    return {"status": "success", "content": schedule_text}

# ============================================================
# 原有业务路由（账号与注册登录保留）
# ============================================================
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
                (user_id, json.dumps(current_executive_profile, ensure_ascii=False), "{}", now),
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
    global current_executive_profile
    fields = {}
    if update.profile is not None:
        fields["profile"] = json.dumps(update.profile, ensure_ascii=False)
        current_executive_profile.update(update.profile)
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


# ============================================================
# 后台常驻监听线程：Agentboxd 自动回复（基准同步模式）
# ============================================================
def background_agentboxd_listener():
    """常驻后台：启动自动跳过存量邮件，只响应未来进来的新邮件"""
    time.sleep(1) # 等待 FastAPI 端口绑定完成
    print("\n" + "=" * 60)
    print("🚀 [Agentboxd Daemon] 后台邮件监听守护线程已就绪...")
    print("=" * 60)

    processed_ids = set()

    # 1. 启动时扫描收件箱，同步基准（跳过历史邮件）
    try:
        initial_emails = get_emails()
        for mail in initial_emails:
            mid = mail.get("id")
            if mid:
                processed_ids.add(mid)
        print(f"🔍 [Agentboxd 基准同步] 已自动跳过收件箱内现存的 {len(processed_ids)} 封历史邮件。")
        print("👂 监听已就绪，当前只等待【未来刚刚发进来的新邮件】...\n")
    except Exception as e:
        print(f"⚠️ [Agentboxd 基准同步警告]: {e}\n")

    # 2. 正式轮询循环
    while True:
        try:
            emails = get_emails()
            for mail in emails:
                msg_id = mail.get("id")
                if not msg_id or msg_id in processed_ids:
                    continue

                processed_ids.add(msg_id)

                sender_name = mail.get("name")
                sender_email = mail.get("email")
                subject = mail.get("subject", "(No Subject)")
                body = mail.get("body", "")

                print(f"\n📩 [🔥 收到外部来信] 来自: {sender_name} <{sender_email}>")
                print(f"   主题: {subject}")

                # 动态获取当前人设
                preset_id = current_executive_profile.get("persona_preset", "arrogant_founder")
                ai_mode = MODE_MAPPING.get(preset_id, "unicorn_gatekeeper")
                identity_str = get_current_identity_str()

                print(f"🤖 [AI 正在回击] 正在以 [{ai_mode}] 姿态生成回信...")
                reply_body = generate_reply(
                    email=f"Subject: {subject}\n\n{body}",
                    identity_data=current_executive_profile,  # 直接传字典！
                )

                reply_to_email(msg_id, reply_body)
                print(f"✅ [自动回复成功] 已通过 Agentboxd 回执给 {sender_email}！")

        except Exception as err:
            pass

        time.sleep(4)

# 启动后台守护线程
threading.Thread(target=background_agentboxd_listener, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "4000")))