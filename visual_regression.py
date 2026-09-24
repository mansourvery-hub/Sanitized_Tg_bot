"""Visual Regression Testing Suite for Academic Credential Document Rendering.

Provides pixel-level diffing, Root Mean Square Error (RMSE) computation,
high-contrast difference mask visualization, baseline snapshot generation,
and regression verification across academic institutions and document archetypes.
"""

from __future__ import annotations

import io
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageStat

from render_service import RenderPayload, UnifiedAssetRenderer

DEFAULT_BASELINES_DIR = Path(__file__).resolve().parent / "tests" / "visual_baselines"


@dataclass(frozen=True)
class VisualDiffResult:
    """Result contract of a visual comparison between baseline and candidate images."""

    match: bool
    diff_ratio: float
    diff_pixels: int
    total_pixels: int
    rmse: float
    threshold: float
    color_tolerance: int
    dimension_match: bool
    baseline_size: tuple[int, int]
    candidate_size: tuple[int, int]
    diff_image_bytes: bytes | None = None

    def to_dict(self, include_bytes: bool = False) -> dict[str, Any]:
        """Convert result to serializable dictionary."""
        data = {
            "match": self.match,
            "diff_ratio": round(self.diff_ratio, 6),
            "diff_pixels": self.diff_pixels,
            "total_pixels": self.total_pixels,
            "rmse": round(self.rmse, 4),
            "threshold": self.threshold,
            "color_tolerance": self.color_tolerance,
            "dimension_match": self.dimension_match,
            "baseline_size": list(self.baseline_size),
            "candidate_size": list(self.candidate_size),
        }
        if include_bytes and self.diff_image_bytes is not None:
            data["diff_image_bytes_length"] = len(self.diff_image_bytes)
        return data


def _load_image(source: bytes | Path | str | Image.Image) -> Image.Image:
    """Load an image source into a PIL RGB Image."""
    if isinstance(source, Image.Image):
        return source.convert("RGB")
    if isinstance(source, (bytes, bytearray)):
        return Image.open(io.BytesIO(source)).convert("RGB")
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")
    return Image.open(path).convert("RGB")


