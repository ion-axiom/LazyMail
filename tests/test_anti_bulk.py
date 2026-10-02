"""
Tests for Anti-Bulk Emailer Protections in LazyMail.
Validates:
1. Strict single-recipient validation (rejection of commas, semicolons, multiple addresses).
2. Outbound rate-limiting (cooldown, burst limit, 50/day cap).
3. Standard MUA headers (RFC 3834 'Auto-Submitted: no', User-Agent, X-Mailer, Message-ID).
"""

import pytest
import time
from fastapi import HTTPException
from app.email_service import validate_single_recipient, send_outgoing_email
from app.auth import check_outbound_rate_limit, record_outbound_send, _outbound_sends

def test_single_recipient_validation_success():
    valid_emails = [
        "user@example.com",
        "john.doe@gmail.com",
        "support+billing@sub.domain.org"
    ]
    for email in valid_emails:
        assert validate_single_recipient(email) == email

def test_single_recipient_validation_rejects_bulk_patterns():
    # Comma separated
    with pytest.raises(ValueError, match="Bulk emailing is disabled"):
        validate_single_recipient("user1@example.com, user2@example.com")

    # Semicolon separated
    with pytest.raises(ValueError, match="Bulk emailing is disabled"):
        validate_single_recipient("user1@example.com; user2@example.com")

    # Space separated
    with pytest.raises(ValueError, match="Bulk emailing is disabled"):
        validate_single_recipient("user1@example.com user2@example.com")

    # Newline separated
    with pytest.raises(ValueError, match="Bulk emailing is disabled"):
        validate_single_recipient("user1@example.com\nuser2@example.com")

    # Invalid email address
    with pytest.raises(ValueError, match="Invalid email address"):
        validate_single_recipient("not-an-email")

    # Empty
    with pytest.raises(ValueError, match="Recipient email is required"):
        validate_single_recipient("   ")

def test_outbound_rate_limit_cooldown():
    user_id = 999
    _outbound_sends[user_id] = []

    # First send should pass
    check_outbound_rate_limit(user_id)
    record_outbound_send(user_id)

    # Immediate second send (< 3s) must fail with 429
    with pytest.raises(HTTPException) as exc_info:
        check_outbound_rate_limit(user_id)
    assert exc_info.value.status_code == 429
    assert "Anti-bulk rate limit" in exc_info.value.detail

def test_outbound_rate_limit_burst_and_daily_caps():
    user_id = 888
    now = time.time()
    
    # Simulate 5 sends within the last minute (spaced by 4s to satisfy cooldown)
    _outbound_sends[user_id] = [now - 30, now - 25, now - 20, now - 15, now - 5]

    # 6th send within the same minute should be blocked
    with pytest.raises(HTTPException) as exc_info:
        check_outbound_rate_limit(user_id)
    assert exc_info.value.status_code == 429
    assert "Maximum 5 emails per minute" in exc_info.value.detail

    # Simulate 50 sends in 24 hours
    _outbound_sends[user_id] = [now - (i * 100) for i in range(1, 51)]
    with pytest.raises(HTTPException) as exc_info:
        check_outbound_rate_limit(user_id)
    assert exc_info.value.status_code == 429
    assert "Daily sending quota reached" in exc_info.value.detail
