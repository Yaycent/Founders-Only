# Founders-Only

React/Vite frontend with a FastAPI backend, SQLite accounts, OpenAI reply drafts,
and Agentboxd inbox access. Start from `frontend/`; the root `src/` is a legacy demo.

## macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
cd frontend
npm ci
```

Configure `backend/.env` locally: JWT_SECRET (32+ random characters), OPENAI_API_KEY,
OPENAI_MODEL, AGENTBOXD_API_KEY, AGENTBOXD_INBOX_ID, AGENTBOXD_ALLOWED_EMAIL.
Never commit `.env` or the database. Register using AGENTBOXD_ALLOWED_EMAIL for inbox access.

Terminal 1, from project root:
```bash
.venv/bin/python backend/app.py
```
Terminal 2:
```bash
cd frontend
npm run dev
```
Open http://localhost:3001. The frontend proxies `/api` to http://127.0.0.1:4000.

## Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
cd frontend
npm ci
```
Terminal 1 (root): `.\.venv\Scripts\python.exe backend\app.py`
Terminal 2 (`frontend`): `npm run dev`

## Integration notes

Dashboard and Executive Identity persist the three new personas per account.
AI Reply Studio supports the saved persona plus the previous styles. Replies are
only sent after confirmation. Samples are labeled and cannot be sent.
Automatic replies are disabled by default; `ENABLE_AUTO_REPLY=true` explicitly
starts the worker using the configured inbox owner's saved profile. Do not enable
this while testing drafts. The standalone worker uses the same opt-in.
Schedule delivery is not connected: the provider module lacks `send_email`;
the endpoint reports this instead of claiming success.

Build: `cd frontend && npm run build`.
