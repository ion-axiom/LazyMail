import os
import time
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.database import (
    init_db,
    save_oauth_config,
    get_oauth_config,
    get_effective_oauth_config,
    upsert_google_user,
    save_google_tokens,
    get_google_tokens,
    update_google_access_token,
    delete_google_tokens,
    get_user_by_id,
    create_user,
    save_email_config,
    get_email_config,
)
from app.auth import create_user_session
from app.crypto_utils import encrypt_credential, decrypt_credential
from app.email_service import (
    get_valid_google_access_token,
    _send_via_gmail_api,
    _sync_inbox_via_gmail_api,
    send_outgoing_email,
    sync_inbox_from_imap,
)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_oauth.db"
    monkeypatch.setattr(config, "DB_PATH", test_db)
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(config, "GOOGLE_CLIENT_SECRET", "")
    monkeypatch.setattr(config, "GOOGLE_REDIRECT_URI", "")
    init_db()
    client.cookies.clear()
    return str(test_db)


client = TestClient(app)


def test_oauth_db_config():
    # Initially empty
    cfg = get_oauth_config()
    assert cfg is None

    # Save config
    save_oauth_config("test-client-id.apps.googleusercontent.com", "test-secret", "https://lazymail.derekr.co.uk/api/auth/google/callback")
    cfg = get_oauth_config()
    assert cfg is not None
    assert cfg["client_id"] == "test-client-id.apps.googleusercontent.com"
    assert cfg["client_secret"] == "test-secret"
    assert cfg["redirect_uri"] == "https://lazymail.derekr.co.uk/api/auth/google/callback"

    # Effective config priority
    eff = get_effective_oauth_config()
    assert eff["client_id"] == "test-client-id.apps.googleusercontent.com"
    assert eff["client_secret"] == "test-secret"


def test_upsert_google_user_and_tokens():
    # 1. Create a user via upsert_google_user
    user_id = upsert_google_user(
        google_id="gid_123456",
        email="testuser@gmail.com",
        display_name="Test User",
        avatar_url="https://lh3.googleusercontent.com/a/photo.jpg"
    )
    assert user_id is not None
    user = get_user_by_id(user_id)
    assert user["username"] == "testuser"
    assert user["google_id"] == "gid_123456"
    assert user["display_name"] == "Test User"
    assert user["avatar_url"] == "https://lh3.googleusercontent.com/a/photo.jpg"

    # 2. Re-upserting same google_id updates profile without creating duplicate
    user_id2 = upsert_google_user(
        google_id="gid_123456",
        email="testuser@gmail.com",
        display_name="Test User Updated",
        avatar_url="https://lh3.googleusercontent.com/a/photo2.jpg"
    )
    assert user_id2 == user_id
    user2 = get_user_by_id(user_id)
    assert user2["display_name"] == "Test User Updated"
    assert user2["avatar_url"] == "https://lh3.googleusercontent.com/a/photo2.jpg"

    # 3. Save google tokens
    encrypted_rt = encrypt_credential("mock_refresh_token_12345")
    future_iso = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    save_google_tokens(
        user_id=user_id,
        encrypted_refresh_token=encrypted_rt,
        access_token="initial_access_token",
        expires_at_iso=future_iso
    )

    tokens = get_google_tokens()
    assert tokens is not None
    assert decrypt_credential(tokens["encrypted_refresh_token"]) == "mock_refresh_token_12345"
    assert tokens["access_token"] == "initial_access_token"

    # 4. Update access token
    new_future_iso = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    update_google_access_token("refreshed_access_token", new_future_iso)
    tokens_updated = get_google_tokens()
    assert tokens_updated["access_token"] == "refreshed_access_token"

    # 5. Delete tokens
    delete_google_tokens()
    assert get_google_tokens() is None


def test_get_valid_google_access_token_cached_and_refreshed():
    user_id = upsert_google_user("gid_token_test", "tok@gmail.com", "Tok Test", "")
    encrypted_rt = encrypt_credential("refresh_abc_123")

    # Future expiration: should return cached token without HTTP request
    future_iso = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    save_google_tokens(user_id, encrypted_rt, "valid_cached_token", future_iso)

    token = get_valid_google_access_token()
    assert token == "valid_cached_token"

    # Expired token: should call Google token refresh endpoint
    past_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    update_google_access_token("expired_token", past_iso)

    # Configure OAuth client credentials
    save_oauth_config("client-id-xyz", "client-secret-xyz", "https://lazymail.derekr.co.uk/api/auth/google/callback")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "newly_refreshed_token_456",
        "expires_in": 3600
    }
    mock_response.headers = {"content-type": "application/json"}

    with patch("httpx.post", return_value=mock_response) as mock_post:
        refreshed = get_valid_google_access_token()
        assert refreshed == "newly_refreshed_token_456"
        assert mock_post.called
        args, kwargs = mock_post.call_args
        assert args[0] == "https://oauth2.googleapis.com/token"
        assert kwargs["data"]["grant_type"] == "refresh_token"
        assert kwargs["data"]["client_id"] == "client-id-xyz"
        assert kwargs["data"]["client_secret"] == "client-secret-xyz"


