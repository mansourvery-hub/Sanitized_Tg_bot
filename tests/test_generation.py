"""
Tests for local identity and document generation system.
"""

import json
import random
import shutil
import tempfile
import unittest
from datetime import date
from io import BytesIO
from pathlib import Path

import pypdf
from PIL import Image

from generation import (
    GENERATOR_VERSION,
    INSTITUTIONS,
    DocumentArchetype,
    DocumentKind,
    SyntheticProfile,
    _current_term,
    _current_term_for_institution,
    _document_print_date,
    _generate_crn,
    _generate_student_id,
    _html_to_pdf,
    _resolve_css_vars,
    generate_batch,
    generate_document,
    generate_fixture_bundle,
    generate_profile,
    inspect_readback_artifact,
    list_scenarios,
    readback_validate_html,
    readback_validate_pdf,
    render_pdf,
    render_png,
    validate_document,
    validate_profile,
)


class TestGenerationSystem(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_identity_determinism(self):
        profile1 = generate_profile(seed=42)
        profile2 = generate_profile(seed=42)
        profile3 = generate_profile(seed=99)

        self.assertEqual(profile1.first_name, profile2.first_name)
        self.assertEqual(profile1.last_name, profile2.last_name)
        self.assertEqual(profile1.student_id, profile2.student_id)
        self.assertEqual(profile1.email, profile2.email)
        self.assertNotEqual(profile1.student_id, profile3.student_id)

    def test_profile_constraints(self):
        profile = generate_profile(scenario_name="undergraduate", seed=123)
        self.assertGreater(profile.enrollment_date, profile.date_of_birth)
        self.assertGreater(profile.expected_graduation, profile.enrollment_date)
        self.assertIn("@", profile.email)

    def test_institution_consistency(self):
        profile = generate_profile(scenario_name="undergraduate", seed=42)
        self.assertEqual(profile.institution_id, "psu")
        self.assertEqual(profile.institution.portal_name, "LionPATH")
        self.assertEqual(
            profile.institution.producer_string, "Oracle PeopleTools 8.59.15"
        )
        self.assertTrue(profile.student_id.isdigit())
        self.assertEqual(len(profile.student_id), 9)

    def test_institution_id_generation_formats(self):
        rng = random.Random(42)
        psu_id = _generate_student_id(rng, INSTITUTIONS["psu"])
        self.assertEqual(len(psu_id), 9)
        self.assertTrue(psu_id.startswith("9"))

        tech_id = _generate_student_id(rng, INSTITUTIONS["nittany_tech"])
        self.assertTrue(tech_id.startswith("N"))
        self.assertEqual(len(tech_id), 9)

        k12_id = _generate_student_id(rng, INSTITUTIONS["springfield_k12"])
        self.assertTrue(k12_id.startswith("E-"))
        self.assertEqual(len(k12_id), 9)

    def test_dynamic_term_resolution(self):
        # Fall test
        season, year, start, end = _current_term(date(2026, 10, 15))
        self.assertEqual(season, "Fall")
        self.assertEqual(year, 2026)
        self.assertLessEqual(start, date(2026, 10, 15))
        self.assertGreaterEqual(end, date(2026, 10, 15))

        # Spring test
        season, year, start, end = _current_term(date(2026, 2, 20))
        self.assertEqual(season, "Spring")
        self.assertEqual(year, 2026)

        # Summer test
        season, year, start, end = _current_term(date(2026, 6, 10))
        self.assertEqual(season, "Summer")
        self.assertEqual(year, 2026)

    def test_document_print_date_constraints(self):
        rng = random.Random(99)
        ref = date(2026, 10, 15)
        term_start = date(2026, 8, 26)
        print_dt = _document_print_date(rng, term_start, as_of=ref)

        self.assertLess(print_dt.date(), ref)
        self.assertGreaterEqual(print_dt.date(), term_start)
        self.assertGreaterEqual(print_dt.hour, 8)
        self.assertLessEqual(print_dt.hour, 17)

    def test_crn_generation_diversity(self):
        rng = random.Random(123)
        crns = [_generate_crn(rng, "psu", i) for i in range(5)]
        self.assertEqual(len(crns), 5)
        self.assertEqual(len(set(crns)), 5)  # all distinct
        for crn in crns:
            self.assertEqual(len(crn), 5)
            self.assertFalse(crn == crn[::-1])  # not palindromic

    def test_synthetic_profile_extended_fields_and_serialization(self):
        profile = generate_profile(scenario_name="undergraduate", seed=42)
        self.assertTrue(len(profile.current_term_label) > 0)
        self.assertIsNotNone(profile.term_start_date)
        self.assertIsNotNone(profile.term_end_date)
        self.assertIsNotNone(profile.document_print_date)
        self.assertGreater(profile.gpa_cumulative, 0.0)
        self.assertGreater(len(profile.advisor_name), 0)
        self.assertGreater(len(profile.document_seal_hash), 0)

        # Serialization round-trip
        data = profile.to_dict()
        restored = SyntheticProfile.from_dict(data)
        self.assertEqual(restored.first_name, profile.first_name)
        self.assertEqual(restored.last_name, profile.last_name)
        self.assertEqual(restored.current_term_label, profile.current_term_label)
        self.assertEqual(restored.term_start_date, profile.term_start_date)
        self.assertEqual(restored.term_end_date, profile.term_end_date)

    def test_resolve_css_vars(self):
        html_input = '<div style="background: var(--bg-light); color: var(--psu-blue); border: var(--custom, #123456);"></div>'
        resolved = _resolve_css_vars(html_input)
        self.assertIn("#f4f6f9", resolved)
        self.assertIn("#1E407C", resolved)
        self.assertIn("#123456", resolved)
        self.assertNotIn("var(--psu-blue)", resolved)

    def test_spoofed_pdf_metadata(self):
        profile = generate_profile(scenario_name="undergraduate", seed=42)
        doc = generate_document(profile, doc_kind=DocumentKind.SCHEDULE)
        pdf_bytes = render_pdf(
            doc.html_content,
            institution=profile.institution,
            profile=profile,
            term_label=profile.current_term_label,
        )

        reader = pypdf.PdfReader(BytesIO(pdf_bytes))
        metadata = reader.metadata
        self.assertIsNotNone(metadata)
        assert metadata is not None
        self.assertEqual(metadata.producer, profile.institution.producer_string)
        self.assertEqual(metadata.creator, profile.institution.pdf_creator)
        self.assertIn(profile.institution.portal_name, str(metadata.title))
        self.assertIn(profile.institution.name, str(metadata.get("/Keywords", "")))
        self.assertIsNotNone(metadata.creation_date)

    def test_render_png_high_fidelity(self):
        html = "<html><body><h1>High Fidelity Verification</h1></body></html>"
        png_bytes = render_png(html, width=800, height=600, require_high_fidelity=True)
        self.assertTrue(png_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(png_bytes), 1000)

    def test_teacher_scenario_constraints(self):
        profile = generate_profile(scenario_name="teacher", seed=77)
        self.assertEqual(profile.academic_level.value, "k12_teacher")
        self.assertTrue(profile.email.endswith(".org"))
        self.assertTrue(profile.student_id.startswith("E-"))

    def test_document_generation(self):
        profile = generate_profile(seed=42)
        doc = generate_document(profile, doc_kind=DocumentKind.SCHEDULE)

        self.assertIn(profile.first_name, doc.html_content)
        self.assertIn(profile.last_name, doc.html_content)
        self.assertIn(profile.student_id, doc.html_content)
        self.assertTrue(doc.rendered_html.startswith("<!DOCTYPE html>"))

    def test_profile_and_document_validation(self):
        profile = generate_profile(seed=42)
        val_profile = validate_profile(profile)
        self.assertTrue(val_profile.valid)
        self.assertEqual(len(val_profile.errors), 0)

        doc = generate_document(profile, doc_kind=DocumentKind.SCHEDULE)
        val_doc = validate_document(doc, profile)
        self.assertTrue(val_doc.valid)
        self.assertEqual(len(val_doc.errors), 0)

    def test_fixture_generation(self):
        out_dir = self.tmp_path / "test_fixture"
        res = generate_fixture_bundle(
            scenario_name="undergraduate",
            seed=42,
            output_dir=out_dir,
        )

        self.assertTrue(res.validation.valid)
        self.assertTrue((out_dir / "profile.json").exists())
        self.assertTrue((out_dir / "document.html").exists())
        self.assertTrue((out_dir / "document.pdf").exists())
        self.assertTrue((out_dir / "document.png").exists())
        self.assertTrue((out_dir / "report.json").exists())

        with open(out_dir / "report.json", encoding="utf-8") as f:
            data = json.load(f)
            self.assertTrue(data["profile_valid"])
            self.assertEqual(data["generator_version"], GENERATOR_VERSION)

    def test_readback_validation_html(self):
        profile = generate_profile(scenario_name="undergraduate", seed=42)
        doc = generate_document(profile, doc_kind=DocumentKind.SCHEDULE)
        html_str = doc.html_content

        rb_val = readback_validate_html(html_str, profile)
        self.assertTrue(rb_val.valid, f"Readback failed errors: {rb_val.errors}")

    def test_readback_validation_pdf(self):
        profile = generate_profile(scenario_name="undergraduate", seed=42)
        doc = generate_document(profile, doc_kind=DocumentKind.SCHEDULE)
        html_str = doc.html_content

        pdf_bytes = _html_to_pdf(html_str)

        rb_val = readback_validate_pdf(pdf_bytes, profile)
        self.assertTrue(rb_val.valid, f"PDF Readback errors: {rb_val.errors}")

    def test_inspect_readback_artifact_missing_and_empty_file(self):
        profile = generate_profile(scenario_name="undergraduate", seed=42)
        non_existent = self.tmp_path / "missing.html"
        val = inspect_readback_artifact(non_existent, profile)
        self.assertFalse(val.valid)
        self.assertIn("FILE_NOT_FOUND", [e.code for e in val.errors])

        empty_file = self.tmp_path / "empty.html"
        empty_file.touch()
        val = inspect_readback_artifact(empty_file, profile)
        self.assertFalse(val.valid)
        self.assertIn("EMPTY_FILE", [e.code for e in val.errors])

    def test_inspect_readback_artifact_html_preflight_valid(self):
        profile = generate_profile(scenario_name="undergraduate", seed=42)
        doc = generate_document(profile, doc_kind=DocumentKind.SCHEDULE)
        path = self.tmp_path / "valid_schedule.html"
        path.write_text(doc.html_content, encoding="utf-8")

        val = inspect_readback_artifact(path, profile, preflight_mode=True)
        self.assertTrue(
            val.valid, f"Expected valid HTML readback, got errors: {val.errors}"
        )
        self.assertEqual(len(val.errors), 0)

    def test_inspect_readback_artifact_html_preflight_checks_and_bypass(self):
        profile = generate_profile(scenario_name="undergraduate", seed=42)

        # 1. Missing name and ID
        bad_html_path = self.tmp_path / "unrelated.html"
        bad_html_path.write_text(
            "<html><body>Generic Unrelated Document</body></html>", encoding="utf-8"
        )
        val = inspect_readback_artifact(bad_html_path, profile, preflight_mode=False)
        self.assertFalse(val.valid)
        codes = [e.code for e in val.errors]
        self.assertIn("READBACK_NAME_MISSING", codes)
        self.assertIn("READBACK_ID_MISSING", codes)

        # 2. Missing current term label in standard academic document
        no_term_html = (
            f"<html><body>"
            f"<p>{profile.first_name} {profile.last_name}</p>"
            f"<p>ID: {profile.student_id}</p>"
            f"<p>Institution: {profile.institution_name}</p>"
            f"</body></html>"
        )
        no_term_path = self.tmp_path / "no_term.html"
        no_term_path.write_text(no_term_html, encoding="utf-8")

        val_preflight = inspect_readback_artifact(
            no_term_path, profile, preflight_mode=True
        )
        self.assertFalse(val_preflight.valid)
        self.assertIn("VERIFY_MISSING_TERM", [e.code for e in val_preflight.errors])

        val_no_preflight = inspect_readback_artifact(
            no_term_path, profile, preflight_mode=False
        )
        self.assertTrue(val_no_preflight.valid)
        self.assertNotIn(
            "VERIFY_MISSING_TERM", [e.code for e in val_no_preflight.errors]
        )

        # 3. Institution name mismatch
        wrong_inst_html = (
            f"<html><body>"
            f"<p>{profile.first_name} {profile.last_name}</p>"
            f"<p>ID: {profile.student_id}</p>"
            f"<p>Term: {profile.current_term_label}</p>"
            f"<p>Institution: Unrelated State College</p>"
            f"</body></html>"
        )
        wrong_inst_path = self.tmp_path / "wrong_inst.html"
        wrong_inst_path.write_text(wrong_inst_html, encoding="utf-8")

        val_inst_err = inspect_readback_artifact(
            wrong_inst_path, profile, preflight_mode=True
        )
        self.assertFalse(val_inst_err.valid)
        self.assertIn(
            "VERIFY_INSTITUTION_MISMATCH", [e.code for e in val_inst_err.errors]
        )

        # 4. ID Card exempt from term requirement
        id_card_html = (
            f"<html><body>"
            f"<h1>Student ID Card</h1>"
            f"<p>{profile.first_name} {profile.last_name}</p>"
            f"<p>ID: {profile.student_id}</p>"
            f"<p>Institution: {profile.institution_name}</p>"
            f"</body></html>"
        )
        id_card_path = self.tmp_path / "id_card.html"
        id_card_path.write_text(id_card_html, encoding="utf-8")

        val_id = inspect_readback_artifact(id_card_path, profile, preflight_mode=True)
        self.assertTrue(
            val_id.valid, f"ID card should not fail for missing term: {val_id.errors}"
        )
        self.assertNotIn("VERIFY_MISSING_TERM", [e.code for e in val_id.errors])

    def test_inspect_readback_artifact_pdf_preflight_valid_and_fingerprints(self):
        profile = generate_profile(scenario_name="undergraduate", seed=42)
        doc = generate_document(profile, doc_kind=DocumentKind.SCHEDULE)
        pdf_bytes = render_pdf(
            doc.html_content,
            institution=profile.institution,
            profile=profile,
            term_label=profile.current_term_label,
        )

        valid_pdf_path = self.tmp_path / "schedule.pdf"
        valid_pdf_path.write_bytes(pdf_bytes)

        # 1. Valid PDF passing preflight inspection
        val = inspect_readback_artifact(valid_pdf_path, profile, preflight_mode=True)
        self.assertTrue(
            val.valid, f"Expected valid PDF readback, got errors: {val.errors}"
        )

        # 2. Invalid PDF magic header
        bad_magic_path = self.tmp_path / "invalid_magic.pdf"
        bad_magic_path.write_bytes(b"NOT_A_REAL_PDF_HEADER")
        val_bad_magic = inspect_readback_artifact(
            bad_magic_path, profile, preflight_mode=False
        )
        self.assertFalse(val_bad_magic.valid)
        self.assertIn("PDF_MAGIC_INVALID", [e.code for e in val_bad_magic.errors])

        # 3. PDF with unsanitized generator fingerprint
        reader = pypdf.PdfReader(BytesIO(pdf_bytes))
        writer = pypdf.PdfWriter()
        writer.append_pages_from_reader(reader)
        writer.add_metadata({"/Producer": "xhtml2pdf 0.2.20"})
        buf = BytesIO()
        writer.write(buf)

        bad_producer_path = self.tmp_path / "unsanitized_producer.pdf"
        bad_producer_path.write_bytes(buf.getvalue())

        val_fp_preflight = inspect_readback_artifact(
            bad_producer_path, profile, preflight_mode=True
        )
        self.assertFalse(val_fp_preflight.valid)
        self.assertIn(
            "PDF_PRODUCER_FINGERPRINT", [e.code for e in val_fp_preflight.errors]
        )

        val_fp_bypassed = inspect_readback_artifact(
            bad_producer_path, profile, preflight_mode=False
        )
        self.assertTrue(val_fp_bypassed.valid)
        self.assertNotIn(
            "PDF_PRODUCER_FINGERPRINT", [e.code for e in val_fp_bypassed.errors]
        )

    def test_inspect_readback_artifact_images(self):
        profile = generate_profile(scenario_name="undergraduate", seed=42)

        # 1. Invalid image magic
        bad_png = self.tmp_path / "corrupt.png"
        bad_png.write_bytes(b"NOT_A_PNG")
        val_png = inspect_readback_artifact(bad_png, profile, preflight_mode=False)
        self.assertFalse(val_png.valid)
        self.assertIn("PNG_MAGIC_INVALID", [e.code for e in val_png.errors])

        bad_jpeg = self.tmp_path / "corrupt.jpg"
        bad_jpeg.write_bytes(b"NOT_A_JPEG")
        val_jpg = inspect_readback_artifact(bad_jpeg, profile, preflight_mode=False)
        self.assertFalse(val_jpg.valid)
        self.assertIn("JPEG_MAGIC_INVALID", [e.code for e in val_jpg.errors])

        # 2. Low-resolution PNG (< 1000px width)
        low_res = Image.new("RGB", (640, 480), color="white")
        low_res_path = self.tmp_path / "low_res.png"
        low_res.save(low_res_path, format="PNG")

        val_low_res = inspect_readback_artifact(
            low_res_path, profile, preflight_mode=True
        )
        self.assertFalse(val_low_res.valid)
        self.assertIn("PNG_RESOLUTION_LOW", [e.code for e in val_low_res.errors])

        val_low_res_bypassed = inspect_readback_artifact(
            low_res_path, profile, preflight_mode=False
        )
        self.assertTrue(val_low_res_bypassed.valid)
        self.assertNotIn(
            "PNG_RESOLUTION_LOW", [e.code for e in val_low_res_bypassed.errors]
        )

        # 3. High-resolution PNG (>= 1000px width)
        hi_res = Image.new("RGB", (1280, 900), color="white")
        hi_res_path = self.tmp_path / "hi_res.png"
        hi_res.save(hi_res_path, format="PNG")

        val_hi_res = inspect_readback_artifact(
            hi_res_path, profile, preflight_mode=True
        )
        self.assertTrue(val_hi_res.valid)

    def test_batch_generation(self):
        out_dir = self.tmp_path / "batch_test"
        res = generate_batch(
            scenario_name="undergraduate",
            count=5,
            base_seed=100,
            output_dir=out_dir,
        )

        self.assertEqual(res["total"], 5)
        self.assertEqual(res["valid"], 5)
        self.assertEqual(res["invalid"], 0)
        self.assertTrue((out_dir / "summary.json").exists())

    def test_scenarios_list(self):
        scenarios = list_scenarios()
        self.assertIn("undergraduate", scenarios)
        self.assertIn("graduate", scenarios)
        self.assertIn("teacher", scenarios)

    def test_five_institutions_id_formats(self):
        for seed in range(1, 30):
            rng = random.Random(seed)
            # PSU: 9 digits starting with 9
            psu_id = _generate_student_id(rng, INSTITUTIONS["psu"])
            self.assertEqual(len(psu_id), 9)
            self.assertTrue(psu_id.isdigit())
            self.assertTrue(psu_id.startswith("9"))

            # UCLA: 9 digits starting with 9
            ucla_id = _generate_student_id(rng, INSTITUTIONS["ucla"])
            self.assertEqual(len(ucla_id), 9)
            self.assertTrue(ucla_id.isdigit())
            self.assertTrue(ucla_id.startswith("9"))

            # NYU: N followed by 8 digits
            nyu_id = _generate_student_id(rng, INSTITUTIONS["nyu"])
            self.assertEqual(len(nyu_id), 9)
            self.assertTrue(nyu_id.startswith("N"))
            self.assertTrue(nyu_id[1:].isdigit())

            # UMich: 8 digits
            umich_id = _generate_student_id(rng, INSTITUTIONS["umich"])
            self.assertEqual(len(umich_id), 8)
            self.assertTrue(umich_id.isdigit())

            # UT Austin: 2-4 lowercase letters + 3-5 digits
            ut_id = _generate_student_id(rng, INSTITUTIONS["ut_austin"])
            self.assertTrue(any(c.isalpha() for c in ut_id))
            self.assertTrue(any(c.isdigit() for c in ut_id))
            self.assertTrue(ut_id.islower())

    def test_umich_winter_term_calendar(self):
        # January-April must return Winter for UMich, never Spring
        jan_term = _current_term(date(2026, 1, 15), institution_id="umich")
        self.assertEqual(jan_term[0], "Winter")
        self.assertEqual(jan_term[1], 2026)

        mar_term = _current_term(date(2026, 3, 20), institution_id="umich")
        self.assertEqual(mar_term[0], "Winter")
        self.assertEqual(mar_term[1], 2026)

        label, _, _ = _current_term_for_institution("umich", date(2026, 2, 10))
        self.assertIn("Winter", label)
        self.assertNotIn("Spring", label)

    def test_ucla_quarter_calendar(self):
        label_fall, _, _ = _current_term_for_institution("ucla", date(2026, 10, 15))
        self.assertIn("Fall", label_fall)

        label_winter, _, _ = _current_term_for_institution("ucla", date(2027, 2, 10))
        self.assertIn("Winter", label_winter)

        label_spring, _, _ = _current_term_for_institution("ucla", date(2027, 4, 15))
        self.assertIn("Spring", label_spring)

    def test_document_archetypes_and_registrar_letters(self):
        # UCLA: REGISTRAR_LETTER
        ucla_prof = generate_profile(
            scenario_name="undergraduate",
            institution_id="ucla",
            seed=42,
        )
        self.assertEqual(
            ucla_prof.institution.document_archetype, DocumentArchetype.REGISTRAR_LETTER
        )
        ucla_doc = generate_document(ucla_prof, doc_kind=DocumentKind.SCHEDULE)
        self.assertNotIn("<th>Course</th>", ucla_doc.html_content)
        self.assertNotIn("<th>CRN</th>", ucla_doc.html_content)
        self.assertIn("ENROLLMENT VERIFICATION", ucla_doc.html_content)
        self.assertIn("OFFICE OF THE REGISTRAR", ucla_doc.html_content)
        self.assertIn("University of California, Los Angeles", ucla_doc.html_content)
        val_ucla = readback_validate_html(ucla_doc.html_content, ucla_prof)
        self.assertTrue(val_ucla.valid, f"UCLA readback failed: {val_ucla.errors}")

        # UT Austin: REGISTRAR_LETTER
        ut_prof = generate_profile(
            scenario_name="undergraduate",
            institution_id="ut_austin",
            seed=42,
        )
        self.assertEqual(
            ut_prof.institution.document_archetype, DocumentArchetype.REGISTRAR_LETTER
        )
        ut_doc = generate_document(ut_prof, doc_kind=DocumentKind.SCHEDULE)
        self.assertNotIn("<th>Course</th>", ut_doc.html_content)
        self.assertNotIn("<th>CRN</th>", ut_doc.html_content)
        self.assertIn("ENROLLMENT CERTIFICATION", ut_doc.html_content)
        self.assertIn("The University of Texas at Austin", ut_doc.html_content)
        val_ut = readback_validate_html(ut_doc.html_content, ut_prof)
        self.assertTrue(val_ut.valid, f"UT Austin readback failed: {val_ut.errors}")

        # PSU: PORTAL_SCREENSHOT
        psu_prof = generate_profile(
            scenario_name="undergraduate",
            institution_id="psu",
            seed=42,
        )
        self.assertEqual(
            psu_prof.institution.document_archetype,
            DocumentArchetype.PORTAL_SCREENSHOT,
        )
        psu_doc = generate_document(psu_prof, doc_kind=DocumentKind.SCHEDULE)
        self.assertIn("<th>Course</th>", psu_doc.html_content)
        self.assertIn("LionPATH", psu_doc.html_content)
        val_psu = readback_validate_html(psu_doc.html_content, psu_prof)
        self.assertTrue(val_psu.valid, f"PSU readback failed: {val_psu.errors}")

        # NYU: PORTAL_SCREENSHOT
        nyu_prof = generate_profile(
            scenario_name="undergraduate",
            institution_id="nyu",
            seed=42,
        )
        self.assertEqual(
            nyu_prof.institution.document_archetype,
            DocumentArchetype.PORTAL_SCREENSHOT,
        )
        nyu_doc = generate_document(nyu_prof, doc_kind=DocumentKind.SCHEDULE)
        self.assertIn("<th>Course</th>", nyu_doc.html_content)
        self.assertIn("Albert Student Center", nyu_doc.html_content)
        val_nyu = readback_validate_html(nyu_doc.html_content, nyu_prof)
        self.assertTrue(val_nyu.valid, f"NYU readback failed: {val_nyu.errors}")

        # UMich: PORTAL_SCREENSHOT
        umich_prof = generate_profile(
            scenario_name="undergraduate",
            institution_id="umich",
            seed=42,
        )
        self.assertEqual(
            umich_prof.institution.document_archetype,
            DocumentArchetype.PORTAL_SCREENSHOT,
        )
        umich_doc = generate_document(umich_prof, doc_kind=DocumentKind.SCHEDULE)
        self.assertIn("<th>Course</th>", umich_doc.html_content)
        self.assertIn("Wolverine Access", umich_doc.html_content)
        val_umich = readback_validate_html(umich_doc.html_content, umich_prof)
        self.assertTrue(val_umich.valid, f"UMich readback failed: {val_umich.errors}")

    def test_institution_backward_compatibility(self):
        self.assertIn("springfield_k12", INSTITUTIONS)
        self.assertIn("nittany_tech", INSTITUTIONS)
        k12 = INSTITUTIONS["springfield_k12"]
        # Test backward-compatible aliases
        self.assertEqual(k12.producer_string, k12.pdf_producer)
        self.assertEqual(k12.id_format, k12.student_id_format)
        self.assertEqual(k12.id_prefix, k12.student_id_prefix)

        # Ensure teacher scenario still generates valid profile and faculty summary
        teacher_prof = generate_profile(scenario_name="teacher", seed=10)
        self.assertEqual(teacher_prof.role, "teacher")
        val_t = validate_profile(teacher_prof)
        self.assertTrue(val_t.valid)
        doc_t = generate_document(teacher_prof, doc_kind=DocumentKind.FACULTY_SUMMARY)
        self.assertEqual(doc_t.kind, DocumentKind.FACULTY_SUMMARY)
        val_doc_t = validate_document(doc_t)
        self.assertTrue(val_doc_t.valid)

    def test_all_document_kinds_across_institutions(self):
        institutions = ["psu", "ucla", "nyu", "umich", "ut_austin"]
        for inst_id in institutions:
            prof = generate_profile(
                scenario_name="undergraduate",
                institution_id=inst_id,
                seed=77,
            )
            # Test Tuition Receipt
            tuition_doc = generate_document(prof, doc_kind=DocumentKind.TUITION_RECEIPT)
            self.assertEqual(tuition_doc.kind, DocumentKind.TUITION_RECEIPT)
            self.assertIn(prof.first_name, tuition_doc.html_content)
            self.assertIn(prof.student_id, tuition_doc.html_content)
            self.assertIn(prof.institution.primary_color, tuition_doc.html_content)
            val_t = validate_document(tuition_doc)
            self.assertTrue(
                val_t.valid, f"Tuition receipt invalid for {inst_id}: {val_t.errors}"
            )

            # Test ID Card
            id_doc = generate_document(prof, doc_kind=DocumentKind.ID_CARD)
            self.assertEqual(id_doc.kind, DocumentKind.ID_CARD)
            self.assertIn(prof.first_name, id_doc.html_content)
            self.assertIn(prof.student_id, id_doc.html_content)
            self.assertIn(prof.institution.primary_color, id_doc.html_content)
            val_id = validate_document(id_doc)
            self.assertTrue(
                val_id.valid, f"ID card invalid for {inst_id}: {val_id.errors}"
            )

            # Test Enrollment Certificate
            cert_doc = generate_document(
                prof, doc_kind=DocumentKind.ENROLLMENT_CERTIFICATE
            )
            self.assertEqual(cert_doc.kind, DocumentKind.ENROLLMENT_CERTIFICATE)
            self.assertIn(prof.first_name, cert_doc.html_content)
            self.assertIn(prof.student_id, cert_doc.html_content)
            self.assertIn(prof.institution.primary_color, cert_doc.html_content)
            val_cert = validate_document(cert_doc)
            self.assertTrue(
                val_cert.valid, f"Certificate invalid for {inst_id}: {val_cert.errors}"
            )


if __name__ == "__main__":
    unittest.main()
