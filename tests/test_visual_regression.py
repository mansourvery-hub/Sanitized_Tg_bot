"""Unit tests for Visual Regression Testing Suite (visual_regression.py)."""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from render_service import HeadlessRenderer, RasterFormat, RenderPayload, ViewportConfig
from visual_regression import (
    DEFAULT_BASELINE_SPECS,
    DEFAULT_BASELINES_DIR,
    VisualBaselineSpec,
    VisualRegressionSuite,
    _load_image,
    compare_images,
)


class MockConstantRenderer(HeadlessRenderer):
    """Mock renderer producing predictable solid or patterned PNG bytes."""

    def __init__(self, color: tuple[int, int, int] = (255, 255, 255)) -> None:
        self.color = color

    def render_markup(
        self,
        html_content: str,
        viewport: ViewportConfig,
        fmt: RasterFormat,
    ) -> bytes:
        img = Image.new("RGB", (viewport.width, viewport.height), self.color)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


class TestVisualRegressionEngine(unittest.TestCase):
    """Unit tests for the pixel-diff comparison engine."""

    def test_compare_identical_images(self) -> None:
        img1 = Image.new("RGB", (100, 100), (240, 240, 240))
        img2 = Image.new("RGB", (100, 100), (240, 240, 240))

        result = compare_images(img1, img2, threshold=0.001)

        self.assertTrue(result.match)
        self.assertEqual(result.diff_ratio, 0.0)
        self.assertEqual(result.diff_pixels, 0)
        self.assertEqual(result.rmse, 0.0)
        self.assertTrue(result.dimension_match)
        self.assertEqual(result.baseline_size, (100, 100))
        self.assertEqual(result.candidate_size, (100, 100))

    def test_compare_images_within_threshold(self) -> None:
        img1 = Image.new("RGB", (100, 100), (255, 255, 255))
        img2 = Image.new("RGB", (100, 100), (255, 255, 255))

        # Change a 2x2 block (4 pixels out of 10,000 = 0.04% diff)
        draw = ImageDraw.Draw(img2)
        draw.rectangle([10, 10, 11, 11], fill=(0, 0, 0))

        result = compare_images(
            img1, img2, threshold=0.001, color_tolerance=10, generate_diff_image=True
        )

        self.assertTrue(result.match)
        self.assertEqual(result.diff_pixels, 4)
        self.assertAlmostEqual(result.diff_ratio, 4 / 10000.0, places=5)
        self.assertGreater(result.rmse, 0.0)
        self.assertIsNotNone(result.diff_image_bytes)

    def test_compare_images_exceeding_threshold(self) -> None:
        img1 = Image.new("RGB", (100, 100), (255, 255, 255))
        img2 = Image.new("RGB", (100, 100), (255, 255, 255))

        # Change a 40x40 block (1600 pixels out of 10,000 = 16% diff)
        draw = ImageDraw.Draw(img2)
        draw.rectangle([10, 10, 49, 49], fill=(255, 0, 0))

        result = compare_images(
            img1, img2, threshold=0.01, color_tolerance=10, generate_diff_image=True
        )

        self.assertFalse(result.match)
        self.assertGreater(result.diff_ratio, 0.01)
        self.assertEqual(result.diff_pixels, 1600)
        self.assertIsNotNone(result.diff_image_bytes)

        # Confirm diff composite is a readable image
        diff_img = Image.open(io.BytesIO(result.diff_image_bytes or b""))
        self.assertGreater(diff_img.width, 100)
        self.assertGreater(diff_img.height, 100)

    def test_color_tolerance_antialiasing_filtering(self) -> None:
        img1 = Image.new("RGB", (50, 50), (100, 100, 100))
        img2 = Image.new("RGB", (50, 50), (100, 100, 100))

        # Delta of 8 on 10 pixels
        draw = ImageDraw.Draw(img2)
        draw.rectangle([0, 0, 9, 0], fill=(108, 100, 100))

        # With tolerance 10, delta of 8 should be ignored
        res_tolerant = compare_images(img1, img2, color_tolerance=10)
        self.assertTrue(res_tolerant.match)
        self.assertEqual(res_tolerant.diff_pixels, 0)

        # With tolerance 5, delta of 8 should be counted
        res_strict = compare_images(img1, img2, color_tolerance=5)
        self.assertEqual(res_strict.diff_pixels, 10)

    def test_dimension_mismatch(self) -> None:
        img1 = Image.new("RGB", (100, 100), (255, 255, 255))
        img2 = Image.new("RGB", (120, 100), (255, 255, 255))

        result = compare_images(img1, img2, threshold=0.5)

        self.assertFalse(result.dimension_match)
        self.assertFalse(result.match)
        self.assertEqual(result.baseline_size, (100, 100))
        self.assertEqual(result.candidate_size, (120, 100))
        self.assertGreater(result.diff_pixels, 0)

    def test_load_image_from_various_sources(self) -> None:
        pil_img = Image.new("RGB", (20, 20), (50, 60, 70))
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        raw_bytes = buf.getvalue()

        # Load from Image
        loaded_img = _load_image(pil_img)
        self.assertEqual(loaded_img.size, (20, 20))

        # Load from bytes
        loaded_bytes = _load_image(raw_bytes)
        self.assertEqual(loaded_bytes.size, (20, 20))

        # Non-existent file raises FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            _load_image(Path("/tmp/non_existent_image_12345.png"))

    def test_result_to_dict_serialization(self) -> None:
        img = Image.new("RGB", (30, 30), (0, 0, 0))
        result = compare_images(img, img, threshold=0.005)
        data = result.to_dict(include_bytes=True)

        self.assertTrue(data["match"])
        self.assertEqual(data["diff_ratio"], 0.0)
        self.assertEqual(data["rmse"], 0.0)
        self.assertEqual(data["baseline_size"], [30, 30])
        self.assertIn("diff_image_bytes_length", data)


