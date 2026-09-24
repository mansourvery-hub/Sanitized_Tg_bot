# Project Agent Guide — Sanitized_Tg_bot

## Stack & Quality Gates
- Python: `./venv/bin/python` (3.11–3.14), deps via `requirements.lock.txt`, Playwright `chromium` required for PNG.
- Linters: `ruff check` + `ruff format --check`; type: `pyright`; tests: `./venv/bin/python -m unittest discover -s tests -v` (fast) vs full suite via GH Actions.

## Project Notes
- [2026-09-24, Muse Spark 1.2] Institution pass-rate ranking is data-driven via `Institution.estimated_pass_rate_low/high` and `generation.get_best_institutions_for_service()`; adding an Institution with those fields auto-ranks, per-service override via `SERVICE_INSTITUTION_OVERRIDES`. Verified by: `tests/test_generation.py::test_service_recommendation_ranking`.
- [2026-09-24, Muse Spark 1.2] International student IDs use 2020–2024 windows (up_diliman/unilag `YYYY`, um `SYYYY`), makerere `YY/U/NNNNN/PS`; changing window requires updating `tests/test_generation.py` regex and regenerating `tests/visual_baselines`. Verified by: `generation._generate_student_id` vs `test_international_institution_profiles`.

## Lessons Learned
- [2026-09-24, Muse Spark 1.2] Logos are opt-in and user-supplied: never hardcode an institution logo or invent a placeholder mark. The wizard asks at runtime (`--logo` for non-interactive); URL downloads are cached by URL digest under `$XDG_CACHE_HOME/sanitized_tg_bot/logos` so re-renders stay byte-identical. The institution name alone satisfies the "name or logo" requirement. Verified by: `test_logo_is_opt_in_and_user_supplied`, `test_logo_download_is_cached_and_deterministic`.
- [2026-09-24, Muse Spark 1.2] Visual baseline churn (formerly ~0.06% on unchanged code) was caused by salted `hash()` on strings in `_generate_crn` and `_spoof_pdf_metadata`; both now use `_stable_hash_int` (blake2b), so repeated `generate_baselines(force=True)` is byte-identical (only intentionally-changed specs differ). Do not reintroduce `hash()` on str for reproducibility. Verified by: `app.py visual-regression` 12/12 at 0.000% and `test_generation_is_deterministic_across_processes`.
- [2026-09-24, Muse Spark 1.2] Re-render an existing bundle with `app.py refresh <bundle-dir>`; it reloads `profile.json` and rewrites document.html/pdf/png in place, preserving name/DOB/student_id/email so a document already submitted to a verification form stays consistent. Use this instead of regenerating with a new seed. Verified by: `test_refresh_bundle_preserves_identity`.
- [2026-09-24, Muse Spark 1.2] Wizard `--scenario` argparse `choices` rejects aliases like `student→undergraduate`; alias mapping must happen after `parse_args` in `app.py:cmd_wizard`. Verified by: `app.py --wizard-mode service --service one --scenario student` raised `invalid choice` before fix.
- [2026-09-24, Muse Spark 1.2] `xhtml2pdf` warning `Ignoring CSS properties ... border-collapse` is harmless; layout uses table fallbacks and readback still valid. Verified by: `generate_fixture_bundle` → `readback_validate_pdf` passes despite warning.
