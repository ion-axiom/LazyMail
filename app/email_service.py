import imaplib
import smtplib
import ssl
import socket
import email
import base64
import httpx
from email.header import decode_header, Header
from email.utils import parseaddr, parsedate_to_datetime, formataddr, make_msgid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
import html
import re

from app.database import (
    get_email_config,
    upsert_received_email,
    prune_received_emails,
    save_sent_email,
    get_google_tokens,
    update_google_access_token,
    get_effective_oauth_config
)
from app.crypto_utils import decrypt_credential
from app.config import MAX_INBOX_EMAILS, INBOX_DAYS_LIMIT

def decode_header_str(header_value: Optional[str]) -> str:
    """Decode RFC 2047 encoded email headers into clean unicode string."""
    if not header_value:
        return ""
    try:
        decoded_fragments = decode_header(header_value)
        parts = []
        for text, encoding in decoded_fragments:
            if isinstance(text, bytes):
                encoding = encoding or "utf-8"
                try:
                    parts.append(text.decode(encoding, errors="replace"))
                except Exception:
                    parts.append(text.decode("utf-8", errors="replace"))
            else:
                parts.append(str(text))
        return " ".join(parts).strip()
    except Exception:
        return str(header_value)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def validate_single_recipient(recipient: str) -> str:
    """
    Ensure the recipient is strictly a single valid email address.
    Rejects commas, semicolons, multiple addresses, BCC/CC lists, or newlines
    to prevent the application from ever being utilized for bulk or mass mailing.
    """
    if not recipient or not recipient.strip():
        raise ValueError("Recipient email is required.")

    clean = recipient.strip()
    # Reject multiple email separators or line breaks
    if any(sep in clean for sep in [",", ";", "\n", "\r", " "]):
        raise ValueError(
            "Bulk emailing is disabled: LazyMail is a personal email client and only permits a single recipient."
        )

    if clean.count("@") != 1 or not EMAIL_REGEX.match(clean):
        raise ValueError(f"Invalid email address: '{clean}'. Please enter a single valid email address.")

    return clean

def clean_snippet(text: str, max_chars: int = 150) -> str:
    """Extract a clean single-line snippet from email body."""
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) > max_chars:
        return cleaned[:max_chars].rstrip() + "..."
    return cleaned

def extract_body(msg: email.message.Message) -> Tuple[str, str]:
    """Extract plain text and HTML bodies from an email message."""
    plain_text = ""
    html_content = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                continue

            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                try:
                    decoded = payload.decode(charset, errors="replace")
                except Exception:
                    decoded = payload.decode("utf-8", errors="replace")

                if content_type == "text/plain" and not plain_text:
                    plain_text = decoded
                elif content_type == "text/html" and not html_content:
                    html_content = decoded
            except Exception:
                continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            if payload:
                try:
                    decoded = payload.decode(charset, errors="replace")
                except Exception:
                    decoded = payload.decode("utf-8", errors="replace")
                if msg.get_content_type() == "text/html":
                    html_content = decoded
                else:
                    plain_text = decoded
        except Exception:
            plain_text = ""

    if not plain_text and html_content:
        # Strip simple tags for plain text fallback
        plain_text = re.sub(r"<[^>]+>", " ", html_content)
        plain_text = html.unescape(plain_text)

    return plain_text.strip(), html_content.strip()

def get_imap_connection(config: Dict[str, Any], timeout: int = 15) -> imaplib.IMAP4:
    """Connect to IMAP server using SSL or plain connection."""
    host = config.get("imap_host", "imap.gmail.com")
    port = int(config.get("imap_port", 993))
    use_ssl = bool(config.get("imap_use_ssl", 1))

    if use_ssl:
        context = ssl.create_default_context()
        client = imaplib.IMAP4_SSL(host, port, ssl_context=context)
    else:
        client = imaplib.IMAP4(host, port)
    return client

