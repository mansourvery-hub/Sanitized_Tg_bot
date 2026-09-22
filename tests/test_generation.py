"""
Tests for local identity and document generation system.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from generation import (
    GENERATOR_VERSION,
    AcademicLevel,
    DocumentKind,
    GenerationReport,
    GenerationResult,
    Institution,
    PersonRole,
    SyntheticProfile,
    ValidationError,
    generate_batch,
    generate_document,
    generate_fixture_bundle,
    generate_profile,
    SCENARIOS,
    list_scenarios,
    readback_validate_html,
    readback_validate_pdf,
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
        self.assertTrue(profile.email.endswith(profile.institution.domain))

    def test_institution_consistency(self):
        profile = generate_profile(scenario_name="undergraduate", seed=456)
        self.assertEqual(profile.institution_id, profile.institution.id)
        self.assertEqual(profile.institution_name, profile.institution.name)

    def test_teacher_scenario_constraints(self):
        profile = generate_profile(scenario_name="teacher", seed=789)
        self.assertEqual(profile.role, PersonRole.TEACHER)
        self.assertEqual(profile.academic_level, AcademicLevel.K12_TEACHER)
        self.assertIsNotNone(profile.hire_date)
        self.assertIsNotNone(profile.employee_id)

    def test_document_generation(self):
        profile = generate_profile(scenario_name="undergraduate", seed=42)
        doc = generate_document(profile, doc_kind=DocumentKind.SCHEDULE)

        self.assertEqual(doc.kind, DocumentKind.SCHEDULE)
        self.assertEqual(doc.profile.student_id, profile.student_id)
        self.assertIn(profile.first_name, doc.fields["Student Name"])

    def test_profile_and_document_validation(self):
        profile = generate_profile(scenario_name="undergraduate", seed=42)
        val_res = validate_profile(profile)
        self.assertTrue(val_res.valid)
        self.assertEqual(len(val_res.errors), 0)

        doc = generate_document(profile, doc_kind=DocumentKind.SCHEDULE)
        doc_val = validate_document(doc)
        self.assertTrue(doc_val.valid)

    def test_fixture_generation(self):
        out_dir = self.tmp_path / "test_fix_42"
        res = generate_fixture_bundle(
            scenario_name="undergraduate",
            seed=42,
            output_dir=out_dir,
        )

        self.assertTrue(res.validation.valid)
        self.assertTrue((out_dir / "profile.json").exists())
        self.assertTrue((out_dir / "document.html").exists())
        self.assertTrue((out_dir / "document.pdf").exists())
        self.assertTrue((out_dir / "report.json").exists())

        with open(out_dir / "report.json", "r", encoding="utf-8") as f:
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

        from generation import _html_to_pdf
        pdf_bytes = _html_to_pdf(html_str)

        rb_val = readback_validate_pdf(pdf_bytes, profile)
        self.assertTrue(rb_val.valid, f"PDF Readback errors: {rb_val.errors}")

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


if __name__ == "__main__":
    unittest.main()
