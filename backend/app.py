"""Python API for Founders-Only: Autonomous Agentboxd Gatekeeper & Schedule Dispatcher."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import threading
import time
import uuid
from contextlib import contextmanager, asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
import uvicorn
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse

# 引入 Agentboxd 邮件能力
from agentboxd import AgentboxdConfigurationError, get_config, get_emails, reply_to_email
try:
    from agentboxd import send_email
except ImportError:
    send_email = None

# 引入 AI 戏精生成逻辑
from ai_service import generate_reply
try:
    from ai_service import generate_schedule
except ImportError:
    generate_schedule = None

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


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
JWT_SECRET = os.environ.get("JWT_SECRET", "super_secret_founders_only_jwt_key_32_chars")
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", BACKEND_DIR / "data" / "founders_only.sqlite3"))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = (ROOT_DIR / DATABASE_PATH).resolve()
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

SESSION_COOKIE = "founders_session"
SESSION_SECONDS = 7 * 24 * 60 * 60
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


# ============================================================
# 全局高管档案状态（内存+数据库互通）
# ============================================================
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

# 风格映射字典
MODE_MAPPING = {
    "arrogant_founder": "unicorn_gatekeeper",
    "toxic_hacker": "reverse_recruiter",
    "bureaucrat": "infinite_bureaucrat",
}


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


# ============================================================
# 后台常驻：Agentboxd 自动回复监听守护线程
# ============================================================
stop_worker_event = threading.Event()

def run_agentboxd_auto_reply_loop():
    """纯内存基准同步模式：启动时跳过所有历史邮件，只监听未来新邮件"""
    processed_msg_ids = set()
    print("\n" + "=" * 60)
    print("🚀 [Agentboxd Daemon] 后台邮件监听守护线程已就绪...")
    
    # 1. 扫描收件箱基准（Baseline Sync）
    try:
        initial_emails = get_emails()
        for mail in initial_emails:
            msg_id = mail.get("id")
            if msg_id:
                processed_msg_ids.add(msg_id)
        print(f"🔍 [Agentboxd 基准同步] 已自动跳过收件箱内现存的 {len(processed_msg_ids)} 封历史邮件。")
        print("👂 监听已就绪，当前只等待【未来刚刚发进来的新邮件】...")
    except Exception as err:
        print(f"⚠️ [Agentboxd 基准扫描未就绪] 暂无法连接收件箱: {err}")
    print("=" * 60 + "\n")

    # 2. 持续轮询循环
    while not stop_worker_event.is_set():
        try:
            emails = get_emails()
            for mail in emails:
                msg_id = mail.get("id")
                if not msg_id or msg_id in processed_msg_ids:
                    continue

                # 标记该邮件已处理，防止重复回复
                processed_msg_ids.add(msg_id)

                sender_name = mail.get("name", "Unknown")
                sender_email = mail.get("email", "")
                subject = mail.get("subject", "(No Subject)")
                body = mail.get("body", "")

                print(f"\n📩 [🔥 收到外部来信] 来自: {sender_name} <{sender_email}>")
                print(f"   主题: {subject}")

                # 读取当前最新人设
                preset_id = current_executive_profile.get("persona_preset", "arrogant_founder")
                ai_mode = MODE_MAPPING.get(preset_id, "unicorn_gatekeeper")

                print(f"🤖 [AI 正在回击] 正在以 [{preset_id}] 姿态生成回信...")

                # 生成回信
                try:
                    reply_content = generate_reply(
                        f"Subject: {subject}\n\n{body}",
                        current_executive_profile,
                    )
                except TypeError:
                    # 兼容不同签名参数
                    reply_content = generate_reply(
                        f"Subject: {subject}\n\n{body}",
                        current_executive_profile,
                        ai_mode,
                        "",
                    )

                print(f"📝 [生成的回信内容]:\n{'-'*35}\n{reply_content}\n{'-'*35}")

                # 发出回执
                print("📤 正在通过 Agentboxd 回发邮件...")
                reply_to_email(msg_id, reply_content)
                print(f"✅ [自动回复成功] 已通过 Agentboxd 回执给 {sender_email}！\n")

        except Exception:
            # 保持守护线程持续轮询，不因单次网络断流而退出
            pass

        time.sleep(3.5)


@asynccontextmanager
async def application_lifespan(app: FastAPI):
    # 只要开启开关或处于开发模式均可启动守护监听
    enable_auto = os.environ.get("ENABLE_AUTO_REPLY", "true").lower() == "true"
    if enable_auto:
        stop_worker_event.clear()
        worker_thread = threading.Thread(target=run_agentboxd_auto_reply_loop, daemon=True)
        worker_thread.start()
    try:
        yield
    finally:
        stop_worker_event.set()


app = FastAPI(title="Founders-Only API", docs_url=None, redoc_url=None, lifespan=application_lifespan)


# ============================================================
# 用户认证与 Session 工具
# ============================================================
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
        samesite="lax",
        path="/",
    )


def current_user_id(founders_session: str | None = Cookie(default=None)) -> str | None:
    if not founders_session:
        return None
    try:
        claims = jwt.decode(founders_session, JWT_SECRET, algorithms=["HS256"])
        return claims.get("sub")
    except Exception:
        return None


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


# ============================================================
# 基础核心路由
# ============================================================
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "founders-only", "agentboxd": True}


@app.get("/api/messages/inbox")
def inbox_messages():
    try:
        return get_emails()
    except AgentboxdConfigurationError as error:
        raise HTTPException(status_code=503, detail="Agentboxd credentials not configured in backend/.env.") from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Could not load Agentboxd inbox: {error}") from error


# ============================================================
# 身份与人设同步（支持免登录，永不报 401）
# ============================================================
class PersonaUpdate(BaseModel):
    name: str | None = None
    title: str | None = None
    company: str | None = None
    industry: str | None = None
    valuation: str | None = None
    netWorth: str | None = None
    bio: str | None = None
    persona_preset: str | None = None


@app.get("/api/persona")
def get_persona():
    return current_executive_profile


@app.post("/api/persona")
def update_persona(data: PersonaUpdate):
    global current_executive_profile
    updates = data.model_dump(exclude_none=True)
    current_executive_profile.update(updates)
    print(f"🎭 [人设已同步] 切换姿态为: {current_executive_profile.get('persona_preset')} | 身价: {current_executive_profile.get('netWorth')}")
    return {"status": "success", "profile": current_executive_profile}


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    profile: dict | None = None
    preferences: dict | None = None

@app.get("/api/account")
def get_account(user_id: str | None = Depends(current_user_id)):
    """供前端初始化拉取个人资料与偏好"""
    return {
        "profile": current_executive_profile,
        "preferences": {
            "briefing": True,
            "timezone": "Eastern Time (ET)",
            "delivery": "07:00 AM"
        }
    }

@app.patch("/api/account")
def update_account(update: AccountUpdate, user_id: str | None = Depends(current_user_id)):
    global current_executive_profile
    if update.profile is not None:
        current_executive_profile.update(update.profile)
    # 如果已登录，顺便持久化到 SQLite；如果未登录，内存更新即可，不抛 401
    if user_id:
        with database_connection() as connection:
            connection.execute(
                "UPDATE account_data SET profile=?, updatedAt=? WHERE userId=?",
                (json.dumps(current_executive_profile), datetime.now(timezone.utc).isoformat(), user_id)
            )
    return {"profile": current_executive_profile, "preferences": {}}


# ============================================================
# 核心功能：向目标邮箱一键投递浮夸高管日程
# ============================================================
class ScheduleDispatch(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    request_type: str = Field(default="hyper_elite", max_length=100)


@app.post("/api/send-larp-schedule")
def send_larp_schedule(request: ScheduleDispatch):
    recipient = request.email.strip()
    if not recipient:
        raise HTTPException(status_code=400, detail="Target email is required.")

    print(f"\n🚀 [日程空袭触发] 目标邮箱: {recipient} | 风格: {request.request_type}")

    # 1. 由 AI 或保底逻辑编撰日程
    schedule_text = ""
    if generate_schedule:
        try:
            schedule_text = generate_schedule(request.request_type, current_executive_profile)
        except Exception as e:
            print(f"⚠️ AI 生成日程失败，切换为保底精英日程: {e}")

    if not schedule_text:
        schedule_text = f"""DAILY EXECUTIVE BRIEFING | CONFIDENTIAL