class TestVisualBaselineSuite(unittest.TestCase):
    """Unit tests for baseline management and suite execution."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="visreg_test_")
        self.baselines_dir = Path(self.test_dir) / "baselines"

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_baseline_spec_to_payload(self) -> None:
        spec = VisualBaselineSpec(
            name="test_spec",
            institution_id="psu",
            document_kind="schedule",
            seed=123,
            attributes={"first_name": "Test", "last_name": "User"},
            viewport_width=800,
            viewport_height=600,
        )

        payload: RenderPayload = spec.to_payload()
        self.assertEqual(payload.institution_id, "psu")
        self.assertEqual(payload.document_kind, "schedule")
        self.assertEqual(payload.seed, 123)
        self.assertEqual(payload.viewport.width, 800)
        self.assertEqual(payload.viewport.height, 600)
        self.assertEqual(payload.attributes["first_name"], "Test")

        # Roundtrip dict conversion
        d = spec.to_dict()
        spec2 = VisualBaselineSpec.from_dict(d)
        self.assertEqual(spec.name, spec2.name)
        self.assertEqual(spec.attributes, spec2.attributes)

    def test_generate_and_verify_baselines_in_temp_dir(self) -> None:
        from render_service import UnifiedAssetRenderer

        mock_renderer = UnifiedAssetRenderer(
            backend_renderer=MockConstantRenderer((200, 200, 200))
        )
        spec = VisualBaselineSpec(
            name="mock_card",
            institution_id="nittany_tech",
            document_kind="id_card",
            seed=42,
            viewport_width=200,
            viewport_height=150,
        )

        suite = VisualRegressionSuite(
            baselines_dir=self.baselines_dir,
            renderer=mock_renderer,
            specs=[spec],
        )

        # 1. Generate baselines
        gen_res = suite.generate_baselines(force=True)
        self.assertEqual(gen_res["status"], "success")
        self.assertEqual(gen_res["newly_generated"], 1)
        self.assertTrue((self.baselines_dir / "mock_card.png").exists())
        self.assertTrue((self.baselines_dir / "manifest.json").exists())

        manifest = json.loads(
            (self.baselines_dir / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertIn("mock_card", manifest["baselines"])

        # 2. Verify with matching renderer
        run_res = suite.run_suite()
        self.assertEqual(run_res["total"], 1)
        self.assertEqual(run_res["passed"], 1)
        self.assertEqual(run_res["failed"], 0)
        self.assertTrue(run_res["all_passed"])

    def test_suite_detects_visual_regression_and_writes_diff(self) -> None:
        from render_service import UnifiedAssetRenderer

        baseline_renderer = UnifiedAssetRenderer(
            backend_renderer=MockConstantRenderer((10, 10, 10))
        )
        spec = VisualBaselineSpec(
            name="color_drift",
            institution_id="psu",
            document_kind="schedule",
            seed=42,
            viewport_width=100,
            viewport_height=100,
        )

        suite = VisualRegressionSuite(
            baselines_dir=self.baselines_dir,
            renderer=baseline_renderer,
            specs=[spec],
        )
        suite.generate_baselines(force=True)

        # Introduce visual drift via a conflicting candidate renderer
        drifted_renderer = UnifiedAssetRenderer(
            backend_renderer=MockConstantRenderer((250, 250, 250))
        )
        suite.renderer = drifted_renderer

        diff_output_dir = Path(self.test_dir) / "diffs"
        run_res = suite.run_suite(threshold=0.01, diff_dir=diff_output_dir)

        self.assertEqual(run_res["total"], 1)
        self.assertEqual(run_res["passed"], 0)
        self.assertEqual(run_res["failed"], 1)
        self.assertFalse(run_res["all_passed"])

        # Candidate and diff images should have been written
        self.assertTrue((diff_output_dir / "color_drift_candidate.png").exists())
        self.assertTrue((diff_output_dir / "color_drift_diff.png").exists())

    def test_missing_baseline_raises_error(self) -> None:
        spec = VisualBaselineSpec(
            name="missing_card",
            institution_id="psu",
            document_kind="schedule",
        )
        suite = VisualRegressionSuite(
            baselines_dir=self.baselines_dir,
            specs=[spec],
        )
        with self.assertRaises(FileNotFoundError):
            suite.verify_spec(spec)


class TestCanonicalBaselinesManifest(unittest.TestCase):
    """Integrity checks for the committed golden baseline assets."""

    def test_manifest_and_png_assets_exist(self) -> None:
        self.assertTrue(
            DEFAULT_BASELINES_DIR.exists(),
            f"Baselines directory '{DEFAULT_BASELINES_DIR}' must exist.",
        )
        manifest_file = DEFAULT_BASELINES_DIR / "manifest.json"
        self.assertTrue(
            manifest_file.exists(),
            f"Manifest file '{manifest_file}' must exist.",
        )

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        self.assertIn("baselines", manifest)

        for spec in DEFAULT_BASELINE_SPECS:
            self.assertIn(
                spec.name,
                manifest["baselines"],
                f"Spec '{spec.name}' missing from manifest.json",
            )
            png_file = DEFAULT_BASELINES_DIR / f"{spec.name}.png"
            self.assertTrue(
                png_file.exists(),
                f"Baseline PNG file '{png_file}' must exist.",
            )
            self.assertGreater(
                png_file.stat().st_size,
                1000,
                f"Baseline PNG '{png_file}' must not be empty.",
            )

    def test_international_baselines_present_and_valid(self) -> None:
        """Verify international university golden baselines are present in specs and manifest."""
        manifest_file = DEFAULT_BASELINES_DIR / "manifest.json"
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        specs_by_name = {spec.name: spec for spec in DEFAULT_BASELINE_SPECS}

        international_keys = (
            "up_diliman_form5",
            "usp_atestado_matricula",
            "universiti_malaya_surat_pengesahan",
            "makerere_enrollment_letter",
            "unilag_enrollment_letter",
        )
        for key in international_keys:
            self.assertIn(
                key, specs_by_name, f"Spec '{key}' must be in DEFAULT_BASELINE_SPECS"
            )
            self.assertIn(
                key, manifest["baselines"], f"Spec '{key}' must be in manifest"
            )
            png_file = DEFAULT_BASELINES_DIR / f"{key}.png"
            self.assertTrue(
                png_file.exists(), f"Golden baseline PNG '{png_file}' must exist"
            )
            self.assertGreater(png_file.stat().st_size, 5000)


if __name__ == "__main__":
    unittest.main()
