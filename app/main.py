from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone, timedelta
import secrets
import urllib.parse
import httpx

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
    get_stats,
    upsert_google_user,
    save_google_tokens,
    get_google_tokens,
    delete_google_tokens,
    save_oauth_config,
    get_oauth_config,
    get_effective_oauth_config
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
from app.config import (
    BASE_DIR,
    MAX_SENT_EMAILS,
    MAX_INBOX_EMAILS,
    INBOX_DAYS_LIMIT,
    APP_VERSION,
    APP_AUTHOR,
    APP_AUTHOR_ALIAS,
    APP_AUTHOR_URL
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="LazyMail Client",
    description=f"LazyMail Client v{APP_VERSION} by {APP_AUTHOR} ({APP_AUTHOR_URL})",
    version=APP_VERSION,
    contact={
        "name": APP_AUTHOR,
        "url": APP_AUTHOR_URL,
    },
    lifespan=lifespan
)

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

class OAuthConfigRequest(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = ""

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
    oauth_cfg = get_effective_oauth_config()
    google_tokens = get_google_tokens()
    has_oauth_tokens = bool(google_tokens and google_tokens.get("encrypted_refresh_token"))

    return {
        "app_name": "LazyMail",
        "app_version": APP_VERSION,
        "app_author": APP_AUTHOR,
        "app_author_alias": APP_AUTHOR_ALIAS,
        "app_author_url": APP_AUTHOR_URL,
        "setup_required": user_count == 0 and not has_oauth_tokens,
        "logged_in": current_user is not None,
        "username": current_user["username"] if current_user else None,
        "display_name": current_user.get("display_name") if current_user else None,
        "avatar_url": current_user.get("avatar_url") if current_user else None,
        "has_email_config": (cfg is not None and bool(cfg.get("email_address"))) or has_oauth_tokens,
        "configured_email": cfg.get("email_address") if cfg else (current_user.get("email") if current_user else None),
        "oauth_configured": bool(oauth_cfg["client_id"] and oauth_cfg["client_secret"]),
        "is_google_authenticated": has_oauth_tokens
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

# --- Google OAuth 2.0 APIs ---

@app.get("/api/auth/google/config")
async def get_google_oauth_config_endpoint():
    cfg = get_effective_oauth_config()
    return {
        "is_configured": bool(cfg["client_id"] and cfg["client_secret"]),
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"]
    }

@app.post("/api/auth/google/config")
async def save_google_oauth_config_endpoint(req: OAuthConfigRequest, request: Request):
    save_oauth_config(req.client_id, req.client_secret, req.redirect_uri or "")
    return {"message": "Google OAuth configuration saved successfully."}

@app.get("/api/auth/google/login")
async def google_login(request: Request):
    cfg = get_effective_oauth_config()
    client_id = cfg["client_id"]
    if not client_id:
        return RedirectResponse(url="/?error=oauth_not_configured")

    redirect_uri = cfg["redirect_uri"]
    if not redirect_uri:
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        host = request.headers.get("x-forwarded-host") or request.url.netloc
        redirect_uri = f"{proto}://{host}/api/auth/google/callback"

    state = secrets.token_urlsafe(32)
    scopes = (
        "openid "
        "https://www.googleapis.com/auth/userinfo.email "
        "https://www.googleapis.com/auth/userinfo.profile "
        "https://www.googleapis.com/auth/gmail.send "
        "https://www.googleapis.com/auth/gmail.readonly"
    )

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scopes,
        "access_type": "offline",
        "prompt": "consent",
        "state": state
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    response = RedirectResponse(url=auth_url, status_code=303)
    response.set_cookie(
        key="lazymail_oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        max_age=600,
        path="/"
    )
    return response

@app.get("/api/auth/google/callback")
async def google_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    if error:
        return RedirectResponse(url=f"/?error={urllib.parse.quote(error)}")

    stored_state = request.cookies.get("lazymail_oauth_state")
    if not state or not stored_state or state != stored_state:
        return RedirectResponse(url="/?error=invalid_state")

    if not code:
        return RedirectResponse(url="/?error=missing_code")

    cfg = get_effective_oauth_config()
    client_id = cfg["client_id"]
    client_secret = cfg["client_secret"]
    redirect_uri = cfg["redirect_uri"]
    if not redirect_uri:
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        host = request.headers.get("x-forwarded-host") or request.url.netloc
        redirect_uri = f"{proto}://{host}/api/auth/google/callback"

    async with httpx.AsyncClient(timeout=20.0) as client:
        # 1. Exchange authorization code for tokens
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            }
        )
        if token_resp.status_code != 200:
            return RedirectResponse(url="/?error=token_exchange_failed")

        token_data = token_resp.json()
        access_token = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")
        expires_in = int(token_data.get("expires_in", 3600))
        expires_at_iso = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

        # 2. Fetch user profile from Google UserInfo endpoint
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_resp.status_code != 200:
            return RedirectResponse(url="/?error=userinfo_failed")

        userinfo = userinfo_resp.json()
        google_id = userinfo.get("sub", "")
        email_addr = userinfo.get("email", "")
        display_name = userinfo.get("name") or email_addr.split("@")[0]
        avatar_url = userinfo.get("picture", "")

        # 3. Upsert user in database
        user_id = upsert_google_user(google_id, email_addr, display_name, avatar_url)

        # 4. Encrypt and save refresh token if provided
        encrypted_rt = encrypt_credential(refresh_token) if refresh_token else ""
        save_google_tokens(user_id, encrypted_rt, access_token, expires_at_iso)

        # 5. Automatically populate active email_address and sender_name in email_config
        existing_cfg = get_email_config()
        enc_pw = existing_cfg.get("encrypted_password") if existing_cfg else ""
        save_email_config(
            email_address=email_addr,
            encrypted_password=enc_pw or encrypt_credential("oauth_managed"),
            sender_name=display_name,
            imap_host="imap.gmail.com",
            imap_port=993,
            imap_use_ssl=1,
            smtp_host="smtp.gmail.com",
            smtp_port=465,
            smtp_use_ssl=1
        )

        # 6. Issue user session cookie
        session_token = create_user_session(user_id)
        redirect = RedirectResponse(url="/", status_code=303)
        redirect.set_cookie(
            key="lazymail_session",
            value=session_token,
            httponly=True,
            samesite="lax",
            max_age=86400,
            path="/"
        )
        redirect.delete_cookie(key="lazymail_oauth_state", path="/")
        return redirect