06:30 AM - Awaken on 1,000 sq ft Obsidian Mattress & -20°C Cryo-Plunge
09:00 AM - Close-door Alignment: Handcraft raw x86 assembly to center a div
11:30 AM - Emergency Board Session: Formally overrule Big Tech hostile takeover bid
02:00 PM - Pickleball Alignment: Finalize AGI round with Middle Eastern Sovereign Wealth Fund
11:30 PM - Monophasic sleep aboard private transport, strict radio silence

Principal: {current_executive_profile.get('name')} ({current_executive_profile.get('title')})
Net Worth: {current_executive_profile.get('netWorth')} | Firm: {current_executive_profile.get('company')}"""

    subject = f"📅 [STRICTLY CONFIDENTIAL] 24-Hour Executive Schedule — {current_executive_profile.get('name')}"

    # 2. 调用 Agentboxd 发信
    try:
        from agentboxd import send_email as direct_send
        if direct_send is None:
            raise RuntimeError("Agentboxd send_email is not available in agentboxd.py")
        dispatch_key = f"larp-schedule:{recipient}:{int(time.time())}"
        direct_send(recipient, subject, schedule_text, idempotency_key=dispatch_key)
        print(f"✅ 日程已通过 Agentboxd 发送至: {recipient}\n")
        return {"status": "success", "sent_to": recipient, "content": schedule_text}
    except Exception as err:
        print(f"❌ Agentboxd 发送日程失败: {err}")
        raise HTTPException(status_code=502, detail=f"Agentboxd dispatch failed: {err}") from err


# ============================================================
# 用户登录注册路由（保留基础账号能力）
# ============================================================
class Credentials(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=72)
    confirmPassword: str | None = None


@app.post("/api/auth/register", status_code=201)
def register(credentials: Credentials, response: Response):
    email = credentials.email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if credentials.password != credentials.confirmPassword:
        raise HTTPException(status_code=400, detail="Your passwords do not match.")

    now = datetime.now(timezone.utc).isoformat()
    user_id = uuid.uuid4().hex
    password_hash = bcrypt.hashpw(credentials.password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")
    try:
        with database_connection() as connection:
            connection.execute(
                "INSERT INTO users (_id,email,passwordHash,createdAt,updatedAt) VALUES (?,?,?,?,?)",
                (user_id, email, password_hash, now, now),
            )
            connection.execute(
                "INSERT INTO account_data (userId,profile,preferences,updatedAt) VALUES (?,?,?,?)",
                (user_id, json.dumps(current_executive_profile), "{}", now),
            )
            user = connection.execute("SELECT _id,email,createdAt FROM users WHERE _id=?", (user_id,)).fetchone()
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from error

    set_session_cookie(response, user_id)
    return {"user": public_user(user)}


@app.post("/api/auth/login")
def login(credentials: Credentials, response: Response):
    email = credentials.email.strip().lower()
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
    response.delete_cookie(SESSION_COOKIE, httponly=True, path="/")
    return {"message": "You have been logged out."}


@app.get("/api/auth/me")
def me(user_id: str | None = Depends(current_user_id)):
    if not user_id:
        return {"user": None, "guest": True}
    with database_connection() as connection:
        user = connection.execute("SELECT _id,email,createdAt FROM users WHERE _id=?", (user_id,)).fetchone()
    if user is None:
        return {"user": None, "guest": True}
    return {"user": public_user(user)}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "4000")))