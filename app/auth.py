import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends
from app.config import SESSION_EXPIRE_HOURS
from app.database import (
    save_session,
    get_session,
    delete_session,
    cleanup_expired_sessions,
    get_user_by_id,
    get_user_count
)

# In-memory simple rate-limiting for failed login attempts (ip -> [timestamps])
_login_failures: Dict[str, list] = {}

# In-memory outbound rate-limiting for email sends (user_id -> [timestamps])
# Enforces human sending cadence and stops bulk/spam tooling:
# - Minimum 3 seconds cooldown between consecutive sends
# - Maximum 5 emails per minute
# - Maximum 50 emails per 24 hours (matching the 50 sent messages capacity)
_outbound_sends: Dict[int, list] = {}

def record_failed_login(client_ip: str):
    now = time.time()
    attempts = _login_failures.get(client_ip, [])
    # Keep attempts from last 5 minutes
    attempts = [t for t in attempts if now - t < 300]
    attempts.append(now)
    _login_failures[client_ip] = attempts

def check_login_rate_limit(client_ip: str):
    now = time.time()
    attempts = _login_failures.get(client_ip, [])
    recent_attempts = [t for t in attempts if now - t < 300]
    if len(recent_attempts) >= 5:
        wait_seconds = int(300 - (now - recent_attempts[0]))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please wait {wait_seconds} seconds."
        )

def reset_failed_logins(client_ip: str):
    if client_ip in _login_failures:
        del _login_failures[client_ip]

def check_outbound_rate_limit(user_id: int):
    """
    Enforces anti-bulk sending rules:
    1. At least 3 seconds between consecutive emails (human interaction pace).
    2. Max 5 emails per minute.
    3. Max 50 emails per day (matches personal mailbox sent limit).
    """
    now = time.time()
    history = _outbound_sends.get(user_id, [])
    # Retain events in rolling 24-hour window
    recent_24h = [t for t in history if now - t < 86400]
    _outbound_sends[user_id] = recent_24h

    # 1. Human cooldown check (3s)
    if recent_24h:
        elapsed = now - recent_24h[-1]
        if elapsed < 3.0:
            remaining = int(3.0 - elapsed) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Anti-bulk rate limit: Please wait {remaining} second(s) before sending another email."
            )

    # 2. Burst limit check (5/min)
    recent_1m = [t for t in recent_24h if now - t < 60]
    if len(recent_1m) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Anti-bulk rate limit exceeded: Maximum 5 emails per minute allowed for personal use."
        )

    # 3. Daily quota check (50/day)
    if len(recent_24h) >= 50:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily sending quota reached (50 emails/day). Bulk mailing is prohibited."
        )

def record_outbound_send(user_id: int):
    now = time.time()
    history = _outbound_sends.get(user_id, [])
    history = [t for t in history if now - t < 86400]
    history.append(now)
    _outbound_sends[user_id] = history

def create_user_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS)
    save_session(token, user_id, expires_at)
    return token

def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    cleanup_expired_sessions()
    token = request.cookies.get("lazymail_session")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
    
    if not token:
        return None

    session = get_session(token)
    if not session:
        return None
    return get_user_by_id(session["user_id"])

def get_current_user(request: Request) -> Dict[str, Any]:
    user = get_current_user_optional(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in."
        )
    return user
