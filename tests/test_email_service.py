import pytest
import smtplib
from unittest.mock import MagicMock, patch

from app.email_service import (
    _perform_smtp_login,
    _create_smtp_connection,
    send_outgoing_email,
    test_credentials as check_test_credentials,
    sync_inbox_from_imap,
)
from app.database import save_email_config
from app.crypto_utils import encrypt_credential


def test_perform_smtp_login_auth_error():
    mock_server = MagicMock()
    mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"5.7.8 BadCredentials")

    with pytest.raises(RuntimeError) as exc_info:
        _perform_smtp_login(mock_server, "user@gmail.com", "bad_passcode")

    assert "535 Bad Credentials" in str(exc_info.value)
    assert "https://myaccount.google.com/apppasswords" in str(exc_info.value)


def test_perform_smtp_login_server_disconnected():
    mock_server = MagicMock()
    mock_server.login.side_effect = smtplib.SMTPServerDisconnected("Connection unexpectedly closed")

    with pytest.raises(RuntimeError) as exc_info:
        _perform_smtp_login(mock_server, "user@gmail.com", "bad_passcode")

    assert "535 Bad Credentials" in str(exc_info.value)
    assert "Google closed the connection during login" in str(exc_info.value)
    assert "https://myaccount.google.com/apppasswords" in str(exc_info.value)


def test_test_credentials_diagnostics():
    with patch("app.email_service.get_imap_connection") as mock_imap_get, \
         patch("app.email_service._create_smtp_connection") as mock_smtp_conn:

        mock_imap = MagicMock()
        mock_imap.login.side_effect = Exception("[AUTHENTICATIONFAILED] Invalid credentials")
        mock_imap_get.return_value = mock_imap

        mock_smtp = MagicMock()
        mock_smtp.__enter__.return_value = mock_smtp
        mock_smtp.login.side_effect = smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
        mock_smtp_conn.return_value = mock_smtp

        res = check_test_credentials("user@gmail.com", "bad_passcode")

        assert res["success"] is False
        assert res["imap_ok"] is False
        assert res["smtp_ok"] is False
        assert "Google rejected your username or App Password" in res["imap_message"]
        assert "535 Bad Credentials" in res["smtp_message"]


def test_send_outgoing_email_auth_failure():
    save_email_config(
        email_address="sender@gmail.com",
        encrypted_password=encrypt_credential("abcd efgh ijkl mnop"),
        sender_name="Sender",
        imap_host="imap.gmail.com",
        imap_port=993,
        imap_use_ssl=1,
        smtp_host="smtp.gmail.com",
        smtp_port=465,
        smtp_use_ssl=1,
    )

    with patch("app.email_service._create_smtp_connection") as mock_conn:
        mock_smtp = MagicMock()
        mock_smtp.__enter__.return_value = mock_smtp
        mock_smtp.login.side_effect = smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
        mock_conn.return_value = mock_smtp

        with pytest.raises(RuntimeError) as exc_info:
            send_outgoing_email("recipient@example.com", "Test Subject", "Test Body")

        assert "535 Bad Credentials" in str(exc_info.value)
