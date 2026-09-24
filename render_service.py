"""Unified Asset Render Service.

Provides a robust architectural contract for rendering high-fidelity raster assets
directly from JSON payload structures via `generation.py` layouts, replacing static
hardcoded pixel or template generation across test suites and services.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, ClassVar, Protocol

from generation import (
    INSTITUTIONS,
    Document,
    DocumentKind,
    SyntheticProfile,
    generate_document,
    generate_profile,
    render_png,
)


class RasterFormat(str, Enum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"


@dataclass(frozen=True)
class ViewportConfig:
    """Headless capture viewport parameters."""

    width: int = 1200
    height: int = 900
    device_scale_factor: float = 2.0


@dataclass(frozen=True)
class RenderPayload:
    """Canonical, immutable JSON-serializable specification payload."""

    schema_version: str
    scenario_id: str
    document_kind: str
    institution_id: str
    attributes: dict[str, Any]
    viewport: ViewportConfig = field(default_factory=ViewportConfig)
    target_format: RasterFormat = RasterFormat.PNG
    seed: int = 42

    @classmethod
    def from_json(cls, data: Mapping[str, Any] | str) -> RenderPayload:
        if isinstance(data, str):
            raw = json.loads(data)
        elif isinstance(data, Mapping):
            raw = dict(data)
        else:
            raise TypeError(
                f"Payload must be a JSON string or dict mapping, got {type(data).__name__}"
            )

        if "schema_version" not in raw:
            raw["schema_version"] = "1.0"

        for required_key in ("scenario_id", "document_kind", "institution_id"):
            if required_key not in raw:
                raise ValueError(f"Missing required payload key: '{required_key}'")

        viewport_data = raw.get("viewport", {})
        viewport = ViewportConfig(
            width=int(viewport_data.get("width", 1200)),
            height=int(viewport_data.get("height", 900)),
            device_scale_factor=float(viewport_data.get("device_scale_factor", 2.0)),
        )

        fmt_str = str(raw.get("target_format", "png")).lower()
        try:
            target_format = RasterFormat(fmt_str)
        except ValueError:
            target_format = RasterFormat.PNG

        return cls(
            schema_version=str(raw["schema_version"]),
            scenario_id=str(raw["scenario_id"]),
            document_kind=str(raw["document_kind"]),
            institution_id=str(raw["institution_id"]),
            attributes=dict(raw.get("attributes", {})),
            viewport=viewport,
            target_format=target_format,
            seed=int(raw.get("seed", 42)),
        )


@dataclass(frozen=True)
class RenderResult:
    """Immutable output artifact contract returned by the rendering service."""

    raw_bytes: bytes
    format: RasterFormat
    width: int
    height: int
    digest_sha256: str
    metadata: dict[str, Any] = field(default_factory=dict)


class HeadlessRenderer(Protocol):
    """Protocol for pluggable layout-to-raster renderers."""

    def render_markup(
        self,
        html_content: str,
        viewport: ViewportConfig,
        fmt: RasterFormat,
    ) -> bytes: ...


class AssetRenderService(ABC):
    """Primary service boundary for dynamic visual regression and asset rendering."""

    @abstractmethod
    def render_from_payload(self, payload: RenderPayload) -> RenderResult:
        """Render a typed payload specification into a raster image."""
        ...

    @abstractmethod
    def render_from_json(self, raw_json: Mapping[str, Any] | str) -> RenderResult:
        """Hydrate JSON and execute end-to-end raster rendering."""
        ...


class PayloadTransformer:
    """Transforms raw payload attributes into domain entities in `generation.py`."""

    KIND_MAP: ClassVar[dict[str, DocumentKind]] = {
        "schedule": DocumentKind.SCHEDULE,
        "tuition_receipt": DocumentKind.TUITION_RECEIPT,
        "id_card": DocumentKind.ID_CARD,
        "faculty_summary": DocumentKind.FACULTY_SUMMARY,
        "enrollment_certificate": DocumentKind.ENROLLMENT_CERTIFICATE,
    }

    INSTITUTION_ALIAS_MAP: ClassVar[dict[str, str]] = {
        "2565": "psu",
        "651379": "psu",
        "8387": "psu",
        "8382": "psu",
        "penn_state": "psu",
        "pennstate": "psu",
        "ucla": "ucla",
        "285": "ucla",
        "nyu": "nyu",
        "2678": "nyu",
        "umich": "umich",
        "2027": "umich",
        "michigan": "umich",
        "ut_austin": "ut_austin",
        "3895": "ut_austin",
        "utaustin": "ut_austin",
        "ut": "ut_austin",
        "k12": "springfield_k12",
        "springfield": "springfield_k12",
        "springfield_k12": "springfield_k12",
        "nittany_tech": "nittany_tech",
    }

    @classmethod
    def resolve_document_kind(cls, kind_str: str) -> DocumentKind:
        normalized = kind_str.strip().lower().replace("-", "_")
        if normalized in cls.KIND_MAP:
            return cls.KIND_MAP[normalized]
        return DocumentKind.SCHEDULE

    @classmethod
    def resolve_institution_id(cls, inst_key: str) -> str:
        cleaned = inst_key.strip().lower()
        if cleaned in INSTITUTIONS:
            return cleaned
        return cls.INSTITUTION_ALIAS_MAP.get(cleaned, "psu")

    @classmethod
    def map_to_profile(cls, payload: RenderPayload) -> SyntheticProfile:
        attrs = payload.attributes
        inst_id = cls.resolve_institution_id(payload.institution_id)

        # Baseline complete profile from generation engine
        profile = generate_profile(
            scenario_name="undergraduate",
            institution_id=inst_id,
            seed=payload.seed,
        )

        # Apply specific attribute overrides
        if "first_name" in attrs:
            profile.first_name = str(attrs["first_name"]).strip()
        if "last_name" in attrs:
            profile.last_name = str(attrs["last_name"]).strip()
        if "student_id" in attrs:
            profile.student_id = str(attrs["student_id"]).strip()
        if "email" in attrs:
            profile.email = str(attrs["email"]).strip()
        if "program" in attrs:
            profile.program = str(attrs["program"]).strip()
        if "enrollment_type" in attrs:
            profile.enrollment_type = str(attrs["enrollment_type"]).strip()
        if "campus" in attrs:
            profile.campus = str(attrs["campus"]).strip()
        if "current_term_label" in attrs:
            profile.current_term_label = str(attrs["current_term_label"]).strip()

        def _parse_optional_date(val: Any) -> date | None:
            if not val:
                return None
            if isinstance(val, date):
                return val
            try:
                return date.fromisoformat(str(val))
            except (ValueError, TypeError):
                return None

        if "term_start_date" in attrs:
            profile.term_start_date = _parse_optional_date(attrs["term_start_date"])
        if "term_end_date" in attrs:
            profile.term_end_date = _parse_optional_date(attrs["term_end_date"])
        if "document_print_date" in attrs:
            profile.document_print_date = _parse_optional_date(
                attrs["document_print_date"]
            )

        return profile


class UnifiedAssetRenderer(AssetRenderService):
    """Reference implementation of AssetRenderService utilizing generation.py layouts."""

    def __init__(self, backend_renderer: HeadlessRenderer | None = None) -> None:
        self._backend = backend_renderer

    def render_from_json(self, raw_json: Mapping[str, Any] | str) -> RenderResult:
        payload = RenderPayload.from_json(raw_json)
        return self.render_from_payload(payload)

    def render_from_payload(self, payload: RenderPayload) -> RenderResult:
        profile = PayloadTransformer.map_to_profile(payload)
        doc_kind = PayloadTransformer.resolve_document_kind(payload.document_kind)

        # Generate intermediate HTML/DOM representation via generation engine
        doc: Document = generate_document(
            profile=profile, doc_kind=doc_kind, seed=payload.seed
        )

        # Render to target raster format
        if self._backend is not None:
            raw_bytes = self._backend.render_markup(
                html_content=doc.html_content,
                viewport=payload.viewport,
                fmt=payload.target_format,
            )
        else:
            raw_bytes = render_png(
                doc.html_content,
                width=payload.viewport.width,
                height=payload.viewport.height,
            )

        digest = hashlib.sha256(raw_bytes).hexdigest()

        return RenderResult(
            raw_bytes=raw_bytes,
            format=payload.target_format,
            width=payload.viewport.width,
            height=payload.viewport.height,
            digest_sha256=digest,
            metadata={
                "schema_version": payload.schema_version,
                "scenario_id": payload.scenario_id,
                "document_kind": doc_kind.value,
                "institution_id": profile.institution_id,
                "document_title": doc.title,
                "student_id": profile.student_id,
            },
        )


# Global singleton instance
_DEFAULT_RENDERER = UnifiedAssetRenderer()


def render_asset_from_json(data: Mapping[str, Any] | str) -> RenderResult:
    """Convenience helper to render raster bytes directly from JSON string or dict."""
    return _DEFAULT_RENDERER.render_from_json(data)


def render_institutional_image(
    first_name: str,
    last_name: str,
    institution_id: str = "psu",
    doc_kind: str = "schedule",
    student_id: str | None = None,
    seed: int = 42,
) -> bytes:
    """Direct drop-in replacement helper for legacy img_generator functions."""
    payload_data: dict[str, Any] = {
        "schema_version": "1.0",
        "scenario_id": f"{institution_id}_{doc_kind}",
        "document_kind": doc_kind,
        "institution_id": institution_id,
        "seed": seed,
        "attributes": {
            "first_name": first_name,
            "last_name": last_name,
        },
    }
    if student_id:
        payload_data["attributes"]["student_id"] = student_id

    result = _DEFAULT_RENDERER.render_from_json(payload_data)
    return result.raw_bytes