def _create_smtp_connection(
    smtp_host: str,
    smtp_port: int,
    smtp_use_ssl: bool,
    timeout: int = 20
) -> smtplib.SMTP:
    """
    Connect to SMTP server with automatic fallback between port 465 (SSL) and port 587 (STARTTLS)
    for Gmail to ensure maximum connectivity resilience.
    """
    primary_is_ssl = (smtp_use_ssl and smtp_port == 465)
    try:
        if primary_is_ssl:
            context = ssl.create_default_context()
            return smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=timeout)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=timeout)
            if smtp_use_ssl:
                context = ssl.create_default_context()
                server.starttls(context=context)
            return server
    except (socket.error, OSError, smtplib.SMTPConnectError, TimeoutError) as conn_err:
        # Fallback between Gmail's ports (465 SSL <-> 587 STARTTLS) if primary connection fails
        if "gmail.com" in smtp_host.lower():
            fallback_port = 587 if smtp_port == 465 else 465
            try:
                if fallback_port == 465:
                    context = ssl.create_default_context()
                    return smtplib.SMTP_SSL(smtp_host, fallback_port, context=context, timeout=timeout)
                else:
                    fallback_server = smtplib.SMTP(smtp_host, fallback_port, timeout=timeout)
                    context = ssl.create_default_context()
                    fallback_server.starttls(context=context)
                    return fallback_server
            except Exception:
                pass
        raise conn_err

def _perform_smtp_login(server: smtplib.SMTP, email_address: str, raw_password: str) -> None:
    """
    Authenticate against SMTP server with comprehensive handling for Gmail 535 Bad Credentials
    and unexpected connection drops caused by rejected credentials.
    """
    try:
        server.login(email_address, raw_password)
    except smtplib.SMTPAuthenticationError as auth_err:
        raise RuntimeError(
            "Gmail Authentication Failed (535 Bad Credentials): Google rejected your username or App Password. "
            "Please make sure 2-Step Verification is active on your Google Account, generate a fresh 16-character "
            "App Password at https://myaccount.google.com/apppasswords, and update Settings."
        ) from auth_err
    except smtplib.SMTPServerDisconnected as disc_err:
        # Google drops the TCP socket immediately upon receiving invalid credentials.
        # Python's smtplib catches the 535 and tries fallback auth methods over the closed socket,
        # raising SMTPServerDisconnected('Connection unexpectedly closed').
        raise RuntimeError(
            "Gmail Authentication Failed (535 Bad Credentials): Google closed the connection during login. "
            "This happens when Google rejects your credentials or the App Password was revoked. "
            "Please verify 2-Step Verification is enabled and generate a fresh 16-character App Password at "
            "https://myaccount.google.com/apppasswords, then update Settings."
        ) from disc_err
    except Exception as login_err:
        err_str = str(login_err)
        if (
            "535" in err_str
            or "BadCredentials" in err_str
            or "Username and Password not accepted" in err_str
            or "Application-specific password required" in err_str
            or "AUTHENTICATIONFAILED" in err_str
        ):
            raise RuntimeError(
                "Gmail Authentication Failed (535 Bad Credentials): Google rejected your username or App Password. "
                "Please generate a fresh 16-character App Password at https://myaccount.google.com/apppasswords and update Settings."
            ) from login_err
        raise RuntimeError(f"SMTP Login Failed: {err_str}") from login_err

