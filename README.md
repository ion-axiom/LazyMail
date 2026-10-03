# LazyMail — Secure & Robust Email Client

**Version**: `1.0.0`  
**Author**: [Derek Richards (alias: DerekR)](https://derekr.co.uk)  
**Website**: [https://derekr.co.uk](https://derekr.co.uk)  
**Copyright**: [COPYRIGHT.md](file:///Users/lifehance/Development/LazyMail/COPYRIGHT.md) (c) 2026 Derek Richards

LazyMail is a secure, elegant, and robust web email client specifically designed for Gmail. It allows you to synchronize the last 7 days of incoming emails (capped at 50 messages), compose and send emails via SMTP, maintain an encrypted local store of sent emails (capped at 50 messages), and purge messages on demand from an encrypted SQLite database.

---

## Key Features

1. **Secure Authentication & Session Protection**
   - Initial bootstrap setup wizard to establish a Master Admin account.
   - Salted password hashing with `bcrypt` (12 rounds).
   - Session protection with HTTP-only, SameSite cookies and auto-expiration.
   - Brute-force rate limiting to prevent unauthorized access.

2. **Encrypted Gmail Credentials Storage**
   - SQLite database stores Gmail address, IMAP (`imap.gmail.com:993` SSL) and SMTP (`smtp.gmail.com:465` SSL / `587` STARTTLS) configuration.
   - Google App Passwords are encrypted at rest with **AES-256 (Fernet)** using a master key (`data/.secret.key`).
   - Integrated **Connection Test** diagnostic tool to verify IMAP and SMTP login before saving.

3. **7-Day IMAP Inbox Synchronization (Max 50)**
   - Syncs emails received in the last 7 days via Gmail IMAP.
   - Restricts cached messages in SQLite to the newest 50.
   - Multipart MIME decoding: supports UTF-8/RFC-2047 headers, plain text, and safe HTML preview rendered in an isolated sandbox iframe.

4. **SMTP Email Sending & Sent Storage (Max 50)**
   - Clean compose modal with validation for recipient, subject, and message body.
   - Dispatches outgoing emails via Gmail SMTP with TLS/SSL encryption.
   - Automatically stores sent messages in SQLite and enforces a strict 50-message cap (pruning oldest sent messages).

5. **Anti-Bulk Sending Protections & MUA Compliance**
   - **Personal MUA Headers**: Includes `Auto-Submitted: no` (RFC 3834 non-automated human message header), `User-Agent: LazyMail MUA/1.0`, and `X-Mailer: LazyMail Personal Client` to distinguish personal correspondence from automated marketing/bulk emailers.
   - **Strict Single-Recipient Enforcement**: Rejects commas, semicolons, lists, or multiple addresses in both client-side and server-side validation.
   - **Outbound Rate Limiting**: Enforces a 3-second human cooldown between consecutive sends, max 5 emails/minute burst limit, and a strict 50 emails/day ceiling (matching the SQLite sent storage limit).
   - **RFC-5322 Standard Message-ID**: Automatically generates legitimate per-message Message-ID strings with domain entropy.

6. **Granular Database Purge Facility**
   - Purge Sent Messages only.
   - Purge Received Messages (cache) only.
   - Purge All Messages (both sent and received) with automatic SQLite `VACUUM` to reclaim disk space.
   - Confirmation dialogs prevent accidental data loss.

7. **Bilingual Support (Turkish Default & English)**
   - Default language: **Turkish (`tr`)** with immediate fallback/toggle to **English (`en`)**.
   - Segmented interactive language switcher pill (`🇹🇷 TR | 🇬🇧 EN`) on both the top navigation bar and authentication modals.
   - Comprehensive localization of labels, placeholders, dialogs, empty states, date formatting, and toast notifications.
   - User preference persisted seamlessly in browser `localStorage`.

8. **Fully Mobile-Ready Responsive UX**
   - **Adaptive Breakpoints**: Custom-tuned layouts for desktop, tablet (<= 900px), smartphone (<= 768px), and compact phones (<= 480px).
   - **Off-Canvas Drawer Navigation**: Smooth sliding sidebar drawer with semi-transparent backdrop overlay and touch-friendly controls.
   - **Mobile Master-Detail View**: Email reader slides in full-screen on mobile with a dedicated Back button (`← Geri` / `← Back`) to return instantly to the list.
   - **iOS Safari Optimization**: Viewport notch awareness (`viewport-fit=cover`) and automatic input zoom prevention (`font-size: 16px`).
   - Seamless **Dark / Light mode** toggle with persistent user preference.

---

## Directory Structure

```
LazyMail/
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration, paths, encryption key derivation
│   ├── crypto_utils.py     # bcrypt password hashing & Fernet AES-256 encryption
│   ├── database.py         # SQLite schema, transactions, migrations, and capping
│   ├── email_service.py    # IMAP sync, SMTP dispatch, connection diagnostics
│   ├── auth.py             # Session tokens, rate limiting, route guards
│   └── main.py             # FastAPI REST endpoints and static file serving
├── data/
│   ├── lazymail.db         # SQLite database
│   └── .secret.key         # Secure key file (0600 permissions)
├── static/
│   ├── css/
│   │   └── app.css         # Custom design system with glassmorphic tokens
│   └── js/
│       ├── app.js          # Reactive frontend controller
│       └── translations.js # Bilingual i18n dictionary (TR & EN)
├── templates/
│   └── index.html          # Semantic HTML5 single-page application
├── tests/
│   ├── test_lazymail.py    # Core functionality test suite
│   └── test_i18n.py        # Bilingual & language switcher parity tests (15/15 passing)
├── requirements.txt        # Frozen dependencies
├── start.sh                # Executable launcher script
└── README.md
```

---

## Quick Start

### 1. Launch the Server

Run the launcher script:
```bash
./start.sh
```

Or run manually with `.venv`:
```bash
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Access the Application

Open your browser to:
```
http://127.0.0.1:8000
```

1. **1-Click Google OAuth Sign-In (Recommended)**:
   - Click the prominent **Sign in with Google** button to authenticate directly with Google OAuth 2.0.
   - Grants seamless, password-free access with offline refresh tokens. All emails are dispatched and synchronized directly through the official Google Gmail REST API (`gmail.googleapis.com`) without needing IMAP/SMTP app passwords or port configuration.
   - If configuring custom credentials, enter your **Google Client ID** and **Client Secret** either via the UI modal (**Settings -> Google OAuth Settings**) or in the `.env` file (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`).
2. **Alternative Username & App Passcode Setup**:
   - You can also enter a username and your 16-character Google App Passcode to connect via standard IMAP/SMTP.
3. **Sync Inbox**: Click **Sync IMAP / Sync Google** on the inbox toolbar to pull messages.
4. **Send Email**: Click **Compose** to draft and send messages.
5. **Purge Data**: Go to **Purge Database** whenever you wish to clear sent or received messages.

---

## Gmail App Password Setup

Because Google deprecated Less Secure Apps, standard passwords cannot be used for IMAP/SMTP. Instead, generate a free **App Password**:

1. Go to your [Google Account Security Settings](https://myaccount.google.com/security).
2. Ensure **2-Step Verification** is turned ON.
3. Under *2-Step Verification*, click on **App passwords** (or search "App passwords" in the top bar).
4. Enter an app name (e.g. `LazyMail`) and click **Create**.
5. Copy the generated **16-character password** into LazyMail Settings.

---

## Running Tests

To run the automated test suite:
```bash
PYTHONPATH=. .venv/bin/pytest tests/ -v
```

---

## Production Deployment with Docker & CI/CD (Ionos Debian VPS)

LazyMail is fully containerized and configured for automated CI/CD deployment via GitHub Actions to a Debian Linux VPS hosted by Ionos.

### Port Allocation: 3011
To coexist alongside other Quasar and Docker applications running on ports `3000`–`3010`, LazyMail binds to **host port `3011`** (`3011:8000`).

### 1. Repository Files for Deployment
- [`Dockerfile`](file:///Users/lifehance/Development/LazyMail/Dockerfile): Python 3.11 slim image, unprivileged storage, curl healthcheck.
- [`docker-compose.yml`](file:///Users/lifehance/Development/LazyMail/docker-compose.yml): Configured with host port `"${HOST_PORT:-3011}:8000"` and persistent volume `./data:/app/data` (saving SQLite DB and encryption keys).
- [`.dockerignore`](file:///Users/lifehance/Development/LazyMail/.dockerignore): Prevents local virtual environments, test databases, or secret keys from leaking into the Docker image.
- [`.github/workflows/deploy.yml`](file:///Users/lifehance/Development/LazyMail/.github/workflows/deploy.yml): Runs tests with `pytest` on every push/PR, then automatically SSHs into the Ionos VPS on pushes to `main` to build and deploy.

### 2. GitHub Secrets & Variables Setup
In your GitHub repository, navigate to **Settings > Secrets and variables > Actions**:

#### Repository Variables (or Secrets)
| Name | Type | Description |
|---|---|---|
| `SERVER_IP` | **Variable** (or Secret) | Public IPv4 address of your Ionos VPS |
| `VPS_USER` | Secret | SSH user with sudo/Docker privileges (`root` or `debian`) |
| `VPS_SSH_KEY` | Secret | Private SSH key matching `~/.ssh/authorized_keys` on VPS |
| `VPS_SSH_PORT` | *(Optional Secret)* | SSH Port (defaults to `22`) |
| `DEPLOY_PATH` | *(Optional Secret)* | Absolute directory on VPS (defaults to `/opt/lazymail`) |
| `VPS_HOST` | *(Optional fallback)* | Alternative name for `SERVER_IP` |

### 3. One-Time Setup on Ionos Debian VPS

SSH into your Ionos server:
```bash
ssh user@your-vps-ip
```

#### Install Docker and Docker Compose (if not already installed):
```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

#### Ensure Target Directory & Permissions:
```bash
sudo mkdir -p /opt/lazymail
sudo chown -R $USER:$USER /opt/lazymail
```

### 4. Fast Setup with `lazyadmin` (Domain & Nginx Proxy)

LazyMail includes the [`lazyadmin`](file:///Users/lifehance/Development/LazyMail/lazyadmin) management script to automatically configure Nginx for `lazymail.derekr.co.uk`, bind port `3011` strictly to `127.0.0.1` (protecting it from direct public access), and configure Let's Encrypt SSL.

On your Linux (Debian) VPS:
```bash
cd /opt/lazymail
sudo ./lazyadmin setup
```

The script automatically executes **5 safety checks** before modifying anything to protect other apps on the server:
1. **Nginx Baseline Check**: Tests existing Nginx health with `nginx -t`; aborts if existing sites have syntax errors so running apps aren't disrupted.
2. **Domain Collision Check**: Scans all files in `/etc/nginx/sites-available` to prevent accidentally overwriting or clashing with another website.
3. **Port Isolation Check**: Checks `3011` and ensures existing Quasar/Docker apps on `3000-3010` remain untouched.
4. **Atomic Configuration with Rollback**: Creates a timestamped backup; if the new config fails validation, it rolls back automatically without reloading Nginx.
5. **DNS Pre-Validation for SSL**: Dynamically verifies `lazymail.derekr.co.uk` resolves to the server's public IP before running Certbot to prevent failed challenges.

#### Additional `lazyadmin` Commands:
```bash
sudo ./lazyadmin status   # Shows Nginx service, Docker container, and port 3011 health
sudo ./lazyadmin ports    # Inspects active ports (3000-3020) and running Docker containers
sudo ./lazyadmin ssl      # Obtains or renews SSL certificates
sudo ./lazyadmin test     # Performs Nginx syntax checks and internal port queries
sudo ./lazyadmin help     # Displays all available commands
```

### 5. Automated CI/CD Trigger
Whenever you push changes to the `main` branch on GitHub:
1. GitHub Actions spins up an Ubuntu runner and executes the pytest test suite.
2. If tests pass, GitHub Actions connects via SSH to your Ionos VPS.
3. It pulls the latest code, ensures `./data` persistence, updates the Docker container with `docker compose up -d --build`, and confirms port `3011` is healthy.

Thank you