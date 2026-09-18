# Historical Secret Exposure Audit

**Audit Date:** September 18, 2026  
**Repository:** `Sanitized_Tg_bot` (`https://github.com/mansourvery-hub/Sanitized_Tg_bot`)  
**Scope:** Git history inspection for credential-bearing objects and auxiliary scripts.

---

## 1. Executive Summary

During the initial repository sanitization, auxiliary modules (`oaiteam/` and `military/`) were removed from the working tree in commit `96e95b0` (`security: remove unrelated credential-bearing auxiliary modules`).

However, standard Git workflows preserve the full commit history. A historical audit confirmed that `oaiteam/invite.py`—which contained hardcoded authentication credentials (a ChatGPT account Bearer JWT token and an `ACCOUNT_ID` string)—remains fully reachable through the commit history of the repository and its public remote tracking refs.

---

## 2. Findings

### 2.1 File & Content Overview
- **File path:** `oaiteam/invite.py`
- **Git Object ID:** Blob `361f985574f0e6a42ca0e63d390489d34b0824b7`
- **Content:**
  - Hardcoded default value for `TOKEN`: a complete Bearer JSON Web Token (`ey...`)
  - Hardcoded default value for `ACCOUNT_ID`: a 36-character UUID string identifying a ChatGPT workspace account
  - HTTP requests sending the Bearer token to `https://chatgpt.com/backend-api/accounts/{ACCOUNT_ID}/invites`
  - Note: Per security policy, the exact token string and secret values are redacted from this report.

### 2.2 Historical Commits & Reachability
The file was traced across git history:
- **Introduced:** Commit `025e8fc68b5ca1991d971215ba60adc08292ed86` ("第一次提交", 2025-12-07).
- **Active in:** Every upstream commit from `025e8fc` through `f34a199` (PR #53 merge), as well as initial fork audit commit `8b0ca00`.
- **Removed from working tree:** Commit `96e95b0a728fcf1801ac8fb8d48334d1bf9b5c02` ("security: remove unrelated credential-bearing auxiliary modules").
- **Current refs containing the commit:**
  - Local branch: `refs/heads/main`
  - Remote tracking branch: `refs/remotes/origin/main` (and `origin/HEAD`)
  - Upstream branch: `refs/remotes/upstream/main`
- **Tags:** No git tags currently reference or contain these commits.

### 2.3 Reachability from Public Repository
Because `origin/main` is public on GitHub and includes commit `025e8fc`, any user cloning the repository has full access to the commit history and can view the exposed credentials via:
```bash
git show 025e8fc:oaiteam/invite.py
# or
git log -p -S"chatgpt.com"
```
The Git blob remains reachable and unpacked/packed in git storage.

---

## 3. Risk Assessment

1. **Token Exposure:**
   Although the auxiliary invite script is not part of the bot's runtime code and the token may be expired or revoked by OpenAI, publishing live or historical tokens in public repositories violates basic credential hygiene and exposes associated accounts to automated credential scrapers.
2. **Account Identifier Exposure:**
   The workspace `ACCOUNT_ID` links the repository history to a specific ChatGPT team/workspace tenant.
3. **Repository Cleanliness & Compliance:**
   A genuinely sanitized repository should not retain historical commits containing credentials in its primary branch.

---

## 4. History Rewriting Recommendation

- **Recommendation:** Proceed with Stage 3 history rewriting to scrub `oaiteam/` from historical commits in `Sanitized_Tg_bot`.
- **Tooling:** Use `git-filter-repo` (or equivalent established history rewriting tool).
- **Safety Pre-conditions:**
  1. Create a full local backup branch/tag (`backup-pre-scrub-stage2`).
  2. Record the pre-rewrite commit SHA and tree SHA.
  3. Confirm the current working tree is clean.
  4. Ensure all legitimate application history and upstream commits are preserved intact, only excising `oaiteam/` from tree objects.
  5. Use `--force-with-lease` when updating the remote `origin/main`.