def test_credentials(
    email_address: str,
    raw_password: str,
    imap_host: str = "imap.gmail.com",
    imap_port: int = 993,
    imap_use_ssl: int = 1,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 465,
    smtp_use_ssl: int = 1
) -> Dict[str, Any]:
    """Test both IMAP and SMTP authentication with detailed diagnostics."""
    results = {
        "imap_ok": False,
        "smtp_ok": False,
        "imap_message": "",
        "smtp_message": "",
        "success": False
    }

    # 1. Test IMAP
    try:
        config = {
            "imap_host": imap_host,
            "imap_port": imap_port,
            "imap_use_ssl": imap_use_ssl
        }
        imap_client = get_imap_connection(config, timeout=12)
        try:
            imap_client.login(email_address, raw_password)
        except Exception as imap_login_err:
            err = str(imap_login_err)
            if "Application-specific password required" in err or "AUTHENTICATIONFAILED" in err or "Invalid credentials" in err:
                results["imap_message"] = (
                    "Authentication failed: Google rejected your username or App Password. "
                    "Ensure 2-Step Verification is enabled on your Google Account and generate a fresh 16-character "
                    "App Password at https://myaccount.google.com/apppasswords."
                )
            else:
                results["imap_message"] = f"IMAP Authentication Error: {err}"
            raise
        imap_client.select("INBOX", readonly=True)
        imap_client.logout()
        results["imap_ok"] = True
        results["imap_message"] = "IMAP connection and login succeeded."
    except Exception as e:
        if not results["imap_message"]:
            results["imap_message"] = f"IMAP Error: {e}"

    # 2. Test SMTP
    try:
        with _create_smtp_connection(smtp_host, smtp_port, bool(smtp_use_ssl), timeout=12) as smtp_client:
            try:
                _perform_smtp_login(smtp_client, email_address, raw_password)
                results["smtp_ok"] = True
                results["smtp_message"] = "SMTP connection and login succeeded."
            except RuntimeError as auth_e:
                results["smtp_message"] = str(auth_e)
    except Exception as e:
        if not results["smtp_message"]:
            results["smtp_message"] = f"SMTP Connection Error: {e}"

    results["success"] = results["imap_ok"] and results["smtp_ok"]
    return results

def get_valid_google_access_token() -> Optional[str]:
    """
    Retrieve a valid Google OAuth 2.0 access token.
    Automatically refreshes the token using the stored refresh token if expired.
    """
    tokens = get_google_tokens()
    if not tokens or not tokens.get("encrypted_refresh_token"):
        return None

    access_token = tokens.get("access_token")
    expires_at_str = tokens.get("access_token_expires_at")

    if access_token and expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at > datetime.now(timezone.utc) + timedelta(seconds=60):
                return access_token
        except Exception:
            pass

    raw_refresh_token = decrypt_credential(tokens["encrypted_refresh_token"])
    if not raw_refresh_token:
        raise ValueError("Failed to decrypt stored Google refresh token.")

    oauth_cfg = get_effective_oauth_config()
    client_id = oauth_cfg["client_id"]
    client_secret = oauth_cfg["client_secret"]
    if not client_id or not client_secret:
        raise ValueError("Google OAuth Client credentials are not configured.")

    try:
        resp = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": raw_refresh_token,
                "grant_type": "refresh_token"
            },
            timeout=15.0
        )
        if resp.status_code != 200:
            error_data = resp.json() if "application/json" in resp.headers.get("content-type", "") else {}
            err_msg = error_data.get("error_description") or error_data.get("error") or resp.text
            raise RuntimeError(f"Google Token Refresh Failed ({resp.status_code}): {err_msg}")

        data = resp.json()
        new_access_token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

        update_google_access_token(new_access_token, expires_at)
        return new_access_token
    except Exception as e:
        if isinstance(e, (RuntimeError, ValueError)):
            raise
        raise RuntimeError(f"Failed to refresh Google access token: {e}") from e

def _send_via_gmail_api(msg: MIMEMultipart, recipient: str) -> None:
    access_token = get_valid_google_access_token()
    if not access_token:
        raise RuntimeError("No valid Google access token available. Please sign in with Google.")

    raw_bytes = msg.as_bytes()
    raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")

    try:
        resp = httpx.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={"raw": raw_b64},
            timeout=25.0
        )
        if resp.status_code != 200:
            err_data = resp.json() if "application/json" in resp.headers.get("content-type", "") else {}
            err_msg = err_data.get("error", {}).get("message") or resp.text
            raise RuntimeError(f"Gmail API Send Error ({resp.status_code}): {err_msg}")
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"Failed to send email via Gmail API: {e}") from e

