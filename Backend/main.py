
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from agentboxd import get_emails, reply_to_email
from ai_service import generate_reply

load_dotenv()

app = FastAPI(title="Founders-Only API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3001",
        "http://localhost:3001",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

class ReplyRequest(BaseModel):
    email_id: str
    identity: dict
    mode: str = "menace"

class SendRequest(BaseModel):
    email_id: str
    reply: str = Field(min_length=1)
    confirmed: bool = False

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/emails")
def emails():
    try:
        return {"emails": get_emails()}
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve emails"
        )

@app.post("/api/generate-reply")
def generate(request: ReplyRequest):
    try:
        emails_list = get_emails()
        email = next(
            (e for e in emails_list
             if e.get("id") == request.email_id),
            None
        )

        if email is None:
            raise HTTPException(404, "Email not found")

        content = (
            f"Subject: {email.get('subject', '')}\n"
            f"Body: {email.get('text', '')}"
        )

        reply = generate_reply(
            content,
            request.identity,
            request.mode
        )
        return {"reply": reply}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="AI generation failed"
        )

@app.post("/api/send-reply")
def send(request: SendRequest):
    if not request.confirmed:
        raise HTTPException(
            status_code=400,
            detail="User confirmation required"
        )

    try:
        result = reply_to_email(
            request.email_id, request.reply
        )
        return {"result": result}
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not send reply"
        )
