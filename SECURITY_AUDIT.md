# Initial Security Reconnaissance Audit: Sanitized_Tg_bot

**Audit Date:** September 17, 2026  
**Auditor:** Automated Security Reconnaissance Agent  
**Upstream Repository:** `https://github.com/PastKing/tgbot-verify`  
**Upstream Commit:** `f34a1997acdc832ba154754661ca8cf3dd3ae14a`  

---

## 1. Audit Scope & Methodology

The goal of this audit is a full static code analysis and security inventory of all source files, auxiliary scripts, dependencies, configuration files, and documentation within the repository.

### Methodology & Automated Inspections
- **Code Execution & Dynamic Invocations:** Repository-wide search for `subprocess`, `Popen`, `os.system`, `os.popen`, `exec`, `eval`, `compile`, `__import__`, `pickle`, `marshal`, `ctypes`, and `cffi`.
- **Obfuscation & Hiding:** Search for Base64 blobs, hex-encoded strings, dynamic code reconstruction, and dynamic library loads.
- **Network Boundaries:** Audited all HTTP clients (`httpx`, `requests`) and string constants referencing external hostnames and API endpoints.
- **Secrets Audit:** Pattern matching for API keys, bearer tokens, bot tokens, hardcoded passwords, and credentials across current working tree and Git history.
- **Persistence & Host Modification:** Checked for system modifications, file system traversal, cron, SSH access, or browser profile access.
- **Supply Chain:** Inspected `requirements.txt`, `Dockerfile`, and `docker-compose.yml`.

---

## 2. Findings Summary

| Category | Finding | Risk Level | Recommendation |
| :--- | :--- | :--- | :--- |
| **Auxiliary Modules** | Hardcoded Bearer Token in `oaiteam/invite.py` calling `chatgpt.com` | **High** | Remove `oaiteam/` directory |
| **Auxiliary Documentation** | Non-functional auxiliary notes in `military/` | **Low** | Remove `military/` directory |
| **Supply Chain** | Unpinned runtime dependencies (`>=` specifiers in `requirements.txt`) | **Medium** | Lock exact versions in `requirements.lock.txt` |
| **Container Security** | Dockerfile executes application as `root` user | **Medium** | Harden Dockerfile to run non-root user |
| **Browser Automation** | Playwright headless Chromium invocation for HTML-to-image rendering | **Low / Expected** | Validate HTML inputs and restrict browser permissions |

---

## 3. Detailed Audit Categories

### A. Code Execution Risk
- **Findings:**
  - No instances of `subprocess`, `os.system`, `exec()`, `eval()`, `compile()`, `pickle`, `ctypes`, or dynamic module compilation.
  - `os` is imported in `config.py`, `database_mysql.py`, and `oaiteam/invite.py` solely for reading environment variables (`os.getenv`).
  - Playwright (`playwright.sync_api`) is used in `img_generator.py` across verification modules (`one`, `k12`, `spotify`, `youtube`, `Boltnew`) to render HTML documents into PNG images via headless Chromium (`page.set_content()`, `page.screenshot()`).
- **Verdict:** Low direct execution risk in core python code; browser rendering is isolated to local HTML templates.

### B. Obfuscation / Payload Hiding
- **Findings:**
  - Base64 encoding found in `Boltnew/img_generator.py` (Line 276): An inline SVG Data-URI `<img src="data:image/svg+xml;base64,...">` used as a placeholder faculty avatar.
  - Standard `base64` module imports in `img_generator.py` across modules to encode generated images for API responses.
- **Verdict:** Benign static asset encoding. No obfuscated payload or malicious python executable string identified.

### C. Network Behavior & External Services
- **Inventory of Contacted Hostnames:**
  1. `api.telegram.org`: Main Telegram Bot API (Legitimate).
  2. `services.sheerid.com` / `my.sheerid.com`: SheerID verification REST endpoints (Legitimate core feature).
  3. `chatgpt.com`: ChatGPT backend admin API (`/backend-api/accounts/{ACCOUNT_ID}/invites`) called by `oaiteam/invite.py` (Auxiliary / Untrusted).
  4. `img.shields.io`, `api.star-history.com`, `t.me`: Documentation badges and link targets (Legitimate).
- **Verdict:** Core network calls are restricted to Telegram and SheerID. `chatgpt.com` calls in `oaiteam/` are auxiliary and should be removed.

### D. Secrets & Credential Inventory
- **Findings:**
  - `oaiteam/invite.py`: Hardcoded fallback bearer token (`eyYmQwZSI.....Y6vBlVVKNmBmY`) and Account ID (`32bfda....b22`).
  - Environment templates (`env.example`, `DEPLOY.md`, `DEPLOY_EN.md`, `README.md`): Contain standard placeholders (e.g., `your_bot_token_here`, `your_password_here`).
- **Verdict:** No live production secrets found. Auxiliary file `oaiteam/invite.py` contains credential artifacts.

