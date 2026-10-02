import imaplib
import smtplib
import ssl
import email
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
    save_sent_email
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
        imap_client.login(email_address, raw_password)
        imap_client.select("INBOX", readonly=True)
        imap_client.logout()
        results["imap_ok"] = True
        results["imap_message"] = "IMAP connection and login succeeded."
    except Exception as e:
        err = str(e)
        if "Application-specific password required" in err or "AUTHENTICATIONFAILED" in err:
            results["imap_message"] = (
                "Authentication failed: Gmail requires a 16-character App Password. "
                "Ensure 2-Step Verification is enabled on your Google Account and generate an App Password."
            )
        else:
            results["imap_message"] = f"IMAP Error: {err}"

    # 2. Test SMTP
    try:
        if smtp_use_ssl and smtp_port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=12) as smtp_client:
                smtp_client.login(email_address, raw_password)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as smtp_client:
                if smtp_use_ssl:
                    context = ssl.create_default_context()
                    smtp_client.starttls(context=context)
                smtp_client.login(email_address, raw_password)
        results["smtp_ok"] = True
        results["smtp_message"] = "SMTP connection and login succeeded."
    except Exception as e:
        err = str(e)
        if "Application-specific password required" in err or "535" in err or "Authentication" in err:
            results["smtp_message"] = (
                "Authentication failed: Gmail requires an App Password. "
                "Ensure 2-Step Verification is enabled and use your 16-character App Password."
            )
        else:
            results["smtp_message"] = f"SMTP Error: {err}"

    results["success"] = results["imap_ok"] and results["smtp_ok"]
    return results

def sync_inbox_from_imap(days: int = INBOX_DAYS_LIMIT, max_emails: int = MAX_INBOX_EMAILS) -> Dict[str, Any]:
    """
    Connect to IMAP, query emails from the last `days` (default 7),
    fetch up to `max_emails` (default 50) sorted newest first,
    and persist into SQLite received_emails.
    """
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
        imap_client.login(config["email_address"], raw_password)
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

    config = get_email_config()
    if not config or not config.get("email_address") or not config.get("encrypted_password"):
        raise ValueError("Email settings are not configured. Please configure your Gmail account.")

    raw_password = decrypt_credential(config["encrypted_password"])
    if not raw_password:
        raise ValueError("Failed to decrypt stored credentials.")

    sender_email = config["email_address"]
    sender_name = (config.get("sender_name") or "").strip()
    
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

    smtp_host = config.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(config.get("smtp_port", 465))
    smtp_use_ssl = bool(config.get("smtp_use_ssl", 1))

    try:
        if smtp_use_ssl and smtp_port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=20) as server:
                server.login(sender_email, raw_password)
                server.send_message(msg, from_addr=sender_email, to_addrs=[recipient])
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                if smtp_use_ssl:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                server.login(sender_email, raw_password)
                server.send_message(msg, from_addr=sender_email, to_addrs=[recipient])
    except Exception as e:
        err = str(e)
        if "Application-specific password required" in err or "535" in err:
            raise RuntimeError("SMTP Authentication Failed: Gmail requires a 16-character App Password.") from e
        if "5.7.30" in err or "DKIM" in err:
            raise RuntimeError(
                "Gmail DKIM Authentication Failed (550 5.7.30): "
                "Gmail blocked this message because DKIM authentication did not pass for your sending domain. "
                "If you are using a Google Workspace custom domain, DKIM must be turned on in the Google Admin Console. "
                "If using a personal Gmail account, ensure the sender address in Settings exactly matches your @gmail.com account."
            ) from e
        raise RuntimeError(f"Failed to send email via SMTP: {err}") from e

    # Persist sent email to SQLite and enforce max 50 sent messages cap
    sent_id = save_sent_email(recipient.strip(), subject, body)

    return {
        "id": sent_id,
        "recipient": recipient.strip(),
        "subject": subject,
        "sent_at": datetime.utcnow().isoformat(),
        "status": "sent"
    }
