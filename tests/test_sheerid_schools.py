"""Unit tests for SheerID institution directory and multi-institution verifier routing."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from Boltnew.img_generator import generate_images as boltnew_generate_images
from one.img_generator import generate_image as one_generate_image
from sheerid_schools import (
    DEFAULT_SCHOOL_ID,
    TARGET_INSTITUTION_SCHOOLS,
    generate_institutional_student_email,
    get_available_institutions_summary,
    resolve_sheerid_school,
)
from spotify.img_generator import generate_image as spotify_generate_image
from youtube.img_generator import generate_image as youtube_generate_image


class TestSheerIDSchoolResolution(unittest.TestCase):
    """Tests for resolving school inputs and aliases."""

    def test_default_resolution_on_none_or_empty(self):
        canonical_id, school = resolve_sheerid_school(None)
        self.assertEqual(canonical_id, DEFAULT_SCHOOL_ID)
        self.assertEqual(school["id"], 2565)
        self.assertEqual(school["domain"], "PSU.EDU")

        canonical_id_empty, school_empty = resolve_sheerid_school("   ")
        self.assertEqual(canonical_id_empty, DEFAULT_SCHOOL_ID)
        self.assertEqual(school_empty["id"], 2565)

    def test_alias_and_numeric_resolutions(self):
        cases = [
            ("psu", "2565", "psu", "PSU.EDU"),
            ("penn_state", "2565", "psu", "PSU.EDU"),
            ("ucla", "285", "ucla", "UCLA.EDU"),
            ("285", "285", "ucla", "UCLA.EDU"),
            ("nyu", "2678", "nyu", "NYU.EDU"),
            ("2678", "2678", "nyu", "NYU.EDU"),
            ("umich", "2027", "umich", "UMICH.EDU"),
            ("michigan", "2027", "umich", "UMICH.EDU"),
            ("2027", "2027", "umich", "UMICH.EDU"),
            ("ut_austin", "3895", "ut_austin", "UTEXAS.EDU"),
            ("utaustin", "3895", "ut_austin", "UTEXAS.EDU"),
            ("texas", "3895", "ut_austin", "UTEXAS.EDU"),
            ("3895", "3895", "ut_austin", "UTEXAS.EDU"),
        ]
        for slug, expected_id, expected_inst_id, expected_domain in cases:
            with self.subTest(slug=slug):
                cid, metadata = resolve_sheerid_school(slug)
                self.assertEqual(cid, expected_id)
                self.assertEqual(metadata["inst_id"], expected_inst_id)
                self.assertEqual(metadata["domain"], expected_domain)

    def test_regional_campus_fallback(self):
        fallback_schools = {
            "651379": {
                "id": 651379,
                "idExtended": "651379",
                "name": "Pennsylvania State University-World Campus",
                "domain": "PSU.EDU",
            }
        }
        cid, metadata = resolve_sheerid_school(
            "651379", fallback_schools=fallback_schools
        )
        self.assertEqual(cid, "651379")
        self.assertEqual(metadata["name"], "Pennsylvania State University-World Campus")
        self.assertEqual(metadata["inst_id"], "psu")

    def test_unknown_school_falls_back_to_default(self):
        cid, metadata = resolve_sheerid_school("some_nonexistent_school_xyz")
        self.assertEqual(cid, DEFAULT_SCHOOL_ID)
        self.assertEqual(metadata["id"], 2565)


class TestEmailGenerationAndSummary(unittest.TestCase):
    """Tests for institutional email generation and catalog summary."""

    def test_generate_institutional_student_email(self):
        email = generate_institutional_student_email("Jane", "Doe", "UCLA.EDU")
        self.assertTrue(email.startswith("jane.doe"))
        self.assertTrue(email.endswith("@ucla.edu"))
        local_part = email.split("@")[0]
        digits = local_part.replace("jane.doe", "")
        self.assertTrue(digits.isdigit())
        self.assertTrue(3 <= len(digits) <= 4)

    def test_get_available_institutions_summary(self):
        summary = get_available_institutions_summary()
        self.assertGreaterEqual(len(summary), 5)
        slugs = {item["slug"] for item in summary}
        self.assertTrue({"psu", "ucla", "nyu", "umich", "ut_austin"}.issubset(slugs))


class TestConfigSynchronization(unittest.TestCase):
    """Verify that verifier module configs expose all target institutions."""

    def test_one_config_contains_target_schools(self):
        from one.config import SCHOOLS

        for inst_id, meta in TARGET_INSTITUTION_SCHOOLS.items():
            self.assertIn(inst_id, SCHOOLS)
            self.assertEqual(SCHOOLS[inst_id]["domain"], meta["domain"])
        for alias in ("ucla", "nyu", "umich", "ut_austin"):
            self.assertIn(alias, SCHOOLS)

    def test_spotify_config_contains_target_schools(self):
        from spotify.config import SCHOOLS

        for inst_id in TARGET_INSTITUTION_SCHOOLS:
            self.assertIn(inst_id, SCHOOLS)
        for alias in ("ucla", "nyu", "umich", "ut_austin"):
            self.assertIn(alias, SCHOOLS)

    def test_youtube_config_contains_target_schools(self):
        from youtube.config import SCHOOLS

        for inst_id in TARGET_INSTITUTION_SCHOOLS:
            self.assertIn(inst_id, SCHOOLS)
        for alias in ("ucla", "nyu", "umich", "ut_austin"):
            self.assertIn(alias, SCHOOLS)

    def test_boltnew_config_contains_target_schools(self):
        from Boltnew.config import SCHOOLS

        for inst_id in TARGET_INSTITUTION_SCHOOLS:
            self.assertIn(inst_id, SCHOOLS)
        for alias in ("ucla", "nyu", "umich", "ut_austin"):
            self.assertIn(alias, SCHOOLS)


class TestMultiInstitutionImageGeneration(unittest.TestCase):
    """Verify multi-institution image generation in verification engines."""

    def test_one_generator_multi_institution(self):
        for target_school in ("ucla", "nyu", "umich", "ut_austin"):
            with self.subTest(school=target_school):
                data = one_generate_image("Alex", "Morgan", school_id=target_school)
                self.assertIsInstance(data, bytes)
                self.assertGreater(len(data), 1000)
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")

    def test_spotify_generator_multi_institution(self):
        for target_school in ("ucla", "nyu", "umich", "ut_austin"):
            with self.subTest(school=target_school):
                data = spotify_generate_image("Chris", "Evans", school_id=target_school)
                self.assertIsInstance(data, bytes)
                self.assertGreater(len(data), 1000)
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")

    def test_youtube_generator_multi_institution(self):
        for target_school in ("ucla", "nyu", "umich", "ut_austin"):
            with self.subTest(school=target_school):
                data = youtube_generate_image("Dana", "Scully", school_id=target_school)
                self.assertIsInstance(data, bytes)
                self.assertGreater(len(data), 1000)
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")

    def test_boltnew_generator_multi_institution(self):
        for target_school in ("ucla", "nyu", "umich", "ut_austin"):
            with self.subTest(school=target_school):
                assets = boltnew_generate_images(
                    "Fox", "Mulder", school_id=target_school
                )
                self.assertEqual(len(assets), 2)
                for asset in assets:
                    self.assertIsInstance(asset["data"], bytes)
                    self.assertGreater(len(asset["data"]), 1000)
                    self.assertEqual(asset["data"][:8], b"\x89PNG\r\n\x1a\n")


class TestVerifierWorkflowPayloads(unittest.TestCase):
    """Verify verifier step payloads with institution resolution."""

    @patch("one.sheerid_verifier.SheerIDVerifier._sheerid_request")
    def test_one_verifier_submits_selected_institution(self, mock_request):
        from one.sheerid_verifier import SheerIDVerifier

        captured_body: dict = {}

        def fake_request(method, url, body=None, **kwargs):
            if "collectStudentPersonalInfo" in url:
                nonlocal captured_body
                captured_body = body or {}
                return {
                    "currentStep": "success",
                    "submissionUrl": "https://s3.example.com",
                }, 200
            return {"currentStep": "success"}, 200

        mock_request.side_effect = fake_request

        verifier = SheerIDVerifier("fake-verification-id-12345")
        with patch.object(verifier, "_upload_to_s3", return_value=True):
            verifier.verify(
                first_name="Jane",
                last_name="Doe",
                school_id="ucla",
            )

        self.assertEqual(captured_body["organization"]["id"], 285)
        self.assertIn("California-Los Angeles", captured_body["organization"]["name"])
        self.assertTrue(captured_body["email"].endswith("@ucla.edu"))


if __name__ == "__main__":
    unittest.main()
