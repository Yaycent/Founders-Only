import http.cookiejar
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from http.cookies import SimpleCookie
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORT = 4300 + secrets.randbelow(500)
BASE = f"http://127.0.0.1:{PORT}"


def request(path, method="GET", body=None, cookie=None):
    headers = {}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if cookie is not None:
        headers["Cookie"] = cookie
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=3)
    except urllib.error.HTTPError as error:
        response = error
    payload = json.loads(response.read().decode())
    raw_cookie = response.headers.get("Set-Cookie")
    session_cookie = None
    if raw_cookie:
        jar = SimpleCookie()
        jar.load(raw_cookie)
        if "founders_session" in jar:
            session_cookie = "founders_session=" + jar["founders_session"].value
    return response.status, payload, session_cookie, raw_cookie or ""


def main():
    temp_dir = tempfile.TemporaryDirectory(prefix="founders-auth-smoke-", ignore_cleanup_errors=True)
    db_path = Path(temp_dir.name) / "test.sqlite3"
    env = os.environ.copy()
    env.update({
        "PORT": str(PORT),
        "DATABASE_PATH": str(db_path),
        "JWT_SECRET": secrets.token_urlsafe(48),
        "NODE_ENV": "test",
    })
    server = subprocess.Popen(
        [sys.executable, str(ROOT / "backend" / "app.py")],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError("Python backend exited: " + (server.stdout.read() or ""))
            try:
                status, _, _, _ = request("/api/health")
                if status == 200:
                    break
            except (OSError, TimeoutError):
                time.sleep(0.1)
        else:
            raise RuntimeError("Python backend did not start: " + (server.stdout.read() or ""))

        suffix = f"{time.time_ns()}-{secrets.token_hex(3)}"
        first = {"email": f"first-{suffix}@example.test", "password": "Founders-Only-Test-Password-1"}
        status, _, _, _ = request("/api/auth/register", "POST", {**first, "confirmPassword": "different-password"})
        assert status == 400, "mismatched passwords must be rejected"

        status, data, cookie, set_cookie = request("/api/auth/register", "POST", {**first, "confirmPassword": first["password"]})
        assert status == 201, f"registration failed: {data}"
        assert cookie and "httponly" in set_cookie.lower(), "registration must set an HttpOnly session cookie"
        assert "passwordHash" not in data["user"]

        status, _, _, _ = request("/api/auth/register", "POST", {**first, "confirmPassword": first["password"]})
        assert status == 409, "duplicate email must be rejected"
        status, _, _, _ = request("/api/auth/login", "POST", {"email": first["email"], "password": "wrong-password"})
        assert status == 401, "invalid credentials must be rejected"

        status, login_data, first_cookie, _ = request("/api/auth/login", "POST", first)
        assert status == 200 and login_data["user"]["email"] == first["email"]
        status, _, _, _ = request("/api/auth/me", cookie=first_cookie)
        assert status == 200, "valid JWT must access protected identity endpoint"
        status, first_account, _, _ = request("/api/account", "PATCH", {"profile": {"name": "First Account"}}, first_cookie)
        assert status == 200 and first_account["profile"]["name"] == "First Account"

        second = {"email": f"second-{suffix}@example.test", "password": "Founders-Only-Test-Password-2"}
        status, _, second_cookie, _ = request("/api/auth/register", "POST", {**second, "confirmPassword": second["password"]})
        assert status == 201
        status, second_account, _, _ = request("/api/account", "PATCH", {"profile": {"name": "Second Account"}}, second_cookie)
        assert status == 200 and second_account["profile"]["name"] == "Second Account"
        status, first_read, _, _ = request("/api/account", cookie=first_cookie)
        assert status == 200 and first_read["profile"]["name"] == "First Account", "accounts must be isolated"

        status, _, cleared_cookie, _ = request("/api/auth/logout", "POST", cookie=first_cookie)
        assert status == 200
        status, _, _, _ = request("/api/account", cookie=cleared_cookie)
        assert status == 401, "logged-out cookie must not authorize protected API"
        status, _, _, _ = request("/api/account", cookie=second_cookie)
        assert status == 200, "logging out one account must not affect another account"

        with sqlite3.connect(db_path) as conn:
            rows = conn.execute("SELECT passwordHash FROM users").fetchall()
            columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        assert len(rows) == 2 and all(row[0].startswith("$2") for row in rows), "database must only contain bcrypt hashes"
        assert "password" not in columns, "plaintext password column must not exist"
        print("Auth smoke tests passed: Python backend, registration, validation, duplicate email, login, JWT protection, per-user data, logout, and bcrypt storage.")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
        temp_dir.cleanup()


if __name__ == "__main__":
    main()
