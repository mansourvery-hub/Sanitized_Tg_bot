# Safe Local Execution & Development Guide

This guide describes how to run and test `Sanitized_Tg_bot` locally with minimal security risk to your host environment.

---

## 1. Minimal-Risk Local Architecture

```text
working copy
    ↓
AI-agent code audit/editing
    ↓
.venv
    ↓
Firejail
    ↓
bot.py
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

### Security Guarantees & Network Boundary Explained

- **`--private`**: Isolates the process's home and filesystem view by mounting a temporary `tmpfs` over `$HOME`. The process cannot view or access host home directory files.
- **`--net=default`**: Permits ordinary outbound networking required for Telegram API (`api.telegram.org`) and SheerID (`services.sheerid.com`). **Note:** Firejail with `--net=default` does NOT provide a strict outbound network allowlist. Outbound traffic is permitted through the default host network interface.
- **Explicit Exposure Warnings**: Never mount or expose the following host resources into the process sandbox or container:
  - `~/.ssh` (SSH private keys and known hosts)
  - `~/.aws` (AWS credentials and configuration)
  - `~/.config/gcloud` (Google Cloud SDK credentials)
  - browser profiles (e.g. `~/.config/google-chrome`, `~/.mozilla`)
  - `/` (host system root)
  - `docker.sock` (`/var/run/docker.sock`)
- **No Elevated Privileges**: Firejail executes as an unprivileged user process without elevated host capabilities.

---

## 4. Security Rules for Local Experimentation

1. **Dedicated Bot Token**: Never test with production Telegram bot tokens.
2. **Dedicated Database**: Use a local or isolated test MySQL database instance.
3. **Environment Isolation**: Keep secrets in `.env` outside version control (`.env` is ignored by `.gitignore`).
4. **No Sensitive Volume Mounts**: Strictly adhere to the warnings above; do not expose host directories or sockets.
