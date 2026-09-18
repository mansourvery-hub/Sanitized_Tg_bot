# Safe Local Execution & Development Guide

This guide describes how to run and test `Sanitized_Tg_bot` locally with minimal security risk to your host environment.

---

## 1. Minimal-Risk Local Architecture

```text
Git working copy
    ↓
AI agent edits / audits
    ↓
Python virtual environment (.venv)
    ↓
Firejail execution isolation (sandbox)
```

---

## 2. Environment Setup

### Step 1: Create an Isolated Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt
```

### Step 2: Configure Local Environment Secrets

Copy `env.example` to `.env` (never commit `.env` to Git):

```bash
cp env.example .env
```

Edit `.env` and configure dedicated development credentials:
- `BOT_TOKEN`: Use a dedicated test bot token from [@BotFather](https://t.me/BotFather).
- `ADMIN_USER_ID`: Your Telegram numeric ID.
- `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`: Point to a local or isolated test database.

---

## 3. Isolated Execution Boundary with Firejail (Recommended)

To protect host credentials (SSH keys, cloud configs, browser profiles, personal files), execute the bot inside a lightweight [Firejail](https://firejail.wordpress.com/) sandbox.

### Firejail Baseline Command

```bash
firejail --private --net=default .venv/bin/python bot.py
```

### Security Guarantees Explained

- **`--private`**: Mounts temporary `tmpfs` directories over `$HOME`. The running Python process cannot access host SSH keys (`~/.ssh`), browser profiles (`~/.config/google-chrome`, `~/.mozilla`), or cloud credentials (`~/.aws`, `~/.gcp`).
- **`--net=default`**: Permits normal outbound HTTP/HTTPS connections to Telegram API (`api.telegram.org`) and SheerID (`services.sheerid.com`) while keeping local file access restricted.
- **No Docker Socket**: The bot process is given no access to `/var/run/docker.sock`.
- **No Host Root Access**: Firejail runs in user mode without elevated host privileges.

---

## 4. Security Rules for Local Experimentation

1. **Dedicated Bot Token**: Never test with production Telegram bot tokens.
2. **Dedicated Database**: Use a local test MySQL database instance.
3. **Environment Isolation**: Keep secrets in `.env` outside version control. `.env` is listed in `.gitignore`.
4. **No Sensitive Volume Mounts**: Avoid mounting your host home directory or system root (`/`) into containers or sandbox processes.
