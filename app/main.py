from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from pathlib import Path

from app.database import (
    init_db,
    get_user_count,
    get_user_by_username,
    create_user,
    update_user_password,
    update_user_last_login,
    get_email_config,
    save_email_config,
    get_received_emails,
    get_received_email_by_id,
    get_sent_emails,
    get_sent_email_by_id,
    purge_messages,
    get_stats
)
from app.crypto_utils import hash_password, verify_password, encrypt_credential, decrypt_credential, normalize_passcode
from app.auth import (
    create_user_session,
    delete_session,
    get_current_user,
    get_current_user_optional,
    check_login_rate_limit,
    record_failed_login,
    reset_failed_logins,
    check_outbound_rate_limit,
    record_outbound_send
)
from app.email_service import (
    sync_inbox_from_imap,
    send_outgoing_email,
    test_credentials,
    validate_single_recipient
)
from app.config import BASE_DIR, MAX_SENT_EMAILS, MAX_INBOX_EMAILS, INBOX_DAYS_LIMIT

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="LazyMail Client", version="1.0.0", lifespan=lifespan)

# Static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Pydantic Schemas
class SetupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)

class LoginRequest(BaseModel):
    username: str
    password: str

class EmailConfigRequest(BaseModel):
    email_address: str
    password: Optional[str] = None
    sender_name: Optional[str] = ""
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_use_ssl: bool = True
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_use_ssl: bool = True

class TestConfigRequest(BaseModel):
    email_address: Optional[str] = None
    password: Optional[str] = None
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_use_ssl: bool = True
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_use_ssl: bool = True

class SendEmailRequest(BaseModel):
    recipient: str
    subject: str
    message: str

class PurgeRequest(BaseModel):
    target: str = Field(..., pattern="^(sent|received|all)$")

# --- Web UI Routes ---

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = BASE_DIR / "templates" / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend template not found")
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))

# --- Auth APIs ---

@app.get("/api/auth/status")
async def auth_status(request: Request):
    user_count = get_user_count()
    current_user = get_current_user_optional(request)
    cfg = get_email_config()
    return {
        "setup_required": user_count == 0,
        "logged_in": current_user is not None,
        "username": current_user["username"] if current_user else None,
        "has_email_config": cfg is not None and bool(cfg.get("email_address")),
        "configured_email": cfg.get("email_address") if cfg else None
    }

@app.post("/api/auth/setup")
async def setup_admin(req: SetupRequest, response: Response):
    if get_user_count() > 0:
        raise HTTPException(status_code=400, detail="Setup has already been completed.")
    
    raw_user = req.username.strip()
    raw_pass = req.password.strip()

    if "@" in raw_user:
        username = raw_user.split("@")[0].lower()
        email_address = raw_user.lower()
    else:
        username = raw_user.lower()
        email_address = f"{username}@gmail.com"

    clean_pass = normalize_passcode(raw_pass)
    hashed = hash_password(clean_pass)
    user_id = create_user(username, hashed)
    token = create_user_session(user_id)

    # Automatically populate Gmail IMAP & SMTP account details in SQLite
    encrypted_pw = encrypt_credential(clean_pass)
    save_email_config(
        email_address=email_address,
        encrypted_password=encrypted_pw,
        sender_name=username,
        imap_host="imap.gmail.com",
        imap_port=993,
        imap_use_ssl=1,
        smtp_host="smtp.gmail.com",
        smtp_port=465,
        smtp_use_ssl=1
    )

    response.set_cookie(
        key="lazymail_session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,
        path="/"
    )
    return {
        "message": "Account created and Gmail connection configured successfully!",
        "username": username,
        "email_address": email_address,
        "token": token
    }

