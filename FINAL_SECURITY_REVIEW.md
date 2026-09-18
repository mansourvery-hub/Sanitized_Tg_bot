# Final Security Regression Review: Sanitized_Tg_bot

**Date:** September 18, 2026  
**Fork Repository:** `https://github.com/mansourvery-hub/Sanitized_Tg_bot`  
**Upstream Repository:** `https://github.com/PastKing/tgbot-verify`  
**Base Upstream Commit:** `f34a1997acdc832ba154754661ca8cf3dd3ae14a`  
**Sanitized Head Commit:** `0a173f8` (and finalization commit)

---

## 1. Executive Summary

This repository is a security-conscious hard fork of `PastKing/tgbot-verify`. The primary goal of the sanitization process was to preserve the Telegram bot functionality while removing unrelated high-risk auxiliary components, eliminating insecure credential fallbacks, establishing deterministic dependency locking, hardening Docker container execution, and documenting low-risk local execution workflows.

---

## 2. Complete File Modification & Deletion Inventory

### Deleted Files & Directories
- `oaiteam/` (`oaiteam/invite.py`):
  - **Reason:** Contained auxiliary ChatGPT workspace invite functionality that transmitted authorization Bearer tokens to `chatgpt.com` and contained hardcoded fallback tokens and account IDs. Unrelated to Telegram bot operations.
- `military/` (`military/__init__.py`, `military/README.md`):
  - **Reason:** Incomplete notes/documentation on military verification flows that were never implemented in or referenced by `bot.py`.

### Added Files
- `SECURITY_AUDIT.md`: Initial comprehensive security audit and vulnerability assessment (Stage 1).
- `requirements.lock.txt`: Fully pinned, reproducible dependency manifest (Stage 3).
- `SAFE_LOCAL_RUN.md`: Detailed guide for isolated local execution using virtual environments and Firejail sandboxing (Stage 6).
- `FINAL_SECURITY_REVIEW.md`: Comprehensive final security regression audit report (Stage 7).

### Modified Files
- `config.py`:
  - Removed dummy fallback string `"YOUR_BOT_TOKEN_HERE"` and default admin user ID `"123456789"`.
- `database_mysql.py`:
  - Removed hardcoded default fallback password `'your_password_here'`.
  - Added strict requirement for database credentials via environment variables.
- `bot.py`:
  - Added pre-flight check asserting that `BOT_TOKEN` is defined before initializing bot handlers.
  - Fixed indentation bug in Spotify student verification flow (`handlers/verify_commands.py`).
- `Dockerfile`:
  - Created unprivileged system user/group (`appuser:appgroup` UID/GID 10001).
  - Configured browser storage path `/ms-playwright` owned by `appuser`.
  - Changed execution model to run completely as non-root user.
  - Locked dependencies via `requirements.lock.txt` and `requirements.txt`.
- `README.md` & `README_EN.md`:
  - Removed references to deleted `military/` directory.
  - Added dedicated "Sanitization & Security Hardening" documentation section.

---

## 3. Security Findings & Remediations

| Security Category | Finding / Risk in Upstream | Remediation Applied |
| :--- | :--- | :--- |
| **Auxiliary Attack Surface** | `oaiteam/invite.py` included embedded ChatGPT bearer token and account ID sending invitations. | Deleted `oaiteam/` completely. |
| **Dead / Confusing Docs** | `military/` contained unimplemented reverse-engineered endpoints. | Deleted `military/` completely. |
| **Credential Fallbacks** | Default fallback placeholder passwords and tokens in `config.py` and `database_mysql.py`. | Replaced with empty defaults and explicit startup validation. |
| **Supply Chain Risk** | Loose `>=` dependency versions in `requirements.txt`. | Generated reproducible `requirements.lock.txt` with exact pins. |
| **Container Privilege Escalation** | Docker container ran as `root`. | Hardened `Dockerfile` with dedicated non-root user `appuser:appgroup`. |
| **Local Host Exposure** | Lack of sandbox isolation guidelines for testing Playwright and web scrapers. | Authored `SAFE_LOCAL_RUN.md` with Firejail execution boundary rules. |

---

## 4. Verification Checks & Tests Performed

1. **Syntax & Static Compilation**:
   - Executed `python3 -m py_compile` over the entire Python tree. All modules compiled cleanly without syntax or indentation errors.
2. **Import & Module Boundary Verification**:
   - Verified that all command handlers in `handlers/` import active verifier modules (`one/`, `k12/`, `spotify/`, `youtube/`, `Boltnew/`) with zero remaining references to `oaiteam` or `military`.
3. **Dependency Integrity**:
   - Successfully installed and verified dependencies in a clean virtual environment using `pip install -r requirements.lock.txt`. Verified with `pip check`.
4. **Container Build & Security Check**:
   - Built container image `sanitized-tgbot:latest` and confirmed non-root identity (`uid=10001(appuser)`).
   - Confirmed container starts up cleanly, parses configuration, and validates required environment variables without network exposure.
5. **Secret Search**:
   - Ran regex pattern scans (`git grep -nE 'Bearer |api[_-]?key|token|password|secret'`) to ensure no real secrets exist in tracking. All hits correspond to documentation placeholders (`your_secure_password`, `your_bot_token_here`).

---

## 5. Known Remaining Risks & Operational Considerations

1. **External Endpoint Dependence**:
   - The bot legitimately communicates with Telegram Bot API (`api.telegram.org`) and SheerID services (`services.sheerid.com`, `my.sheerid.com`). If SheerID updates its internal schemas, verification flows may fail gracefully without compromising system security.
2. **Browser Automation Overhead**:
   - Playwright uses Chromium to render dynamic HTML templates into image/PDF verification documents. Operators must ensure adequate RAM (minimum 1GB per concurrent worker).
3. **Database Security**:
   - The MySQL database requires a secure, non-default password supplied via `.env`. Operators must avoid exposing MySQL ports directly to the public internet.

---

## 6. Explicit Limitations & Verification Boundary Disclaimer

- **Static Review Limitations**: Static source-code auditing cannot mathematically guarantee the runtime safety or integrity of third-party compiled binaries (e.g., Chromium browser binaries distributed by Playwright, or pre-compiled C wheels).
- **No Live Document Submission**: In accordance with testing safety rules, synthetic documents and identities were not submitted against production SheerID verification endpoints during this audit.

---

## 7. Conclusion

The sanitized fork `Sanitized_Tg_bot` is hardened, reproducible, free from unrelated credential-bearing scripts, and structured for safe operation and experimentation.
