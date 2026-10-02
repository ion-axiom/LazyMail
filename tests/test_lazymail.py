import pytest
import os
import tempfile
from pathlib import Path

# Override DB path for tests
from app import config
test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
config.DB_PATH = Path(test_db.name)

from app.crypto_utils import hash_password, verify_password, encrypt_credential, decrypt_credential
from app.database import (
    init_db,
    create_user,
    get_user_by_username,
    save_email_config,
    get_email_config,
    upsert_received_email,
    get_received_emails,
    get_received_email_by_id,
    save_sent_email,
    get_sent_emails,
    purge_messages,
    get_stats
)
from app.email_service import decode_header_str, clean_snippet
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    original = config.DB_PATH
    config.DB_PATH = Path(test_db.name)
    init_db()
    yield
    config.DB_PATH = original
    try:
        if os.path.exists(test_db.name):
            os.remove(test_db.name)
    except Exception:
        pass

def test_crypto_password_hashing():
    pw = "SuperSecret123!"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_crypto_credential_encryption():
    secret_app_pw = "abcd efgh ijkl mnop"
    encrypted = encrypt_credential(secret_app_pw)
    assert encrypted != secret_app_pw
    decrypted = decrypt_credential(encrypted)
    assert decrypted == secret_app_pw

def test_user_creation_and_retrieval():
    hashed = hash_password("AdminPass2026")
    user_id = create_user("admin_test", hashed)
    assert user_id > 0

    user = get_user_by_username("admin_test")
    assert user is not None
    assert user["username"] == "admin_test"

def test_email_config_save_and_retrieve():
    enc_pw = encrypt_credential("gmail_app_pw_1234")
    save_email_config(
        email_address="testuser@gmail.com",
        encrypted_password=enc_pw,
        sender_name="Test User",
        imap_host="imap.gmail.com",
        imap_port=993,
        imap_use_ssl=1,
        smtp_host="smtp.gmail.com",
        smtp_port=465,
        smtp_use_ssl=1
    )

    cfg = get_email_config()
    assert cfg is not None
    assert cfg["email_address"] == "testuser@gmail.com"
    assert cfg["sender_name"] == "Test User"
    assert decrypt_credential(cfg["encrypted_password"]) == "gmail_app_pw_1234"

def test_sent_emails_cap_at_50():
    """Verify that sent emails in SQLite are strictly capped at max 50."""
    # Insert 55 sent emails
    for i in range(1, 56):
        save_sent_email(f"recipient{i}@example.com", f"Subject {i}", f"Message body {i}")

    sent = get_sent_emails(limit=100)
    assert len(sent) == 50
    # Oldest (1 through 5) should have been pruned, latest (55) present
    assert sent[0]["recipient"] == "recipient55@example.com"
    assert sent[0]["subject"] == "Subject 55"

def test_received_emails_storage_and_search():
    for i in range(1, 10):
        upsert_received_email({
            "message_id": f"<msg-{i}@example.com>",
            "sender": f"Sender {i}",
            "sender_email": f"sender{i}@example.com",
            "recipient": "me@example.com",
            "subject": f"Invoice #{i} for Services",
            "snippet": f"Here is the invoice number {i}...",
            "body_plain": f"Full body text for invoice {i}",
            "body_html": f"<p>Full body text for invoice {i}</p>",
            "received_at": f"2026-10-0{i % 9 + 1}T10:00:00"
        })

    emails = get_received_emails()
    assert len(emails) == 9

    # Test search query
    results = get_received_emails(query="Invoice #3")
    assert len(results) == 1
    assert results[0]["subject"] == "Invoice #3 for Services"

    # Test detail fetching & marking read
    detail = get_received_email_by_id(results[0]["id"])
    assert detail is not None
    assert detail["is_read"] == 1

def test_purge_messages_facility():
    stats_before = get_stats()
    assert stats_before["received_count"] > 0
    assert stats_before["sent_count"] > 0

    # Purge only sent messages
    res_sent = purge_messages("sent")
    assert res_sent["purged_sent"] == 50
    assert res_sent["purged_received"] == 0

    stats_after_sent = get_stats()
    assert stats_after_sent["sent_count"] == 0
    assert stats_after_sent["received_count"] > 0

    # Purge received messages
    res_recv = purge_messages("received")
    assert res_recv["purged_received"] == 9

    stats_final = get_stats()
    assert stats_final["sent_count"] == 0
    assert stats_final["received_count"] == 0

def test_header_decoding_and_snippet():
    assert decode_header_str("Hello World") == "Hello World"
    assert decode_header_str("=?utf-8?B?VGVzdCBTdWJqZWN0?=") == "Test Subject"
    snippet = clean_snippet("Line 1\n\nLine 2     Line 3 - Extra Words Here", max_chars=20)
    assert snippet == "Line 1 Line 2 Line 3..."