def _sync_inbox_via_gmail_api(days: int = INBOX_DAYS_LIMIT, max_emails: int = MAX_INBOX_EMAILS) -> Dict[str, Any]:
    access_token = get_valid_google_access_token()
    if not access_token:
        raise RuntimeError("No valid Google access token available. Please sign in with Google.")

    query = f"newer_than:{days}d"
    try:
        resp = httpx.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"maxResults": max_emails, "q": query},
            timeout=25.0
        )
        if resp.status_code != 200:
            err_data = resp.json() if "application/json" in resp.headers.get("content-type", "") else {}
            err_msg = err_data.get("error", {}).get("message") or resp.text
            raise RuntimeError(f"Gmail API Inbox Error ({resp.status_code}): {err_msg}")

        data = resp.json()
        messages_meta = data.get("messages", [])
        fetched_count = 0

        for item in messages_meta:
            msg_id = item["id"]
            try:
                detail_resp = httpx.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"format": "raw"},
                    timeout=15.0
                )
                if detail_resp.status_code != 200:
                    continue

                raw_encoded = detail_resp.json().get("raw", "")
                if not raw_encoded:
                    continue

                raw_bytes = base64.urlsafe_b64decode(raw_encoded + "=" * (-len(raw_encoded) % 4))
                msg = email.message_from_bytes(raw_bytes)

                message_id = msg.get("Message-ID", f"gmail-{msg_id}")
                subject = decode_header_str(msg.get("Subject", "(No Subject)"))
                from_header = decode_header_str(msg.get("From", "Unknown Sender"))
                to_header = decode_header_str(msg.get("To", ""))

                sender_name, sender_email = parseaddr(from_header)
                if not sender_name:
                    sender_name = sender_email or from_header

                date_header = msg.get("Date")
                received_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                if date_header:
                    try:
                        parsed_dt = parsedate_to_datetime(date_header)
                        if parsed_dt.tzinfo is None:
                            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                        else:
                            parsed_dt = parsed_dt.astimezone(timezone.utc)
                        received_iso = parsed_dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pass

                body_plain, body_html = extract_body(msg)
                snippet = clean_snippet(body_plain or body_html)

                email_record = {
                    "message_id": message_id,
                    "sender": sender_name,
                    "sender_email": sender_email,
                    "recipient": to_header,
                    "subject": subject,
                    "snippet": snippet,
                    "body_plain": body_plain,
                    "body_html": body_html,
                    "received_at": received_iso
                }

                upsert_received_email(email_record)
                fetched_count += 1
            except Exception:
                continue

        prune_received_emails(max_emails)
        return {
            "status": "success",
            "fetched_count": fetched_count,
            "days_window": days,
            "max_emails_limit": max_emails,
            "source": "gmail_api"
        }
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"Failed to sync inbox via Gmail API: {e}") from e