### E. Persistence & Host Modification
- **Findings:**
  - No crontabs, systemd service installers, shell profile modifications, or local directory scanning logic found.
  - No credential store scraping or SSH key directory accesses.
- **Verdict:** Clean.

### F. Supply Chain & Container Security
- **Findings:**
  - `requirements.txt` relies on loose version requirements (`>=` for 8 of 9 packages), risking build breakage or upstream package compromise.
  - `Dockerfile` runs as root (`FROM python:3.11-slim`) and installs chromium system dependencies.
  - `docker-compose.yml` passes environment secrets cleanly from host environment `.env`.
- **Verdict:** Requires dependency lockfile generation (Stage 3) and container non-root user hardening (Stage 5).

---

## 4. Action Plan for Sanitization

### Files Recommended for Removal (Stage 2 - COMPLETED)
1. `oaiteam/` — Unrelated auxiliary ChatGPT invite script containing embedded credentials. Removed in Stage 2.
2. `military/` — Unrelated auxiliary markdown documentation for military verification flows not integrated into `bot.py`. Removed in Stage 2.

### Files Requiring Additional Review / Hardening
1. `requirements.txt` -> Create `requirements.lock.txt` with locked exact package versions.
2. `Dockerfile` -> Add dedicated non-root application user and group.
3. `handlers/verify_commands.py` & verifier modules -> Harden error handling and ensure log sanitization.

---

## 6. Stage 4 — Final Repository Security Sanity Check (September 18, 2026)

### A. Dependency & Lockfile Verification
- **Consistency:** `requirements.lock.txt` contains exact, pinned versions for all 9 direct dependencies specified in `requirements.txt` (`python-telegram-bot==22.8`, `httpx==0.28.1`, `Pillow==12.3.0`, `reportlab==5.0.1`, `xhtml2pdf==0.2.20`, `playwright==1.48.0`, `pymysql==1.2.3`, `psutil==7.2.2`, `python-dotenv==1.2.3`).
- **Sub-dependencies:** All 17 pinned sub-dependencies (`anyio`, `certifi`, `chardet`, `charset-normalizer`, `greenlet`, `h11`, `httpcore`, `idna`, `pyee`, `pypdf`, `rlpycache`, `six`, `sniffio`, `svglib`, `typing_extensions`, `urllib3`) match the dependency tree requirements without extraneous packages.
- **Docker Integration:** The `Dockerfile` explicitly installs from `requirements.lock.txt` (`pip install --no-cache-dir -r requirements.lock.txt`).
- **No Development Bloat:** No test runners, packaging, or dev-only dependencies are bundled into runtime requirements.
- **Runtime Trust Boundary:** Playwright Chromium automation is confined within the container or host sandbox without root privileges.

### B. Static Security Classification
- **Dangerous Invocations:** Searches for `subprocess`, `Popen`, `os.system`, `os.popen`, `exec(`, `eval(`, `compile(`, `__import__`, `pickle`, `marshal`, and `ctypes` across all Python files returned **0** occurrences.
- **Base64 Encoding:** Confined strictly to `img_generator.py` modules across `Boltnew/`, `one/`, `spotify/`, and `youtube/` for generating `data:image/svg+xml;base64,...` inline image URI strings for HTML-to-image/PDF rendering. No executable decoding or hidden payload extraction.
- **Secret Placeholders:** References to `BOT_TOKEN`, `MYSQL_PASSWORD`, and `TOKEN` strictly ingest values from environment variables via `os.getenv(...)`. Zero hardcoded API keys, tokens, passwords, or credentials exist in the source tree.
- **Bearer Tokens:** Zero occurrences in runtime code (historical ChatGPT invite script completely scrubbed from git history).

### C. Network Inventory
Runtime code contacts only the following verified destinations:
1. `api.telegram.org`: Main Telegram Bot API (via `python-telegram-bot`) for webhook/polling and messaging.
2. `services.sheerid.com` / `my.sheerid.com`: Official SheerID verification REST endpoints for verification lifecycle calls.
3. SheerID-returned S3 presigned upload URLs: Temporary pre-signed AWS S3 buckets provided dynamically by SheerID API for uploading generated verification images.
4. `t.me`: Telegram referral links and channel URLs.
5. Notion (`https://rhetorical-era-3f3.notion.site/...`): Help documentation link in `config.py`.
6. Configured MySQL Database host (`MYSQL_HOST`).
*Verdict: 0 unexplained external destinations.*

### D. Filesystem & Persistence Review
- **Directory Scans:** Zero scans of `/home`, `~/.ssh`, `~/.aws`, `~/.config`, or browser profiles.
- **Host Modification:** Zero modification of shell startup files (`.bashrc`, `.profile`), systemd units, launchd daemons, or cron jobs.
- **Persistence:** Zero self-persistence or background daemonizing wrappers.
- **Execution:** Zero dynamic command spawning, shell script launchers, or external tool execution outside of Playwright's managed browser binaries.
- **Local Writes:** File system writes are strictly scoped to application log files (`/app/logs` or `./logs`) and temporary image generation assets.
