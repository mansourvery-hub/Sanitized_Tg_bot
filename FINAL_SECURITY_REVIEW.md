# Final Release Security Review: Sanitized_Tg_bot

**Date:** September 18, 2026  
**Fork Repository:** `https://github.com/mansourvery-hub/Sanitized_Tg_bot`  
**Upstream Repository:** `https://github.com/PastKing/tgbot-verify`  

---

## 1. Provenance

- **Upstream Repository:** `https://github.com/PastKing/tgbot-verify`
- **Upstream Base Commit:** `f34a1997acdc832ba154754661ca8cf3dd3ae14a` (Merge PR #53)
- **Sanitized Repository:** `https://github.com/mansourvery-hub/Sanitized_Tg_bot`
- **Sanitized HEAD Commit:** Final commit `security: finalize sanitized repository` (post-scrub)
- **Git History Rewriting:** Yes. Historical commits were scrubbed using `git-filter-repo` to permanently expunge `oaiteam/` from all commits while preserving commit metadata, dates, and author attributions.
- **Historical Credential Scrubbing:** Verified. Blob `361f985574f0e6a42ca0e63d390489d34b0824b7` (`oaiteam/invite.py`) and historical references to the embedded ChatGPT token and account identifier were removed across all repository refs. Running `git log --all -- oaiteam/invite.py` returns 0 commits.

---

## 2. Current Source Tree

The sanitized working tree maintains all functional components of the Telegram verification bot while removing unverified, auxiliary, and credential-bearing artifacts:

- **`oaiteam/`:** Completely absent from working tree and Git history.
- **`military/`:** Completely absent from working tree.
- **Intended Verifier Modules Present & Intact:**
  - `one/`: One education verification module (`config.py`, `img_generator.py`, `service.py`, `temp.html`).
  - `k12/`: K12 student verification module (`config.py`, `img_generator.py`, `service.py`, `card-temp.html`).
  - `spotify/`: Spotify student verification module (`config.py`, `img_generator.py`, `service.py`, `temp.html`).
  - `youtube/`: YouTube student verification module (`config.py`, `img_generator.py`, `service.py`, `temp.html`).
  - `Boltnew/`: Bolt verification module (`config.py`, `img_generator.py`, `service.py`, `temp.html`).
- **Core Orchestration & Infrastructure:**
  - `bot.py`: Telegram application entrypoint and conversation router.
  - `config.py`: Environment configuration loader.
  - `database_mysql.py`: Database client and persistence layer.
  - `handlers/`: Telegram update handlers (`user_commands.py`, `verify_commands.py`, `admin_commands.py`).
  - `utils/`: Message formatting, helper functions, and shared verification logic.
- **Executable / Binary Payloads:** Confirmed absent. No compiled binaries, shared objects, executable wrappers, or unexpected blobs are tracked in the repository.

---

## 3. Static Security

A complete static analysis was conducted across all files in the current repository:

### A. Code Execution Search
- Repository-wide regex audit: `subprocess|Popen|os\.system|os\.popen|exec\(|eval\(|compile\(|__import__|pickle|marshal|ctypes|socket`
- **Result:** Zero occurrences in application code. No subprocess invocation, dynamic code execution, dangerous deserialization, or raw socket calls exist.

### B. Obfuscation Search
- Pattern scan for Base64 and hex encoding payloads, character array reconstruction, or hidden eval routines.
- **Result:** No obfuscated code. Standard `base64` imports in `Boltnew/img_generator.py`, `one/img_generator.py`, `spotify/img_generator.py`, and `youtube/img_generator.py` are strictly utilized to encode inline SVG card templates into standard data URIs (`data:image/svg+xml;base64,...`) for local Playwright rendering.

### C. Secret Search
- Regex scan across all tracked files: `Bearer |api[_-]?key|password|secret|token`
- **Result:** No hardcoded tokens, passwords, or live credentials exist in tracked files.
  - `bot.py`: Enforces `BOT_TOKEN` validation from environment variables; fails fast if missing.
  - `database_mysql.py`: Reads `MYSQL_PASSWORD` exclusively from environment variables with no hardcoded fallback.
  - Documentation files (`DEPLOY.md`, `DEPLOY_EN.md`, `README.md`, `env.example`): Contain non-sensitive placeholder templates (e.g. `your_bot_token_here`).

### D. Persistence Search
- Audit for crontab installations, systemd unit generation, autostart entries, or shell profile modifications (`~/.bashrc`, `~/.zshrc`).
- **Result:** Zero persistence mechanisms found. The bot executes strictly as a foreground process.

### E. Filesystem & Host Access Search
- Scanned for directory traversals, home directory scraping, or access to sensitive paths (`~/.ssh`, `~/.aws`, `~/.config`, browser profiles, `/etc/passwd`).
- **Result:** Clean. Filesystem operations are strictly confined to reading local HTML templates, writing generated verification images/PDFs within the application working directory, and appending execution logs in `./logs/`.

### F. Network Inventory
The runtime code contacts only explicitly verified destinations:
1. **Telegram Bot API:** `https://api.telegram.org` (and referral link domain `https://t.me`) — Required for core Telegram Bot bot interaction.
2. **SheerID REST Services:** `https://services.sheerid.com` and `https://my.sheerid.com` — Required for initiating and checking student/teacher verification status.
3. **SheerID S3 Presigned Uploads:** Dynamic presigned Amazon S3 URLs returned by the official SheerID API for document image attachment submission.
4. **Documentation & Information URLs:** `https://rhetorical-era-3f3.notion.site` (help guide) and `img.shields.io` (documentation badges).

---

## 4. Dependency Security

- **Lockfile Implementation:** All dependencies and sub-dependencies are deterministically locked in `requirements.lock.txt` (26 total packages).
- **Direct Runtime Dependencies:**
  - `python-telegram-bot==22.8`
  - `httpx==0.28.1`
  - `Pillow==12.3.0`
  - `reportlab==5.0.1`
  - `xhtml2pdf==0.2.20`
  - `playwright==1.48.0`
  - `pymysql==1.2.3`
  - `psutil==7.2.2`
  - `python-dotenv==1.2.3`
- **Docker Enforcement:** `Dockerfile` explicitly installs from the locked manifest: `RUN pip install --no-cache-dir -r requirements.lock.txt`.
- **Dependency Installation Verification:** Successfully built in an isolated container environment and verified using `pip check`. All transitive dependencies are satisfied with zero conflicts.
- **Third-Party Supply Chain Limitations:** While all versions are pinned, the project relies on third-party PyPI wheels and Debian base packages. Future production deployments should implement cryptographic package hash verification (`pip install --require-hashes`).

---

## 5. Container Security

- **Non-Root Runtime:** The container defines and switches to an unprivileged system user:
  ```dockerfile
  RUN groupadd -g 10001 appgroup && \
      useradd -u 10001 -g appgroup -s /bin/bash -m appuser
  USER appuser
  ```
  Container verification confirmed runtime `uid=10001(appuser) gid=10001(appgroup)`.
- **Browser Execution Model:** Playwright downloads and executes Chromium strictly within `/ms-playwright`, owned by `appuser`. The browser executes without root privileges or dangerous `--no-sandbox` overrides.
- **Mounts & Docker Socket:**
  - No host Docker socket mounts (`/var/run/docker.sock`).
  - No host root filesystem mounts.
  - Ephemeral container storage is used for temporary render files.
- **Remaining Browser/Runtime Risks:** Headless Chromium rendering involves complex native parsing of HTML/CSS. Running as non-root mitigates container breakout risk, but memory allocation should be monitored (recommended 1-2GB per worker).

---

## 6. Local Execution Security

Documented in detail in `SAFE_LOCAL_RUN.md`:
- **Architecture:** Isolated workflow: `working copy -> AI-agent code audit/editing -> .venv -> Firejail -> bot.py`.
- **Filesystem Isolation:** Recommended execution via `firejail --private --net=default .venv/bin/python bot.py`. The `--private` flag mounts private `tmpfs` directories over `$HOME`, shielding SSH keys, AWS credentials, gcloud configs, and browser profiles from inspection.
- **Sandbox Limitations:** Firejail's `--net=default` permits ordinary outbound HTTP/HTTPS networking to Telegram and SheerID, but does NOT enforce an outbound domain allowlist. Outbound traffic to the host default network is enabled.
- **Environment Separation:** Local execution requires a dedicated non-production bot token and test database configuration in `.env`, which is strictly excluded from version control via `.gitignore`.

---

## 7. Remaining Risks & Operational Realities

Static and local verification cannot declare software "completely secure" or "risk-free". The following operational realities and residual risks are explicitly recognized:

1. **Repository-Level Status:**
   - Auxiliary credential scripts (`oaiteam/`) and dead notes (`military/`) have been removed from the working tree and erased from Git history.
   - The repository tree is clean, consistent, and reproducible.
2. **Third-Party Service Trust:**
   - The core functionality relies on external services: Telegram API and SheerID API.
   - SheerID API contract changes or bot token revocations will impact application availability.
3. **Runtime & Supply Chain Residual Risk:**
   - Pre-compiled binaries (Chromium, Python C-extensions such as `Pillow`, `cffi`, and `cryptography`) are trusted upstream artifacts.
   - Hash checking (`--require-hashes`) and automated dependency vulnerability scanning (e.g. Dependabot, Trivy) should be integrated into ongoing CI/CD.
4. **Operational & Host Security:**
   - Protection of production credentials relies on host environment hygiene. Leaking `.env` or exposing MySQL ports publicly creates significant operational risk independent of codebase sanitization.
5. **Items Not Verified (Safety Gate):**
   - In accordance with project safety directives, live verification workflows submitting synthetic personal identification data to SheerID were **not** performed.

---

## 8. Final Verification Checklist

- [x] `python3 -m py_compile` executed across all Python files with zero errors.
- [x] All application modules (`bot`, `database_mysql`, `config`, `handlers`, `utils`, `one`, `k12`, `spotify`, `youtube`, `Boltnew`) successfully imported inside runtime environment.
- [x] Clean Docker build with `--no-cache` verified installing `requirements.lock.txt`.
- [x] Docker container verified running as unprivileged `appuser:appgroup` (UID/GID 10001).
- [x] Git history rewritten via `git-filter-repo` to permanently remove `oaiteam/invite.py`.
- [x] `git log --all -- oaiteam/invite.py` verified returning 0 results.
- [x] No hardcoded production secrets or unhandled default passwords remain.
- [x] Local execution safety guide (`SAFE_LOCAL_RUN.md`) accurately describes boundaries and constraints.
- [x] Working tree clean and properly tracked.