def test_fastapi_endpoints():
    client = TestClient(app)
    # Auth status
    res = client.get("/api/auth/status")
    assert res.status_code == 200
    data = res.json()
    assert "setup_required" in data
    assert data["app_version"] == "1.0.0"
    assert "Derek Richards" in data["app_author"]
    assert data["app_author_url"] == "https://derekr.co.uk"

def test_full_api_user_flow():
    client = TestClient(app)
    # 1. Setup new admin user if not exists or login
    status_res = client.get("/api/auth/status")
    if status_res.json()["setup_required"]:
        setup_res = client.post("/api/auth/setup", json={"username": "master_admin", "password": "StrongPassword123!"})
        assert setup_res.status_code == 200
    else:
        login_res = client.post("/api/auth/login", json={"username": "admin_test", "password": "AdminPass2026"})
        assert login_res.status_code == 200

    # 2. Config retrieval (authenticated)
    cfg_res = client.get("/api/config")
    assert cfg_res.status_code == 200
    assert "email_address" in cfg_res.json()

    # 3. Stats endpoint
    stats_res = client.get("/api/stats")
    assert stats_res.status_code == 200
    assert "received_count" in stats_res.json()
    assert stats_res.json()["max_sent_limit"] == 50

    # 4. Sent emails listing
    sent_res = client.get("/api/emails/sent")
    assert sent_res.status_code == 200
    assert "emails" in sent_res.json()

    # 5. Purge endpoint via API
    purge_res = client.post("/api/emails/purge", json={"target": "sent"})
    assert purge_res.status_code == 200
    assert "purged_sent" in purge_res.json()

def test_gmail_prefix_and_passcode_auto_population():
    import tempfile
    from pathlib import Path
    import app.config as cfg
    from app.database import init_db, get_email_config
    from app.crypto_utils import decrypt_credential

    # Use a separate test db to test isolated fresh setup
    fresh_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    original_db = cfg.DB_PATH
    cfg.DB_PATH = Path(fresh_db.name)
    init_db()

    try:
        client = TestClient(app)
        # 1. First run setup with username prefix and 16-character passcode
        username_prefix = "harrypotter12345"
        passcode = "abcd efgh ijkl mnop"

        setup_res = client.post("/api/auth/setup", json={
            "username": username_prefix,
            "password": passcode
        })
        assert setup_res.status_code == 200
        data = setup_res.json()
        assert data["email_address"] == "harrypotter12345@gmail.com"
        assert data["username"] == "harrypotter12345"

        # 2. Verify email_config is auto-populated in SQLite
        email_cfg = get_email_config()
        assert email_cfg is not None
        assert email_cfg["email_address"] == "harrypotter12345@gmail.com"
        assert decrypt_credential(email_cfg["encrypted_password"]) == "abcdefghijklmnop"
        assert email_cfg["imap_host"] == "imap.gmail.com"
        assert email_cfg["smtp_host"] == "smtp.gmail.com"

        # 3. Test login with username prefix and spaces in passcode
        login_res1 = client.post("/api/auth/login", json={
            "username": "harrypotter12345",
            "password": "abcd efgh ijkl mnop"
        })
        assert login_res1.status_code == 200

        # 4. Test login with full email address and passcode without spaces
        login_res2 = client.post("/api/auth/login", json={
            "username": "harrypotter12345@gmail.com",
            "password": "abcdefghijklmnop"
        })
        assert login_res2.status_code == 200
    finally:
        cfg.DB_PATH = original_db
        try:
            os.remove(fresh_db.name)
        except Exception:
            pass

def test_fifo_received_emails_capping_and_ordering():
    """Verify that received emails are strictly ordered by date & time (latest at top) and capped at 50 (FIFO)."""
    # Insert 60 emails with ascending dates and times
    for i in range(1, 61):
        day = (i % 28) + 1
        hour = (i % 24)
        minute = (i % 60)
        upsert_received_email({
            "message_id": f"<fifo-test-{i}@example.com>",
            "sender": f"Sender {i}",
            "sender_email": f"sender{i}@example.com",
            "recipient": "me@example.com",
            "subject": f"Chronological Email #{i}",
            "snippet": f"Snippet {i}",
            "body_plain": f"Body {i}",
            "body_html": f"<p>Body {i}</p>",
            "received_at": f"2026-09-{day:02d} {hour:02d}:{minute:02d}:00"
        })

    # Retrieve inbox messages
    inbox = get_received_emails(limit=100)

    # 1. Database is capped at max 50
    assert len(inbox) == 50

    # 2. Latest message by date & time is strictly at the top (index 0)
    for j in range(len(inbox) - 1):
        time_current = inbox[j]["received_at"]
        time_next = inbox[j + 1]["received_at"]
        assert time_current >= time_next, f"Message at index {j} ({time_current}) should be newer than {j+1} ({time_next})"


