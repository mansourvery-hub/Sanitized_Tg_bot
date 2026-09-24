# Project Agent Guide — Sanitized_Tg_bot

## Stack & Quality Gates
- Python: `./venv/bin/python` (3.11–3.14), deps via `requirements.lock.txt`, Playwright `chromium` required for PNG.
- Linters: `ruff check` + `ruff format --check`; type: `pyright`; tests: `./venv/bin/python -m unittest discover -s tests -v` (fast) vs full suite via GH Actions.

## Project Notes
- [2026-09-24, Muse Spark 1.2] Institution pass-rate ranking is data-driven via `Institution.estimated_pass_rate_low/high` and `generation.get_best_institutions_for_service()`; adding an Institution with those fields auto-ranks, per-service override via `SERVICE_INSTITUTION_OVERRIDES`. Verified by: `tests/test_generation.py::test_service_recommendation_ranking`.
- [2026-09-24, Muse Spark 1.2] International student IDs use 2020–2024 windows (up_diliman/unilag `YYYY`, um `SYYYY`), makerere `YY/U/NNNNN/PS`; changing window requires updating `tests/test_generation.py` regex and regenerating `tests/visual_baselines`. Verified by: `generation._generate_student_id` vs `test_international_institution_profiles`.

## Lessons Learned
- [2026-09-24, Muse Spark 1.2] Visual regression baselines are ~0.06% nondeterministic even with same seed (font hinting/sub-pixel); `VisualRegressionSuite.generate_baselines(force=True)` will churn psu/nyu/umich PNGs and manifest hashes without code change. Verified by: `app.py visual-regression` twice shows 0.06% diff on unchanged code.
- [2026-09-24, Muse Spark 1.2] Wizard `--scenario` argparse `choices` rejects aliases like `student→undergraduate`; alias mapping must happen after `parse_args` in `app.py:cmd_wizard`. Verified by: `app.py --wizard-mode service --service one --scenario student` raised `invalid choice` before fix.
- [2026-09-24, Muse Spark 1.2] `xhtml2pdf` warning `Ignoring CSS properties ... border-collapse` is harmless; layout uses table fallbacks and readback still valid. Verified by: `generate_fixture_bundle` → `readback_validate_pdf` passes despite warning.