def test_send_via_gmail_api_success():
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    msg = MIMEMultipart()
    msg["Subject"] = "OAuth Test"
    msg["From"] = "me@gmail.com"
    msg["To"] = "friend@example.com"
    msg.attach(MIMEText("Hello from Gmail API!", "plain"))

    user_id = upsert_google_user("gid_send", "me@gmail.com", "Me", "")
    encrypted_rt = encrypt_credential("refresh_123")
    future_iso = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    save_google_tokens(user_id, encrypted_rt, "mock_access_token", future_iso)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "msg_12345", "threadId": "th_67890"}
    mock_resp.headers = {"content-type": "application/json"}

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        _send_via_gmail_api(msg, "friend@example.com")
        assert mock_post.called
        args, kwargs = mock_post.call_args
        assert args[0] == "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        assert kwargs["headers"]["Authorization"] == "Bearer mock_access_token"
        assert "raw" in kwargs["json"]


def test_send_outgoing_email_dispatches_to_gmail_api_when_authenticated():
    user_id = upsert_google_user("gid_send_test", "sender@gmail.com", "Sender", "")
    encrypted_rt = encrypt_credential("rt_123")
    future_iso = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    save_google_tokens(user_id, encrypted_rt, "valid_token_xyz", future_iso)

    with patch("app.email_service._send_via_gmail_api") as mock_send:
        mock_send.return_value = None
        result = send_outgoing_email(
            recipient="recipient@example.com",
            subject="Hello via Google API",
            body="Content"
        )
        assert result["status"] == "sent"
        assert mock_send.called


def test_api_auth_google_login_not_configured():
    # When no OAuth client id is configured:
    response = client.get("/api/auth/google/login", follow_redirects=False)
    assert response.status_code in (302, 303, 307)
    assert "error=oauth_not_configured" in response.headers["location"]


def test_api_auth_google_login_configured():
    save_oauth_config("google-client-id-abc", "google-secret-abc", "https://lazymail.derekr.co.uk/api/auth/google/callback")
    response = client.get("/api/auth/google/login", follow_redirects=False)
    assert response.status_code in (302, 303, 307)
    location = response.headers["location"]
    assert "accounts.google.com/o/oauth2/v2/auth" in location
    assert "google-client-id-abc" in location
    assert "gmail.send" in location
    assert "gmail.readonly" in location
    assert "access_type=offline" in location
    assert "lazymail_oauth_state" in response.cookies


def test_api_auth_google_callback_flow():
    import httpx
    from unittest.mock import AsyncMock

    save_oauth_config("client-id-123", "secret-123", "https://lazymail.derekr.co.uk/api/auth/google/callback")

    # Step 1: initiate login to get cookie state
    login_resp = client.get("/api/auth/google/login", follow_redirects=False)
    state = login_resp.cookies.get("lazymail_oauth_state")
    assert state is not None

    # Step 2: Mock Google token and userinfo responses
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.headers = {"content-type": "application/json"}
    mock_token_resp.json.return_value = {
        "access_token": "google_access_token_live",
        "refresh_token": "google_refresh_token_live",
        "expires_in": 3600,
        "token_type": "Bearer"
    }

    mock_userinfo_resp = MagicMock()
    mock_userinfo_resp.status_code = 200
    mock_userinfo_resp.headers = {"content-type": "application/json"}
    mock_userinfo_resp.json.return_value = {
        "sub": "google_sub_88888",
        "email": "derek@gmail.com",
        "name": "Derek Richards",
        "picture": "https://lh3.googleusercontent.com/a/derek.jpg"
    }

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_async_post, \
         patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_async_get:
        mock_async_post.return_value = mock_token_resp
        mock_async_get.return_value = mock_userinfo_resp

        client.cookies.set("lazymail_oauth_state", state)
        cb_resp = client.get(f"/api/auth/google/callback?code=mock_auth_code&state={state}", follow_redirects=False)
        assert cb_resp.status_code in (302, 303, 307)
        assert cb_resp.headers["location"] in ("/", "/?google_auth=success")
        assert "lazymail_session" in cb_resp.cookies

        # Status check using new session cookie
        session_cookie = cb_resp.cookies["lazymail_session"]
        status_resp = client.get("/api/auth/status", cookies={"lazymail_session": session_cookie})
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["logged_in"] is True
        assert data["is_google_authenticated"] is True
        assert data["display_name"] == "Derek Richards"
        assert data["configured_email"] == "derek@gmail.com"
        assert data["avatar_url"] == "https://lh3.googleusercontent.com/a/derek.jpg"


def test_api_auth_google_disconnect_endpoint():
    user_id = upsert_google_user("gid_disconnect", "disc@gmail.com", "Disconnect Test", "")
    encrypted_rt = encrypt_credential("rt_disc")
    future_iso = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    save_google_tokens(user_id, encrypted_rt, "token_disc", future_iso)

    # Login to create session
    session_token = create_user_session(user_id)

    disc_resp = client.post("/api/auth/google/disconnect", headers={"Authorization": f"Bearer {session_token}"})
    assert disc_resp.status_code == 200
    assert disc_resp.json()["success"] is True

    # Check tokens removed
    assert get_google_tokens() is None
