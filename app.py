#!/usr/bin/env python3
"""
CLI entry point for Sanitized Local Identity & Document Framework.

Provides commands for listing options, generating identities, generating documents,
rendering artifacts, running validation, generating full fixture bundles,
batch generating test data, and inspecting generated artifacts.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

from generation import (
    GENERATOR_VERSION,
    INSTITUTIONS,
    SCENARIOS,
    SERVICE_DEFINITIONS,
    ArtifactType,
    DocumentKind,
    SyntheticProfile,
    generate_batch,
    generate_document,
    generate_fixture_bundle,
    generate_profile,
    get_best_institutions_for_service,
    inspect_readback_artifact,
    refresh_bundle,
    render_pdf,
    render_png,
    validate_artifact,
    validate_document,
    validate_profile,
)


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str))


def cmd_list(args: argparse.Namespace) -> int:
    """List available scenarios, institutions, and document kinds."""
    info = {
        "generator_version": GENERATOR_VERSION,
        "scenarios": list(SCENARIOS.keys()),
        "scenario_details": {
            k: {
                "role": v.role.value if hasattr(v.role, "value") else str(v.role),
                "academic_level": v.academic_level.value
                if hasattr(v.academic_level, "value")
                else str(v.academic_level),
                "min_age": v.min_age,
                "max_age": v.max_age,
                "institution_id": v.institution_id,
            }
            for k, v in SCENARIOS.items()
        },
        "institutions": [
            {
                "id": inst.id,
                "name": inst.name,
                "city": inst.city,
                "country": inst.country,
                "domain": inst.domain,
                "type": inst.institution_type,
            }
            for inst in INSTITUTIONS.values()
        ],
        "document_kinds": [dk.value for dk in DocumentKind],
    }

    if args.json:
        _print_json(info)
    else:
        print(f"Sanitized Local Identity Engine (v{GENERATOR_VERSION})\n")
        print("Available Scenarios:")
        for name, details in info["scenario_details"].items():
            print(
                f"  - {name:20s} (Role: {details['role']}, Level: {details['academic_level']}, Age: {details['min_age']}-{details['max_age']})"
            )

        print("\nAvailable Institutions:")
        for inst in info["institutions"]:
            print(
                f"  - [{inst['id']}] {inst['name']} ({inst['city']}, {inst['country']}) - Domain: {inst['domain']}"
            )

        print("\nAvailable Document Kinds:")
        for dk in info["document_kinds"]:
            print(f"  - {dk}")

    return 0


def cmd_identity(args: argparse.Namespace) -> int:
    """Generate and display a canonical synthetic profile."""
    profile = generate_profile(
        scenario_name=args.scenario,
        seed=args.seed,
        override_institution_id=args.institution,
    )
    val_res = validate_profile(profile)

    res = {
        "generator_version": GENERATOR_VERSION,
        "scenario": args.scenario,
        "seed": args.seed if args.seed is not None else profile.student_id,
        "valid": val_res.valid,
        "errors": [e.to_dict() for e in val_res.errors],
        "profile": profile.to_dict(),
    }

    if args.json:
        _print_json(res)
    else:
        print("=== CANONICAL SYNTHETIC PROFILE ===")
        print(f"Name:               {profile.first_name} {profile.last_name}")
        print(f"Role:               {profile.role.value}")
        print(f"Academic Level:     {profile.academic_level.value}")
        print(f"Birth Date:         {profile.date_of_birth.strftime('%Y-%m-%d')}")
        print(
            f"Institution:        {profile.institution_name} ({profile.institution_id})"
        )
        print(f"Student/ID:         {profile.student_id}")
        print(f"Email:              {profile.email}")
        print(f"Program/Major:      {profile.program}")
        print(f"Enrollment/Hire:    {profile.enrollment_date.strftime('%Y-%m-%d')}")
        print(f"Exp. Graduation:    {profile.expected_graduation.strftime('%Y-%m-%d')}")
        print(f"Academic Year:      {profile.academic_year}")
        print(f"Validation:         {'VALID' if val_res.valid else 'INVALID'}")
        if not val_res.valid:
            print("Validation Errors:")
            for err in val_res.errors:
                print(f"  - [{err.code}] {err.field}: {err.message}")

    return 0 if val_res.valid else 1


def cmd_document(args: argparse.Namespace) -> int:
    """Project a canonical profile into a logical document model."""
    profile = generate_profile(
        scenario_name=args.scenario,
        seed=args.seed,
        override_institution_id=args.institution,
    )

    doc_kind = DocumentKind.SCHEDULE
    if args.kind:
        try:
            doc_kind = DocumentKind(args.kind)
        except ValueError:
            print(
                f"Error: Unknown document kind '{args.kind}'. Options: {[dk.value for dk in DocumentKind]}"
            )
            return 1

    doc = generate_document(profile, doc_kind=doc_kind)
    val_doc = validate_document(doc)

    res = {
        "generator_version": GENERATOR_VERSION,
        "kind": doc.kind.value,
        "title": doc.title,
        "valid": val_doc.valid,
        "errors": [e.to_dict() for e in val_doc.errors],
        "profile": profile.to_dict(),
        "fields": doc.fields,
    }

    if args.json:
        _print_json(res)
    else:
        print("=== LOGICAL DOCUMENT MODEL ===")
        print(f"Kind:               {doc.kind.value}")
        print(f"Title:              {doc.title}")
        print(f"Profile Name:       {profile.first_name} {profile.last_name}")
        print(f"Validation Status:  {'VALID' if val_doc.valid else 'INVALID'}")
        print("Fields:")
        for k, v in doc.fields.items():
            if k != "html":
                print(f"  - {k:20s}: {v}")

    return 0 if val_doc.valid else 1


def cmd_render(args: argparse.Namespace) -> int:
    """Generate profile, project document, and render HTML/PDF/PNG to disk."""
    profile = generate_profile(
        scenario_name=args.scenario,
        seed=args.seed,
        override_institution_id=args.institution,
    )

    doc_kind = DocumentKind.SCHEDULE
    if args.kind:
        try:
            doc_kind = DocumentKind(args.kind)
        except ValueError:
            print(f"Error: Unknown document kind '{args.kind}'")
            return 1

    doc = generate_document(profile, doc_kind=doc_kind, logo_source=args.logo)
    out_dir = (
        Path(args.output)
        if args.output
        else Path("output") / f"render-{args.scenario}-{args.seed or 'default'}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    fmt = args.format.lower()
    artifact_path = None

    if fmt == "html":
        artifact_path = out_dir / "document.html"
        artifact_path.write_text(doc.html_content, encoding="utf-8")
    elif fmt == "pdf":
        artifact_path = out_dir / "document.pdf"
        pdf_bytes = render_pdf(
            doc.html_content,
            institution=profile.institution,
            profile=profile,
            term_label=profile.current_term_label,
        )
        artifact_path.write_bytes(pdf_bytes)
    elif fmt == "png":
        artifact_path = out_dir / "document.png"
        png_bytes = render_png(doc.html_content)
        artifact_path.write_bytes(png_bytes)
    else:
        print(f"Error: Unsupported format '{fmt}'. Options: html, pdf, png")
        return 1

    val_art = inspect_readback_artifact(artifact_path, profile)

    if args.json:
        _print_json(
            {
                "generator_version": GENERATOR_VERSION,
                "format": fmt,
                "path": str(artifact_path),
                "valid": val_art.valid,
                "errors": [e.to_dict() for e in val_art.errors],
                "warnings": val_art.warnings,
            }
        )
    else:
        print("=== RENDER COMPLETE ===")
        print(f"Format:     {fmt.upper()}")
        print(f"Path:       {artifact_path}")
        print(f"Validation: {'VALID' if val_art.valid else 'INVALID'}")
        if val_art.warnings:
            print("Warnings:")
            for w in val_art.warnings:
                print(f"  - {w}")
        if not val_art.valid:
            print("Errors:")
            for err in val_art.errors:
                print(f"  - [{err.code}] {err.field}: {err.message}")

    return 0 if val_art.valid else 1


def cmd_fixture(args: argparse.Namespace) -> int:
    """Generate a complete local fixture bundle with profile, documents, artifacts & report."""
    output_dir = Path(args.output) if args.output else Path("output/fixture")
    res = generate_fixture_bundle(
        scenario_name=args.scenario,
        seed=args.seed if args.seed is not None else 12345,
        output_dir=output_dir,
        override_institution_id=args.institution,
        logo_source=args.logo,
    )

    if args.json:
        _print_json(res.to_dict())
    else:
        print("=== FIXTURE BUNDLE CREATED ===")
        print(f"Scenario:          {res.scenario}")
        print(f"Seed:              {res.seed}")
        print(
            f"Output Directory:  {Path(res.artifacts[0].path).parent if res.artifacts else 'N/A'}"
        )
        print(
            f"Profile:           {res.profile.first_name} {res.profile.last_name} ({res.profile.student_id})"
        )
        print(f"Artifacts Count:   {len(res.artifacts)}")
        print(f"Validation Status: {'VALID' if res.validation.valid else 'INVALID'}")
        if res.validation.warnings:
            print("Warnings:")
            for w in res.validation.warnings:
                print(f"  - {w}")
        if not res.validation.valid:
            print("Errors:")
            for err in res.validation.errors:
                print(f"  - [{err.code}] {err.field}: {err.message}")

    return 0 if res.validation.valid else 1


def cmd_batch(args: argparse.Namespace) -> int:
    """Batch generate fixtures with deterministic seed derivation and summary report."""
    summary = generate_batch(
        scenario_name=args.scenario,
        count=args.count,
        base_seed=args.seed if args.seed is not None else 1000,
        output_dir=args.output,
        override_institution_id=args.institution,
    )

    if args.json:
        _print_json(summary)
    else:
        print("=== BATCH GENERATION COMPLETE ===")
        print(f"Scenario:        {summary['scenario']}")
        print(f"Base Seed:       {summary['base_seed']}")
        print(f"Total Generated: {summary['total_generated']}")
        print(f"Valid:           {summary['valid_count']}")
        print(f"Invalid:         {summary['invalid_count']}")
        print(f"Output Dir:      {summary['batch_output_dir']}")
        if summary["failure_categories"]:
            print("Failure Categories:")
            for cat, cnt in summary["failure_categories"].items():
                print(f"  - {cat}: {cnt}")

    return 0 if summary["invalid_count"] == 0 else 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a generated fixture bundle directory or artifact file."""
    target = Path(args.target)
    if not target.exists():
        print(f"Error: Target path '{target}' does not exist.")
        return 1

    if target.is_dir():
        prof_file = target / "profile.json"
        if not prof_file.exists():
            print(f"Error: Profile file 'profile.json' missing in directory '{target}'")
            return 1

        try:
            prof_data = json.loads(prof_file.read_text(encoding="utf-8"))
            profile = SyntheticProfile.from_dict(prof_data)
        except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
            print(f"Error parsing profile JSON: {exc}")
            return 1

        val_prof = validate_profile(profile)
        art_validations = []
        for file_path in target.glob("*"):
            if file_path.name not in ("profile.json", "report.json"):
                art_val = inspect_readback_artifact(file_path, profile)
                art_validations.append((file_path.name, art_val))

        all_valid = val_prof.valid and all(v.valid for _, v in art_validations)

        if args.json:
            _print_json(
                {
                    "target": str(target),
                    "valid": all_valid,
                    "profile_validation": val_prof.to_dict(),
                    "artifacts": [
                        {
                            "file": name,
                            "valid": v.valid,
                            "errors": [e.to_dict() for e in v.errors],
                        }
                        for name, v in art_validations
                    ],
                }
            )
        else:
            print(f"=== VALIDATION REPORT: {target.name} ===")
            print(f"Profile Status: {'VALID' if val_prof.valid else 'INVALID'}")
            print("Artifact Readback Check:")
            for name, v in art_validations:
                print(f"  - {name:20s}: {'VALID' if v.valid else 'INVALID'}")
                if not v.valid:
                    for err in v.errors:
                        print(f"      [{err.code}] {err.field}: {err.message}")

        return 0 if all_valid else 1

    else:
        val = validate_artifact(
            target,
            ArtifactType.HTML
            if target.suffix == ".html"
            else ArtifactType.PDF
            if target.suffix == ".pdf"
            else ArtifactType.PNG
            if target.suffix == ".png"
            else ArtifactType.JSON,
        )
        if args.json:
            _print_json(
                {
                    "path": str(target),
                    "valid": val.valid,
                    "errors": [e.to_dict() for e in val.errors],
                }
            )
        else:
            print(
                f"Validation for file '{target}': {'VALID' if val.valid else 'INVALID'}"
            )
            if not val.valid:
                for err in val.errors:
                    print(f"  - [{err.code}] {err.field}: {err.message}")

        return 0 if val.valid else 1


def cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect and display structured details of a profile JSON or fixture directory."""
    target = Path(args.target)
    if target.is_dir():
        target = target / "profile.json"

    if not target.exists():
        print(f"Error: File '{target}' does not exist.")
        return 1

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        profile = SyntheticProfile.from_dict(data)
    except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
        print(f"Error parsing profile file '{target}': {exc}")
        return 1

    val = validate_profile(profile)

    if args.json:
        _print_json(
            {
                "file": str(target),
                "profile": profile.to_dict(),
                "validation": val.to_dict(),
            }
        )
    else:
        print("=== FIXTURE PROFILE INSPECTION ===")
        print(f"Name:            {profile.first_name} {profile.last_name}")
        print(f"Role:            {profile.role.value}")
        print(f"Academic Level:  {profile.academic_level.value}")
        print(f"Birth Date:      {profile.date_of_birth.strftime('%Y-%m-%d')}")
        print(f"Institution:     {profile.institution_name} ({profile.institution_id})")
        print(f"Student/ID:      {profile.student_id}")
        print(f"Email:           {profile.email}")
        print(f"Program/Major:   {profile.program}")
        print(f"Enrollment/Hire: {profile.enrollment_date.strftime('%Y-%m-%d')}")
        print(f"Graduation:      {profile.expected_graduation.strftime('%Y-%m-%d')}")
        print(f"Academic Year:   {profile.academic_year}")
        print(f"Validation:      {'VALID' if val.valid else 'INVALID'}")

    return 0


def _prompt_doc_kind(
    preset: str | None = None, interactive: bool = True
) -> DocumentKind:
    """Ask which document type to produce (the code supports all five)."""
    if preset:
        return DocumentKind(preset)
    if not interactive:
        return DocumentKind.SCHEDULE
    print("\nDocument type:")
    labels = [
        ("schedule", "Class schedule / educational timetable (portal view)"),
        ("enrollment_certificate", "Enrollment verification certificate (letter)"),
        ("id_card", "Student ID card (with expiry date)"),
        ("tuition_receipt", "Tuition receipt / billing statement"),
        ("faculty_summary", "Faculty / employee verification"),
    ]
    for i, (value, desc) in enumerate(labels, start=1):
        print(f"  [{i}] {desc}")
    try:
        choice = input("Choose [1]: ").strip() or "1"
    except (KeyboardInterrupt, EOFError):
        print()
        return DocumentKind.SCHEDULE
    try:
        return DocumentKind(labels[int(choice) - 1][0])
    except (ValueError, IndexError):
        print(f"[!] Invalid choice '{choice}', using schedule.")
        return DocumentKind.SCHEDULE


def _prompt_logo_source(interactive: bool = True) -> str | None:
    """Ask at runtime which logo (if any) to place on the document.

    Returns a local path, an http(s) URL, or None for no logo. Nothing is
    hardcoded: the user supplies the source on every run.
    """
    if not interactive:
        return None
    print("\nInstitutional logo (optional):")
    print("  [1] No logo                 (institution name only; default)")
    print("  [2] Use a local image file  (SVG/PNG/JPEG/WebP/GIF)")
    print("  [3] Download from a URL     (cached locally after first download)")
    try:
        choice = input("Choose [1]: ").strip() or "1"
    except (KeyboardInterrupt, EOFError):
        print()
        return None
    try:
        if choice == "2":
            return input("Local file path: ").strip() or None
        if choice == "3":
            return input("Logo URL (http/https): ").strip() or None
    except (KeyboardInterrupt, EOFError):
        print()
    return None


def cmd_refresh(args: argparse.Namespace) -> int:
    """Re-render an existing bundle in place from its saved profile.json."""
    target = Path(args.target)
    if target.is_dir() and not (target / "profile.json").exists():
        print(f"Error: No profile.json in '{target}'.", file=sys.stderr)
        return 1

    doc_kind = DocumentKind.SCHEDULE
    if args.kind:
        try:
            doc_kind = DocumentKind(args.kind)
        except ValueError:
            print(f"Error: Unknown document kind '{args.kind}'", file=sys.stderr)
            return 1

    try:
        res = refresh_bundle(target, doc_kind=doc_kind, logo_source=args.logo)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    p = res.profile
    print("=== BUNDLE REFRESHED ===")
    print(f"  Status:        {'VALID' if res.validation.valid else 'INVALID'}")
    print(f"  Directory:     {target.resolve()}")
    print(f"  Name (kept):   {p.first_name} {p.last_name}  (DOB {p.date_of_birth})")
    print(f"  ID (kept):     {p.student_id}")
    print(f"  Email (kept):  {p.email}")
    print(f"  Institution:   {p.institution_name} ({p.institution_id})")
    print("  Artifacts rewritten:")
    for art in res.artifacts:
        print(f"    - {Path(art.path).name} ({art.byte_size} bytes)")
    if res.validation.errors:
        print("  Errors:")
        for err in res.validation.errors:
            print(f"    - [{err.code}] {err.field}: {err.message}")
    return 0 if res.validation.valid else 1


def cmd_visual_regression(args: argparse.Namespace) -> int:
    """Run visual regression suite, update baselines, or compare individual images."""
    from visual_regression import (
        DEFAULT_BASELINES_DIR,
        VisualRegressionSuite,
        compare_images,
    )

    threshold = float(args.threshold)
    color_tolerance = int(args.color_tolerance)

    if args.compare:
        base_path = Path(args.compare[0])
        cand_path = Path(args.compare[1])
        if not base_path.exists():
            print(f"Error: Baseline image not found: {base_path}", file=sys.stderr)
            return 1
        if not cand_path.exists():
            print(f"Error: Candidate image not found: {cand_path}", file=sys.stderr)
            return 1

        result = compare_images(
            baseline=base_path,
            candidate=cand_path,
            threshold=threshold,
            color_tolerance=color_tolerance,
            generate_diff_image=bool(args.diff_out),
        )

        if args.diff_out and result.diff_image_bytes:
            out_p = Path(args.diff_out)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_bytes(result.diff_image_bytes)

        if args.json:
            _print_json(result.to_dict())
        else:
            print("=== VISUAL COMPARISON RESULT ===")
            print(
                f"Verdict:         {'MATCH (PASS)' if result.match else 'MISMATCH (FAIL)'}"
            )
            print(
                f"Diff Ratio:      {result.diff_ratio * 100:.4f}% (Threshold: {threshold * 100:.2f}%)"
            )
            print(f"Diff Pixels:     {result.diff_pixels} / {result.total_pixels}")
            print(f"RMSE:            {result.rmse:.4f}")
            print(
                f"Dimensions:      Baseline {result.baseline_size} vs Candidate {result.candidate_size}"
            )
            if args.diff_out:
                print(f"Diff Artifact:   {args.diff_out}")

        return 0 if result.match else 1

    baselines_dir = (
        Path(args.baselines_dir) if args.baselines_dir else DEFAULT_BASELINES_DIR
    )
    suite = VisualRegressionSuite(baselines_dir=baselines_dir)

    if args.update_baselines:
        res = suite.generate_baselines(force=True)
        if args.json:
            _print_json(res)
        else:
            print(
                f"Updated {res['total_specs']} baseline snapshots in: {res['baselines_dir']}"
            )
            print(f"Manifest written to: {res['manifest_file']}")
        return 0

    diff_dir = (
        Path(args.diff_dir) if args.diff_dir else Path("output") / "visual_regressions"
    )
    suite_res = suite.run_suite(
        threshold=threshold,
        color_tolerance=color_tolerance,
        diff_dir=diff_dir,
    )

    if args.json:
        _print_json(suite_res)
    else:
        print("=== VISUAL REGRESSION SUITE ===")
        print(f"Total Specs:     {suite_res['total']}")
        print(f"Passed:          {suite_res['passed']}")
        print(f"Failed:          {suite_res['failed']}")
        print(f"Overall Status:  {'PASSED' if suite_res['all_passed'] else 'FAILED'}\n")
        print(f"{'Spec Name':<32} {'Verdict':<10} {'Diff %':<10} {'RMSE':<8}")
        print("-" * 64)
        for name, data in suite_res["results"].items():
            verdict = "PASS" if data["match"] else "FAIL"
            diff_pct = f"{data['diff_ratio'] * 100:.3f}%"
            print(f"{name:<32} {verdict:<10} {diff_pct:<10} {data['rmse']:<8.2f}")

        if not suite_res["all_passed"]:
            print(
                f"\n[!] Discrepancies detected. Diff artifacts written to: {diff_dir}"
            )

    return 0 if suite_res["all_passed"] else 1


def _service_display_name(sid: str) -> str:
    info = SERVICE_DEFINITIONS.get(sid, {})
    return info.get("name", sid)


def _resolve_service_arg(val: str | None) -> str | None:
    if not val:
        return None
    norm = val.strip().lower().replace("-", "_")
    if norm in SERVICE_DEFINITIONS:
        return SERVICE_DEFINITIONS[norm].get("id", norm)
    # fuzzy: bare name contains
    for sid, info in SERVICE_DEFINITIONS.items():
        if norm == sid or norm in info.get("name", "").lower():
            return info.get("id", sid)
    return norm


def cmd_wizard(args: argparse.Namespace) -> int:
    """Interactive wizard: Target workflow or Service-optimized (best pass-rate) mode."""
    print("==========================================================================")
    print("      Sanitized Local Identity & Document Generator - Interactive Wizard  ")
    print("==========================================================================")

    # Non-interactive service shortcut: --service spotify --seed 42 --institution X
    preset_service = _resolve_service_arg(getattr(args, "service", None))
    preset_institution = getattr(args, "institution", None)
    preset_scenario = getattr(args, "scenario", None)

    # Decide wizard mode
    mode = getattr(args, "wizard_mode", None) or getattr(args, "mode", None)
    # Also support legacy --target non-interactive for classic mode
    legacy_target = getattr(args, "target", None)

    # If service was explicitly passed, default to service mode
    if preset_service and not mode:
        mode = "2"

    if not mode and not legacy_target:
        print("Select input mode:")
        print("  [1] Target workflow / module       (classic 1-8 list)")
        print(
            "  [2] Service-optimized              (pick service → best credentials auto-suggested)"
        )
        print()
        try:
            mode = input("Enter mode (1-2) [default: 1]: ").strip() or "1"
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return 1
    elif not mode:
        mode = "1"

    # Normalize mode aliases
    if mode in ("workflow", "1"):
        mode = "1"
    elif mode in ("service", "2"):
        mode = "2"

    # ── Service-optimized mode ──────────────────────────────────────────
    if mode == "2":
        svc_info: dict[str, str] = {}
        service_id: str = preset_service or ""
        # Build canonical service list (dedup aliases)
        seen: dict[str, dict] = {}
        for sid, info in SERVICE_DEFINITIONS.items():
            cid = info.get("id", sid)
            if cid not in seen and sid == cid:
                seen[cid] = info
        ordered_services = list(seen.values())

        if not preset_service:
            print("\nSelect service:")
            for idx, svc in enumerate(ordered_services, start=1):
                role = svc.get("role", "")
                print(f"  [{idx}] {svc['name']:<28s} ({svc['id']}) — {role}")
            print()
            try:
                svc_choice = (
                    input(
                        f"Enter service (1-{len(ordered_services)}) [default: 1]: "
                    ).strip()
                    or "1"
                )
            except (KeyboardInterrupt, EOFError):
                print("\nAborted.")
                return 1
            try:
                svc_idx = int(svc_choice) - 1
                svc_info = ordered_services[svc_idx]
                service_id = svc_info["id"]
            except (ValueError, IndexError):
                print(f"Invalid choice '{svc_choice}', using 1.")
                service_id = ordered_services[0]["id"]
        else:
            service_id = preset_service
            svc_info = SERVICE_DEFINITIONS.get(
                service_id, {"name": service_id, "id": service_id}
            )

        # Rank institutions for this service by pass rate — dynamic, no hardcoding
        ranked = get_best_institutions_for_service(service_id, limit=len(INSTITUTIONS))
        recommended = ranked[0] if ranked else INSTITUTIONS["psu"]
        rec_label = recommended.pass_rate_label or "n/a"
        # Show all ranked institutions (future-proof: adding/removing uni auto-appears)
        print(
            f"\n[+] Recommended for {svc_info.get('name', service_id)} (ranked by estimated pass rate):"
        )
        for i, inst in enumerate(ranked, start=1):
            marker = " ← recommended (press Enter)" if i == 1 else ""
            label = inst.pass_rate_label or "n/a"
            print(f"    {i:>2}. {inst.id:<20s} {inst.name:<45s} {label}{marker}")
        print()

        # Institution prompt with dynamic default — lists every uni
        default_inst = recommended.id
        if not preset_institution:
            avail_hint = ", ".join(sorted(INSTITUTIONS.keys()))
            prompt = f"Enter institution [{default_inst}] (press Enter for recommended {default_inst} — {rec_label} est., or choose from: {avail_hint}): "
            try:
                inst_input = input(prompt).strip() or default_inst
            except (KeyboardInterrupt, EOFError):
                print("\nAborted.")
                return 1
        else:
            inst_input = preset_institution

        # Scenario prompt with service-appropriate default (with alias mapping)
        default_scen = svc_info.get("default_scenario", "undergraduate")
        scenario_aliases = {
            "student": "undergraduate",
            "undergrad": "undergraduate",
            "undergraduated": "undergraduate",
            "grad": "graduate",
            "teacher": "teacher",
            "k12": "teacher",
        }
        if not preset_scenario:
            try:
                raw = (
                    input(f"Enter scenario [{default_scen}]: ").strip() or default_scen
                )
                norm = raw.strip().lower().replace("-", "_").replace(" ", "_")
                scen_input = scenario_aliases.get(norm, norm)
                if scen_input not in SCENARIOS:
                    print(
                        f"[!] Unknown scenario '{raw}'. Available: {', '.join(SCENARIOS.keys())} — using '{default_scen}'."
                    )
                    scen_input = default_scen
            except (KeyboardInterrupt, EOFError):
                print("\nAborted.")
                return 1
        else:
            norm = preset_scenario.strip().lower().replace("-", "_").replace(" ", "_")
            scen_input = scenario_aliases.get(norm, norm)
            if scen_input not in SCENARIOS:
                print(
                    f"[!] Unknown scenario '{preset_scenario}'. Available: {', '.join(SCENARIOS.keys())} — using '{default_scen}'."
                )
                scen_input = default_scen

        # Institution validation (fallback to recommended if unknown)
        if inst_input not in INSTITUTIONS:
            print(
                f"[!] Unknown institution '{inst_input}'. Available: {', '.join(sorted(INSTITUTIONS.keys()))} — using '{default_inst}'."
            )
            inst_input = default_inst

        target_info = {
            "name": f"{svc_info.get('name', service_id)} → {inst_input} ({scen_input})",
            "scenario": scen_input,
            "institution": inst_input,
            "kind": None,
            "service_id": service_id,
        }

        # Seed
        seed_val = getattr(args, "seed", None)
        if seed_val is None and not getattr(args, "non_interactive", False):
            try:
                seed_str = input(
                    "Enter seed integer (Press Enter for random seed): "
                ).strip()
                seed_val = int(seed_str) if seed_str else None
            except ValueError:
                print("Invalid seed integer, using random seed.")
                seed_val = None

        logo_source = getattr(args, "logo", None)
        if logo_source is None and not getattr(args, "non_interactive", False):
            logo_source = _prompt_logo_source(interactive=True)

        doc_kind = _prompt_doc_kind(
            preset=getattr(args, "kind", None),
            interactive=not getattr(args, "non_interactive", False),
        )

        print(f"\n[+] Generating bundle for: {target_info['name']}")
        actual_seed = (
            seed_val if seed_val is not None else random.randint(10000, 999999)
        )
        target_dir = (
            Path("output") / f"{choice_slug(target_info['name'])}-{actual_seed}"
        )
        res = generate_fixture_bundle(
            scenario_name=target_info["scenario"],
            seed=actual_seed,
            output_dir=target_dir,
            override_institution_id=target_info["institution"],
            doc_kind=doc_kind,
            logo_source=logo_source,
        )
        print(
            "\n--------------------------------------------------------------------------"
        )
        print(
            f"  Status:             {'SUCCESS (VALID)' if res.validation.valid else 'INVALID'}"
        )
        print(
            f"  Service:            {svc_info.get('name', service_id)} ({service_id})"
        )
        print(f"  Target Module:      {target_info['name']}")
        print(f"  Generated Name:     {res.profile.first_name} {res.profile.last_name}")
        print(f"  ID:                 {res.profile.student_id}")
        print(f"  Email:              {res.profile.email}")
        print(
            f"  Institution:        {res.profile.institution_name} ({res.profile.institution_id}) — {res.profile.institution.pass_rate_label or 'n/a'} est."
        )
        print(f"  Output Directory:   {target_dir.resolve()}")
        print("  Artifacts Created:")
        for art in res.artifacts:
            print(
                f"    - {Path(art.path).name} ({art.byte_size} bytes, SHA256: {art.sha256[:10]}...)"
            )
        print(
            "--------------------------------------------------------------------------"
        )
        print(
            "  Note: 'Ignoring CSS ... border-collapse' from xhtml2pdf is normal — engine limitation, tables already use fallbacks; output is valid."
        )
        _print_post_generation_tips(res.profile, service_id=service_id)
        print(
            "--------------------------------------------------------------------------\n"
        )
        return 0 if res.validation.valid else 1

    # ── Classic target workflow mode (legacy) ───────────────────────────
    print("Select target workflow / module:")
    print("  [1] PSU Student                (Penn State - LionPATH Student Schedule)")
    print(
        "  [2] UCLA Student               (UCLA - Registrar Enrollment Verification Letter)"
    )
    print("  [3] NYU Student                (NYU - Albert Student Center Schedule)")
    print("  [4] UMich Student              (UMich - Wolverine Access Class Schedule)")
    print(
        "  [5] UT Austin Student          (UT Austin - Texas One Stop Enrollment Certification)"
    )
    print("  [6] K12 Teacher / Employee     (Springfield K-12 Employee Access Center)")
    print("  [7] Bolt.new Teacher / PSU     (Penn State / LionPATH Faculty Access)")
    print("  [8] Custom / Advanced Scenario")
    print()

    targets = {
        "1": {
            "name": "PSU Student",
            "scenario": "undergraduate",
            "institution": "psu",
            "kind": DocumentKind.SCHEDULE,
        },
        "2": {
            "name": "UCLA Student",
            "scenario": "undergraduate",
            "institution": "ucla",
            "kind": DocumentKind.SCHEDULE,
        },
        "3": {
            "name": "NYU Student",
            "scenario": "undergraduate",
            "institution": "nyu",
            "kind": DocumentKind.SCHEDULE,
        },
        "4": {
            "name": "UMich Student",
            "scenario": "undergraduate",
            "institution": "umich",
            "kind": DocumentKind.SCHEDULE,
        },
        "5": {
            "name": "UT Austin Student",
            "scenario": "undergraduate",
            "institution": "ut_austin",
            "kind": DocumentKind.SCHEDULE,
        },
        "6": {
            "name": "K12 Teacher",
            "scenario": "teacher",
            "institution": "springfield_k12",
            "kind": DocumentKind.FACULTY_SUMMARY,
        },
        "7": {
            "name": "Bolt.new Teacher",
            "scenario": "teacher",
            "institution": "psu",
            "kind": DocumentKind.FACULTY_SUMMARY,
        },
    }

    choice = getattr(args, "target", None)
    if not choice:
        try:
            choice = input("Enter choice (1-8) [default: 1]: ").strip() or "1"
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return 1

    if choice == "8":
        print("\nAvailable scenarios:", ", ".join(SCENARIOS.keys()))
        scen_input = (
            input("Enter scenario [undergraduate]: ").strip() or "undergraduate"
        )
        print("Available institutions:", ", ".join(INSTITUTIONS.keys()))
        inst_input = input("Enter institution [psu]: ").strip() or "psu"
        target_info = {
            "name": f"Custom ({scen_input}/{inst_input})",
            "scenario": scen_input,
            "institution": inst_input,
            "kind": None,
        }
    else:
        target_info = targets.get(choice, targets["1"])

    seed_val = getattr(args, "seed", None)
    if seed_val is None and not getattr(args, "non_interactive", False):
        try:
            seed_str = input(
                "Enter seed integer (Press Enter for random seed): "
            ).strip()
            seed_val = int(seed_str) if seed_str else None
        except ValueError:
            print("Invalid seed integer, using random seed.")
            seed_val = None

    logo_source = getattr(args, "logo", None)
    if logo_source is None and not getattr(args, "non_interactive", False):
        logo_source = _prompt_logo_source(interactive=True)

    doc_kind = _prompt_doc_kind(
        preset=getattr(args, "kind", None),
        interactive=not getattr(args, "non_interactive", False),
    )

    print(f"\n[+] Generating bundle for: {target_info['name']}")
    actual_seed = seed_val if seed_val is not None else random.randint(10000, 999999)

    target_dir = Path("output") / f"{choice_slug(target_info['name'])}-{actual_seed}"
    res = generate_fixture_bundle(
        scenario_name=target_info["scenario"],
        seed=actual_seed,
        output_dir=target_dir,
        override_institution_id=target_info["institution"],
        doc_kind=doc_kind,
        logo_source=logo_source,
    )

    print(
        "\n--------------------------------------------------------------------------"
    )
    print(
        f"  Status:             {'SUCCESS (VALID)' if res.validation.valid else 'INVALID'}"
    )
    print(f"  Target Module:      {target_info['name']}")
    print(f"  Generated Name:     {res.profile.first_name} {res.profile.last_name}")
    print(f"  ID:                 {res.profile.student_id}")
    print(f"  Email:              {res.profile.email}")
    print(
        f"  Institution:        {res.profile.institution_name} ({res.profile.institution_id})"
    )
    print(f"  Output Directory:   {target_dir.resolve()}")
    print("  Artifacts Created:")
    for art in res.artifacts:
        print(
            f"    - {Path(art.path).name} ({art.byte_size} bytes, SHA256: {art.sha256[:10]}...)"
        )
    print("--------------------------------------------------------------------------")
    print(
        "  Note: 'Ignoring CSS ... border-collapse' from xhtml2pdf is normal — engine limitation, tables already use fallbacks; output is valid."
    )
    _print_post_generation_tips(res.profile, service_id=None)
    print(
        "--------------------------------------------------------------------------\n"
    )

    return 0 if res.validation.valid else 1


def _print_post_generation_tips(
    profile: SyntheticProfile,
    service_id: str | None = None,
) -> None:
    """Plain-language next steps to get the highest success rate."""
    inst = profile.institution
    label = inst.pass_rate_label or "n/a"

    print("  What to do next (simple — do all for best chance):")
    if label != "n/a":
        print(
            f"    • Your pick: {inst.name} ({inst.id}) — about {label} success in testing."
        )
        if label.startswith("20"):
            print(
                "      Tip: for a higher estimate, re-run wizard mode [2] Service-optimized and press Enter for makerere (83–90%)."
            )
    print(
        "    • Use the exact name, birthdate and email shown above in the SheerID form — copy/paste, don't fix spelling."
    )
    print(
        "      For intl schools use the generated regional name (Okello, Reyes, Silva) — not John Smith."
    )
    print(
        f"    • Email: use {profile.email} — already has the correct school domain. Click the verification link from the same browser/IP you used to open the SheerID link."
    )
    print(
        "    • Don't edit the PDF/PNG — IDs, term dates, portal name and credits are already in the school's real format."
    )
    print(
        "    • Upload the PNG (real browser screenshot) — it passes Tier A pixel checks better than PDFs. Keep the PDF as backup."
    )
    print(
        "    • Network: use a clean residential proxy — one proxy/IP per verification. Keep the same IP for the whole flow (form → email click → upload). Don't submit many from the same IP quickly — SheerID flags spikes from same IP range (Pillar 0 Anomaly Detection). Avoid datacenter/VPN IPs."
    )
    print(
        "    • Device: keep the same browser/device for the whole flow (SheerID checks device fingerprint). Don't switch IP/device mid-flow."
    )
    print(
        "    • Variation: use a new seed each time (new name/ID). Don't reuse the same document — identical structures from same IP are flagged."
    )
    print("  Further reading (details behind each tip):")
    print(
        "    • International University Template Research — High Pass-Rate Targets.html — institution selection, per-uni ground truth & pass drivers"
    )
    print(
        "    • generation.py — SheerID-Targeted Research & Architecture.html — § Pillar 0 waterfall & Tiers A/B/C + Signal Matrix"
    )
    print(
        "    • generation.py — Verification Engine Research & Architecture.html — original Pillars 1–4 & layout forensics"
    )
    print(
        "    • University Portal Template Research — Real Institutional Templates.html — US portal field formats"
    )
    print("    • README.md / README_EN.md — supported institutions table & CLI usage")
    print("    • SAFE_LOCAL_RUN.md — isolated local testing (Firejail/.venv)")


def choice_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("/", "-").replace(".", "")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Unified Local Identity & Document Generation Framework",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Top-level arguments for wizard when run directly
    parser.add_argument(
        "--target",
        choices=["1", "2", "3", "4", "5", "6", "7", "8"],
        help="Pre-select target workflow for wizard (classic mode)",
    )
    parser.add_argument(
        "--service",
        help="Pre-select service for service-optimized wizard (e.g. spotify, one, youtube, k12, boltnew)",
    )
    parser.add_argument(
        "--institution",
        choices=list(INSTITUTIONS.keys()),
        help="Institution override for wizard",
    )
    parser.add_argument(
        "--scenario",
        help="Scenario override for wizard (undergraduate, graduate, teacher, etc.; aliases like student→undergraduate)",
    )
    parser.add_argument(
        "--wizard-mode",
        "--mode",
        dest="wizard_mode",
        choices=["1", "2", "workflow", "service"],
        help="Wizard mode: 1/workflow (classic) or 2/service (service-optimized)",
    )
    parser.add_argument(
        "--seed", type=int, help="Deterministic seed integer for wizard"
    )
    parser.add_argument(
        "--logo",
        help="Optional institutional logo: local image path or http(s) URL",
    )
    parser.add_argument(
        "--kind",
        choices=[dk.value for dk in DocumentKind],
        help="Document type to generate (schedule, enrollment_certificate, id_card, ...)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # List command
    p_list = subparsers.add_parser(
        "list", help="List available scenarios and institutions"
    )
    p_list.add_argument("--json", action="store_true", help="Format output as JSON")

    # Identity command
    p_id = subparsers.add_parser(
        "identity", help="Generate a canonical synthetic identity profile"
    )
    p_id.add_argument(
        "--scenario",
        default="undergraduate",
        choices=list(SCENARIOS.keys()),
        help="Scenario name",
    )
    p_id.add_argument(
        "--institution",
        choices=list(INSTITUTIONS.keys()),
        help="Institution override (e.g. psu, springfield_k12)",
    )
    p_id.add_argument(
        "--seed", type=int, default=None, help="Deterministic seed integer"
    )
    p_id.add_argument("--json", action="store_true", help="Format output as JSON")

    # Document command
    p_doc = subparsers.add_parser(
        "document", help="Project profile into a logical document model"
    )
    p_doc.add_argument(
        "--scenario",
        default="undergraduate",
        choices=list(SCENARIOS.keys()),
        help="Scenario name",
    )
    p_doc.add_argument(
        "--institution",
        choices=list(INSTITUTIONS.keys()),
        help="Institution override (e.g. psu, springfield_k12)",
    )
    p_doc.add_argument(
        "--kind",
        choices=[dk.value for dk in DocumentKind],
        help="Document kind override",
    )
    p_doc.add_argument(
        "--seed", type=int, default=None, help="Deterministic seed integer"
    )
    p_doc.add_argument("--json", action="store_true", help="Format output as JSON")

    # Render command
    p_rnd = subparsers.add_parser(
        "render", help="Render local HTML, PDF, or PNG document artifact"
    )
    p_rnd.add_argument(
        "--scenario",
        default="undergraduate",
        choices=list(SCENARIOS.keys()),
        help="Scenario name",
    )
    p_rnd.add_argument(
        "--institution",
        choices=list(INSTITUTIONS.keys()),
        help="Institution override (e.g. psu, springfield_k12)",
    )
    p_rnd.add_argument(
        "--kind",
        choices=[dk.value for dk in DocumentKind],
        help="Document kind override",
    )
    p_rnd.add_argument(
        "--format",
        default="html",
        choices=["html", "pdf", "png"],
        help="Output artifact format",
    )
    p_rnd.add_argument(
        "--seed", type=int, default=None, help="Deterministic seed integer"
    )
    p_rnd.add_argument("--output", help="Custom output directory")
    p_rnd.add_argument(
        "--logo",
        help="Optional institutional logo: local image path or http(s) URL",
    )
    p_rnd.add_argument("--json", action="store_true", help="Format output as JSON")

    # Fixture command
    p_fix = subparsers.add_parser(
        "fixture",
        help="Generate complete fixture bundle (JSON, HTML, PDF, PNG, Report)",
    )
    p_fix.add_argument(
        "--scenario",
        default="undergraduate",
        choices=list(SCENARIOS.keys()),
        help="Scenario name",
    )
    p_fix.add_argument(
        "--institution",
        choices=list(INSTITUTIONS.keys()),
        help="Institution override (e.g. psu, springfield_k12)",
    )
    p_fix.add_argument(
        "--seed", type=int, default=12345, help="Deterministic seed integer"
    )
    p_fix.add_argument("--output", help="Custom target output directory")
    p_fix.add_argument(
        "--logo",
        help="Optional institutional logo: local image path or http(s) URL",
    )
    p_fix.add_argument("--json", action="store_true", help="Format output as JSON")

    # Batch command
    p_btc = subparsers.add_parser(
        "batch", help="Run batch fixture generation with summary tracking"
    )
    p_btc.add_argument(
        "--scenario",
        default="undergraduate",
        choices=list(SCENARIOS.keys()),
        help="Scenario name",
    )
    p_btc.add_argument(
        "--institution",
        choices=list(INSTITUTIONS.keys()),
        help="Institution override (e.g. psu, springfield_k12)",
    )
    p_btc.add_argument(
        "--count", type=int, default=10, help="Number of items to generate"
    )
    p_btc.add_argument("--seed", type=int, default=1000, help="Base seed integer")
    p_btc.add_argument("--output", help="Custom target output directory")
    p_btc.add_argument("--json", action="store_true", help="Format output as JSON")

    # Validate command
    p_val = subparsers.add_parser(
        "validate", help="Validate a fixture directory or artifact on disk"
    )
    p_val.add_argument(
        "target", help="Directory path or artifact file path to validate"
    )
    p_val.add_argument("--json", action="store_true", help="Format output as JSON")

    # Inspect command
    p_ins = subparsers.add_parser(
        "inspect", help="Inspect a profile JSON or fixture directory"
    )
    p_ins.add_argument("target", help="Profile JSON file or fixture directory")
    p_ins.add_argument("--json", action="store_true", help="Format output as JSON")

    # Refresh command
    p_ref = subparsers.add_parser(
        "refresh",
        help="Re-render an existing bundle in place from its saved profile (keeps identity)",
    )
    p_ref.add_argument(
        "target", help="Existing bundle directory containing profile.json"
    )
    p_ref.add_argument(
        "--kind",
        choices=[dk.value for dk in DocumentKind],
        default="schedule",
        help="Document kind to regenerate (default: schedule)",
    )
    p_ref.add_argument(
        "--logo",
        help="Optional institutional logo: local image path or http(s) URL (downloaded and cached)",
    )

    # Visual Regression command
    p_vis = subparsers.add_parser(
        "visual-regression",
        aliases=["visreg"],
        help="Run visual regression suite, update baselines, or compare images",
    )
    p_vis.add_argument(
        "--update-baselines",
        action="store_true",
        help="Regenerate golden baseline images and manifest.json",
    )
    p_vis.add_argument(
        "--compare",
        nargs=2,
        metavar=("BASELINE", "CANDIDATE"),
        help="Compare two specific image files directly",
    )
    p_vis.add_argument(
        "--diff-out",
        help="Output file path to save 3-panel diff PNG artifact",
    )
    p_vis.add_argument(
        "--diff-dir",
        help="Directory to save failed candidate and diff artifacts (default: output/visual_regressions)",
    )
    p_vis.add_argument(
        "--baselines-dir",
        help="Directory containing baseline golden images and manifest.json",
    )
    p_vis.add_argument(
        "--threshold",
        type=float,
        default=0.005,
        help="Maximum allowed differing pixel ratio (default: 0.005)",
    )
    p_vis.add_argument(
        "--color-tolerance",
        type=int,
        default=15,
        help="Per-channel color delta tolerance (0-255, default: 15)",
    )
    p_vis.add_argument("--json", action="store_true", help="Format output as JSON")

    # Wizard command (default)
    p_wiz = subparsers.add_parser(
        "wizard",
        help="Interactive menu to select a target workflow/module and generate everything",
    )
    p_wiz.add_argument(
        "--target",
        choices=["1", "2", "3", "4", "5", "6", "7", "8"],
        help="Pre-select target workflow (classic mode)",
    )
    p_wiz.add_argument(
        "--service",
        help="Pre-select service for service-optimized mode (e.g. spotify, one, youtube, k12, boltnew)",
    )
    p_wiz.add_argument(
        "--institution",
        choices=list(INSTITUTIONS.keys()),
        help="Institution override for wizard",
    )
    p_wiz.add_argument(
        "--scenario",
        help="Scenario override for wizard (aliases: student→undergraduate)",
    )
    p_wiz.add_argument(
        "--wizard-mode",
        "--mode",
        dest="wizard_mode",
        choices=["1", "2", "workflow", "service"],
        help="Wizard mode: 1/workflow or 2/service",
    )
    p_wiz.add_argument("--seed", type=int, help="Deterministic seed integer")
    p_wiz.add_argument(
        "--logo",
        help="Optional institutional logo: local image path or http(s) URL",
    )
    p_wiz.add_argument(
        "--kind",
        choices=[dk.value for dk in DocumentKind],
        help="Document type to generate (schedule, enrollment_certificate, id_card, ...)",
    )

    args = parser.parse_args()

    if not args.command:
        # If no subcommand was given, run the interactive wizard (passing top-level --target and --seed)
        return cmd_wizard(args)

    commands = {
        "wizard": cmd_wizard,
        "list": cmd_list,
        "identity": cmd_identity,
        "document": cmd_document,
        "render": cmd_render,
        "fixture": cmd_fixture,
        "batch": cmd_batch,
        "validate": cmd_validate,
        "inspect": cmd_inspect,
        "refresh": cmd_refresh,
        "visual-regression": cmd_visual_regression,
        "visreg": cmd_visual_regression,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