@app.post("/api/auth/google/disconnect")
async def google_disconnect(user: dict = Depends(get_current_user)):
    delete_google_tokens()
    return {"success": True, "message": "Google Account disconnected successfully."}

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
    google_tokens = get_google_tokens()
    if google_tokens and google_tokens.get("encrypted_refresh_token"):
        # Test connection via Google REST API
        try:
            from app.email_service import get_valid_google_access_token
            access_token = get_valid_google_access_token()
            if not access_token:
                return {
                    "success": False,
                    "imap_ok": False,
                    "smtp_ok": False,
                    "imap_message": "Google OAuth token not available",
                    "smtp_message": "Please reconnect your Google account"
                }
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if r.status_code == 200:
                    profile = r.json()
                    email_addr = profile.get("emailAddress", "Google Account")
                    return {
                        "success": True,
                        "imap_ok": True,
                        "smtp_ok": True,
                        "imap_message": f"Gmail REST API Bağlantısı Başarılı ({email_addr})",
                        "smtp_message": "Gmail REST API Gönderim Hazır (Kota Aktif)"
                    }
                else:
                    return {
                        "success": False,
                        "imap_ok": False,
                        "smtp_ok": False,
                        "imap_message": f"Google API Hatası: {r.status_code}",
                        "smtp_message": r.text
                    }
        except Exception as e:
            return {
                "success": False,
                "imap_ok": False,
                "smtp_ok": False,
                "imap_message": f"Google API Test Hatası: {e}",
                "smtp_message": str(e)
            }

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