def sync_inbox_from_imap(days: int = INBOX_DAYS_LIMIT, max_emails: int = MAX_INBOX_EMAILS) -> Dict[str, Any]:
    """
    Synchronize inbox emails. Uses Gmail REST API when Google OAuth is connected,
    or falls back to IMAP for password/app-password configurations.
    """
    google_tokens = get_google_tokens()
    if google_tokens and google_tokens.get("encrypted_refresh_token"):
        return _sync_inbox_via_gmail_api(days=days, max_emails=max_emails)

    config = get_email_config()
    if not config or not config.get("email_address") or not config.get("encrypted_password"):
        raise ValueError("Email account is not configured yet. Please configure Gmail details in Settings.")

    raw_password = decrypt_credential(config["encrypted_password"])
    if not raw_password:
        raise ValueError("Failed to decrypt stored credentials.")

    imap_client = get_imap_connection(config)
    fetched_count = 0
    new_count = 0

    try:
        try:
            imap_client.login(config["email_address"], raw_password)
        except Exception as auth_err:
            err_str = str(auth_err)
            if (
                "AUTHENTICATIONFAILED" in err_str
                or "Invalid credentials" in err_str
                or "Application-specific password" in err_str
            ):
                raise RuntimeError(
                    "Gmail IMAP Authentication Failed: Google rejected your username or App Password. "
                    "Please make sure 2-Step Verification is active and generate a fresh 16-character "
                    "App Password at https://myaccount.google.com/apppasswords, then save it in Settings."
                ) from auth_err
            raise RuntimeError(f"IMAP Login Failed: {err_str}") from auth_err
        status, _ = imap_client.select("INBOX", readonly=True)
        if status != "OK":
            raise RuntimeError("Could not open INBOX folder on IMAP server.")

        # Compute cutoff date in RFC format (e.g., 25-Sep-2026)
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
        search_criterion = f'(SINCE "{cutoff_date}")'

        status, data = imap_client.search(None, search_criterion)
        if status != "OK":
            raise RuntimeError("Failed to search messages via IMAP.")

        msg_ids = data[0].split()
        if not msg_ids:
            # Fallback to fetching recent messages if SINCE yields none due to server timezone
            status, data = imap_client.search(None, "ALL")
            if status == "OK" and data[0]:
                msg_ids = data[0].split()

        # Sort reverse chronological (newest IMAP sequence IDs last, so reverse)
        msg_ids = list(reversed(msg_ids))[:max_emails]

        for num in msg_ids:
            try:
                res, msg_data = imap_client.fetch(num, "(RFC822)")
                if res != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                message_id = msg.get("Message-ID", f"lazymail-{num.decode('utf-8')}-{datetime.utcnow().timestamp()}")
                subject = decode_header_str(msg.get("Subject", "(No Subject)"))
                from_header = decode_header_str(msg.get("From", "Unknown Sender"))
                to_header = decode_header_str(msg.get("To", config["email_address"]))

                sender_name, sender_email = parseaddr(from_header)
                if not sender_name:
                    sender_name = sender_email or from_header

                # Date parsing: Normalize to UTC "%Y-%m-%d %H:%M:%S" for exact chronological ordering
                date_header = msg.get("Date")
                received_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                if date_header:
                    try:
                        parsed_dt = parsedate_to_datetime(date_header)
                        if parsed_dt.tzinfo is None:
                            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                        else:
                            parsed_dt = parsed_dt.astimezone(timezone.utc)
                        received_iso = parsed_dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pass

                body_plain, body_html = extract_body(msg)
                snippet = clean_snippet(body_plain or body_html)

                email_record = {
                    "message_id": message_id,
                    "sender": sender_name,
                    "sender_email": sender_email,
                    "recipient": to_header,
                    "subject": subject,
                    "snippet": snippet,
                    "body_plain": body_plain,
                    "body_html": body_html,
                    "received_at": received_iso
                }

                upsert_received_email(email_record)
                fetched_count += 1
            except Exception as item_err:
                # Log or ignore individual message parsing error
                continue

        # Prune to max 50 in database
        prune_received_emails(max_emails)
        return {
            "status": "success",
            "fetched_count": fetched_count,
            "days_window": days,
            "max_emails_limit": max_emails
        }
    finally:
        try:
            imap_client.close()
        except Exception:
            pass
        try:
            imap_client.logout()
        except Exception:
            pass