@app.post("/api/auth/login")
async def login(req: LoginRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_login_rate_limit(client_ip)

    user = get_user_by_username(req.username.strip())
    if not user or not verify_password(req.password, user["password_hash"]):
        record_failed_login(client_ip)
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    reset_failed_logins(client_ip)
    update_user_last_login(user["id"])
    token = create_user_session(user["id"])

    response.set_cookie(
        key="lazymail_session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,
        path="/"
    )
    return {"message": "Login successful", "username": user["username"], "token": token}

@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("lazymail_session")
    if token:
        delete_session(token)
    response.delete_cookie(key="lazymail_session", path="/")
    return {"message": "Logged out successfully"}

# --- Settings & Email Configuration APIs ---

@app.get("/api/config")
async def get_config(user: dict = Depends(get_current_user)):
    cfg = get_email_config()
    if not cfg:
        return {
            "is_configured": False,
            "email_address": "",
            "sender_name": "",
            "imap_host": "imap.gmail.com",
            "imap_port": 993,
            "imap_use_ssl": True,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 465,
            "smtp_use_ssl": True,
            "has_password": False
        }
    return {
        "is_configured": True,
        "email_address": cfg["email_address"],
        "sender_name": cfg.get("sender_name") or "",
        "imap_host": cfg["imap_host"],
        "imap_port": cfg["imap_port"],
        "imap_use_ssl": bool(cfg["imap_use_ssl"]),
        "smtp_host": cfg["smtp_host"],
        "smtp_port": cfg["smtp_port"],
        "smtp_use_ssl": bool(cfg["smtp_use_ssl"]),
        "has_password": bool(cfg.get("encrypted_password")),
        "updated_at": cfg.get("updated_at")
    }

@app.post("/api/config")
async def update_config(req: EmailConfigRequest, user: dict = Depends(get_current_user)):
    existing = get_email_config()
    encrypted_pw = ""
    if req.password:
        clean_pass = normalize_passcode(req.password)
        encrypted_pw = encrypt_credential(clean_pass)
        update_user_password(user["id"], hash_password(clean_pass))
    elif existing and existing.get("encrypted_password"):
        encrypted_pw = existing["encrypted_password"]
    else:
        raise HTTPException(status_code=400, detail="Password or App Password is required.")

    save_email_config(
        email_address=req.email_address.strip(),
        encrypted_password=encrypted_pw,
        sender_name=req.sender_name.strip() if req.sender_name else "",
        imap_host=req.imap_host.strip(),
        imap_port=req.imap_port,
        imap_use_ssl=1 if req.imap_use_ssl else 0,
        smtp_host=req.smtp_host.strip(),
        smtp_port=req.smtp_port,
        smtp_use_ssl=1 if req.smtp_use_ssl else 0
    )
    return {"message": "Configuration saved successfully."}

@app.post("/api/config/test")
async def test_email_config(req: TestConfigRequest, user: dict = Depends(get_current_user)):
    existing = get_email_config()
    target_email = (req.email_address or "").strip()
    target_pass = (req.password or "").strip()

    if not target_email and existing:
        target_email = existing.get("email_address", "")
    if not target_pass and existing:
        target_pass = decrypt_credential(existing.get("encrypted_password", ""))

    if not target_email or not target_pass:
        raise HTTPException(status_code=400, detail="Email and password/app password are required to test connection.")

    res = test_credentials(
        email_address=target_email,
        raw_password=target_pass,
        imap_host=req.imap_host,
        imap_port=req.imap_port,
        imap_use_ssl=1 if req.imap_use_ssl else 0,
        smtp_host=req.smtp_host,
        smtp_port=req.smtp_port,
        smtp_use_ssl=1 if req.smtp_use_ssl else 0
    )
    return res

# --- Inbox / IMAP Sync APIs ---

@app.get("/api/emails/inbox")
async def list_inbox_emails(q: Optional[str] = None, user: dict = Depends(get_current_user)):
    emails = get_received_emails(query=q, limit=MAX_INBOX_EMAILS)
    return {"emails": emails, "count": len(emails), "limit": MAX_INBOX_EMAILS}

@app.get("/api/emails/inbox/{email_id}")
async def get_inbox_email(email_id: int, user: dict = Depends(get_current_user)):
    email_item = get_received_email_by_id(email_id)
    if not email_item:
        raise HTTPException(status_code=404, detail="Email not found.")
    return email_item

@app.post("/api/emails/sync")
async def sync_emails(user: dict = Depends(get_current_user)):
    try:
        result = sync_inbox_from_imap(days=INBOX_DAYS_LIMIT, max_emails=MAX_INBOX_EMAILS)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Sent Emails APIs ---

@app.get("/api/emails/sent")
async def list_sent_emails(q: Optional[str] = None, user: dict = Depends(get_current_user)):
    emails = get_sent_emails(query=q, limit=MAX_SENT_EMAILS)
    return {"emails": emails, "count": len(emails), "limit": MAX_SENT_EMAILS}

@app.get("/api/emails/sent/{email_id}")
async def get_sent_email_detail(email_id: int, user: dict = Depends(get_current_user)):
    email_item = get_sent_email_by_id(email_id)
    if not email_item:
        raise HTTPException(status_code=404, detail="Sent email not found.")
    return email_item

@app.post("/api/emails/send")
async def send_email_endpoint(req: SendEmailRequest, user: dict = Depends(get_current_user)):
    # 1. Anti-bulk: Enforce personal human cadence rate limit
    check_outbound_rate_limit(user["id"])

    # 2. Anti-bulk: Validate strictly single recipient
    try:
        clean_recipient = validate_single_recipient(req.recipient)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    if not req.subject.strip():
        raise HTTPException(status_code=400, detail="Subject is required.")
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message body cannot be empty.")

    try:
        sent_info = send_outgoing_email(
            recipient=clean_recipient,
            subject=req.subject,
            body=req.message
        )
        # Record send timestamp for rate limiting
        record_outbound_send(user["id"])
        return {"message": "Email sent successfully!", "data": sent_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Purge & Database Maintenance ---

@app.post("/api/emails/purge")
async def purge_emails_endpoint(req: PurgeRequest, user: dict = Depends(get_current_user)):
    res = purge_messages(req.target)
    return {
        "message": f"Purge completed successfully for target '{req.target}'.",
        "purged_sent": res["purged_sent"],
        "purged_received": res["purged_received"]
    }

@app.get("/api/stats")
async def email_stats(user: dict = Depends(get_current_user)):
    return get_stats()
