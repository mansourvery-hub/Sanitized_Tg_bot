"""Unit test suite for unified asset render service."""

from __future__ import annotations

import json
import unittest

from render_service import (
    RasterFormat,
    RenderPayload,
    UnifiedAssetRenderer,
    render_asset_from_json,
    render_institutional_image,
)


class TestRenderService(unittest.TestCase):
    def setUp(self):
        self.renderer = UnifiedAssetRenderer()

    def test_render_from_json_string(self):
        raw_json = json.dumps(
            {
                "schema_version": "1.0",
                "scenario_id": "test_psu_schedule",
                "document_kind": "schedule",
                "institution_id": "psu",
                "target_format": "png",
                "seed": 42,
                "viewport": {"width": 1000, "height": 800, "device_scale_factor": 2.0},
                "attributes": {
                    "first_name": "Jordan",
                    "last_name": "Miller",
                    "student_id": "987654321",
                },
            }
        )
        result = render_asset_from_json(raw_json)

        self.assertEqual(result.format, RasterFormat.PNG)
        self.assertEqual(result.width, 1000)
        self.assertEqual(result.height, 800)
        self.assertTrue(result.raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(result.raw_bytes), 2000)
        self.assertEqual(result.metadata["institution_id"], "psu")
        self.assertEqual(result.metadata["student_id"], "987654321")
        self.assertTrue(len(result.digest_sha256) == 64)

    def test_render_multi_institution_payloads(self):
        cases = [
            ("ucla", "schedule"),
            ("nyu", "tuition_receipt"),
            ("umich", "schedule"),
            ("ut_austin", "enrollment_certificate"),
        ]
        for inst_id, doc_kind in cases:
            payload = {
                "schema_version": "1.0",
                "scenario_id": f"test_{inst_id}_{doc_kind}",
                "document_kind": doc_kind,
                "institution_id": inst_id,
                "seed": 99,
                "attributes": {
                    "first_name": "Taylor",
                    "last_name": "Swift",
                },
            }
            res = self.renderer.render_from_json(payload)
            self.assertTrue(res.raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertGreater(len(res.raw_bytes), 1500)
            self.assertEqual(res.metadata["institution_id"], inst_id)

    def test_payload_validation_errors(self):
        # Missing scenario_id
        with self.assertRaises(ValueError):
            RenderPayload.from_json(
                {"document_kind": "schedule", "institution_id": "psu"}
            )

        # Missing institution_id
        with self.assertRaises(ValueError):
            RenderPayload.from_json(
                {"scenario_id": "scen_1", "document_kind": "schedule"}
            )

        # Invalid type
        with self.assertRaises(TypeError):
            RenderPayload.from_json(12345)  # type: ignore

    def test_deterministic_render_digest(self):
        payload = {
            "schema_version": "1.0",
            "scenario_id": "idempotent_test",
            "document_kind": "schedule",
            "institution_id": "psu",
            "seed": 777,
            "attributes": {
                "first_name": "Deterministic",
                "last_name": "Subject",
                "student_id": "911223344",
                "document_print_date": "2026-09-15",
                "term_start_date": "2026-08-24",
                "term_end_date": "2026-12-18",
            },
        }
        res1 = self.renderer.render_from_json(payload)
        res2 = self.renderer.render_from_json(payload)

        self.assertEqual(res1.digest_sha256, res2.digest_sha256)
        self.assertEqual(res1.raw_bytes, res2.raw_bytes)

    def test_legacy_bridge_helper(self):
        png_bytes = render_institutional_image(
            first_name="Morgan",
            last_name="Freeman",
            institution_id="psu",
            student_id="999888777",
            seed=42,
        )
        self.assertTrue(png_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(png_bytes), 2000)

    def test_legacy_modules_integrated_with_render_service(self):
        from k12.img_generator import generate_teacher_png
        from one.img_generator import generate_image as one_generate_image
        from spotify.img_generator import generate_image as spotify_generate_image
        from youtube.img_generator import generate_image as youtube_generate_image

        # Test one/
        one_bytes = one_generate_image("Jane", "Doe")
        self.assertTrue(one_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(one_bytes), 50000)

        # Test spotify/
        spotify_bytes = spotify_generate_image("Sam", "Smith")
        self.assertTrue(spotify_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(spotify_bytes), 50000)

        # Test youtube/
        youtube_bytes = youtube_generate_image("Robin", "Williams")
        self.assertTrue(youtube_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(youtube_bytes), 50000)

        # Test k12/
        k12_bytes = generate_teacher_png("Sarah", "Connor")
        self.assertTrue(k12_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(k12_bytes), 20000)

        # Test Boltnew/
        from Boltnew.img_generator import generate_images as boltnew_generate_images

        bolt_assets = boltnew_generate_images("Alan", "Turing")
        self.assertEqual(len(bolt_assets), 2)
        for asset in bolt_assets:
            self.assertTrue(asset["data"].startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertGreater(len(asset["data"]), 20000)


if __name__ == "__main__":
    unittest.main()