def send_outgoing_email(recipient: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Send an email via SMTP and save to SQLite (capping sent messages to max 50).
    """
    if not recipient or not recipient.strip():
        raise ValueError("Recipient email is required.")
    if not subject:
        subject = "(No Subject)"
    if body is None:
        body = ""

    recipient = validate_single_recipient(recipient)

    # Check if Google OAuth 2.0 is active
    google_tokens = get_google_tokens()
    has_oauth = bool(google_tokens and google_tokens.get("encrypted_refresh_token"))

    config = get_email_config()
    sender_email = (config.get("email_address") if config else "") or "me"
    sender_name = (config.get("sender_name") if config else "") or ""
    raw_password = ""

    if not has_oauth:
        if not config or not config.get("email_address") or not config.get("encrypted_password"):
            raise ValueError("Email settings are not configured. Please sign in with Google or configure Gmail account.")

        raw_password = decrypt_credential(config["encrypted_password"])
        if not raw_password:
            raise ValueError("Failed to decrypt stored credentials.")
    
    # Properly encode sender display name to RFC-2047 if present
    if sender_name:
        from_header = formataddr((Header(sender_name, "utf-8").encode(), sender_email))
    else:
        from_header = sender_email

    sender_domain = sender_email.split("@")[-1] if "@" in sender_email else "gmail.com"

    msg = MIMEMultipart("alternative")
    msg["From"] = from_header
    msg["To"] = recipient
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=sender_domain)

    # Standard personal MUA headers (RFC 3834 non-automated human message)
    # Distinguishes individual correspondence from bulk automated mailers
    msg["User-Agent"] = "LazyMail MUA/1.0 (Personal Email Client)"
    msg["X-Mailer"] = "LazyMail Personal Client 1.0"
    msg["Auto-Submitted"] = "no"

    # Attach plain text
    part_text = MIMEText(body, "plain", "utf-8")
    msg.attach(part_text)

    # If body has newlines, also create a clean HTML version for recipients supporting HTML
    html_formatted = "<p>" + html.escape(body).replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
    part_html = MIMEText(f"<html><body>{html_formatted}</body></html>", "html", "utf-8")
    msg.attach(part_html)

    if has_oauth:
        _send_via_gmail_api(msg, recipient)
        sent_id = save_sent_email(recipient.strip(), subject, body)
        return {
            "id": sent_id,
            "recipient": recipient.strip(),
            "subject": subject,
            "sent_at": datetime.utcnow().isoformat(),
            "status": "sent"
        }

    smtp_host = config.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(config.get("smtp_port", 465))
    smtp_use_ssl = bool(config.get("smtp_use_ssl", 1))

    try:
        server = _create_smtp_connection(smtp_host, smtp_port, smtp_use_ssl, timeout=20)
    except Exception as conn_err:
        raise RuntimeError(f"Could not connect to SMTP server ({smtp_host}:{smtp_port}): {conn_err}") from conn_err

    try:
        with server:
            # Login with dedicated 535 Bad Credentials diagnostics
            _perform_smtp_login(server, sender_email, raw_password)

            # Send email message
            try:
                server.send_message(msg, from_addr=sender_email, to_addrs=[recipient])
            except Exception as send_err:
                err = str(send_err)
                if "5.7.30" in err or "DKIM" in err:
                    raise RuntimeError(
                        "Gmail DKIM Authentication Failed (550 5.7.30): "
                        "Gmail blocked this message because DKIM authentication did not pass for your sending domain. "
                        "If you are using a Google Workspace custom domain, DKIM must be turned on in the Google Admin Console. "
                        "If using a personal Gmail account, ensure the sender address in Settings exactly matches your @gmail.com account."
                    ) from send_err
                raise RuntimeError(f"Failed to send email via SMTP: {err}") from send_err
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to send email via SMTP: {e}") from e

    # Persist sent email to SQLite and enforce max 50 sent messages cap
    sent_id = save_sent_email(recipient.strip(), subject, body)

    return {
        "id": sent_id,
        "recipient": recipient.strip(),
        "subject": subject,
        "sent_at": datetime.utcnow().isoformat(),
        "status": "sent"
    }