def _pad_to_dimensions(
    img: Image.Image,
    target_width: int,
    target_height: int,
    bg_color: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Pad an image to target dimensions if it is smaller."""
    if img.size == (target_width, target_height):
        return img
    padded = Image.new("RGB", (target_width, target_height), bg_color)
    padded.paste(img, (0, 0))
    return padded


def _generate_3panel_composite(
    baseline: Image.Image,
    diff_mask: Image.Image,
    candidate: Image.Image,
) -> bytes:
    """Generate a side-by-side 3-panel comparison image (Baseline | Diff Mask | Candidate)."""
    w, h = baseline.size
    header_height = 36
    margin = 8
    total_width = (w * 3) + (margin * 4)
    total_height = h + header_height + (margin * 2)

    # 1. Dim baseline for diff background
    dimmed_baseline = ImageEnhance.Brightness(baseline).enhance(0.35)

    # 2. Diff overlay: high-contrast magenta/red where differing
    highlight = Image.new("RGB", (w, h), (255, 0, 85))
    diff_highlight_view = Image.composite(highlight, dimmed_baseline, diff_mask)

    # 3. Canvas assembly
    canvas = Image.new("RGB", (total_width, total_height), (24, 26, 31))
    draw = ImageDraw.Draw(canvas)

    # Panel placements
    x_base = margin
    x_diff = x_base + w + margin
    x_cand = x_diff + w + margin
    y_panels = header_height + margin

    canvas.paste(baseline, (x_base, y_panels))
    canvas.paste(diff_highlight_view, (x_diff, y_panels))
    canvas.paste(candidate, (x_cand, y_panels))

    # Header labels
    draw.text((x_base + 8, 10), "BASELINE (REFERENCE)", fill=(180, 190, 205))
    draw.text(
        (x_diff + 8, 10), "DIFFERENCE MASK (REGRESSIONS IN RED)", fill=(255, 85, 115)
    )
    draw.text((x_cand + 8, 10), "CANDIDATE (ACTUAL)", fill=(180, 190, 205))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def compare_images(
    baseline: bytes | Path | str | Image.Image,
    candidate: bytes | Path | str | Image.Image,
    threshold: float = 0.005,
    color_tolerance: int = 15,
    generate_diff_image: bool = True,
) -> VisualDiffResult:
    """Compare baseline and candidate images for visual regressions.

    Args:
        baseline: Baseline golden image (bytes, path, or PIL Image).
        candidate: Candidate rendered image to evaluate.
        threshold: Maximum allowed fraction of differing pixels (default 0.005 = 0.5%).
        color_tolerance: Per-channel color delta tolerance (0-255) for antialiasing.
        generate_diff_image: Whether to synthesize the 3-panel diff PNG artifact.

    Returns:
        VisualDiffResult containing match verdict, pixel counts, RMSE, and diff artifact.
    """
    img_base = _load_image(baseline)
    img_cand = _load_image(candidate)

    base_size = img_base.size
    cand_size = img_cand.size
    dimension_match = base_size == cand_size

    # Handle dimension discrepancies by normalizing to bounding canvas
    max_w = max(base_size[0], cand_size[0])
    max_h = max(base_size[1], cand_size[1])

    norm_base = _pad_to_dimensions(img_base, max_w, max_h)
    norm_cand = _pad_to_dimensions(img_cand, max_w, max_h)

    total_pixels = max_w * max_h

    # Fast check: ImageChops difference
    diff = ImageChops.difference(norm_base, norm_cand)
    bbox = diff.getbbox()

    if bbox is None and dimension_match:
        # 100% byte/pixel identical
        diff_bytes = None
        if generate_diff_image:
            zero_mask = Image.new("L", (max_w, max_h), 0)
            diff_bytes = _generate_3panel_composite(norm_base, zero_mask, norm_cand)
        return VisualDiffResult(
            match=True,
            diff_ratio=0.0,
            diff_pixels=0,
            total_pixels=total_pixels,
            rmse=0.0,
            threshold=threshold,
            color_tolerance=color_tolerance,
            dimension_match=True,
            baseline_size=base_size,
            candidate_size=cand_size,
            diff_image_bytes=diff_bytes,
        )

    # Per-channel color tolerance filter: flag pixel if any RGB channel delta exceeds tolerance
    table = [0 if i <= color_tolerance else 255 for i in range(256)]
    r_diff, g_diff, b_diff = diff.split()
    r_mask = r_diff.point(table, mode="L")
    g_mask = g_diff.point(table, mode="L")
    b_mask = b_diff.point(table, mode="L")
    mask = ImageChops.lighter(ImageChops.lighter(r_mask, g_mask), b_mask)
    hist = mask.histogram()
    diff_pixels = hist[255] if len(hist) > 255 else 0

    # Add size mismatch penalty pixels if dimensions differed
    if not dimension_match:
        size_diff_pixels = abs(
            base_size[0] * base_size[1] - cand_size[0] * cand_size[1]
        )
        diff_pixels = max(diff_pixels, size_diff_pixels)

    diff_ratio = diff_pixels / total_pixels if total_pixels > 0 else 0.0

    # Channel-wise Root Mean Square Error (RMSE)
    stat = ImageStat.Stat(diff)
    rms_values = stat.rms
    rmse = (
        math.sqrt(sum(val * val for val in rms_values) / len(rms_values))
        if rms_values
        else 0.0
    )

    # Determine verdict: both dimension match and threshold must be satisfied
    match = dimension_match and (diff_ratio <= threshold)

    diff_image_bytes = None
    if generate_diff_image:
        diff_image_bytes = _generate_3panel_composite(norm_base, mask, norm_cand)

    return VisualDiffResult(
        match=match,
        diff_ratio=diff_ratio,
        diff_pixels=diff_pixels,
        total_pixels=total_pixels,
        rmse=rmse,
        threshold=threshold,
        color_tolerance=color_tolerance,
        dimension_match=dimension_match,
        baseline_size=base_size,
        candidate_size=cand_size,
        diff_image_bytes=diff_image_bytes,
    )


@dataclass
class VisualBaselineSpec:
    """Specification describing a deterministic baseline visual snapshot."""

    name: str
    institution_id: str
    document_kind: str
    seed: int = 42
    attributes: dict[str, Any] = field(default_factory=dict)
    viewport_width: int = 1200
    viewport_height: int = 900
    description: str = ""

    def to_payload(self) -> RenderPayload:
        """Project spec into a typed RenderPayload."""
        from render_service import ViewportConfig

        return RenderPayload(
            schema_version="1.0",
            scenario_id=f"visreg_{self.name}",
            document_kind=self.document_kind,
            institution_id=self.institution_id,
            seed=self.seed,
            viewport=ViewportConfig(
                width=self.viewport_width,
                height=self.viewport_height,
                device_scale_factor=2.0,
            ),
            attributes=dict(self.attributes),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert specification to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VisualBaselineSpec:
        """Create specification from dictionary."""
        return cls(**data)


# Canonical visual baseline snapshots covering target institutions & document archetypes
DEFAULT_BASELINE_SPECS: list[VisualBaselineSpec] = [
    VisualBaselineSpec(
        name="psu_portal_schedule",
        institution_id="psu",
        document_kind="schedule",
        seed=42,
        attributes={
            "first_name": "Jordan",
            "last_name": "Miller",
            "student_id": "987654321",
            "term_label": "Fall 2026",
            "document_print_date": "2026-09-01",
        },
        description="Penn State University - LionPATH Class Schedule Portal View",
    ),
    VisualBaselineSpec(
        name="ucla_registrar_letter",
        institution_id="ucla",
        document_kind="verification_letter",
        seed=42,
        attributes={
            "first_name": "Elena",
            "last_name": "Reyes",
            "student_id": "105938472",
            "term_label": "Fall Quarter 2026",
            "document_print_date": "2026-09-01",
        },
        description="UCLA - Office of the Registrar Enrollment Verification Letter",
    ),
    VisualBaselineSpec(
        name="nyu_albert_schedule",
        institution_id="nyu",
        document_kind="schedule",
        seed=42,
        attributes={
            "first_name": "Zachary",
            "last_name": "Brooks",
            "student_id": "N18294726",
            "term_label": "Fall 2026",
            "document_print_date": "2026-09-01",
        },
        description="New York University - Albert Student Center Class Schedule",
    ),
    VisualBaselineSpec(
        name="umich_wolverine_schedule",
        institution_id="umich",
        document_kind="schedule",
        seed=42,
        attributes={
            "first_name": "Samantha",
            "last_name": "Chen",
            "student_id": "48920183",
            "term_label": "Fall 2026",
            "document_print_date": "2026-09-01",
        },
        description="University of Michigan - Wolverine Access Class Schedule",
    ),
    VisualBaselineSpec(
        name="ut_austin_enrollment_letter",
        institution_id="ut_austin",
        document_kind="verification_letter",
        seed=42,
        attributes={
            "first_name": "Marcus",
            "last_name": "Vance",
            "student_id": "893740128",
            "term_label": "Fall 2026",
            "document_print_date": "2026-09-01",
        },
        description="UT Austin - Texas One Stop Enrollment Certification Letter",
    ),
    VisualBaselineSpec(
        name="springfield_faculty_summary",
        institution_id="springfield_k12",
        document_kind="faculty_summary",
        seed=42,
        attributes={
            "first_name": "Patricia",
            "last_name": "Holloway",
            "student_id": "EMP-49201",
            "document_print_date": "2026-09-01",
        },
        description="Springfield K-12 - Employee Access Faculty Verification Summary",
    ),
    VisualBaselineSpec(
        name="nittany_tech_id_card",
        institution_id="nittany_tech",
        document_kind="id_card",
        seed=42,
        attributes={
            "first_name": "David",
            "last_name": "Sterling",
            "student_id": "902847192",
            "document_print_date": "2026-09-01",
        },
        description="Nittany Tech - Official Campus ID Card Visual",
    ),
    VisualBaselineSpec(
        name="up_diliman_form5",
        institution_id="up_diliman",
        document_kind="schedule",
        seed=42,
        attributes={
            "first_name": "Juan",
            "last_name": "Dela Cruz",
            "student_id": "2022-14920",
            "term_label": "1st Semester AY 2025-2026",
            "document_print_date": "2025-08-15",
        },
        description="University of the Philippines Diliman - Form 5 Enrollment Certificate / Schedule",
    ),
    VisualBaselineSpec(
        name="usp_atestado_matricula",
        institution_id="usp",
        document_kind="schedule",
        seed=42,
        attributes={
            "first_name": "Lucas",
            "last_name": "Silva",
            "student_id": "11849201",
            "term_label": "2º Semestre de 2025",
            "document_print_date": "2025-08-04",
        },
        description="Universidade de São Paulo - Atestado de Matrícula",
    ),
    VisualBaselineSpec(
        name="universiti_malaya_surat_pengesahan",
        institution_id="universiti_malaya",
        document_kind="schedule",
        seed=42,
        attributes={
            "first_name": "Muhammad",
            "last_name": "Razak",
            "student_id": "S2023184920",
            "term_label": "Semester 1, Session 2025/2026",
            "document_print_date": "2025-09-01",
        },
        description="Universiti Malaya - Surat Pengesahan Pendaftaran Pelajar",
    ),
    VisualBaselineSpec(
        name="makerere_enrollment_letter",
        institution_id="makerere",
        document_kind="schedule",
        seed=42,
        attributes={
            "first_name": "Emmanuel",
            "last_name": "Okello",
            "student_id": "23/U/14920/EVE",
            "term_label": "Semester I 2025/2026",
            "document_print_date": "2025-08-18",
        },
        description="Makerere University - Official Letter of Enrollment",
    ),
    VisualBaselineSpec(
        name="unilag_enrollment_letter",
        institution_id="unilag",
        document_kind="schedule",
        seed=42,
        attributes={
            "first_name": "Babatunde",
            "last_name": "Adeyemi",
            "student_id": "2023/1/14920",
            "term_label": "First Semester 2025/2026 Session",
            "document_print_date": "2025-10-06",
        },
        description="University of Lagos - Letter of Student Enrollment",
    ),
]


class VisualRegressionSuite:
    """Manager for generating and verifying visual regression baselines."""

    def __init__(
        self,
        baselines_dir: Path | str = DEFAULT_BASELINES_DIR,
        renderer: UnifiedAssetRenderer | None = None,
        specs: list[VisualBaselineSpec] | None = None,
    ) -> None:
        self.baselines_dir = Path(baselines_dir)
        self.renderer = renderer or UnifiedAssetRenderer()
        self.specs = specs or DEFAULT_BASELINE_SPECS
        self.manifest_path = self.baselines_dir / "manifest.json"

    def generate_baselines(self, force: bool = False) -> dict[str, Any]:
        """Generate and save baseline golden PNGs and manifest.json to disk."""
        self.baselines_dir.mkdir(parents=True, exist_ok=True)
        manifest: dict[str, Any] = {
            "version": "1.0",
            "baselines": {},
        }

        generated_count = 0
        for spec in self.specs:
            img_path = self.baselines_dir / f"{spec.name}.png"
            if img_path.exists() and not force:
                raw_bytes = img_path.read_bytes()
                from hashlib import sha256

                digest = sha256(raw_bytes).hexdigest()
            else:
                payload = spec.to_payload()
                result = self.renderer.render_from_payload(payload)
                img_path.write_bytes(result.raw_bytes)
                digest = result.digest_sha256
                generated_count += 1

            manifest["baselines"][spec.name] = {
                "spec": spec.to_dict(),
                "file_name": f"{spec.name}.png",
                "sha256": digest,
                "size_bytes": img_path.stat().st_size,
            }

        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return {
            "status": "success",
            "baselines_dir": str(self.baselines_dir),
            "total_specs": len(self.specs),
            "newly_generated": generated_count,
            "manifest_file": str(self.manifest_path),
        }

    def verify_spec(
        self,
        spec: VisualBaselineSpec,
        threshold: float = 0.005,
        color_tolerance: int = 15,
        diff_dir: Path | None = None,
    ) -> VisualDiffResult:
        """Render a spec and compare against its saved baseline snapshot."""
        baseline_file = self.baselines_dir / f"{spec.name}.png"
        if not baseline_file.exists():
            raise FileNotFoundError(
                f"Baseline file '{baseline_file}' not found. "
                "Run `generate_baselines()` or CLI `python app.py visual-regression --update-baselines` first."
            )

        payload = spec.to_payload()
        candidate_res = self.renderer.render_from_payload(payload)

        result = compare_images(
            baseline=baseline_file,
            candidate=candidate_res.raw_bytes,
            threshold=threshold,
            color_tolerance=color_tolerance,
            generate_diff_image=True,
        )

        # If regression detected and diff output directory is provided, write artifacts
        if not result.match and diff_dir is not None:
            diff_dir.mkdir(parents=True, exist_ok=True)
            candidate_path = diff_dir / f"{spec.name}_candidate.png"
            candidate_path.write_bytes(candidate_res.raw_bytes)

            if result.diff_image_bytes is not None:
                diff_path = diff_dir / f"{spec.name}_diff.png"
                diff_path.write_bytes(result.diff_image_bytes)

        return result

    def run_suite(
        self,
        threshold: float = 0.005,
        color_tolerance: int = 15,
        diff_dir: Path | None = None,
    ) -> dict[str, Any]:
        """Execute full visual regression verification across all registered specs."""
        results: dict[str, VisualDiffResult] = {}
        passed = 0
        failed = 0

        for spec in self.specs:
            res = self.verify_spec(
                spec=spec,
                threshold=threshold,
                color_tolerance=color_tolerance,
                diff_dir=diff_dir,
            )
            results[spec.name] = res
            if res.match:
                passed += 1
            else:
                failed += 1

        return {
            "total": len(self.specs),
            "passed": passed,
            "failed": failed,
            "all_passed": failed == 0,
            "results": {k: v.to_dict() for k, v in results.items()},
        }
