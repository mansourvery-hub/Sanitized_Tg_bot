"""
Unified Generation Engine for Sanitized Local Identity & Document Framework.

Provides canonical synthetic profile generation, constraint satisfaction, document
projections, HTML/PDF/PNG/JPEG rendering, deterministic seeds, artifact validation,
read-back testing, fixture generation, batch generation, and multi-document bundles.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any, ClassVar

import pypdf
from pypdf.errors import PyPdfError

logger = logging.getLogger(__name__)

GENERATOR_VERSION = "2.0.0"


class PersonRole(str, Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    TEACHER = "teacher"


class AcademicLevel(str, Enum):
    UNDERGRADUATE = "undergraduate"
    GRADUATE = "graduate"
    K12_TEACHER = "k12_teacher"
    FACULTY = "faculty"


class DocumentKind(str, Enum):
    SCHEDULE = "schedule"
    TUITION_RECEIPT = "tuition_receipt"
    ID_CARD = "id_card"
    FACULTY_SUMMARY = "faculty_summary"
    ENROLLMENT_CERTIFICATE = "enrollment_certificate"


class ArtifactType(str, Enum):
    HTML = "html"
    PDF = "pdf"
    PNG = "png"
    JPEG = "jpeg"
    JSON = "json"


class DocumentArchetype(str, Enum):
    PORTAL_SCREENSHOT = "portal_screenshot"
    REGISTRAR_LETTER = "registrar_letter"


@dataclass
class Institution:
    id: str
    name: str
    city: str
    country: str
    domain: str
    institution_type: str
    programs: tuple[str, ...]
    portal_name: str = "Student Portal"
    document_archetype: DocumentArchetype = DocumentArchetype.PORTAL_SCREENSHOT
    student_id_label: str = "Student ID"
    student_id_format: str = r"\d{9}"
    student_id_prefix: str = ""
    student_id_starts_with: str = ""
    term_format: str = "{season} {year}"
    term_seasons: tuple[str, ...] = ("Spring", "Summer", "Fall")
    term_system: str = "semester"
    primary_color: str = "#1E407C"
    accent_color: str = "#96BEE6"
    brand_color: str = "#1E407C"
    registrar_title: str = "Office of the University Registrar"
    registrar_address: str = ""
    crn_label: str = "Class Nbr"
    credit_label: str = "Units"
    course_id_format: str = "{SUBJ} {NNN}"
    schools: tuple[str, ...] = ()
    pdf_producer: str = "Oracle PeopleTools 8.59"
    pdf_creator: str = "PeopleSoft Enterprise"
    # Estimated document-review pass rate (from research). Used for service recommendations.
    estimated_pass_rate_low: float | None = None
    estimated_pass_rate_high: float | None = None
    # Legacy alias fields for backward compatibility
    id_format: str | None = None
    id_prefix: str | None = None
    producer_string: str | None = None

    @property
    def estimated_pass_rate_mid(self) -> float | None:
        if (
            self.estimated_pass_rate_low is None
            or self.estimated_pass_rate_high is None
        ):
            return None
        return (self.estimated_pass_rate_low + self.estimated_pass_rate_high) / 2.0

    @property
    def pass_rate_label(self) -> str | None:
        if (
            self.estimated_pass_rate_low is None
            or self.estimated_pass_rate_high is None
        ):
            return None
        lo = int(self.estimated_pass_rate_low * 100)
        hi = int(self.estimated_pass_rate_high * 100)
        return f"{lo}–{hi}%"

    def __post_init__(self) -> None:
        if isinstance(self.document_archetype, str):
            self.document_archetype = DocumentArchetype(self.document_archetype)
        if self.brand_color != "#1E407C" and self.primary_color == "#1E407C":
            self.primary_color = self.brand_color
        else:
            self.brand_color = self.primary_color
        if self.id_format is not None and self.student_id_format == r"\d{9}":
            self.student_id_format = self.id_format
        if self.id_prefix is not None and not self.student_id_prefix:
            self.student_id_prefix = self.id_prefix
        if (
            self.producer_string is not None
            and self.pdf_producer == "Oracle PeopleTools 8.59"
        ):
            self.pdf_producer = self.producer_string
        # Keep aliases synchronized
        self.id_format = self.student_id_format
        self.id_prefix = self.student_id_prefix
        self.producer_string = self.pdf_producer

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["document_archetype"] = self.document_archetype.value
        return res

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Institution:
        data_copy = dict(data)
        if isinstance(data_copy.get("programs"), list):
            data_copy["programs"] = tuple(data_copy["programs"])
        if isinstance(data_copy.get("term_seasons"), list):
            data_copy["term_seasons"] = tuple(data_copy["term_seasons"])
        if isinstance(data_copy.get("schools"), list):
            data_copy["schools"] = tuple(data_copy["schools"])
        if "document_archetype" in data_copy and isinstance(
            data_copy["document_archetype"], str
        ):
            data_copy["document_archetype"] = DocumentArchetype(
                data_copy["document_archetype"]
            )
        return cls(**data_copy)


@dataclass
class Course:
    code: str
    title: str
    crn: str
    credits: int
    meeting_pattern: str
    location: str
    instructor: str
    mode: str = "In-Person"


CourseRecord = Course


@dataclass
class AcademicState:
    term_name: str
    term_code: str
    courses: list[Course]
    total_credits: int
    advisor: str
    cumulative_gpa: float
    tuition_balance: str = "$0.00"
    payment_status: str = "PAID IN FULL"
    transaction_id: str = "TXN-9988271"

    def to_dict(self) -> dict[str, Any]:
        return {
            "term_name": self.term_name,
            "term_code": self.term_code,
            "courses": [asdict(c) for c in self.courses],
            "total_credits": self.total_credits,
            "advisor": self.advisor,
            "cumulative_gpa": self.cumulative_gpa,
            "tuition_balance": self.tuition_balance,
            "payment_status": self.payment_status,
            "transaction_id": self.transaction_id,
        }


@dataclass
class SyntheticProfile:
    first_name: str
    last_name: str
    role: PersonRole
    date_of_birth: date

    institution_id: str
    institution_name: str
    city: str
    country: str
    domain: str

    student_id: str  # or employee ID
    email: str

    program: str
    academic_level: AcademicLevel
    enrollment_date: date
    expected_graduation: date
    academic_year: str

    # Verification & IDV realism fields
    gpa_cumulative: float = 0.0
    gpa_term: float = 0.0
    cumulative_units: float = 0.0
    academic_standing: str = "Good Standing"
    campus: str = "University Park"
    advisor_name: str = ""
    advisor_email: str = ""
    document_seal_hash: str = ""

    current_term_label: str = ""
    term_start_date: date | None = None
    term_end_date: date | None = None
    document_print_date: date | None = None
    enrollment_type: str = "Full-Time"
    college_or_school: str = ""
    login_id: str = ""

    @property
    def institution(self) -> Institution:
        return INSTITUTIONS.get(self.institution_id, INSTITUTIONS["psu"])

    @property
    def hire_date(self) -> date | None:
        if self.role in (PersonRole.TEACHER, PersonRole.FACULTY):
            return self.enrollment_date
        return None

    @property
    def employee_id(self) -> str | None:
        if self.role in (PersonRole.TEACHER, PersonRole.FACULTY):
            return self.student_id
        return None

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["role"] = self.role.value
        res["academic_level"] = self.academic_level.value
        res["date_of_birth"] = self.date_of_birth.isoformat()
        res["enrollment_date"] = self.enrollment_date.isoformat()
        res["expected_graduation"] = self.expected_graduation.isoformat()
        if self.term_start_date:
            res["term_start_date"] = self.term_start_date.isoformat()
        if self.term_end_date:
            res["term_end_date"] = self.term_end_date.isoformat()
        if self.document_print_date:
            res["document_print_date"] = self.document_print_date.isoformat()
        return res

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SyntheticProfile:
        d = dict(data)
        d["role"] = PersonRole(d["role"])
        d["academic_level"] = AcademicLevel(d["academic_level"])
        d["date_of_birth"] = date.fromisoformat(d["date_of_birth"])
        d["enrollment_date"] = date.fromisoformat(d["enrollment_date"])
        d["expected_graduation"] = date.fromisoformat(d["expected_graduation"])
        if d.get("term_start_date") and isinstance(d["term_start_date"], str):
            d["term_start_date"] = date.fromisoformat(d["term_start_date"])
        if d.get("term_end_date") and isinstance(d["term_end_date"], str):
            d["term_end_date"] = date.fromisoformat(d["term_end_date"])
        if d.get("document_print_date") and isinstance(d["document_print_date"], str):
            val = d["document_print_date"]
            if "T" in val:
                d["document_print_date"] = datetime.fromisoformat(val).date()
            else:
                d["document_print_date"] = date.fromisoformat(val)
        valid_fields = {f.name for f in fields(cls)}
        filtered_d = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered_d)


SyntheticStudent = SyntheticProfile


@dataclass
class Document:
    kind: DocumentKind
    title: str
    profile: SyntheticProfile
    fields: dict[str, str]
    html_content: str = ""

    @property
    def rendered_html(self) -> str:
        return self.html_content

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "title": self.title,
            "profile": self.profile.to_dict(),
            "fields": self.fields,
            "html_content": self.html_content,
        }


@dataclass
class GeneratedArtifact:
    kind: DocumentKind
    path: str
    byte_size: int
    sha256: str
    artifact_type: ArtifactType

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "path": self.path,
            "byte_size": self.byte_size,
            "sha256": self.sha256,
            "artifact_type": self.artifact_type.value,
        }


@dataclass
class ValidationError:
    code: str
    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
        }


@dataclass
class GenerationReport:
    profile_valid: bool
    documents_generated: int
    documents_validated: int
    artifacts_validated: int
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    seed: int = 42
    scenario: str = "undergraduate"
    generator_version: str = GENERATOR_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_valid": self.profile_valid,
            "documents_generated": self.documents_generated,
            "documents_validated": self.documents_validated,
            "artifacts_validated": self.artifacts_validated,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "seed": self.seed,
            "scenario": self.scenario,
            "generator_version": self.generator_version,
        }


@dataclass
class GenerationResult:
    profile: SyntheticProfile
    document: Document
    artifacts: list[GeneratedArtifact]
    validation: ValidationResult
    report: GenerationReport
    seed: int
    scenario: str
    generator_version: str = GENERATOR_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "synthetic": True,
            "generator_version": self.generator_version,
            "seed": self.seed,
            "scenario": self.scenario,
            "profile": self.profile.to_dict(),
            "document": self.document.to_dict(),
            "artifacts": [a.to_dict() for a in self.artifacts],
            "validation": self.validation.to_dict(),
            "report": self.report.to_dict(),
        }


# =====================================================================
# INSTITUTIONS & SCENARIOS CATALOG
# =====================================================================

INSTITUTIONS: dict[str, Institution] = {
    "psu": Institution(
        id="psu",
        name="Penn State University",
        city="University Park",
        country="USA",
        domain="psu.edu",
        institution_type="university",
        programs=(
            "Computer Science (BS)",
            "Software Engineering (BS)",
            "Information Sciences and Technology (BS)",
            "Data Science (BS)",
            "Electrical Engineering (BS)",
            "Mechanical Engineering (BS)",
            "Business Administration (BS)",
            "Psychology (BA)",
            "Nursing (BS)",
        ),
        portal_name="LionPATH",
        document_archetype=DocumentArchetype.PORTAL_SCREENSHOT,
        student_id_label="Student ID",
        student_id_format=r"\d{9}",
        student_id_prefix="",
        student_id_starts_with="9",
        term_format="{season} {year}",
        term_seasons=("Spring", "Summer", "Fall"),
        term_system="semester",
        primary_color="#1E407C",
        accent_color="#96BEE6",
        pdf_producer="Oracle PeopleTools 8.59.15",
        pdf_creator="PeopleSoft Enterprise",
        registrar_title="Office of the University Registrar",
        registrar_address="103 Shields Building, University Park, PA 16802",
        crn_label="Class Nbr",
        credit_label="Units",
        course_id_format="{SUBJ} {NNN}",
        schools=(
            "College of Engineering",
            "College of Liberal Arts",
            "Smeal College of Business",
            "College of Information Sciences and Technology",
            "Eberly College of Science",
            "College of Communications",
        ),
        estimated_pass_rate_low=0.20,
        estimated_pass_rate_high=0.35,
    ),
    "ucla": Institution(
        id="ucla",
        name="University of California, Los Angeles",
        city="Los Angeles",
        country="USA",
        domain="ucla.edu",
        institution_type="university",
        programs=(
            "Computer Science",
            "Psychology",
            "Economics",
            "Political Science",
            "Communications",
            "Biology",
            "Sociology",
            "History",
        ),
        portal_name="MyUCLA",
        document_archetype=DocumentArchetype.REGISTRAR_LETTER,
        student_id_label="Student ID",
        student_id_format=r"9\d{8}",
        student_id_prefix="",
        student_id_starts_with="9",
        term_format="{season} {year}",
        term_seasons=("Fall", "Winter", "Spring", "Summer"),
        term_system="quarter",
        primary_color="#2D68C4",
        accent_color="#FFD100",
        pdf_producer="PeopleSoft 9.2",
        pdf_creator="PeopleSoft Enterprise",
        registrar_title="Office of the Registrar, UCLA",
        registrar_address="1113 Murphy Hall, Los Angeles, CA 90095",
        crn_label="N/A",
        credit_label="Units",
        course_id_format="{SUBJ} {NNN}",
        schools=(
            "College of Letters and Science",
            "Henry Samueli School of Engineering and Applied Science",
            "UCLA Anderson School of Management",
            "School of the Arts and Architecture",
            "Herb Alpert School of Music",
            "Jonathan and Karin Fielding School of Public Health",
        ),
        estimated_pass_rate_low=0.20,
        estimated_pass_rate_high=0.35,
    ),
    "nyu": Institution(
        id="nyu",
        name="New York University",
        city="New York",
        country="USA",
        domain="nyu.edu",
        institution_type="university",
        programs=(
            "Computer Science",
            "Economics",
            "Business Administration",
            "Psychology",
            "Media, Culture, and Communication",
            "Politics",
            "Biology",
            "History",
        ),
        portal_name="Albert",
        document_archetype=DocumentArchetype.PORTAL_SCREENSHOT,
        student_id_label="N-Number",
        student_id_format=r"N\d{8}",
        student_id_prefix="N",
        student_id_starts_with="N",
        term_format="{season} {year}",
        term_seasons=("Spring", "Summer", "Fall"),
        term_system="semester",
        primary_color="#57068C",
        accent_color="#8900E1",
        pdf_producer="PeopleSoft 9.2 HCM",
        pdf_creator="PeopleSoft Enterprise",
        registrar_title="Office of the Registrar",
        registrar_address="25 West 4th Street, New York, NY 10012",
        crn_label="Class Number",
        credit_label="Points",
        course_id_format="{SUBJ} {NNN}",
        schools=(
            "College of Arts and Science",
            "Tandon School of Engineering",
            "Stern School of Business",
            "Tisch School of the Arts",
            "Gallatin School of Individualized Study",
            "Silver School of Social Work",
        ),
        estimated_pass_rate_low=0.20,
        estimated_pass_rate_high=0.35,
    ),
    "umich": Institution(
        id="umich",
        name="University of Michigan",
        city="Ann Arbor",
        country="USA",
        domain="umich.edu",
        institution_type="university",
        programs=(
            "Computer Science",
            "Engineering",
            "Business Administration",
            "Psychology",
            "Political Science",
            "Economics",
            "Information",
            "Public Policy",
        ),
        portal_name="Wolverine Access",
        document_archetype=DocumentArchetype.PORTAL_SCREENSHOT,
        student_id_label="UMID",
        student_id_format=r"\d{8}",
        student_id_prefix="",
        student_id_starts_with="",
        term_format="{season} {year}",
        term_seasons=("Winter", "Spring", "Spring-Summer", "Summer", "Fall"),
        term_system="semester",
        primary_color="#00274C",
        accent_color="#FFCB05",
        pdf_producer="PeopleSoft 9.2",
        pdf_creator="MPathways",
        registrar_title="Office of the Registrar",
        registrar_address="2057 Wolverine Tower, Ann Arbor, MI 48109",
        crn_label="Section",
        credit_label="Credit Hours",
        course_id_format="{SUBJ} {NNN}",
        schools=(
            "College of Literature, Science, and the Arts",
            "College of Engineering",
            "Ross School of Business",
            "School of Information",
            "Taubman College of Architecture and Urban Planning",
            "School of Public Health",
            "Gerald R. Ford School of Public Policy",
        ),
        estimated_pass_rate_low=0.20,
        estimated_pass_rate_high=0.35,
    ),
    "ut_austin": Institution(
        id="ut_austin",
        name="The University of Texas at Austin",
        city="Austin",
        country="USA",
        domain="utexas.edu",
        institution_type="university",
        programs=(
            "Computer Science",
            "Business",
            "Communications",
            "Government",
            "Biology",
            "Engineering",
            "Psychology",
            "Economics",
        ),
        portal_name="UT Direct",
        document_archetype=DocumentArchetype.REGISTRAR_LETTER,
        student_id_label="UT EID",
        student_id_format=r"[a-z]{2,4}\d{3,5}",
        student_id_prefix="",
        student_id_starts_with="",
        term_format="{season} {year}",
        term_seasons=("Spring", "Summer", "Fall"),
        term_system="semester",
        primary_color="#BF5700",
        accent_color="#333F48",
        pdf_producer="Adobe PDF Library 15.0",
        pdf_creator="Adobe Acrobat",
        registrar_title="Office of the Registrar, The University of Texas at Austin",
        registrar_address="Main Building (MAI), 110 Inner Campus Drive, Austin, TX 78712",
        crn_label="Unique Number",
        credit_label="Hours",
        course_id_format="{SUBJ} {NNN}",
        schools=(
            "College of Liberal Arts",
            "Cockrell School of Engineering",
            "McCombs School of Business",
            "College of Natural Sciences",
            "Moody College of Communication",
            "Steve Hicks School of Social Work",
            "College of Education",
        ),
        estimated_pass_rate_low=0.20,
        estimated_pass_rate_high=0.35,
    ),
    "springfield_k12": Institution(
        id="springfield_k12",
        name="Springfield School District",
        city="Springfield",
        country="USA",
        domain="springfieldsd.org",
        institution_type="k12_district",
        programs=(
            "Elementary Education",
            "Secondary Mathematics",
            "High School Science",
            "Special Education",
            "Language Arts & Literature",
            "Social Studies",
        ),
        portal_name="Employee Access Center",
        document_archetype=DocumentArchetype.PORTAL_SCREENSHOT,
        student_id_label="Employee ID",
        student_id_format=r"\d{7}",
        student_id_prefix="E-",
        term_format="{season} {year}",
        term_seasons=("Fall", "Spring"),
        term_system="semester",
        registrar_title="Office of Human Resources",
        pdf_producer="PowerSchool SIS 23.5",
        pdf_creator="PowerSchool",
        crn_label="Course ID",
        credit_label="Credits",
        course_id_format="{SUBJ} {NNN}",
        estimated_pass_rate_low=0.35,
        estimated_pass_rate_high=0.50,
    ),
    "nittany_tech": Institution(
        id="nittany_tech",
        name="Nittany Technical College",
        city="State College",
        country="USA",
        domain="nittanytech.edu",
        institution_type="college",
        programs=(
            "Cybersecurity Tech (AS)",
            "Cloud Computing (AS)",
            "Web Development (Cert)",
            "Network Systems (AS)",
        ),
        portal_name="Ellucian Banner",
        document_archetype=DocumentArchetype.PORTAL_SCREENSHOT,
        student_id_label="Student ID",
        student_id_format=r"\d{8}",
        student_id_prefix="N",
        term_format="{season} {year}",
        term_seasons=("Spring", "Summer", "Fall"),
        term_system="semester",
        registrar_title="Office of the Registrar",
        pdf_producer="Ellucian Banner 9.28",
        pdf_creator="Ellucian",
        crn_label="CRN",
        credit_label="Credits",
        course_id_format="{SUBJ} {NNN}",
        estimated_pass_rate_low=0.35,
        estimated_pass_rate_high=0.50,
    ),
    "up_diliman": Institution(
        id="up_diliman",
        name="University of the Philippines Diliman",
        city="Quezon City",
        country="Philippines",
        domain="up.edu.ph",
        institution_type="university",
        programs=(
            "BS Computer Science",
            "BS Mathematics",
            "BS Physics",
            "AB Political Science",
            "BS Chemistry",
            "AB Economics",
            "BS Statistics",
            "AB Filipino",
        ),
        portal_name="CRS",
        document_archetype=DocumentArchetype.REGISTRAR_LETTER,
        student_id_label="Student Number",
        student_id_format=r"20\d{2}-\d{5}",
        term_seasons=("1st Semester", "2nd Semester", "Midyear"),
        term_system="semester",
        primary_color="#7B0027",
        accent_color="#014421",
        pdf_producer="Microsoft Word 16.0",
        pdf_creator="Microsoft Office",
        registrar_title="Office of the University Registrar (OUR)",
        registrar_address="Diliman, Quezon City 1101, Philippines",
        crn_label="Class Code",
        credit_label="Units",
        course_id_format="{SUBJ} {NNN}",
        schools=(
            "College of Engineering",
            "College of Science",
            "College of Social Sciences and Philosophy",
            "College of Arts and Letters",
            "Cesar E.A. Virata School of Business",
            "College of Education",
            "College of Law",
        ),
        estimated_pass_rate_low=0.82,
        estimated_pass_rate_high=0.88,
    ),
    "usp": Institution(
        id="usp",
        name="Universidade de São Paulo",
        city="São Paulo",
        country="Brazil",
        domain="usp.br",
        institution_type="university",
        programs=(
            "Mestrado em Ciência da Computação",
            "Bacharelado em Engenharia Elétrica",
            "Bacharelado em Administração",
            "Bacharelado em Direito",
            "Mestrado em Física",
        ),
        portal_name="Sistema Janus",
        document_archetype=DocumentArchetype.REGISTRAR_LETTER,
        student_id_label="Número USP",
        student_id_format=r"\d{7,8}",
        term_seasons=("1º Semestre", "2º Semestre"),
        term_system="semester",
        primary_color="#003366",
        accent_color="#C9A227",
        pdf_producer="Apache FOP Version 2.4",
        pdf_creator="Apache Software Foundation",
        registrar_title="Pró-Reitoria de Pós-Graduação",
        registrar_address="Rua da Reitoria, 109, Cidade Universitária, São Paulo, SP 05508-220",
        crn_label="Código",
        credit_label="Créditos",
        course_id_format="{SUBJ}{NNN}",
        schools=(
            "Instituto de Matemática e Estatística (IME)",
            "Escola Politécnica (POLI)",
            "Faculdade de Economia, Administração e Contabilidade (FEA)",
            "Faculdade de Direito",
            "Instituto de Física (IF)",
        ),
        estimated_pass_rate_low=0.80,
        estimated_pass_rate_high=0.87,
    ),
    "universiti_malaya": Institution(
        id="universiti_malaya",
        name="Universiti Malaya",
        city="Kuala Lumpur",
        country="Malaysia",
        domain="um.edu.my",
        institution_type="university",
        programs=(
            "Bachelor of Computer Science (Hons)",
            "Bachelor of Engineering (Electrical)",
            "Bachelor of Economics (Hons)",
            "Bachelor of Law (Hons)",
            "Bachelor of Science (Hons)",
        ),
        portal_name="MAYA",
        document_archetype=DocumentArchetype.REGISTRAR_LETTER,
        student_id_label="Matric No.",
        student_id_format=r"S20\d{2}\d{6}",
        student_id_prefix="S",
        term_seasons=("Semester 1", "Semester 2", "Special Semester"),
        term_system="semester",
        primary_color="#880000",
        accent_color="#C9A227",
        pdf_producer="Microsoft Word 16.0",
        pdf_creator="Microsoft Office",
        registrar_title="Pendaftar, Universiti Malaya",
        registrar_address="50603 Kuala Lumpur, Malaysia",
        crn_label="Kod Kursus",
        credit_label="Jam Kredit",
        course_id_format="{SUBJ}{NNN}",
        schools=(
            "Faculty of Computer Science and Information Technology",
            "Faculty of Engineering",
            "Faculty of Business and Economics",
            "Faculty of Arts and Social Sciences",
            "Faculty of Science",
            "Faculty of Law",
        ),
        estimated_pass_rate_low=0.78,
        estimated_pass_rate_high=0.85,
    ),
    "makerere": Institution(
        id="makerere",
        name="Makerere University",
        city="Kampala",
        country="Uganda",
        domain="mak.ac.ug",
        institution_type="university",
        programs=(
            "Bachelor of Science in Computer Science",
            "Bachelor of Engineering (Electrical)",
            "Bachelor of Business Administration",
            "Bachelor of Arts (Social Sciences)",
            "Bachelor of Laws (LLB)",
        ),
        portal_name="Student Portal",
        document_archetype=DocumentArchetype.REGISTRAR_LETTER,
        student_id_label="Student No.",
        student_id_format=r"\d{2}/U/\d{5}/PS",
        term_seasons=("Semester I", "Semester II"),
        term_system="semester",
        primary_color="#003087",
        accent_color="#C9A227",
        pdf_producer="Microsoft Word 16.0",
        pdf_creator="Microsoft Office",
        registrar_title="Academic Registrar",
        registrar_address="P.O. Box 7062, Kampala, Uganda",
        crn_label="Course Code",
        credit_label="Credit Units",
        course_id_format="{SUBJ} {NNN}",
        schools=(
            "College of Computing and Information Sciences (CoCIS)",
            "College of Engineering, Design, Art and Technology (CEDAT)",
            "College of Humanities and Social Sciences (CHUSS)",
            "Makerere University Business School (MUBS)",
            "College of Health Sciences (CHS)",
        ),
        estimated_pass_rate_low=0.83,
        estimated_pass_rate_high=0.90,
    ),
    "unilag": Institution(
        id="unilag",
        name="University of Lagos",
        city="Lagos",
        country="Nigeria",
        domain="unilag.edu.ng",
        institution_type="university",
        programs=(
            "B.Sc. Computer Science",
            "B.Eng. Electrical Engineering",
            "B.Sc. Economics",
            "LLB Law",
            "B.Sc. Accounting",
            "B.Ed. Education",
        ),
        portal_name="UNILAG Student Portal",
        document_archetype=DocumentArchetype.REGISTRAR_LETTER,
        student_id_label="Matriculation Number",
        student_id_format=r"20\d{2}/1/\d{5}",
        term_seasons=("First Semester", "Second Semester"),
        term_system="semester",
        primary_color="#800020",
        accent_color="#C9A227",
        pdf_producer="Microsoft Word 16.0",
        pdf_creator="Microsoft Office",
        registrar_title="Registrar and Secretary to Council",
        registrar_address="University of Lagos, Akoka, Yaba, Lagos State, Nigeria",
        crn_label="Course Code",
        credit_label="Units",
        course_id_format="{SUBJ} {NNN}",
        schools=(
            "Faculty of Science",
            "Faculty of Engineering",
            "Faculty of Social Sciences",
            "Faculty of Law",
            "Faculty of Arts",
            "Faculty of Education",
            "Faculty of Business Administration",
            "Faculty of Environmental Sciences",
        ),
        estimated_pass_rate_low=0.81,
        estimated_pass_rate_high=0.88,
    ),
}


# Service definitions for the service-optimized wizard. Kept in generation.py
# so adding a service or updating the recommendation requires only data edits.
SERVICE_DEFINITIONS: dict[str, dict[str, str]] = {
    "one": {
        "id": "one",
        "name": "Gemini One Pro",
        "role": "teacher",
        "default_scenario": "teacher",
    },
    "k12": {
        "id": "k12",
        "name": "ChatGPT Teacher K-12",
        "role": "teacher",
        "default_scenario": "teacher",
    },
    "spotify": {
        "id": "spotify",
        "name": "Spotify Student",
        "role": "student",
        "default_scenario": "undergraduate",
    },
    "boltnew": {
        "id": "boltnew",
        "name": "Bolt.new Teacher",
        "role": "teacher",
        "default_scenario": "teacher",
    },
    "youtube": {
        "id": "youtube",
        "name": "YouTube Premium Student",
        "role": "student",
        "default_scenario": "undergraduate",
    },
    # Aliases that resolve to canonical service ids
    "gemini": {
        "id": "one",
        "name": "Gemini One Pro",
        "role": "teacher",
        "default_scenario": "teacher",
    },
    "chatgpt": {
        "id": "k12",
        "name": "ChatGPT Teacher K-12",
        "role": "teacher",
        "default_scenario": "teacher",
    },
    "bolt": {
        "id": "boltnew",
        "name": "Bolt.new Teacher",
        "role": "teacher",
        "default_scenario": "teacher",
    },
}

# Optional per-service preference override. If a service lists preferred
# institution ids, those are tried first (in order) before falling back to
# global pass-rate ranking. Empty = fully data-driven via Institution pass rates.
SERVICE_INSTITUTION_OVERRIDES: dict[str, list[str]] = {}


def get_best_institutions_for_service(
    service_id: str | None = None,
    limit: int = 3,
) -> list[Institution]:
    """Return institutions ranked by estimated pass rate for a service.

    Ranking is data-driven: sorted by ``estimated_pass_rate_mid`` descending.
    Adding a new Institution with pass-rate fields automatically participates.
    Per-service overrides in ``SERVICE_INSTITUTION_OVERRIDES`` are honored first.
    """
    # 1) Honor explicit per-service override if present
    if service_id:
        norm = service_id.strip().lower().replace("-", "_")
        # Resolve alias via SERVICE_DEFINITIONS if present
        canon = SERVICE_DEFINITIONS.get(norm, {}).get("id", norm)
        if canon in SERVICE_INSTITUTION_OVERRIDES:
            ordered: list[Institution] = []
            for iid in SERVICE_INSTITUTION_OVERRIDES[canon]:
                inst = INSTITUTIONS.get(iid)
                if inst:
                    ordered.append(inst)
            # Append remaining sorted by pass rate to fill limit
            remaining = [
                inst
                for inst in sorted(
                    INSTITUTIONS.values(),
                    key=lambda i: i.estimated_pass_rate_mid or 0,
                    reverse=True,
                )
                if inst not in ordered
            ]
            ordered.extend(remaining)
            return ordered[:limit]

    # 2) Global ranking by pass rate (mid)
    ranked = sorted(
        INSTITUTIONS.values(),
        key=lambda i: i.estimated_pass_rate_mid or 0,
        reverse=True,
    )
    return ranked[:limit]


def get_recommended_institution_for_service(
    service_id: str | None = None,
) -> Institution:
    """Convenience: top-ranked institution for a service."""
    best = get_best_institutions_for_service(service_id, limit=1)
    return best[0] if best else INSTITUTIONS["psu"]


@dataclass
class ScenarioConfig:
    name: str
    description: str
    role: PersonRole
    academic_level: AcademicLevel
    min_age: int
    max_age: int
    program_duration_years: tuple[int, ...]
    institution_id: str


SCENARIOS: dict[str, ScenarioConfig] = {
    "undergraduate": ScenarioConfig(
        name="undergraduate",
        description="Standard 4-year undergraduate student",
        role=PersonRole.STUDENT,
        academic_level=AcademicLevel.UNDERGRADUATE,
        min_age=18,
        max_age=25,
        program_duration_years=(4,),
        institution_id="psu",
    ),
    "graduate": ScenarioConfig(
        name="graduate",
        description="Master / Doctoral graduate student",
        role=PersonRole.STUDENT,
        academic_level=AcademicLevel.GRADUATE,
        min_age=22,
        max_age=35,
        program_duration_years=(2, 3),
        institution_id="psu",
    ),
    "recent-enrollment": ScenarioConfig(
        name="recent-enrollment",
        description="Freshman recently enrolled student",
        role=PersonRole.STUDENT,
        academic_level=AcademicLevel.UNDERGRADUATE,
        min_age=18,
        max_age=20,
        program_duration_years=(4,),
        institution_id="psu",
    ),
    "near-graduation": ScenarioConfig(
        name="near-graduation",
        description="Senior student nearing graduation",
        role=PersonRole.STUDENT,
        academic_level=AcademicLevel.UNDERGRADUATE,
        min_age=21,
        max_age=24,
        program_duration_years=(4,),
        institution_id="psu",
    ),
    "teacher": ScenarioConfig(
        name="teacher",
        description="K-12 Faculty or Teacher employee",
        role=PersonRole.TEACHER,
        academic_level=AcademicLevel.K12_TEACHER,
        min_age=25,
        max_age=60,
        program_duration_years=(1, 5, 10),
        institution_id="springfield_k12",
    ),
}


def list_scenarios() -> list[str]:
    return list(SCENARIOS.keys())


def get_scenario(name: str) -> ScenarioConfig:
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario '{name}'. Available: {list_scenarios()}")
    return SCENARIOS[name]


# =====================================================================
# SEEDED NAME & DEMOGRAPHIC GENERATOR
# =====================================================================


class SeededNameGenerator:
    """Deterministic Name Generator supporting localized name pools and seeded Random instances."""

    FIRST_NAMES: ClassVar[list[str]] = [
        "Alexander",
        "Benjamin",
        "Charlotte",
        "Daniel",
        "Eleanor",
        "Felix",
        "Gabriel",
        "Hannah",
        "Isabella",
        "Julian",
        "Katherine",
        "Liam",
        "Maya",
        "Nathaniel",
        "Olivia",
        "Penelope",
        "Quinn",
        "Rachel",
        "Samuel",
        "Tristan",
        "Victoria",
        "William",
        "Zoe",
        "Lucas",
        "Sophia",
        "Ethan",
        "Chloe",
        "Noah",
        "Aria",
        "Mason",
    ]

    LAST_NAMES: ClassVar[list[str]] = [
        "Anderson",
        "Baker",
        "Carter",
        "Davis",
        "Edwards",
        "Foster",
        "Garcia",
        "Harrison",
        "Johnson",
        "Miller",
        "Nelson",
        "Owens",
        "Parker",
        "Quinn",
        "Roberts",
        "Smith-Jones",
        "Taylor",
        "Vance-Walker",
        "Williams",
        "Young",
        "Zhang",
        "Patel",
        "O'Connor",
        "Dubois",
        "Schneider",
        "Kovacs",
    ]

    LOCAL_NAMES: ClassVar[dict[str, tuple[list[str], list[str]]]] = {
        "up_diliman": (
            [
                "Juan",
                "Maria",
                "Paolo",
                "Angelo",
                "Mark",
                "Joshua",
                "Christine",
                "Bea",
                "Angela",
                "Gabriel",
                "Miguel",
                "Patricia",
                "Katrina",
                "Christian",
                "Nicole",
            ],
            [
                "Santos",
                "Reyes",
                "Cruz",
                "Bautista",
                "Ocampo",
                "Garcia",
                "Mendoza",
                "Ramos",
                "Aquino",
                "Del Rosario",
                "Tan",
                "Villanueva",
                "Castro",
                "Dizon",
                "Tolentino",
            ],
        ),
        "usp": (
            [
                "Gabriel",
                "Lucas",
                "Matheus",
                "Beatriz",
                "Julia",
                "Mariana",
                "Rodrigo",
                "Thiago",
                "Felipe",
                "Rafael",
                "Larissa",
                "Camila",
                "Bruno",
                "Vinicius",
                "Isabella",
            ],
            [
                "Silva",
                "Santos",
                "Oliveira",
                "Souza",
                "Pereira",
                "Lima",
                "Carvalho",
                "Ferreira",
                "Ribeiro",
                "Alves",
                "Rodrigues",
                "Costa",
                "Almeida",
                "Nascimento",
                "Araujo",
            ],
        ),
        "universiti_malaya": (
            [
                "Muhammad",
                "Ahmad",
                "Nur",
                "Siti",
                "Wei",
                "Jun",
                "Priya",
                "Daniel",
                "Adam",
                "Amirul",
                "Aisyah",
                "Farhan",
                "Yi",
                "Zhi",
                "Haris",
            ],
            [
                "Abdullah",
                "Rahman",
                "Tan",
                "Lim",
                "Lee",
                "Wong",
                "Subramaniam",
                "Ismail",
                "Razak",
                "Othman",
                "Ahmad",
                "Cheong",
                "Ng",
                "Yusof",
                "Ariffin",
            ],
        ),
        "makerere": (
            [
                "Brian",
                "Ronald",
                "Ivan",
                "Grace",
                "Faith",
                "Brenda",
                "Emmanuel",
                "Derrick",
                "Joseph",
                "Paul",
                "Sharon",
                "Sarah",
                "Mercy",
                "David",
                "Fiona",
            ],
            [
                "Okello",
                "Kato",
                "Mukasa",
                "Namubiru",
                "Tumusiime",
                "Kigozi",
                "Nabatanzi",
                "Mugisha",
                "Ochieng",
                "Ssebuguzi",
                "Musoke",
                "Kiiza",
                "Byaruhanga",
                "Akello",
            ],
        ),
        "unilag": (
            [
                "Babatunde",
                "Oluwaseun",
                "Chukwuma",
                "Chioma",
                "Ifeanyi",
                "Aisha",
                "Olumide",
                "Folake",
                "Tunde",
                "Damilola",
                "Femi",
                "Chinedu",
                "Zainab",
                "Blessing",
                "Adebayo",
            ],
            [
                "Adebayo",
                "Okafor",
                "Balogun",
                "Adeleke",
                "Ibrahim",
                "Okon",
                "Eze",
                "Danjuma",
                "Alabi",
                "Lawal",
                "Ojo",
                "Bello",
                "Nwosu",
                "Ogundipe",
                "Bakare",
            ],
        ),
    }

    @classmethod
    def generate(
        cls, rng: random.Random, institution_id: str | None = None
    ) -> tuple[str, str]:
        if institution_id and institution_id in cls.LOCAL_NAMES:
            first_pool, last_pool = cls.LOCAL_NAMES[institution_id]
            return rng.choice(first_pool), rng.choice(last_pool)
        fn = rng.choice(cls.FIRST_NAMES)
        ln = rng.choice(cls.LAST_NAMES)
        return fn, ln


# =====================================================================
# TEMPORAL ANCHOR ENGINE (≤ 90-Day Rule)
# =====================================================================


@dataclass
class TemporalAnchor:
    current_date: date
    academic_year: str
    term_name: str
    term_code: str
    retrieval_date: date
    payment_date: date
    issue_date: date
    expiration_date: date
    term_start_date: date | None = None
    term_end_date: date | None = None


_TERM_WINDOWS: dict[str, tuple[date, date]] = {
    "Fall": (date(2025, 8, 26), date(2025, 12, 19)),
    "Spring": (date(2026, 1, 13), date(2026, 5, 9)),
    "Summer": (date(2026, 5, 18), date(2026, 8, 7)),
}

_TERM_CALENDARS: dict[str, dict[str, tuple[date, date]]] = {
    "psu": {
        "Fall 2025": (date(2025, 8, 26), date(2025, 12, 19)),
        "Spring 2026": (date(2026, 1, 13), date(2026, 5, 9)),
        "Summer 2026": (date(2026, 5, 18), date(2026, 8, 7)),
        "Fall 2026": (date(2026, 8, 24), date(2026, 12, 18)),
        "Spring 2027": (date(2027, 1, 11), date(2027, 5, 7)),
        "Summer 2027": (date(2027, 5, 17), date(2027, 8, 6)),
        "Fall 2027": (date(2027, 8, 23), date(2027, 12, 17)),
    },
    "ucla": {
        # Quarter system: Fall, Winter, Spring, Summer
        "Fall 2025": (date(2025, 9, 22), date(2025, 12, 12)),
        "Winter 2026": (date(2026, 1, 5), date(2026, 3, 20)),
        "Spring 2026": (date(2026, 3, 30), date(2026, 6, 12)),
        "Summer 2026": (date(2026, 6, 22), date(2026, 8, 28)),
        "Fall 2026": (date(2026, 9, 21), date(2026, 12, 11)),
        "Winter 2027": (date(2027, 1, 4), date(2027, 3, 19)),
        "Spring 2027": (date(2027, 3, 29), date(2027, 6, 11)),
        "Summer 2027": (date(2027, 6, 21), date(2027, 8, 27)),
        "Fall 2027": (date(2027, 9, 20), date(2027, 12, 10)),
    },
    "nyu": {
        "Fall 2025": (date(2025, 9, 2), date(2025, 12, 19)),
        "Spring 2026": (date(2026, 1, 27), date(2026, 5, 15)),
        "Summer 2026": (date(2026, 5, 26), date(2026, 8, 14)),
        "Fall 2026": (date(2026, 9, 2), date(2026, 12, 18)),
        "Spring 2027": (date(2027, 1, 25), date(2027, 5, 14)),
        "Summer 2027": (date(2027, 5, 24), date(2027, 8, 13)),
        "Fall 2027": (date(2027, 9, 1), date(2027, 12, 17)),
    },
    "umich": {
        "Fall 2025": (date(2025, 8, 27), date(2025, 12, 13)),
        "Winter 2026": (
            date(2026, 1, 6),
            date(2026, 4, 24),
        ),  # Note: "Winter" NOT "Spring"
        "Spring 2026": (date(2026, 4, 27), date(2026, 6, 5)),
        "Summer 2026": (date(2026, 6, 8), date(2026, 8, 14)),
        "Fall 2026": (date(2026, 8, 26), date(2026, 12, 11)),
        "Winter 2027": (
            date(2027, 1, 5),
            date(2027, 4, 23),
        ),  # Note: "Winter" NOT "Spring"
        "Spring 2027": (date(2027, 4, 26), date(2027, 6, 4)),
        "Summer 2027": (date(2027, 6, 7), date(2027, 8, 13)),
        "Fall 2027": (date(2027, 8, 25), date(2027, 12, 10)),
    },
    "ut_austin": {
        "Fall 2025": (date(2025, 8, 25), date(2025, 12, 11)),
        "Spring 2026": (date(2026, 1, 21), date(2026, 5, 15)),
        "Summer 2026": (date(2026, 6, 1), date(2026, 8, 7)),
        "Fall 2026": (date(2026, 8, 24), date(2026, 12, 10)),
        "Spring 2027": (date(2027, 1, 19), date(2027, 5, 14)),
        "Summer 2027": (date(2027, 5, 31), date(2027, 8, 6)),
        "Fall 2027": (date(2027, 8, 23), date(2027, 12, 9)),
    },
    "up_diliman": {
        "1st Semester AY 2025-2026": (date(2025, 8, 18), date(2025, 12, 20)),
        "2nd Semester AY 2025-2026": (date(2026, 1, 19), date(2026, 5, 30)),
        "1st Semester AY 2026-2027": (date(2026, 8, 17), date(2026, 12, 19)),
        "2nd Semester AY 2026-2027": (date(2027, 1, 18), date(2027, 5, 29)),
    },
    "usp": {
        "1º Semestre de 2025": (date(2025, 2, 17), date(2025, 6, 30)),
        "2º Semestre de 2025": (date(2025, 8, 4), date(2025, 12, 12)),
        "1º Semestre de 2026": (date(2026, 2, 16), date(2026, 6, 29)),
        "2º Semestre de 2026": (date(2026, 8, 3), date(2026, 12, 11)),
        "1º Semestre de 2027": (date(2027, 2, 15), date(2027, 6, 28)),
    },
    "universiti_malaya": {
        "Semester 1, Session 2025/2026": (date(2025, 9, 1), date(2026, 1, 16)),
        "Semester 2, Session 2025/2026": (date(2026, 2, 9), date(2026, 6, 19)),
        "Semester 1, Session 2026/2027": (date(2026, 8, 31), date(2027, 1, 15)),
        "Semester 2, Session 2026/2027": (date(2027, 2, 8), date(2027, 6, 18)),
    },
    "makerere": {
        "Semester I 2025/2026": (date(2025, 8, 18), date(2025, 12, 19)),
        "Semester II 2025/2026": (date(2026, 2, 9), date(2026, 6, 20)),
        "Semester I 2026/2027": (date(2026, 8, 17), date(2026, 12, 18)),
        "Semester II 2026/2027": (date(2027, 2, 8), date(2027, 6, 19)),
    },
    "unilag": {
        "First Semester 2025/2026 Session": (date(2025, 10, 6), date(2026, 2, 13)),
        "Second Semester 2025/2026 Session": (date(2026, 3, 2), date(2026, 7, 10)),
        "First Semester 2026/2027 Session": (date(2026, 10, 5), date(2027, 2, 12)),
        "Second Semester 2026/2027 Session": (date(2027, 3, 1), date(2027, 7, 9)),
    },
}


def _current_term_for_institution(
    institution_id: str,
    as_of: date | None = None,
) -> tuple[str, date, date]:
    """
    Returns (term_label, term_start, term_end) for the term
    containing 'as_of' (defaults to today), for the given institution.
    UCLA Winter/Spring quarter names and UMich Winter names are preserved.
    """
    d = as_of or datetime.now(timezone.utc).date()
    cal = _TERM_CALENDARS.get(institution_id, _TERM_CALENDARS["psu"])
    for label, (start, end) in cal.items():
        if start <= d <= end:
            return label, start, end

    # Dynamic year resolution if outside static range
    y = d.year
    if institution_id == "ucla":
        q_cal = {
            f"Winter {y}": (date(y, 1, 4), date(y, 3, 19)),
            f"Spring {y}": (date(y, 3, 29), date(y, 6, 11)),
            f"Summer {y}": (date(y, 6, 21), date(y, 8, 27)),
            f"Fall {y}": (date(y, 9, 20), date(y, 12, 10)),
        }
        for label, (start, end) in q_cal.items():
            if start <= d <= end:
                return label, start, end
    elif institution_id == "umich":
        u_cal = {
            f"Winter {y}": (date(y, 1, 5), date(y, 4, 23)),
            f"Spring {y}": (date(y, 4, 26), date(y, 6, 4)),
            f"Summer {y}": (date(y, 6, 7), date(y, 8, 13)),
            f"Fall {y}": (date(y, 8, 25), date(y, 12, 10)),
        }
        for label, (start, end) in u_cal.items():
            if start <= d <= end:
                return label, start, end

    future = {k: v for k, v in cal.items() if v[0] > d}
    if future:
        nearest = min(future.items(), key=lambda x: x[1][0])
        return nearest[0], nearest[1][0], nearest[1][1]
    last = list(cal.items())[-1]
    return last[0], last[1][0], last[1][1]


def _current_term(
    as_of: date | None = None,
    institution_id: str | None = None,
) -> tuple[str, int, date, date]:
    """
    Returns (season, year, term_start, term_end) for the term
    containing 'as_of' (defaults to today).
    """
    d = as_of or datetime.now(timezone.utc).date()
    if institution_id and institution_id in _TERM_CALENDARS:
        label, start, end = _current_term_for_institution(institution_id, d)
        parts = label.split()
        season = parts[0]
        year = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else d.year
        return season, year, start, end

    y = d.year
    windows = {
        ("Fall", y - 1): (date(y - 1, 8, 26), date(y - 1, 12, 19)),
        ("Spring", y): (date(y, 1, 13), date(y, 5, 9)),
        ("Summer", y): (date(y, 5, 18), date(y, 8, 7)),
        ("Fall", y): (date(y, 8, 26), date(y, 12, 19)),
        ("Spring", y + 1): (date(y + 1, 1, 13), date(y + 1, 5, 9)),
    }
    for (season, year), (start, end) in windows.items():
        if start <= d <= end:
            return season, year, start, end

    upcoming = min(windows.items(), key=lambda item: abs((item[1][0] - d).days))
    (season, year), (st, en) = upcoming
    return season, year, st, en


def _document_print_date(
    rng: random.Random,
    profile_or_start: Any,
    as_of: date | None = None,
) -> datetime:
    """Generate a plausible print datetime within working hours during the current term."""
    today = as_of or datetime.now(timezone.utc).date()
    if isinstance(profile_or_start, date):
        term_start = profile_or_start
    elif (
        hasattr(profile_or_start, "term_start_date")
        and profile_or_start.term_start_date
    ):
        term_start = profile_or_start.term_start_date
    else:
        term_start = today - timedelta(days=30)

    window_start = max(term_start, today - timedelta(days=30))
    window_end = today - timedelta(days=1)
    if window_start > window_end:
        window_start = window_end - timedelta(days=1)

    span = max(1, (window_end - window_start).days)
    chosen_day = window_start + timedelta(days=rng.randint(0, span))
    return datetime.combine(chosen_day, datetime.min.time()).replace(
        hour=rng.randint(8, 17),
        minute=rng.randint(0, 59),
        second=rng.randint(0, 59),
    )


def _generate_crn(rng: random.Random, institution_id: str, course_index: int) -> str:
    """
    CRN that matches real institutional formatting.
    PSU CRNs: 5 digits, range 10000-89999 (not starting with 9), non-sequential.
    Seeded per institution + index so the same seed always gives the same CRN,
    but different courses in the same schedule are non-sequential.
    """
    local_rng = random.Random(
        hash(f"{institution_id}:{course_index}") + rng.randint(0, 9999)
    )
    for _ in range(20):
        crn = local_rng.randint(10000, 89999)
        s = str(crn)
        if s == s[::-1]:
            continue
        if len(set(s)) <= 2:
            continue
        return s
    return str(local_rng.randint(10000, 89999))


def get_temporal_anchor(
    rng: random.Random, anchor_date: date | None = None
) -> TemporalAnchor:
    """
    Computes a strict TemporalAnchor satisfying the ≤ 90-day verification rule:
    - Current date defaults to today (or reference date).
    - Retrieval / print timestamp: 1 to 30 days prior to current date.
    - Tuition payment date: 15 to 45 days prior to current date.
    - ID card expiration date: End of active academic year or anticipated graduation.
    """
    cur = anchor_date if anchor_date else datetime.now(timezone.utc).date()
    month = cur.month
    year = cur.year

    if 8 <= month <= 12:
        term_name = "Fall Semester"
        term_code = f"1{str(year)[-2:]}8"
        acad_year = f"{year}-{year + 1} Academic Year"
        exp_date = date(year + 1, 6, 30)
    elif 1 <= month <= 5:
        term_name = "Spring Semester"
        term_code = f"1{str(year)[-2:]}1"
        acad_year = f"{year - 1}-{year} Academic Year"
        exp_date = date(year, 6, 30)
    else:
        term_name = "Summer Session"
        term_code = f"1{str(year)[-2:]}5"
        acad_year = f"{year - 1}-{year} Academic Year"
        exp_date = date(year, 8, 31)

    # Retrieval date: 1 to 30 days prior (strictly ≤ 90 days)
    days_ago_ret = rng.randint(1, 30)
    ret_date = cur - timedelta(days=days_ago_ret)

    # Payment date: 15 to 45 days prior
    days_ago_pay = rng.randint(15, min(45, max(15, days_ago_ret + 10)))
    pay_date = cur - timedelta(days=days_ago_pay)

    # Issue date: start of term or retrieval date
    issue_date = ret_date

    _season, _ty, term_start, term_end = _current_term(cur)

    return TemporalAnchor(
        current_date=cur,
        academic_year=acad_year,
        term_name=term_name,
        term_code=term_code,
        retrieval_date=ret_date,
        payment_date=pay_date,
        issue_date=issue_date,
        expiration_date=exp_date,
        term_start_date=term_start,
        term_end_date=term_end,
    )


# =====================================================================
# DYNAMIC CURRICULUM & ACADEMIC STATE GENERATOR
# =====================================================================

CURRICULA: dict[str, list[Course]] = {
    "Computer Science (BS)": [
        Course(
            "CMPSC 311",
            "Systems Programming",
            "31422",
            3,
            "MoWeFr 09:05 AM - 09:55 AM",
            "Hammond 114",
            "Dr. Alan Turing",
            "In-Person",
        ),
        Course(
            "CMPSC 465",
            "Data Structures & Algorithms",
            "32890",
            3,
            "TuTh 11:15 AM - 12:30 PM",
            "IST Building 202",
            "Dr. Grace Hopper",
            "In-Person",
        ),
        Course(
            "MATH 230",
            "Calculus and Vector Analysis",
            "21904",
            4,
            "MoWeFr 11:15 AM - 12:05 PM",
            "McAllister 102",
            "Dr. Richard Feynman",
            "In-Person",
        ),
        Course(
            "STAT 318",
            "Elementary Probability",
            "28411",
            3,
            "TuTh 02:30 PM - 03:45 PM",
            "Thomas 100",
            "Dr. Claude Shannon",
            "In-Person",
        ),
        Course(
            "ENGL 202C",
            "Technical Writing",
            "37712",
            3,
            "MoWe 02:30 PM - 03:45 PM",
            "Sparks 121",
            "Prof. Jane Austen",
            "Hybrid",
        ),
    ],
    "Software Engineering (BS)": [
        Course(
            "SWENG 311",
            "Software Engineering I",
            "33101",
            3,
            "MoWeFr 10:10 AM - 11:00 AM",
            "Westgate 108",
            "Dr. Barbara Liskov",
            "In-Person",
        ),
        Course(
            "SWENG 411",
            "Software Architecture",
            "34190",
            3,
            "TuTh 09:45 AM - 11:00 AM",
            "Westgate 214",
            "Dr. Fred Brooks",
            "In-Person",
        ),
        Course(
            "CMPSC 461",
            "Programming Language Concepts",
            "32115",
            3,
            "MoWeFr 01:25 PM - 02:15 PM",
            "Hammond 216",
            "Dr. John Backus",
            "In-Person",
        ),
        Course(
            "STAT 318",
            "Elementary Probability",
            "28411",
            3,
            "TuTh 02:30 PM - 03:45 PM",
            "Thomas 100",
            "Dr. Claude Shannon",
            "In-Person",
        ),
        Course(
            "CAS 100",
            "Effective Speech",
            "19284",
            3,
            "Fr 01:25 PM - 04:15 PM",
            "Boucke 302",
            "Prof. Mark Twain",
            "In-Person",
        ),
    ],
    "Business Administration (BS)": [
        Course(
            "ACCTG 211",
            "Financial & Managerial Accounting",
            "41022",
            4,
            "MoWe 08:00 AM - 09:15 AM",
            "Smeal 101",
            "Dr. Warren Buffet",
            "In-Person",
        ),
        Course(
            "MGMT 301",
            "Basic Management Concepts",
            "42019",
            3,
            "TuTh 11:00 AM - 12:15 PM",
            "Smeal 114",
            "Dr. Peter Drucker",
            "In-Person",
        ),
        Course(
            "MKTG 301",
            "Principles of Marketing",
            "43088",
            3,
            "MoWeFr 11:15 AM - 12:05 PM",
            "Smeal 120",
            "Dr. Philip Kotler",
            "In-Person",
        ),
        Course(
            "SCM 301",
            "Supply Chain Management",
            "44102",
            3,
            "TuTh 01:30 PM - 02:45 PM",
            "Smeal 205",
            "Dr. Eliyahu Goldratt",
            "In-Person",
        ),
        Course(
            "ECON 104",
            "Macroeconomic Analysis",
            "20199",
            3,
            "MoWe 03:00 PM - 04:15 PM",
            "Whetstone 10",
            "Dr. Milton Friedman",
            "Hybrid",
        ),
    ],
    "Mechanical Engineering (BS)": [
        Course(
            "ME 300",
            "Engineering Thermodynamics",
            "51092",
            3,
            "MoWeFr 08:00 AM - 08:50 AM",
            "Hammond 301",
            "Dr. Nikola Tesla",
            "In-Person",
        ),
        Course(
            "EMCH 213",
            "Strength of Materials",
            "52011",
            3,
            "TuTh 09:30 AM - 10:45 AM",
            "Reber 108",
            "Dr. Stephen Timoshenko",
            "In-Person",
        ),
        Course(
            "MATH 251",
            "Ordinary Differential Equations",
            "22104",
            4,
            "MoWeFr 10:10 AM - 11:00 AM",
            "McAllister 105",
            "Dr. Leonhard Euler",
            "In-Person",
        ),
        Course(
            "PHYS 212",
            "General Physics: Electricity",
            "27112",
            4,
            "TuTh 01:00 PM - 02:15 PM",
            "Osmond 110",
            "Dr. James Clerk Maxwell",
            "In-Person",
        ),
    ],
    "Nursing (BS)": [
        Course(
            "NURS 200W",
            "Professional Nursing Concepts",
            "61022",
            3,
            "Mo 09:00 AM - 12:00 PM",
            "Nursing Sciences 102",
            "Dr. Florence Nightingale",
            "In-Person",
        ),
        Course(
            "NURS 225",
            "Health Assessment",
            "62011",
            4,
            "TuTh 08:00 AM - 11:00 AM",
            "Nursing Sciences 210",
            "Dr. Clara Barton",
            "In-Person",
        ),
        Course(
            "NURS 230",
            "Pathophysiology",
            "63044",
            3,
            "WeFr 01:00 PM - 02:15 PM",
            "Nursing Sciences 104",
            "Dr. Virginia Henderson",
            "In-Person",
        ),
        Course(
            "BIOL 161",
            "Human Anatomy & Physiology",
            "28990",
            4,
            "MoWeFr 02:30 PM - 03:20 PM",
            "Mueller Lab 100",
            "Dr. Andreas Vesalius",
            "In-Person",
        ),
    ],
}

DEFAULT_COURSES = [
    Course(
        "GENED 101",
        "Academic Foundations",
        "10022",
        3,
        "MoWeFr 09:05 AM - 09:55 AM",
        "Boucke 102",
        "Dr. Mentor Academic",
        "In-Person",
    ),
    Course(
        "ELECTIVE 201",
        "Independent Study",
        "10045",
        3,
        "TuTh 02:30 PM - 03:45 PM",
        "Library 204",
        "Dr. Faculty Advisor",
        "Hybrid",
    ),
]


_INSTITUTION_COURSE_POOLS: dict[str, list[dict[str, Any]]] = {
    "psu": [
        {
            "subject": "CMPSC",
            "number": "465",
            "title": "Data Structures & Algorithms",
            "credits": 3.0,
            "days": "MoWeFr",
            "time": "10:10AM–11:00AM",
            "location": "Willard 203",
            "instructor": "Vasquez, R.",
            "mode": "In-Person",
        },
        {
            "subject": "MATH",
            "number": "230",
            "title": "Calculus & Vector Analysis",
            "credits": 4.0,
            "days": "TuTh",
            "time": "01:35PM–02:50PM",
            "location": "Thomas 102",
            "instructor": "Nowak, A.",
            "mode": "In-Person",
        },
        {
            "subject": "ENGL",
            "number": "202C",
            "title": "Technical Writing",
            "credits": 3.0,
            "days": "MoWe",
            "time": "09:05AM–10:20AM",
            "location": "Boucke 214",
            "instructor": "O'Connor, M.",
            "mode": "Hybrid",
        },
        {
            "subject": "STAT",
            "number": "318",
            "title": "Applied Statistics",
            "credits": 3.0,
            "days": "TuTh",
            "time": "11:15AM–12:30PM",
            "location": "Osmond 110",
            "instructor": "Chen, H.",
            "mode": "In-Person",
        },
        {
            "subject": "PHYS",
            "number": "212",
            "title": "Physics — Electricity & Magnetism",
            "credits": 4.0,
            "days": "MoWeFr",
            "time": "02:30PM–03:20PM",
            "location": "Davey Lab 339",
            "instructor": "Bhattacharya, S.",
            "mode": "In-Person",
        },
        {
            "subject": "IST",
            "number": "331",
            "title": "Information & Organizations",
            "credits": 3.0,
            "days": "We",
            "time": "06:00PM–08:45PM",
            "location": "Westgate E201",
            "instructor": "Miller, K.",
            "mode": "Online Sync",
        },
        {
            "subject": "PSYCH",
            "number": "100",
            "title": "Introductory Psychology",
            "credits": 3.0,
            "days": "MoWeFr",
            "time": "08:00AM–08:50AM",
            "location": "Forum 101",
            "instructor": "Kowalski, J.",
            "mode": "In-Person",
        },
        {
            "subject": "ACCTG",
            "number": "211",
            "title": "Financial Accounting",
            "credits": 3.0,
            "days": "TuTh",
            "time": "03:05PM–04:20PM",
            "location": "Business Bldg 108",
            "instructor": "Stern, D.",
            "mode": "In-Person",
        },
        {
            "subject": "BIOL",
            "number": "110",
            "title": "Basic Concepts in Biology",
            "credits": 3.0,
            "days": "MoWeFr",
            "time": "09:05AM–09:55AM",
            "location": "Mueller Lab 158",
            "instructor": "Alvarez, E.",
            "mode": "In-Person",
        },
        {
            "subject": "COMM",
            "number": "150",
            "title": "Media Literacy & Society",
            "credits": 3.0,
            "days": "TuTh",
            "time": "12:05PM–01:20PM",
            "location": "Carnegie 113",
            "instructor": "Hayes, B.",
            "mode": "In-Person",
        },
    ],
    "ucla": [
        {
            "subject": "CS",
            "number": "31",
            "title": "Introduction to Computer Science I",
            "credits": 4.0,
            "days": "TuTh",
            "time": "02:00PM–03:50PM",
            "location": "Boelter Hall 3400",
            "instructor": "Smallberg, D.",
            "mode": "In-Person",
        },
        {
            "subject": "MATH",
            "number": "32A",
            "title": "Calculus of Several Variables",
            "credits": 4.0,
            "days": "MoWeFr",
            "time": "10:00AM–10:50AM",
            "location": "MS 4000A",
            "instructor": "Greene, J.",
            "mode": "In-Person",
        },
        {
            "subject": "ENGLISH",
            "number": "3",
            "title": "Writing for the Disciplines",
            "credits": 4.0,
            "days": "TuTh",
            "time": "12:30PM–01:45PM",
            "location": "Kaplan Hall 135",
            "instructor": "King, R.",
            "mode": "In-Person",
        },
        {
            "subject": "ECON",
            "number": "1",
            "title": "Principles of Economics",
            "credits": 5.0,
            "days": "MoWeFr",
            "time": "09:00AM–09:50AM",
            "location": "Dodd Hall 121",
            "instructor": "Rojas, F.",
            "mode": "In-Person",
        },
        {
            "subject": "PSYCH",
            "number": "10",
            "title": "Introductory Psychology",
            "credits": 4.0,
            "days": "TuTh",
            "time": "11:00AM–12:15PM",
            "location": "Franz Hall 1178",
            "instructor": "Firstenberg, I.",
            "mode": "In-Person",
        },
        {
            "subject": "POL SCI",
            "number": "10",
            "title": "Introduction to Political Theory",
            "credits": 4.0,
            "days": "MoWe",
            "time": "02:00PM–03:15PM",
            "location": "Bunche Hall 1209",
            "instructor": "Panagia, D.",
            "mode": "Hybrid",
        },
        {
            "subject": "SOCIOL",
            "number": "1",
            "title": "Introduction to Sociology",
            "credits": 4.0,
            "days": "TuTh",
            "time": "09:30AM–10:45AM",
            "location": "Haines Hall 39",
            "instructor": "Collett, J.",
            "mode": "In-Person",
        },
        {
            "subject": "CHEM",
            "number": "14A",
            "title": "Atomic and Molecular Structure",
            "credits": 4.0,
            "days": "MoWeFr",
            "time": "11:00AM–11:50AM",
            "location": "Young Hall CS50",
            "instructor": "Lavelle, L.",
            "mode": "In-Person",
        },
    ],
    "nyu": [
        {
            "subject": "CSCI-UA",
            "number": "101",
            "title": "Introduction to Computer Science",
            "credits": 4.0,
            "days": "TuTh",
            "time": "02:00PM–03:15PM",
            "location": "Warren Weaver 109",
            "instructor": "Kapp, C.",
            "mode": "In-Person",
        },
        {
            "subject": "WRITEXP-UA",
            "number": "1",
            "title": "Writing the Essay",
            "credits": 4.0,
            "days": "MoWe",
            "time": "11:00AM–12:15PM",
            "location": "Silver Center 401",
            "instructor": "Gould, S.",
            "mode": "In-Person",
        },
        {
            "subject": "ECON-UA",
            "number": "1",
            "title": "Introduction to Microeconomics",
            "credits": 4.0,
            "days": "Fr",
            "time": "10:00AM–11:50AM",
            "location": "194 Mercer 206",
            "instructor": "Paizis, M.",
            "mode": "In-Person",
        },
        {
            "subject": "PSYCH-UA",
            "number": "1",
            "title": "Introduction to Psychology",
            "credits": 4.0,
            "days": "MoWeFr",
            "time": "09:30AM–10:45AM",
            "location": "Meyer Hall 121",
            "instructor": "Bavel, J.",
            "mode": "In-Person",
        },
        {
            "subject": "MATH-UA",
            "number": "121",
            "title": "Calculus I",
            "credits": 4.0,
            "days": "MoWeFr",
            "time": "12:30PM–01:20PM",
            "location": "Courant Hall 101",
            "instructor": "Shapiro, L.",
            "mode": "In-Person",
        },
        {
            "subject": "HIST-UA",
            "number": "1",
            "title": "World History to 1500",
            "credits": 4.0,
            "days": "TuTh",
            "time": "03:30PM–04:45PM",
            "location": "Kimmel Center 802",
            "instructor": "Zarrow, P.",
            "mode": "In-Person",
        },
        {
            "subject": "FREN-UA",
            "number": "11",
            "title": "Elementary French I",
            "credits": 4.0,
            "days": "MoTuWeTh",
            "time": "01:00PM–01:50PM",
            "location": "Maison Française 102",
            "instructor": "Dubois, E.",
            "mode": "In-Person",
        },
        {
            "subject": "BIOL-UA",
            "number": "11",
            "title": "Principles of Biology I",
            "credits": 4.0,
            "days": "MoWe",
            "time": "02:00PM–03:15PM",
            "location": "Brown Bldg 101",
            "instructor": "Fitch, D.",
            "mode": "Hybrid",
        },
    ],
    "umich": [
        {
            "subject": "EECS",
            "number": "280",
            "title": "Programming and Intro Data Structures",
            "credits": 4.0,
            "days": "MoWe",
            "time": "10:30AM–12:00PM",
            "location": "Dow 1010",
            "instructor": "DeOrio, A.",
            "mode": "In-Person",
        },
        {
            "subject": "MATH",
            "number": "215",
            "title": "Calculus III",
            "credits": 4.0,
            "days": "MoWeFr",
            "time": "09:00AM–10:00AM",
            "location": "East Hall 1360",
            "instructor": "Boland, P.",
            "mode": "In-Person",
        },
        {
            "subject": "PHYSICS",
            "number": "240",
            "title": "General Physics II",
            "credits": 4.0,
            "days": "MoWe",
            "time": "02:30PM–04:00PM",
            "location": "Randall Lab 170",
            "instructor": "Winn, J.",
            "mode": "In-Person",
        },
        {
            "subject": "ENGLISH",
            "number": "125",
            "title": "Academic Writing",
            "credits": 4.0,
            "days": "TuTh",
            "time": "01:00PM–02:30PM",
            "location": "Tisch Hall 201",
            "instructor": "Silver, D.",
            "mode": "In-Person",
        },
        {
            "subject": "ECON",
            "number": "101",
            "title": "Principles of Economics I",
            "credits": 4.0,
            "days": "MoWeFr",
            "time": "08:00AM–09:00AM",
            "location": "Lorimer Aud",
            "instructor": "Proulx, C.",
            "mode": "In-Person",
        },
        {
            "subject": "PSYCH",
            "number": "111",
            "title": "Introduction to Psychology",
            "credits": 4.0,
            "days": "TuTh",
            "time": "11:30AM–01:00PM",
            "location": "Modern Lang 1200",
            "instructor": "Schreier, P.",
            "mode": "In-Person",
        },
        {
            "subject": "STATS",
            "number": "250",
            "title": "Introduction to Statistics",
            "credits": 4.0,
            "days": "MoWe",
            "time": "04:00PM–05:30PM",
            "location": "Mason Hall 1420",
            "instructor": "Gunderson, B.",
            "mode": "In-Person",
        },
        {
            "subject": "SOC",
            "number": "100",
            "title": "Introduction to Sociology",
            "credits": 3.0,
            "days": "TuTh",
            "time": "10:00AM–11:30AM",
            "location": "Weiser Hall 110",
            "instructor": "McGann, P.",
            "mode": "Hybrid",
        },
    ],
    "ut_austin": [
        {
            "subject": "CS",
            "number": "312",
            "title": "Introduction to Programming",
            "credits": 3.0,
            "days": "TuTh",
            "time": "02:00PM–03:30PM",
            "location": "GDC 2.216",
            "instructor": "Scott, M.",
            "mode": "In-Person",
        },
        {
            "subject": "M",
            "number": "408C",
            "title": "Differential and Integral Calculus",
            "credits": 4.0,
            "days": "MoWeFr",
            "time": "09:00AM–10:00AM",
            "location": "PMA 4.102",
            "instructor": "Starbird, M.",
            "mode": "In-Person",
        },
        {
            "subject": "E",
            "number": "316L",
            "title": "British Literature",
            "credits": 3.0,
            "days": "TuTh",
            "time": "12:30PM–02:00PM",
            "location": "PAR 101",
            "instructor": "Rumrich, J.",
            "mode": "In-Person",
        },
        {
            "subject": "ECO",
            "number": "304K",
            "title": "Introduction to Microeconomics",
            "credits": 3.0,
            "days": "MoWeFr",
            "time": "11:00AM–12:00PM",
            "location": "BRB 1.118",
            "instructor": "Brandl, M.",
            "mode": "In-Person",
        },
        {
            "subject": "PSY",
            "number": "301",
            "title": "Introduction to Psychology",
            "credits": 3.0,
            "days": "TuTh",
            "time": "09:30AM–11:00AM",
            "location": "SEA 2.108",
            "instructor": "Pennebaker, J.",
            "mode": "In-Person",
        },
        {
            "subject": "GOV",
            "number": "310L",
            "title": "American Government",
            "credits": 3.0,
            "days": "MoWe",
            "time": "02:00PM–03:30PM",
            "location": "BAT 101",
            "instructor": "Moser, R.",
            "mode": "Hybrid",
        },
        {
            "subject": "CH",
            "number": "301",
            "title": "Principles of Chemistry I",
            "credits": 3.0,
            "days": "MoWeFr",
            "time": "08:00AM–09:00AM",
            "location": "WEL 2.224",
            "instructor": "Laude, D.",
            "mode": "In-Person",
        },
        {
            "subject": "RHE",
            "number": "306",
            "title": "Rhetoric and Writing",
            "credits": 3.0,
            "days": "TuTh",
            "time": "03:30PM–05:00PM",
            "location": "FAC 21",
            "instructor": "Davis, D.",
            "mode": "In-Person",
        },
    ],
    "up_diliman": [
        {
            "subject": "CS",
            "number": "132",
            "title": "Data Science",
            "credits": 3.0,
            "days": "TuTh",
            "time": "02:30PM–04:00PM",
            "location": "AECH 115",
            "instructor": "Tan, M.",
            "mode": "In-Person",
        },
        {
            "subject": "Math",
            "number": "114",
            "title": "Linear Algebra",
            "credits": 3.0,
            "days": "MoWeFr",
            "time": "08:30AM–09:30AM",
            "location": "Math Bldg 204",
            "instructor": "Reyes, J.",
            "mode": "In-Person",
        },
        {
            "subject": "CS",
            "number": "140",
            "title": "Operating Systems",
            "credits": 3.0,
            "days": "TuTh",
            "time": "10:00AM–11:30AM",
            "location": "AECH 201",
            "instructor": "Santos, P.",
            "mode": "In-Person",
        },
        {
            "subject": "Physics",
            "number": "72",
            "title": "Elementary Physics II",
            "credits": 4.0,
            "days": "MoWeFr",
            "time": "10:00AM–11:00AM",
            "location": "NIP Rm 102",
            "instructor": "Aquino, C.",
            "mode": "In-Person",
        },
        {
            "subject": "Eng",
            "number": "13",
            "title": "Writing as Thinking",
            "credits": 3.0,
            "days": "TuTh",
            "time": "01:00PM–02:30PM",
            "location": "CAL 308",
            "instructor": "Cruz, A.",
            "mode": "In-Person",
        },
    ],
    "usp": [
        {
            "subject": "SCC",
            "number": "0103",
            "title": "Algoritmos e Estruturas de Dados I",
            "credits": 8.0,
            "days": "Seg/Qua",
            "time": "08:00–10:00",
            "location": "IME Sala 101",
            "instructor": "Ferreira, C.",
            "mode": "In-Person",
        },
        {
            "subject": "MAC",
            "number": "0110",
            "title": "Introdução à Computação",
            "credits": 8.0,
            "days": "Ter/Qui",
            "time": "10:00–12:00",
            "location": "IME Sala 105",
            "instructor": "Silva, M.",
            "mode": "In-Person",
        },
        {
            "subject": "MAT",
            "number": "0111",
            "title": "Cálculo Diferencial e Integral I",
            "credits": 8.0,
            "days": "Seg/Qua/Sex",
            "time": "14:00–16:00",
            "location": "IME Sala 202",
            "instructor": "Oliveira, R.",
            "mode": "In-Person",
        },
        {
            "subject": "FAP",
            "number": "0151",
            "title": "Física I",
            "credits": 8.0,
            "days": "Ter/Qui",
            "time": "14:00–16:00",
            "location": "IF Ed. Principal",
            "instructor": "Souza, L.",
            "mode": "In-Person",
        },
    ],
    "universiti_malaya": [
        {
            "subject": "WIA",
            "number": "1001",
            "title": "Information Systems",
            "credits": 3.0,
            "days": "Isnin/Rabu",
            "time": "09:00AM–10:30AM",
            "location": "FSKTM DK1",
            "instructor": "Ahmad, N.",
            "mode": "In-Person",
        },
        {
            "subject": "WIA",
            "number": "1002",
            "title": "Data Structures",
            "credits": 4.0,
            "days": "Selasa/Khamis",
            "time": "11:00AM–01:00PM",
            "location": "FSKTM Makmal 3",
            "instructor": "Lim, W.",
            "mode": "In-Person",
        },
        {
            "subject": "WIA",
            "number": "2001",
            "title": "Database Systems",
            "credits": 3.0,
            "days": "Isnin/Rabu",
            "time": "02:00PM–03:30PM",
            "location": "FSKTM DK2",
            "instructor": "Rahman, M.",
            "mode": "In-Person",
        },
        {
            "subject": "GIG",
            "number": "1012",
            "title": "Philosophy and Current Issues",
            "credits": 2.0,
            "days": "Jumaat",
            "time": "09:00AM–11:00AM",
            "location": "FASS Dewan Kuliah",
            "instructor": "Ismail, S.",
            "mode": "In-Person",
        },
    ],
    "makerere": [
        {
            "subject": "CSC",
            "number": "1100",
            "title": "Computer Architecture",
            "credits": 4.0,
            "days": "Mon/Wed",
            "time": "08:00AM–10:00AM",
            "location": "CoCIS Block A",
            "instructor": "Okello, P.",
            "mode": "In-Person",
        },
        {
            "subject": "CSC",
            "number": "1200",
            "title": "Data Communication & Networks",
            "credits": 4.0,
            "days": "Tue/Thu",
            "time": "10:00AM–12:00PM",
            "location": "CoCIS Lab 2",
            "instructor": "Kato, B.",
            "mode": "In-Person",
        },
        {
            "subject": "MTH",
            "number": "1101",
            "title": "Calculus I",
            "credits": 3.0,
            "days": "Mon/Wed/Fri",
            "time": "02:00PM–03:00PM",
            "location": "Science Quad LT1",
            "instructor": "Mukasa, E.",
            "mode": "In-Person",
        },
        {
            "subject": "ENG",
            "number": "1101",
            "title": "Communication Skills",
            "credits": 3.0,
            "days": "Fri",
            "time": "09:00AM–12:00PM",
            "location": "CHUSS Hall 4",
            "instructor": "Namubiru, F.",
            "mode": "In-Person",
        },
    ],
    "unilag": [
        {
            "subject": "CSC",
            "number": "311",
            "title": "Algorithms & Complexity Analysis",
            "credits": 3.0,
            "days": "Mon/Wed",
            "time": "10:00AM–11:30AM",
            "location": "Faculty of Science LR1",
            "instructor": "Dr. Babatunde, A.",
            "mode": "In-Person",
        },
        {
            "subject": "CSC",
            "number": "313",
            "title": "Database Design & Management",
            "credits": 3.0,
            "days": "Tue/Thu",
            "time": "12:00PM–01:30PM",
            "location": "Science Comp Lab 1",
            "instructor": "Prof. Okafor, C.",
            "mode": "In-Person",
        },
        {
            "subject": "MAT",
            "number": "311",
            "title": "Numerical Analysis I",
            "credits": 3.0,
            "days": "Mon/Wed",
            "time": "08:00AM–09:30AM",
            "location": "Math Dept LT3",
            "instructor": "Dr. Balogun, T.",
            "mode": "In-Person",
        },
        {
            "subject": "GST",
            "number": "201",
            "title": "Nigerian Peoples and Culture",
            "credits": 2.0,
            "days": "Fri",
            "time": "09:00AM–11:00AM",
            "location": "Arts Theatre",
            "instructor": "Dr. Lawal, M.",
            "mode": "In-Person",
        },
    ],
}


def _get_course_pool(institution_id: str) -> list[dict[str, Any]]:
    """Return the institution-specific course pool, falling back to PSU."""
    return _INSTITUTION_COURSE_POOLS.get(
        institution_id, _INSTITUTION_COURSE_POOLS["psu"]
    )


def generate_academic_state(
    rng: random.Random,
    program: str,
    temporal: TemporalAnchor,
    institution_id: str = "psu",
    profile: SyntheticProfile | None = None,
) -> AcademicState:
    if institution_id == "psu" and program in CURRICULA:
        base_pool = CURRICULA[program]
        courses: list[Course] = []
        for idx, c in enumerate(base_pool):
            crn = _generate_crn(rng, institution_id, idx)
            courses.append(
                Course(
                    code=c.code,
                    title=c.title,
                    crn=crn,
                    credits=c.credits,
                    meeting_pattern=c.meeting_pattern,
                    location=c.location,
                    instructor=c.instructor,
                    mode=c.mode,
                )
            )
    elif program in CURRICULA:
        base_pool = CURRICULA[program]
        courses = []
        for idx, c in enumerate(base_pool):
            crn = _generate_crn(rng, institution_id, idx)
            courses.append(
                Course(
                    code=c.code,
                    title=c.title,
                    crn=crn,
                    credits=c.credits,
                    meeting_pattern=c.meeting_pattern,
                    location=c.location,
                    instructor=c.instructor,
                    mode=c.mode,
                )
            )
    else:
        raw_pool = _get_course_pool(institution_id)
        target_count = (
            4
            if institution_id in ("ucla", "makerere", "unilag", "universiti_malaya")
            else min(5, len(raw_pool))
        )
        selected_raw = (
            rng.sample(raw_pool, target_count)
            if len(raw_pool) >= target_count
            else list(raw_pool)
        )
        courses = []
        inst = INSTITUTIONS.get(institution_id)
        for idx, item in enumerate(selected_raw):
            subj = item["subject"]
            nbr = item.get("number", "")
            if inst and "{SUBJ}{NNN}" in inst.course_id_format:
                code = f"{subj}{nbr}".strip()
            elif nbr:
                code = f"{subj} {nbr}".strip()
            else:
                code = subj
            crn = _generate_crn(rng, institution_id, idx)
            credits = int(item["credits"])
            meeting = (
                f"{item.get('days', 'MoWeFr')} {item.get('time', '10:00AM-11:00AM')}"
            )
            location = item.get("location", "Main Hall 101")
            instructor = item.get("instructor", "Faculty Instructor")
            mode = item.get("mode", "In-Person")
            courses.append(
                Course(
                    code=code,
                    title=item["title"],
                    crn=crn,
                    credits=credits,
                    meeting_pattern=meeting,
                    location=location,
                    instructor=instructor,
                    mode=mode,
                )
            )

    total_cred = sum(c.credits for c in courses)

    if profile:
        gpa = (
            profile.gpa_cumulative
            if profile.gpa_cumulative > 0
            else round(rng.uniform(3.10, 3.98), 2)
        )
        advisor = profile.advisor_name or "Dr. Arthur Pendelton"
        term_name = profile.current_term_label or temporal.term_name
    else:
        gpa = round(rng.uniform(3.10, 3.98), 2)
        advisors = [
            "Dr. Arthur Pendelton",
            "Dr. Eleanor Vance",
            "Dr. Marcus Sterling",
            "Dr. Sarah Jenkins",
        ]
        advisor = rng.choice(advisors)
        term_name = temporal.term_name

    return AcademicState(
        term_name=term_name,
        term_code=temporal.term_code,
        courses=courses,
        total_credits=total_cred,
        advisor=advisor,
        cumulative_gpa=gpa,
        tuition_balance="$0.00",
        payment_status="PAID IN FULL",
        transaction_id=f"TXN-{rng.randint(1000000, 9999999)}",
    )


def _generate_student_id(rng: random.Random, institution: Institution) -> str:
    """Generate an ID that matches the institution's verified format."""
    iid = institution.id

    if iid == "psu":
        for _ in range(20):
            raw_digits = "".join(str(rng.randint(0, 9)) for _ in range(9))
            if not raw_digits.startswith("9"):
                raw_digits = "9" + raw_digits[1:]
            if raw_digits != raw_digits[::-1] and len(set(raw_digits)) > 3:
                return raw_digits
        fallback = str(rng.randint(10**8, 10**9 - 1))
        if not fallback.startswith("9"):
            fallback = "9" + fallback[1:]
        return fallback

    elif iid == "ucla":
        # Must start with 9, then 8 more digits
        tail = "".join(str(rng.randint(0, 9)) for _ in range(8))
        return f"9{tail}"

    elif iid == "nyu":
        # N + 8 digits
        digits = "".join(str(rng.randint(0, 9)) for _ in range(8))
        return f"N{digits}"

    elif iid == "umich":
        # 8-digit UMID — avoid leading zeros
        return str(rng.randint(10000000, 99999999))

    elif iid == "ut_austin":
        # UT EID: 2–4 lowercase letters + 3–5 digits
        letters = "".join(
            rng.choice("abcdefghjklmnpqrstuvwxyz") for _ in range(rng.randint(2, 3))
        )
        digits = "".join(str(rng.randint(0, 9)) for _ in range(rng.randint(4, 5)))
        return f"{letters}{digits}"

    elif iid == "up_diliman":
        # YYYY-NNNNN: admission year (2020-2024) + 5 digits — per research spec
        year = rng.randint(2020, 2024)
        seq = rng.randint(10000, 99999)
        return f"{year}-{seq:05d}"

    elif iid == "usp":
        # Número USP: 7-8 numeric digits
        return str(rng.randint(1000000, 99999999))

    elif iid == "universiti_malaya":
        # S + 4-digit year + 6-digit sequence — per research spec
        year = rng.randint(2020, 2024)
        seq = rng.randint(100000, 999999)
        return f"S{year}{seq}"

    elif iid == "makerere":
        # YY/U/NNNNN/PS
        year = rng.randint(22, 25)
        seq = rng.randint(10000, 99999)
        return f"{year:02d}/U/{seq:05d}/PS"

    elif iid == "unilag":
        # YYYY/1/NNNNN — per research spec
        year = rng.randint(2020, 2024)
        seq = rng.randint(10000, 99999)
        return f"{year}/1/{seq:05d}"

    else:
        pattern = institution.student_id_format or institution.id_format or r"\d{9}"
        digits = re.findall(r"\\d\{(\d+)\}", pattern)
        n = int(digits[0]) if digits else 9
        pfx = (
            institution.student_id_prefix
            if institution.student_id_prefix is not None
            else (institution.id_prefix or "")
        )
        for _ in range(20):
            raw_digits = "".join(str(rng.randint(0, 9)) for _ in range(n))
            if institution.student_id_starts_with and not raw_digits.startswith(
                institution.student_id_starts_with
            ):
                raw_digits = institution.student_id_starts_with + raw_digits[1:]
            sid = f"{pfx}{raw_digits}"
            if raw_digits != raw_digits[::-1] and len(set(raw_digits)) > 3:
                return sid
        fallback = "".join(str(rng.randint(0, 9)) for _ in range(n))
        return f"{pfx}{fallback}"


def _generate_student_email(
    profile_name: str,
    institution: Institution,
    rng: random.Random,
    student_id: str = "",
    login_id: str = "",
) -> str:
    """Institution-accurate email format."""
    parts = profile_name.split()
    first = parts[0].lower() if parts else "student"
    last = parts[-1].lower() if len(parts) > 1 else "student"

    if institution.id == "ut_austin":
        eid = student_id or login_id or f"{first[:2]}{rng.randint(1000, 9999)}"
        return f"{eid}@my.utexas.edu"
    elif institution.id == "umich":
        uniq = login_id or (first[0] + last)[:8]
        return f"{uniq}@umich.edu"
    elif institution.id == "makerere":
        return f"{first}.{last}{rng.randint(10, 99)}@students.mak.ac.ug"
    elif institution.id == "universiti_malaya":
        return f"{first}.{last}{rng.randint(10, 99)}@siswa.um.edu.my"
    else:
        # Standard: first initial + up to 6 of last + 2 digits @ domain
        return f"{first[0]}{last[:6]}{rng.randint(10, 99)}@{institution.domain}"


def _format_date_intl(dt: date, institution_id: str) -> str:
    """Format a date according to the institution's real document convention."""
    if institution_id in ("makerere", "unilag"):
        # Ordinal English: "15th October, 2025"
        day = dt.day
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(
            day % 10 if day not in (11, 12, 13) else 0, "th"
        )
        return dt.strftime(f"%-d{suffix} %B, %Y")
    elif institution_id == "usp":
        # Brazilian: "15/10/2025"
        return dt.strftime("%d/%m/%Y")
    elif institution_id == "universiti_malaya":
        # Malaysian: "15 Oktober 2025" (in Malay)
        malay_months = [
            "Januari",
            "Februari",
            "Mac",
            "April",
            "Mei",
            "Jun",
            "Julai",
            "Ogos",
            "September",
            "Oktober",
            "November",
            "Disember",
        ]
        return f"{dt.day} {malay_months[dt.month - 1]} {dt.year}"
    else:
        # Philippine / US / default: "October 15, 2025"
        return dt.strftime("%B %d, %Y")


# =====================================================================
# PROFILE GENERATION ENGINE
# =====================================================================


def generate_profile(
    scenario_name: str = "undergraduate",
    seed: int = 42,
    override_institution_id: str | None = None,
    institution_id: str | None = None,
) -> SyntheticProfile:
    scen = get_scenario(scenario_name)
    rng = random.Random(seed)

    inst_id = institution_id or override_institution_id or scen.institution_id
    institution = INSTITUTIONS.get(inst_id, INSTITUTIONS["psu"])

    first_name, last_name = SeededNameGenerator.generate(
        rng, institution_id=institution.id
    )
    program = rng.choice(institution.programs)

    temporal = get_temporal_anchor(rng)
    ref_date = temporal.current_date

    age_years = rng.randint(scen.min_age, scen.max_age)
    birth_year = ref_date.year - age_years
    birth_month = rng.randint(1, 12)
    birth_day = rng.randint(1, 28)
    date_of_birth = date(birth_year, birth_month, birth_day)

    duration_years = rng.choice(scen.program_duration_years)

    if institution.id in _TERM_CALENDARS:
        current_term_label, term_start, term_end = _current_term_for_institution(
            institution.id, ref_date
        )
    else:
        season, term_year, term_start, term_end = _current_term(
            ref_date, institution_id=institution.id
        )
        current_term_label = f"{season} {term_year}"
    print_dt = _document_print_date(rng, term_start, ref_date)

    student_id = _generate_student_id(rng, institution)

    # Institution-accurate login_id
    first_clean = re.sub(r"[^a-z]", "", first_name.lower()) or "j"
    last_clean = re.sub(r"[^a-z]", "", last_name.lower()) or "doe"
    if institution.id == "psu":
        login_id = f"{first_clean[:2]}{last_clean[:2]}{rng.randint(100, 999)}"
    elif institution.id == "nyu":
        login_id = f"{first_clean[:2]}{rng.randint(1000, 9999)}"
    elif institution.id == "umich":
        login_id = (first_clean[0] + last_clean)[:8]
    elif institution.id == "ut_austin":
        login_id = student_id
    elif institution.id == "ucla":
        login_id = f"{first_clean[0]}{last_clean[:7]}"
    elif institution.id == "usp":
        login_id = student_id
    elif institution.id == "universiti_malaya":
        login_id = student_id.lower()
    else:
        login_id = f"{first_clean[0]}{last_clean[:6]}"

    # Institution-accurate college or school
    college_or_school = ""
    if institution.schools:
        prog_low = program.lower()
        matched = None
        for s in institution.schools:
            s_low = s.lower()
            if any(
                k in prog_low and k in s_low
                for k in [
                    "engineer",
                    "business",
                    "arts",
                    "science",
                    "information",
                    "law",
                    "medicine",
                    "nursing",
                ]
            ):
                matched = s
                break
        college_or_school = matched if matched else rng.choice(institution.schools)

    if scen.role in (PersonRole.TEACHER, PersonRole.FACULTY):
        hire_age = rng.randint(22, min(age_years, 35))
        hire_year = birth_year + hire_age
        enrollment_date = date(hire_year, 8, 20)
        expected_graduation = date(hire_year + 30, 6, 30)
        academic_year = temporal.academic_year
        email = f"{first_name.lower()}.{last_name.lower()}@{institution.domain}"
        gpa_cum = 0.0
        gpa_term = 0.0
        cum_units = 0.0
        academic_standing = "Active Employee"
        advisor_name = "Office of the Dean"
        advisor_email = f"dean.faculty@{institution.domain}"
        enrollment_type = "Full-Time Faculty"
    else:
        if scenario_name == "recent-enrollment":
            start_year = ref_date.year
        elif scenario_name == "near-graduation":
            start_year = ref_date.year - (duration_years - 1)
        else:
            elapsed = rng.randint(0, max(0, duration_years - 1))
            start_year = ref_date.year - elapsed

        enrollment_date = date(start_year, 8, 25)
        grad_year = start_year + duration_years
        expected_graduation = date(grad_year, 5, 15)
        academic_year = temporal.academic_year
        email = _generate_student_email(
            f"{first_name} {last_name}",
            institution,
            rng,
            student_id=student_id,
            login_id=login_id,
        )

        acad_state = generate_academic_state(rng, program, temporal, institution.id)
        gpa_cum = acad_state.cumulative_gpa
        gpa_term = round(min(4.0, max(2.5, gpa_cum + rng.uniform(-0.25, 0.25))), 2)
        cum_units = float(rng.randint(28, 118))
        academic_standing = (
            "Ativo"
            if institution.id == "usp"
            else (
                "Aktif"
                if institution.id == "universiti_malaya"
                else ("Regular" if institution.id == "up_diliman" else "Good Standing")
            )
        )
        if institution.id == "usp":
            advisor_name = "Prof. Dr. Carlos Eduardo Ferreira"
        elif institution.id == "unilag":
            advisor_name = "Prof. A. O. Babatunde"
        elif institution.id == "makerere":
            advisor_name = "Dr. Paul Okello"
        elif institution.id == "universiti_malaya":
            advisor_name = "Prof. Madya Dr. Nor Azman Ismail"
        else:
            advisor_name = acad_state.advisor
        adv_clean = (
            advisor_name.lower()
            .replace("dr. ", "")
            .replace("prof. ", "")
            .replace("madya ", "")
            .replace(" ", ".")
        )
        advisor_email = f"{adv_clean}@{institution.domain}"
        enrollment_type = (
            "Regular"
            if institution.id == "up_diliman"
            else ("Ativo" if institution.id == "usp" else "Full-Time")
        )

    campus = "University Park" if institution.id == "psu" else institution.city
    seal_mat = f"{institution.id}:{first_name}:{last_name}:{student_id}:{current_term_label}:{print_dt.date().isoformat()}"
    document_seal_hash = (
        hashlib.sha256(seal_mat.encode("utf-8")).hexdigest()[:16].upper()
    )

    return SyntheticProfile(
        first_name=first_name,
        last_name=last_name,
        role=scen.role,
        date_of_birth=date_of_birth,
        institution_id=institution.id,
        institution_name=institution.name,
        city=institution.city,
        country=institution.country,
        domain=institution.domain,
        student_id=student_id,
        email=email,
        program=program,
        academic_level=scen.academic_level,
        enrollment_date=enrollment_date,
        expected_graduation=expected_graduation,
        academic_year=academic_year,
        gpa_cumulative=gpa_cum,
        gpa_term=gpa_term,
        cumulative_units=cum_units,
        academic_standing=academic_standing,
        campus=campus,
        advisor_name=advisor_name,
        advisor_email=advisor_email,
        document_seal_hash=document_seal_hash,
        current_term_label=current_term_label,
        term_start_date=term_start,
        term_end_date=term_end,
        document_print_date=print_dt.date(),
        enrollment_type=enrollment_type,
        college_or_school=college_or_school,
        login_id=login_id,
    )


# =====================================================================
# DOCUMENT TEMPLATE BUILDERS (xhtml2pdf / Browser Safe CSS)
# =====================================================================


def generate_registrar_letter_document(
    profile: SyntheticProfile,
    academic_state: AcademicState,
    temporal: TemporalAnchor,
    kind: DocumentKind = DocumentKind.SCHEDULE,
) -> Document:
    name = f"{profile.first_name} {profile.last_name}"
    retrieved_str = temporal.retrieval_date.strftime("%B %d, %Y")
    term_start = (
        profile.term_start_date or temporal.term_start_date or temporal.retrieval_date
    )
    term_end = (
        profile.term_end_date or temporal.term_end_date or temporal.expiration_date
    )
    term_start_str = term_start.strftime("%m/%d/%Y")
    term_end_str = term_end.strftime("%m/%d/%Y")
    print_date = profile.document_print_date or temporal.retrieval_date
    print_date_str = print_date.strftime("%B %d, %Y")
    term_label = profile.current_term_label or academic_state.term_name
    inst = profile.institution

    if inst.id == "ucla":
        # Real MyUCLA Proof of Enrollment Letter
        school_str = profile.college_or_school or "College of Letters and Science"
        dob_str = profile.date_of_birth.strftime("%B %d")
        adm_date_str = profile.enrollment_date.strftime("%B %d, %Y")
        deg_term = f"Spring {profile.expected_graduation.year}"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Enrollment Verification - {name}</title>
    <style>
        body {{
            font-family: Helvetica, Arial, sans-serif;
            color: #212529;
            margin: 0;
            padding: 24px;
            background: #ffffff;
            font-size: 12.5px;
        }}
        .topbar {{
            background: #2D68C4;
            color: #ffffff;
            padding: 10px 18px;
            font-size: 13px;
        }}
        .topbar-brand {{
            font-weight: 900;
            letter-spacing: .03em;
            font-size: 16px;
        }}
        .letter-content {{
            padding: 20px 24px;
        }}
        .header-block {{
            text-align: center;
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 12px;
            margin-bottom: 16px;
        }}
        .office-title {{
            font-size: 15px;
            font-weight: 700;
            color: #2D68C4;
        }}
        .office-sub {{
            font-size: 11.5px;
            color: #555555;
            margin-top: 2px;
        }}
        .date-line {{
            text-align: right;
            font-size: 11.5px;
            margin-bottom: 12px;
            color: #333333;
        }}
        .doc-title {{
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 10px;
            letter-spacing: .02em;
        }}
        .cert-statement {{
            font-size: 11.5px;
            margin-bottom: 14px;
            line-height: 1.5;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11.5px;
            margin-bottom: 16px;
        }}
        .info-table td {{
            padding: 4px 0;
        }}
        .info-table td.lbl {{
            width: 190px;
            color: #555555;
        }}
        .history-title {{
            font-size: 11.5px;
            font-weight: 700;
            margin-bottom: 6px;
        }}
        .history-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            margin-bottom: 24px;
        }}
        .history-table th, .history-table td {{
            padding: 6px 8px;
            text-align: left;
            border: 1px solid #dee2e6;
        }}
        .history-table th {{
            background: #f0f3f7;
            font-weight: 700;
        }}
        .footer-block {{
            margin-top: 24px;
            border-top: 1px solid #dee2e6;
            padding-top: 14px;
            font-size: 11px;
            color: #555555;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="topbar">
        <span class="topbar-brand">UCLA</span>
        <span style="margin-left: 14px;">{profile.institution_name}</span>
    </div>
    <div class="letter-content">
        <div class="header-block">
            <div class="office-title">OFFICE OF THE REGISTRAR</div>
            <div class="office-sub">1113 Murphy Hall &bull; Los Angeles, CA 90095</div>
            <div class="office-sub">{inst.domain} &bull; registrar.ucla.edu</div>
        </div>

        <div class="date-line">{print_date_str}</div>

        <div class="doc-title">ENROLLMENT VERIFICATION</div>
        <div class="cert-statement">
            This is to certify that the student named below is enrolled at the {profile.institution_name}.
        </div>

        <table class="info-table">
            <tr><td class="lbl">Student Name:</td><td><strong>{name}</strong></td></tr>
            <tr><td class="lbl">Student ID:</td><td><strong>{profile.student_id}</strong></td></tr>
            <tr><td class="lbl">Date of Birth (Month/Day):</td><td>{dob_str}</td></tr>
            <tr><td class="lbl">Date of Admission:</td><td>{adm_date_str}</td></tr>
            <tr><td class="lbl">College/School:</td><td>{school_str}</td></tr>
            <tr><td class="lbl">Major:</td><td>{profile.program}</td></tr>
            <tr><td class="lbl">Class Level &amp; Career:</td><td>{profile.academic_level.value.title()} &bull; Undergraduate</td></tr>
            <tr><td class="lbl">Official Term Window:</td><td>{term_start_str} to {term_end_str}</td></tr>
            <tr><td class="lbl">Degree-Expected Term:</td><td>{deg_term}</td></tr>
            <tr><td class="lbl">Enrollment Classification:</td><td>{profile.enrollment_type}</td></tr>
            <tr><td class="lbl">Academic Standing:</td><td>{profile.academic_standing}</td></tr>
        </table>

        <div class="history-title">Enrollment History:</div>
        <table class="history-table">
            <thead>
                <tr>
                    <th>Term</th>
                    <th>Dates</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{term_label}</td>
                    <td>{term_start.strftime("%b %d")} &ndash; {term_end.strftime("%b %d, %Y")}</td>
                    <td>{profile.enrollment_type}</td>
                </tr>
            </tbody>
        </table>

        <div class="footer-block">
            <div>This letter was generated by the UCLA Office of the Registrar student information system ({inst.portal_name}).</div>
            <div>Electronic Certification Seal: {profile.document_seal_hash} &bull; {inst.domain}</div>
            <div style="margin-top: 18px;">_________________________________________________</div>
            <div style="font-weight: bold; margin-top: 3px;">{inst.registrar_title}</div>
        </div>
    </div>
</body>
</html>
"""
    elif inst.id == "ut_austin":
        # Real UT Austin Texas One Stop Official Enrollment Certification
        school_str = profile.college_or_school or "Cockrell School of Engineering"
        exp_grad_str = profile.expected_graduation.strftime("%B %Y")

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Enrollment Certification - {name}</title>
    <style>
        body {{
            font-family: Helvetica, Arial, sans-serif;
            color: #212529;
            margin: 0;
            padding: 24px;
            background: #ffffff;
            font-size: 12.5px;
        }}
        .letter-content {{
            padding: 20px 24px;
        }}
        .header-block {{
            text-align: center;
            border-bottom: 2px solid #BF5700;
            padding-bottom: 14px;
            margin-bottom: 16px;
        }}
        .inst-title {{
            font-size: 16px;
            font-weight: 700;
            color: #BF5700;
            letter-spacing: .03em;
        }}
        .office-sub {{
            font-size: 11.5px;
            color: #555555;
            margin-top: 2px;
        }}
        .doc-title {{
            text-align: center;
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 14px;
            text-decoration: underline;
            color: #333F48;
            letter-spacing: .02em;
        }}
        .cert-statement {{
            font-size: 11.5px;
            margin-bottom: 14px;
            line-height: 1.5;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11.5px;
            margin-bottom: 16px;
        }}
        .info-table td {{
            padding: 4px 0;
        }}
        .info-table td.lbl {{
            width: 190px;
            color: #555555;
        }}
        .history-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            margin-bottom: 24px;
        }}
        .history-table th, .history-table td {{
            padding: 6px 8px;
            text-align: left;
            border: 1px solid #dee2e6;
        }}
        .history-table th {{
            background: #f5f5f5;
            font-weight: 700;
        }}
        .footer-block {{
            margin-top: 24px;
            border-top: 1px solid #dee2e6;
            padding-top: 14px;
            font-size: 11px;
            color: #555555;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="letter-content">
        <div class="header-block">
            <div class="inst-title">{profile.institution_name.upper()}</div>
            <div class="office-sub">{inst.registrar_title}</div>
            <div class="office-sub">Main Building (MAI), 110 Inner Campus Drive, Austin, TX 78712 &bull; registrar.utexas.edu</div>
        </div>

        <div class="doc-title">ENROLLMENT CERTIFICATION</div>
        <div class="cert-statement">
            This is to certify that the student named below has been enrolled at {profile.institution_name} as indicated:
        </div>

        <table class="info-table">
            <tr><td class="lbl">Student Name:</td><td><strong>{name}</strong></td></tr>
            <tr><td class="lbl">UT EID:</td><td><strong>{profile.student_id}</strong></td></tr>
            <tr><td class="lbl">Curriculum:</td><td>{profile.program}, B.S. &mdash; {school_str}</td></tr>
            <tr><td class="lbl">Expected Graduation:</td><td>{exp_grad_str}</td></tr>
            <tr><td class="lbl">Official Term Window:</td><td>{term_start_str} to {term_end_str}</td></tr>
            <tr><td class="lbl">Enrollment Classification:</td><td>{profile.enrollment_type}</td></tr>
            <tr><td class="lbl">Academic Standing:</td><td>{profile.academic_standing}</td></tr>
        </table>

        <table class="history-table">
            <thead>
                <tr>
                    <th>Term</th>
                    <th>Dates of Enrollment</th>
                    <th>Hours</th>
                    <th>Classification</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{term_label}</td>
                    <td>{term_start.strftime("%B %d")} &ndash; {term_end.strftime("%B %d, %Y")}</td>
                    <td>{academic_state.total_credits}</td>
                    <td>{profile.enrollment_type}</td>
                </tr>
            </tbody>
        </table>

        <div class="footer-block">
            <div>Electronic Certification Seal: {profile.document_seal_hash} &bull; Issued by Texas One Stop ({inst.portal_name})</div>
            <div style="margin-top: 16px;">_________________________________________________ &ensp;&ensp;&ensp;&ensp;&ensp;&ensp; {print_date_str}</div>
            <div style="font-weight: bold; margin-top: 3px;">{inst.registrar_title} &bull; {inst.domain}</div>
        </div>
    </div>
</body>
</html>
"""
    elif inst.id == "up_diliman":
        # University of the Philippines Diliman — CRS Form 5 (Registration Form)
        school_str = (
            profile.college_or_school
            or (inst.schools[0] if inst.schools else "")
            or "College of Engineering"
        )
        diff_years = max(
            1, min(4, (print_date.year - profile.enrollment_date.year) + 1)
        )
        year_suffix = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(
            diff_years, f"{diff_years}th"
        )
        year_level_str = f"{year_suffix} Year"
        issued_date_str = _format_date_intl(print_date, "up_diliman")
        ref_hash = profile.document_seal_hash[:7].upper()

        course_rows = []
        section_codes = ["THX", "WFX", "MHX", "TFX", "WFV", "THY"]
        for idx, c in enumerate(academic_state.courses):
            sec = section_codes[idx % len(section_codes)]
            course_rows.append(
                f"""<tr>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6;">{c.crn}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6; font-weight: 600;">{c.code}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6;">{c.title}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6; text-align: center;">{sec}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6; text-align: center;">{c.credits}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6;">{c.meeting_pattern}</td>
                </tr>"""
            )
        courses_table_body = "\n".join(course_rows)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Registration Form (Form 5) - {name}</title>
    <style>
        body {{
            font-family: Arial, Helvetica, sans-serif;
            color: #212529;
            margin: 0;
            padding: 24px;
            background: #ffffff;
            font-size: 12px;
        }}
        .topbar {{
            background: #7B0027;
            color: #ffffff;
            padding: 8px 18px;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .topbar-brand {{
            font-weight: 700;
            letter-spacing: .02em;
        }}
        .letter-content {{
            padding: 16px 20px;
        }}
        .header-block {{
            text-align: center;
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 12px;
            margin-bottom: 14px;
        }}
        .inst-title {{
            font-size: 14px;
            font-weight: 700;
            color: #7B0027;
            letter-spacing: .02em;
        }}
        .office-sub {{
            font-size: 12px;
            font-weight: 700;
            color: #014421;
            margin-top: 2px;
        }}
        .loc-sub {{
            font-size: 11px;
            color: #555555;
            margin-top: 2px;
        }}
        .doc-title {{
            font-size: 13px;
            font-weight: 700;
            margin-top: 10px;
            text-decoration: underline;
            color: #212529;
        }}
        .term-sub {{
            font-size: 11px;
            color: #555555;
            margin-top: 3px;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11.5px;
            margin-bottom: 14px;
        }}
        .info-table td {{
            padding: 3px 0;
        }}
        .info-table td.lbl {{
            width: 180px;
            color: #555555;
        }}
        .section-heading {{
            font-size: 11.5px;
            font-weight: 700;
            margin-bottom: 6px;
            color: #212529;
        }}
        .courses-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            margin-bottom: 14px;
        }}
        .courses-table th {{
            background: #7B0027;
            color: #ffffff;
            padding: 6px 8px;
            font-weight: 700;
            text-align: left;
        }}
        .courses-table tfoot td {{
            background: #f8f9fa;
            border-top: 2px solid #dee2e6;
            font-size: 11px;
        }}
        .footer-block {{
            margin-top: 16px;
            border-top: 1px solid #dee2e6;
            padding-top: 12px;
            font-size: 11px;
            color: #555555;
        }}
    </style>
</head>
<body>
    <div class="topbar">
        <span class="topbar-brand">UNIVERSITY OF THE PHILIPPINES DILIMAN</span>
        <span>Office of the University Registrar &bull; CRS</span>
    </div>
    <div class="letter-content">
        <div class="header-block">
            <div class="inst-title">UNIVERSITY OF THE PHILIPPINES DILIMAN</div>
            <div class="office-sub">Office of the University Registrar</div>
            <div class="loc-sub">Diliman, Quezon City 1101 &bull; our.upd.edu.ph &bull; University of the Philippines Diliman</div>
            <div class="doc-title">REGISTRATION FORM (FORM 5)</div>
            <div class="term-sub">{term_label}</div>
        </div>

        <table class="info-table">
            <tr><td class="lbl">Student Number:</td><td><strong>{profile.student_id}</strong></td></tr>
            <tr><td class="lbl">Student Name:</td><td><strong>{name}</strong></td></tr>
            <tr><td class="lbl">Degree Program:</td><td>{profile.program}</td></tr>
            <tr><td class="lbl">College / Unit:</td><td>{school_str}</td></tr>
            <tr><td class="lbl">Year Level:</td><td>{year_level_str}</td></tr>
            <tr><td class="lbl">Status:</td><td>{profile.academic_standing}</td></tr>
        </table>

        <div class="section-heading">Enrolled Courses &mdash; {term_label}</div>
        <table class="courses-table">
            <thead>
                <tr>
                    <th style="width: 12%;">Class Code</th>
                    <th style="width: 14%;">Course</th>
                    <th>Title</th>
                    <th style="width: 10%; text-align: center;">Section</th>
                    <th style="width: 8%; text-align: center;">Units</th>
                    <th style="width: 26%;">Schedule</th>
                </tr>
            </thead>
            <tbody>
                {courses_table_body}
            </tbody>
            <tfoot>
                <tr style="font-weight: 700;">
                    <td colspan="4" style="padding: 6px 8px; text-align: right;">Total Units:</td>
                    <td style="padding: 6px 8px; text-align: center;">{academic_state.total_credits}</td>
                    <td></td>
                </tr>
            </tfoot>
        </table>

        <div class="footer-block">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="vertical-align: top; width: 33%;">
                        <div style="border: 1px dashed #7B0027; color: #7B0027; padding: 10px; text-align: center; font-size: 10px; font-weight: 700;">
                            OFFICIAL SEAL<br>Office of the University Registrar
                        </div>
                    </td>
                    <td style="vertical-align: top; text-align: center; width: 34%;">
                        <div style="margin-top: 15px;">____________________________________</div>
                        <div style="font-weight: 700; margin-top: 4px;">University Registrar</div>
                        <div style="margin-top: 4px; font-size: 10.5px;">Date Issued: {issued_date_str}</div>
                    </td>
                    <td style="vertical-align: top; text-align: right; width: 33%; font-family: monospace; font-size: 10px; color: #666666;">
                        Doc Ref: OUR-F5-{print_date.year}-{ref_hash}<br>
                        Verify: our.upd.edu.ph/verify
                    </td>
                </tr>
            </table>
        </div>
    </div>
</body>
</html>
"""
    elif inst.id == "usp":
        # Universidade de São Paulo — Sistema Janus / Júpiter Atestado de Matrícula
        school_str = (
            profile.college_or_school
            or (inst.schools[0] if inst.schools else "")
            or "Instituto de Matemática e Estatística (IME)"
        )
        emitido_str = _format_date_intl(print_date, "usp")
        matricula_str = _format_date_intl(profile.enrollment_date, "usp")
        auth_code = profile.document_seal_hash[:14].lower()

        course_rows = []
        for c in academic_state.courses:
            course_rows.append(
                f"""<tr>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6; font-family: monospace; font-weight: 600;">{c.code}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6;">{c.title}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6; text-align: center;">{c.credits}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6; text-align: center;">Matriculado</td>
                </tr>"""
            )
        courses_table_body = "\n".join(course_rows)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Atestado de Matrícula - {name}</title>
    <style>
        body {{
            font-family: Arial, Helvetica, sans-serif;
            color: #212529;
            margin: 0;
            padding: 24px;
            background: #ffffff;
            font-size: 12px;
        }}
        .topbar {{
            background: #003366;
            color: #ffffff;
            padding: 8px 18px;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .topbar-brand {{
            font-weight: 700;
            letter-spacing: .02em;
        }}
        .letter-content {{
            padding: 16px 20px;
        }}
        .header-block {{
            text-align: center;
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 12px;
            margin-bottom: 14px;
        }}
        .inst-title {{
            font-size: 14px;
            font-weight: 700;
            color: #003366;
            letter-spacing: .02em;
        }}
        .loc-sub {{
            font-size: 11px;
            color: #555555;
            margin-top: 3px;
        }}
        .doc-title {{
            font-size: 13px;
            font-weight: 700;
            margin-top: 8px;
            color: #003366;
            letter-spacing: .02em;
        }}
        .cert-statement {{
            font-size: 11.5px;
            margin-bottom: 12px;
            line-height: 1.5;
            color: #333333;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11.5px;
            margin-bottom: 14px;
        }}
        .info-table td {{
            padding: 3px 0;
        }}
        .info-table td.lbl {{
            width: 180px;
            color: #555555;
        }}
        .section-heading {{
            font-size: 11px;
            font-weight: 700;
            margin-bottom: 6px;
            color: #003366;
        }}
        .courses-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            margin-bottom: 14px;
        }}
        .courses-table th {{
            background: #003366;
            color: #ffffff;
            padding: 6px 8px;
            font-weight: 700;
            text-align: left;
        }}
        .footer-block {{
            margin-top: 16px;
            border-top: 1px solid #dee2e6;
            padding-top: 12px;
            font-size: 10.5px;
            color: #555555;
            line-height: 1.5;
        }}
    </style>
</head>
<body>
    <div class="topbar">
        <span class="topbar-brand">UNIVERSIDADE DE SÃO PAULO</span>
        <span>Pró-Reitoria de Pós-Graduação &bull; Sistema Janus</span>
    </div>
    <div class="letter-content">
        <div class="header-block">
            <div class="inst-title">UNIVERSIDADE DE SÃO PAULO</div>
            <div class="loc-sub">Rua da Reitoria, 109 &mdash; Cidade Universitária &mdash; São Paulo, SP 05508-220 &bull; Universidade de São Paulo</div>
            <div class="doc-title">ATESTADO DE MATRÍCULA</div>
        </div>

        <div class="cert-statement">
            Atestamos que o(a) aluno(a) abaixo identificado(a) encontra-se regularmente matriculado(a) na Universidade de São Paulo, conforme dados a seguir:
        </div>

        <table class="info-table">
            <tr><td class="lbl">Nome:</td><td><strong>{name}</strong></td></tr>
            <tr><td class="lbl">Número USP:</td><td><strong>{profile.student_id}</strong></td></tr>
            <tr><td class="lbl">Programa:</td><td>{profile.program}</td></tr>
            <tr><td class="lbl">Unidade:</td><td>{school_str}</td></tr>
            <tr><td class="lbl">Semestre:</td><td>{term_label}</td></tr>
            <tr><td class="lbl">Data de Matrícula:</td><td>{matricula_str}</td></tr>
            <tr><td class="lbl">Situação:</td><td><strong>{profile.academic_standing}</strong></td></tr>
            <tr><td class="lbl">Orientador(a) / Coordenador(a):</td><td>{academic_state.advisor}</td></tr>
        </table>

        <div class="section-heading">Disciplinas Matriculadas &mdash; {term_label}</div>
        <table class="courses-table">
            <thead>
                <tr>
                    <th style="width: 16%;">Código</th>
                    <th>Disciplina</th>
                    <th style="width: 14%; text-align: center;">Créditos</th>
                    <th style="width: 16%; text-align: center;">Situação</th>
                </tr>
            </thead>
            <tbody>
                {courses_table_body}
            </tbody>
        </table>

        <div class="footer-block">
            <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                <div>
                    <div>Emitido em: {emitido_str}</div>
                    <div style="margin-top: 4px;">Autenticação digital: <span style="font-family: monospace; font-weight: bold;">{auth_code}</span></div>
                    <div>Verifique em: <span style="color: #003366;">sistemas.usp.br/ateste</span></div>
                </div>
                <div style="text-align: center;">
                    <div style="border: 1px solid #003366; color: #003366; padding: 6px 12px; font-size: 9px; font-weight: bold; background: #f0f4f8;">
                        [QR Autenticação Digital]
                    </div>
                </div>
            </div>
            <div style="margin-top: 10px; font-size: 9.5px; color: #777777;">
                Este documento é emitido eletronicamente pela Universidade de São Paulo e sua autenticidade pode ser confirmada no endereço acima informado com o código de validação.
            </div>
            <div style="margin-top: 14px; border-top: 1px dashed #dee2e6; padding-top: 8px; text-align: center; font-size: 10.5px; color: #555555;">
                <div>________________________________</div>
                <div>Assinatura Eletrônica — Pró-Reitoria de Pós-Graduação</div>
                <div>Universidade de São Paulo</div>
            </div>
        </div>
    </div>
</body>
</html>
"""
    elif inst.id == "universiti_malaya":
        # Universiti Malaya — MAYA Academic Portal Verification Letter
        school_str = (
            profile.college_or_school
            or (inst.schools[0] if inst.schools else "")
            or "Faculty of Computer Science and Information Technology"
        )
        issued_date_str = _format_date_intl(print_date, "universiti_malaya")

        course_rows = []
        for c in academic_state.courses:
            course_rows.append(
                f"""<tr>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6; font-family: monospace; font-weight: 600;">{c.code}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6;">{c.title}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6; text-align: center;">{c.credits}</td>
                </tr>"""
            )
        courses_table_body = "\n".join(course_rows)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Letter of Student Verification - {name}</title>
    <style>
        body {{
            font-family: Arial, Helvetica, sans-serif;
            color: #212529;
            margin: 0;
            padding: 24px;
            background: #ffffff;
            font-size: 12px;
        }}
        .topbar {{
            background: #880000;
            color: #ffffff;
            padding: 8px 18px;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .topbar-brand {{
            font-weight: 700;
            letter-spacing: .02em;
        }}
        .letter-content {{
            padding: 16px 20px;
        }}
        .header-block {{
            text-align: center;
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 12px;
            margin-bottom: 14px;
        }}
        .inst-title {{
            font-size: 14px;
            font-weight: 700;
            color: #880000;
            letter-spacing: .02em;
        }}
        .loc-sub {{
            font-size: 11px;
            color: #555555;
            margin-top: 3px;
        }}
        .doc-title {{
            font-size: 12px;
            font-weight: 700;
            margin-top: 8px;
            color: #212529;
        }}
        .cert-statement {{
            font-size: 11.5px;
            margin-bottom: 10px;
            color: #333333;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11.5px;
            margin-bottom: 14px;
        }}
        .info-table td {{
            padding: 3px 0;
        }}
        .info-table td.lbl {{
            width: 220px;
            color: #555555;
        }}
        .courses-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            margin-bottom: 14px;
        }}
        .courses-table th {{
            background: #880000;
            color: #ffffff;
            padding: 6px 8px;
            font-weight: 700;
            text-align: left;
        }}
        .footer-block {{
            margin-top: 16px;
            border-top: 1px solid #dee2e6;
            padding-top: 12px;
            font-size: 11px;
            color: #555555;
        }}
    </style>
</head>
<body>
    <div class="topbar">
        <span class="topbar-brand">UNIVERSITI MALAYA &mdash; MAYA Academic Portal</span>
        <span>Pejabat Pendaftar / Registrar's Office</span>
    </div>
    <div class="letter-content">
        <div class="header-block">
            <div class="inst-title">UNIVERSITI MALAYA</div>
            <div class="loc-sub">50603 Kuala Lumpur, Malaysia &bull; www.um.edu.my &bull; Universiti Malaya</div>
            <div class="doc-title">SURAT PENGESAHAN PELAJAR / LETTER OF STUDENT VERIFICATION</div>
        </div>

        <div class="cert-statement">
            This is to certify that / Ini untuk mengesahkan bahawa the student named below is currently enrolled at Universiti Malaya:
        </div>

        <table class="info-table">
            <tr><td class="lbl">Nama / Name:</td><td><strong>{name}</strong></td></tr>
            <tr><td class="lbl">No. Matrik / Matric No.:</td><td><strong>{profile.student_id}</strong></td></tr>
            <tr><td class="lbl">Program / Programme:</td><td>{profile.program}</td></tr>
            <tr><td class="lbl">Fakulti / Faculty:</td><td>{school_str}</td></tr>
            <tr><td class="lbl">Semester / Session:</td><td>{term_label}</td></tr>
            <tr><td class="lbl">Status Pelajar / Student Status:</td><td>{profile.academic_standing} / Active</td></tr>
            <tr><td class="lbl">CGPA:</td><td>{academic_state.cumulative_gpa:.2f}</td></tr>
            <tr><td class="lbl">Jam Kredit / Credit Hours Enrolled:</td><td>{academic_state.total_credits}</td></tr>
        </table>

        <table class="courses-table">
            <thead>
                <tr>
                    <th style="width: 22%;">Kod Kursus / Course Code</th>
                    <th>Nama Kursus / Course Name</th>
                    <th style="width: 20%; text-align: center;">Jam Kredit / Credit Hours</th>
                </tr>
            </thead>
            <tbody>
                {courses_table_body}
            </tbody>
        </table>

        <div class="footer-block">
            <div>Tarikh Dikeluarkan / Date Issued: {issued_date_str}</div>
            <div style="margin-top: 14px;">____________________________________</div>
            <div style="font-weight: 700;">Pendaftar / Registrar</div>
            <div>Universiti Malaya</div>
            <div style="margin-top: 6px; font-size: 10px; color: #777777;">
                Pengesahan Elektronik / Electronic Verification: maya.um.edu.my/verify &bull; Ref: UM/MAYA/{profile.document_seal_hash[:8].upper()}
            </div>
        </div>
    </div>
</body>
</html>
"""
    elif inst.id == "makerere":
        # Makerere University — ACMIS Letter of Enrollment
        school_str = (
            profile.college_or_school
            or (inst.schools[0] if inst.schools else "")
            or "College of Computing and Information Sciences (CoCIS)"
        )
        diff_years = max(
            1, min(4, (print_date.year - profile.enrollment_date.year) + 1)
        )
        issued_date_str = _format_date_intl(print_date, "makerere")

        # Extract or format academic year: e.g. "2025/2026"
        year_match = re.search(r"(\d{4})[/-](\d{4})", term_label)
        if year_match:
            acad_year = f"{year_match.group(1)}/{year_match.group(2)}"
        else:
            acad_year = (
                f"{print_date.year - 1}/{print_date.year}"
                if print_date.month < 8
                else f"{print_date.year}/{print_date.year + 1}"
            )
        semester_str = "Semester II" if "Semester II" in term_label else "Semester I"

        course_rows = []
        for c in academic_state.courses:
            course_rows.append(
                f"""<tr>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6; font-weight: 600;">{c.code}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6;">{c.title}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6; text-align: center;">{c.credits}</td>
                </tr>"""
            )
        courses_table_body = "\n".join(course_rows)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Letter of Enrollment - {name}</title>
    <style>
        body {{
            font-family: Arial, Helvetica, sans-serif;
            color: #212529;
            margin: 0;
            padding: 24px;
            background: #ffffff;
            font-size: 12px;
        }}
        .topbar {{
            background: #003087;
            color: #ffffff;
            padding: 8px 18px;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .topbar-brand {{
            font-weight: 700;
            letter-spacing: .02em;
        }}
        .letter-content {{
            padding: 16px 20px;
        }}
        .header-block {{
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 12px;
            margin-bottom: 12px;
        }}
        .inst-title {{
            font-size: 14px;
            font-weight: 700;
            color: #003087;
            letter-spacing: .02em;
        }}
        .loc-sub {{
            font-size: 11px;
            color: #555555;
            margin-top: 2px;
        }}
        .date-line {{
            text-align: right;
            font-size: 11.5px;
            margin-bottom: 10px;
            color: #333333;
        }}
        .doc-title {{
            font-size: 12.5px;
            font-weight: 700;
            margin-bottom: 10px;
            text-decoration: underline;
            color: #003087;
        }}
        .cert-statement {{
            font-size: 11.5px;
            margin-bottom: 10px;
            line-height: 1.5;
            color: #333333;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11.5px;
            margin-bottom: 14px;
        }}
        .info-table td {{
            padding: 3px 0;
        }}
        .info-table td.lbl {{
            width: 200px;
            color: #555555;
        }}
        .courses-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            margin-bottom: 12px;
        }}
        .courses-table th {{
            background: #003087;
            color: #ffffff;
            padding: 6px 8px;
            font-weight: 700;
            text-align: left;
        }}
        .footer-block {{
            margin-top: 14px;
            border-top: 1px solid #dee2e6;
            padding-top: 12px;
            font-size: 11px;
            color: #555555;
            line-height: 1.5;
        }}
    </style>
</head>
<body>
    <div class="topbar">
        <span class="topbar-brand">MAKERERE UNIVERSITY</span>
        <span>Office of the Academic Registrar &bull; ACMIS</span>
    </div>
    <div class="letter-content">
        <div class="header-block">
            <div class="inst-title">MAKERERE UNIVERSITY</div>
            <div class="loc-sub">P.O. Box 7062, Kampala, Uganda &bull; www.mak.ac.ug &bull; Makerere University</div>
            <div class="loc-sub">Tel: +256-414-540628 / 530981</div>
        </div>

        <div class="date-line">{issued_date_str}</div>
        <div class="doc-title">LETTER OF ENROLLMENT &mdash; {term_label}</div>

        <div class="cert-statement">
            This is to certify that the following student is a bonafide registered student of Makerere University for the Academic Year {acad_year}:
        </div>

        <table class="info-table">
            <tr><td class="lbl">Full Name:</td><td><strong>{name}</strong></td></tr>
            <tr><td class="lbl">Student No.:</td><td><strong>{profile.student_id}</strong></td></tr>
            <tr><td class="lbl">Programme:</td><td>{profile.program}</td></tr>
            <tr><td class="lbl">College:</td><td>{school_str}</td></tr>
            <tr><td class="lbl">Year of Study:</td><td>Year {diff_years}</td></tr>
            <tr><td class="lbl">Academic Year:</td><td>{acad_year}</td></tr>
            <tr><td class="lbl">Semester:</td><td>{semester_str}</td></tr>
            <tr><td class="lbl">Academic Term:</td><td>{term_label}</td></tr>
            <tr><td class="lbl">Sponsorship:</td><td>Private (PS)</td></tr>
            <tr><td class="lbl">Registration Status:</td><td>Duly Registered</td></tr>
        </table>

        <table class="courses-table">
            <thead>
                <tr>
                    <th style="width: 22%;">Course Code</th>
                    <th>Course Title</th>
                    <th style="width: 20%; text-align: center;">Credit Units</th>
                </tr>
            </thead>
            <tbody>
                {courses_table_body}
            </tbody>
        </table>

        <div style="font-size: 10.5px; color: #666666; margin-bottom: 8px;">
            This letter has been issued for the purpose of student verification only and shall not be used for any other purpose.
        </div>

        <div class="footer-block">
            <div style="margin-top: 10px;">____________________________________</div>
            <div style="font-weight: 700; margin-top: 2px;">Prof. Buyinza Mukadasi</div>
            <div>Academic Registrar</div>
            <div>Makerere University</div>
            <div style="margin-top: 4px; color: #777777;">Date: {issued_date_str}</div>
            <div style="margin-top: 4px; font-size: 10px; color: #888888;">
                [Official Stamp &bull; ACMIS Verified: MAK/{print_date.year}/{profile.document_seal_hash[:8].upper()}]
            </div>
        </div>
    </div>
</body>
</html>
"""
    elif inst.id == "unilag":
        # University of Lagos — UNILAG Student Portal Letter of Enrollment
        school_str = (
            profile.college_or_school
            or (inst.schools[0] if inst.schools else "")
            or "Faculty of Science"
        )
        diff_years = max(
            1, min(4, (print_date.year - profile.enrollment_date.year) + 1)
        )
        level_str = f"{diff_years}00 Level"
        issued_date_str = _format_date_intl(print_date, "unilag")

        year_match = re.search(r"(\d{4})[/-](\d{4})", term_label)
        if year_match:
            acad_session = f"{year_match.group(1)}/{year_match.group(2)}"
        else:
            acad_session = (
                f"{print_date.year - 1}/{print_date.year}"
                if print_date.month < 8
                else f"{print_date.year}/{print_date.year + 1}"
            )
        semester_str = "Second Semester" if "Second" in term_label else "First Semester"

        dept_str = (
            profile.program.replace("Bachelor of Science (B.Sc.)", "")
            .replace("B.Sc.", "")
            .replace("B.A.", "")
            .replace("Bachelor of", "")
            .strip()
            or "Computer Science"
        )

        course_rows = []
        for c in academic_state.courses:
            course_rows.append(
                f"""<tr>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6; font-weight: 600;">{c.code}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6;">{c.title}</td>
                    <td style="padding: 5px 8px; border-bottom: 1px solid #dee2e6; text-align: center;">{c.credits}</td>
                </tr>"""
            )
        courses_table_body = "\n".join(course_rows)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Letter of Student Enrollment - {name}</title>
    <style>
        body {{
            font-family: Arial, Helvetica, sans-serif;
            color: #212529;
            margin: 0;
            padding: 24px;
            background: #ffffff;
            font-size: 12px;
        }}
        .topbar {{
            background: #800020;
            color: #ffffff;
            padding: 8px 18px;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .topbar-brand {{
            font-weight: 700;
            letter-spacing: .02em;
        }}
        .letter-content {{
            padding: 16px 20px;
        }}
        .header-block {{
            border-bottom: 2px solid #800020;
            padding-bottom: 12px;
            margin-bottom: 12px;
        }}
        .inst-title {{
            font-size: 15px;
            font-weight: 800;
            color: #800020;
            letter-spacing: .03em;
        }}
        .tagline {{
            font-size: 11px;
            color: #555555;
            font-style: italic;
            margin-top: 2px;
        }}
        .loc-sub {{
            font-size: 11px;
            color: #555555;
            margin-top: 2px;
        }}
        .date-line {{
            text-align: right;
            font-size: 11.5px;
            margin-bottom: 10px;
            color: #333333;
        }}
        .doc-title {{
            font-size: 12.5px;
            font-weight: 700;
            margin-bottom: 10px;
            text-decoration: underline;
            color: #800020;
            letter-spacing: .02em;
        }}
        .cert-statement {{
            font-size: 11.5px;
            margin-bottom: 10px;
            line-height: 1.5;
            color: #333333;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11.5px;
            margin-bottom: 14px;
        }}
        .info-table td {{
            padding: 3px 0;
        }}
        .info-table td.lbl {{
            width: 200px;
            color: #555555;
        }}
        .courses-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            margin-bottom: 12px;
        }}
        .courses-table th {{
            background: #800020;
            color: #ffffff;
            padding: 6px 8px;
            font-weight: 700;
            text-align: left;
        }}
        .footer-block {{
            margin-top: 14px;
            border-top: 1px solid #dee2e6;
            padding-top: 12px;
            font-size: 11px;
            color: #555555;
            line-height: 1.5;
        }}
    </style>
</head>
<body>
    <div class="topbar">
        <span class="topbar-brand">UNIVERSITY OF LAGOS</span>
        <span>Office of the Registrar &bull; Student Portal</span>
    </div>
    <div class="letter-content">
        <div class="header-block">
            <div class="inst-title">UNIVERSITY OF LAGOS</div>
            <div class="tagline">&ldquo;University of First Choice and the Nation's Pride&rdquo;</div>
            <div class="loc-sub">Akoka, Yaba, Lagos State, Nigeria &bull; unilag.edu.ng &bull; University of Lagos</div>
        </div>

        <div class="date-line">{issued_date_str}</div>
        <div class="doc-title">LETTER OF STUDENT ENROLLMENT</div>

        <div class="cert-statement">
            This is to certify that the following student is duly enrolled in the University of Lagos for the {term_label}:
        </div>

        <table class="info-table">
            <tr><td class="lbl">Full Name:</td><td><strong>{name}</strong></td></tr>
            <tr><td class="lbl">Matriculation Number:</td><td><strong>{profile.student_id}</strong></td></tr>
            <tr><td class="lbl">Programme:</td><td>{profile.program}</td></tr>
            <tr><td class="lbl">Faculty:</td><td>{school_str}</td></tr>
            <tr><td class="lbl">Department:</td><td>{dept_str}</td></tr>
            <tr><td class="lbl">Level:</td><td>{level_str}</td></tr>
            <tr><td class="lbl">Academic Session:</td><td>{acad_session}</td></tr>
            <tr><td class="lbl">Semester:</td><td>{semester_str}</td></tr>
            <tr><td class="lbl">Mode of Study:</td><td>Full Time</td></tr>
            <tr><td class="lbl">Enrollment Status:</td><td>{profile.academic_standing}</td></tr>
        </table>

        <table class="courses-table">
            <thead>
                <tr>
                    <th style="width: 22%;">Course Code</th>
                    <th>Course Title</th>
                    <th style="width: 20%; text-align: center;">Units</th>
                </tr>
            </thead>
            <tbody>
                {courses_table_body}
            </tbody>
        </table>

        <div style="font-size: 10.5px; color: #666666; margin-bottom: 8px;">
            This letter is issued for the purpose of student verification and proof of enrollment. The University of Lagos shall not be held responsible for any misuse of this document.
        </div>

        <div class="footer-block">
            <div style="margin-top: 10px;">____________________________________</div>
            <div style="font-weight: 700; margin-top: 2px;">Mrs. Olakunle E. Makinde, MNIM, fisn</div>
            <div>Acting Registrar and Secretary to Council</div>
            <div>University of Lagos</div>
            <div style="margin-top: 4px; font-size: 10px; color: #888888;">
                Official Stamp: [UNILAG Crest &amp; Registry Verification Stamp &bull; Ref: UNILAG/REG/{print_date.year}/{profile.document_seal_hash[:8].upper()}]
            </div>
        </div>
    </div>
</body>
</html>
"""
    else:
        # Generic registrar letter
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Enrollment Certification - {name}</title>
    <style>
        body {{
            font-family: Helvetica, Arial, sans-serif;
            color: #212529;
            margin: 0;
            padding: 24px;
            background: #ffffff;
            font-size: 12.5px;
        }}
        .header-block {{
            text-align: center;
            border-bottom: 2px solid {inst.brand_color};
            padding-bottom: 12px;
            margin-bottom: 16px;
        }}
        .inst-title {{
            font-size: 16px;
            font-weight: 700;
            color: {inst.brand_color};
        }}
        .office-sub {{
            font-size: 11.5px;
            color: #555555;
            margin-top: 2px;
        }}
        .doc-title {{
            text-align: center;
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 14px;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11.5px;
            margin-bottom: 16px;
        }}
        .info-table td {{
            padding: 4px 0;
        }}
        .info-table td.lbl {{
            width: 190px;
            color: #555555;
        }}
        .history-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            margin-bottom: 24px;
        }}
        .history-table th, .history-table td {{
            padding: 6px 8px;
            text-align: left;
            border: 1px solid #dee2e6;
        }}
        .history-table th {{
            background: #f5f5f5;
            font-weight: 700;
        }}
        .footer-block {{
            margin-top: 24px;
            border-top: 1px solid #dee2e6;
            padding-top: 14px;
            font-size: 11px;
            color: #555555;
        }}
    </style>
</head>
<body>
    <div class="header-block">
        <div class="inst-title">{profile.institution_name}</div>
        <div class="office-sub">{inst.registrar_title}</div>
        <div class="office-sub">{inst.domain}</div>
    </div>
    <div class="doc-title">OFFICIAL ENROLLMENT CERTIFICATION</div>
    <div style="font-size: 11.5px; margin-bottom: 12px;">
        This document officially certifies that the student named below is currently enrolled in good standing at {profile.institution_name}.
    </div>
    <table class="info-table">
        <tr><td class="lbl">Student Name:</td><td><strong>{name}</strong></td></tr>
        <tr><td class="lbl">Student ID:</td><td><strong>{profile.student_id}</strong></td></tr>
        <tr><td class="lbl">Academic Program:</td><td>{profile.program}</td></tr>
        <tr><td class="lbl">Official Term Window:</td><td>{term_start_str} to {term_end_str}</td></tr>
        <tr><td class="lbl">Enrollment Classification:</td><td>{profile.enrollment_type}</td></tr>
        <tr><td class="lbl">Academic Standing:</td><td>{profile.academic_standing}</td></tr>
    </table>
    <table class="history-table">
        <thead>
            <tr>
                <th>Term</th>
                <th>Dates of Attendance</th>
                <th>Credits</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>{term_label}</td>
                <td>{term_start_str} &ndash; {term_end_str}</td>
                <td>{academic_state.total_credits}</td>
                <td>{profile.enrollment_type}</td>
            </tr>
        </tbody>
    </table>
    <div class="footer-block">
        <div>Electronic Certification Seal: {profile.document_seal_hash} &bull; Generated via {inst.portal_name}</div>
        <div style="margin-top: 16px;">_________________________________________________ &ensp;&ensp;&ensp;&ensp; {print_date_str}</div>
        <div style="font-weight: bold; margin-top: 3px;">{inst.registrar_title} &bull; {inst.domain}</div>
    </div>
</body>
</html>
"""

    fields = {
        "Student Name": name,
        "Student ID": profile.student_id,
        "Institution": profile.institution_name,
        "Portal": profile.institution.portal_name,
        "Program": profile.program,
        "Term": term_label,
        "Term Start Date": term_start_str,
        "Term End Date": term_end_str,
        "Enrollment Type": profile.enrollment_type,
        "Academic Standing": profile.academic_standing,
        "Total Credits": str(academic_state.total_credits),
        "Email": profile.email,
        "Retrieval Date": retrieved_str,
        "Document Print Date": print_date_str,
    }

    doc_title = f"Enrollment Verification - {name}"
    if inst.id == "up_diliman":
        doc_title = f"Registration Form (Form 5) - {name}"
    elif inst.id == "usp":
        doc_title = f"Atestado de Matrícula - {name}"
    elif inst.id == "universiti_malaya":
        doc_title = f"Letter of Student Verification - {name}"
    elif inst.id == "makerere":
        doc_title = f"Letter of Enrollment - {name}"
    elif inst.id == "unilag":
        doc_title = f"Letter of Student Enrollment - {name}"

    return Document(
        kind=kind,
        title=doc_title,
        profile=profile,
        fields=fields,
        html_content=html,
    )


def generate_schedule_document(
    profile: SyntheticProfile, academic_state: AcademicState, temporal: TemporalAnchor
) -> Document:
    # Route registrar letters (e.g. UCLA, UT Austin) to official letter renderer
    if profile.institution.document_archetype == DocumentArchetype.REGISTRAR_LETTER:
        return generate_registrar_letter_document(
            profile, academic_state, temporal, kind=DocumentKind.SCHEDULE
        )

    name = f"{profile.first_name} {profile.last_name}"
    retrieved_str = temporal.retrieval_date.strftime("%B %d, %Y")
    term_start = (
        profile.term_start_date or temporal.term_start_date or temporal.retrieval_date
    )
    term_end = (
        profile.term_end_date or temporal.term_end_date or temporal.expiration_date
    )
    term_start_str = term_start.strftime("%m/%d/%Y")
    term_end_str = term_end.strftime("%m/%d/%Y")
    print_date = profile.document_print_date or temporal.retrieval_date
    print_date_str = print_date.strftime("%B %d, %Y")
    term_label = profile.current_term_label or academic_state.term_name
    inst = profile.institution

    if inst.id == "psu":
        brand_color = "var(--psu-blue)"
        topbar_html = f"""
        <div class="topbar" style="background: {brand_color}; color: #ffffff; padding: 10px 18px;">
            <div style="font-weight: bold; font-size: 16px; float: left;">{profile.institution_name} &mdash; LionPATH</div>
            <div style="font-size: 12px; float: right;">Welcome, <strong>{name}</strong> &ensp;|&ensp; {print_date_str}</div>
            <div style="clear: both;"></div>
        </div>
        """
        breadcrumb = "Home &rsaquo; Self Service &rsaquo; Class Schedule"
        title_text = "My Class Schedule"
        infobar_html = f"""
        <div style="background: #f0f3f7; padding: 8px 12px; font-size: 11.5px; margin-bottom: 12px; border-left: 4px solid {brand_color};">
            Viewing: <strong>{term_label}</strong> &ensp;&bull;&ensp;
            Campus: <strong>{profile.campus}</strong> &ensp;&bull;&ensp;
            Units Enrolled: <strong>{academic_state.total_credits:.2f}</strong> &ensp;&bull;&ensp;
            Cumulative GPA: <strong>{profile.gpa_cumulative:.2f}</strong> &ensp;&bull;&ensp;
            Standing: <strong>{profile.academic_standing}</strong>
        </div>
        """
        crn_header = "Class Nbr"
        credits_header = "Units"

    elif inst.id == "nyu":
        brand_color = "var(--nyu-purple, #57068C)"
        netid_str = (
            profile.login_id
            or f"{profile.first_name[0].lower()}{profile.last_name[:6].lower()}"
        )
        topbar_html = f"""
        <div class="topbar" style="background: {brand_color}; color: #ffffff; padding: 10px 18px;">
            <div style="font-weight: bold; font-size: 16px; float: left;">{profile.institution_name} &mdash; Albert Student Center</div>
            <div style="font-size: 12px; float: right;">Welcome, <strong>{name}</strong> &ensp;|&ensp; {print_date_str} &ensp;|&ensp; NetID: {netid_str}</div>
            <div style="clear: both;"></div>
        </div>
        """
        breadcrumb = "My Academics &rsaquo; Student Center &rsaquo; My Class Schedule"
        title_text = f"Class Schedule &mdash; {term_label}"
        school_name = profile.college_or_school or "College of Arts and Science"
        infobar_html = f"""
        <div style="background: var(--nyu-light-purple, #f8f5fc); padding: 8px 12px; font-size: 11.5px; margin-bottom: 12px; border: 1px solid #e8d5f5;">
            N-Number: <strong>{profile.student_id}</strong> &ensp;&bull;&ensp;
            Career: <strong>{profile.academic_level.value.title()}</strong> &ensp;&bull;&ensp;
            School: <strong>{school_name}</strong> &ensp;&bull;&ensp;
            Total Points: <strong>{academic_state.total_credits}</strong>
        </div>
        """
        crn_header = inst.crn_label
        credits_header = "Points"

    elif inst.id == "umich":
        brand_color = "var(--umich-blue, #00274C)"
        uniq_str = (
            profile.login_id
            or f"{profile.first_name[0].lower()}{profile.last_name[:6].lower()}"
        )
        topbar_html = f"""
        <div class="topbar" style="background: {brand_color}; color: #ffffff; padding: 10px 18px; border-bottom: 3px solid var(--umich-maize, #FFCB05);">
            <div style="font-weight: bold; font-size: 16px; float: left;">{profile.institution_name} &mdash; Wolverine Access</div>
            <div style="font-size: 12px; float: right;">Welcome, <strong>{name}</strong> &ensp;|&ensp; {print_date_str} &ensp;|&ensp; uniqname: {uniq_str}</div>
            <div style="clear: both;"></div>
        </div>
        """
        breadcrumb = "Student Business &rsaquo; My Class Schedule"
        title_text = f"My Class Schedule &mdash; {term_label}"
        school_name = (
            profile.college_or_school
            or "College of Literature, Science, and the Arts (LSA)"
        )
        infobar_html = f"""
        <div style="background: #fff8d6; padding: 8px 12px; font-size: 11.5px; margin-bottom: 12px; border: 1px solid #FFCB05;">
            UMID: <strong>{profile.student_id}</strong> &ensp;&bull;&ensp;
            Program: <strong>{school_name}, {profile.program}</strong> &ensp;&bull;&ensp;
            Credit Hours Enrolled: <strong>{academic_state.total_credits}</strong>
        </div>
        """
        crn_header = "Section"
        credits_header = "Credit Hours"

    else:
        brand_color = inst.brand_color
        topbar_html = f"""
        <div class="topbar" style="background: {brand_color}; color: #ffffff; padding: 10px 18px;">
            <div style="font-weight: bold; font-size: 16px; float: left;">{profile.institution_name} &mdash; {inst.portal_name}</div>
            <div style="font-size: 12px; float: right;">Welcome, <strong>{name}</strong> &ensp;|&ensp; {print_date_str}</div>
            <div style="clear: both;"></div>
        </div>
        """
        breadcrumb = "Home &rsaquo; Student Center &rsaquo; Class Schedule"
        title_text = f"Class Schedule &mdash; {term_label}"
        infobar_html = f"""
        <div style="background: var(--bg-light); padding: 8px 12px; font-size: 11.5px; margin-bottom: 12px; border-left: 4px solid {brand_color};">
            Student ID: <strong>{profile.student_id}</strong> &ensp;&bull;&ensp;
            Term: <strong>{term_label}</strong> &ensp;&bull;&ensp;
            Enrolled Credits: <strong>{academic_state.total_credits}</strong> &ensp;&bull;&ensp;
            Standing: <strong>{profile.academic_standing}</strong>
        </div>
        """
        crn_header = inst.crn_label
        credits_header = "Credits"

    rows_html = ""
    for c in academic_state.courses:
        rows_html += f"""
        <tr>
            <td><strong>{c.code}</strong></td>
            <td>{c.title}</td>
            <td>{c.crn}</td>
            <td>{c.credits}</td>
            <td>{c.meeting_pattern}</td>
            <td>{c.location}</td>
            <td>{c.instructor}</td>
            <td><span style="color: var(--badge-enrolled); font-weight: bold;">Enrolled</span></td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Class Schedule - {name}</title>
    <style>
        body {{
            font-family: Helvetica, Arial, sans-serif;
            color: var(--text-primary);
            margin: 0;
            padding: 0;
            background: #ffffff;
        }}
        .breadcrumb {{
            font-size: 11px;
            color: var(--text-muted);
            padding: 8px 24px;
            background: #f8f9fa;
            border-bottom: 1px solid var(--border-subtle);
        }}
        .main-container {{
            padding: 16px 24px 24px 24px;
        }}
        .schedule-title {{
            color: {brand_color};
            margin-top: 0;
            margin-bottom: 10px;
            font-size: 18px;
            border-bottom: 2px solid {brand_color};
            padding-bottom: 6px;
        }}
        .student-box {{
            border: 1px solid var(--border-subtle);
            background: var(--bg-light);
            padding: 12px 14px;
            margin-bottom: 16px;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .info-table td {{
            padding: 4px 6px;
            font-size: 12px;
        }}
        .info-table td.label {{
            font-weight: bold;
            color: var(--text-muted);
            width: 18%;
        }}
        .schedule-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .schedule-table th, .schedule-table td {{
            border: 1px solid var(--border-subtle);
            padding: 7px 9px;
            text-align: left;
            font-size: 11.5px;
        }}
        .schedule-table th {{
            background-color: {brand_color};
            color: #ffffff;
            font-weight: bold;
        }}
        .schedule-table tr:nth-child(even) {{
            background-color: var(--bg-light);
        }}
        .summary-bar {{
            margin-top: 14px;
            font-size: 12px;
            padding: 8px 12px;
            background: var(--bg-light);
            border: 1px solid var(--border-subtle);
        }}
        .footer {{
            margin-top: 24px;
            font-size: 10.5px;
            color: var(--text-muted);
            border-top: 1px solid var(--border-subtle);
            padding-top: 10px;
            line-height: 1.5;
        }}
    </style>
</head>
<body>
    {topbar_html}
    <div class="breadcrumb">{breadcrumb}</div>
    <div class="main-container">
        <h2 class="schedule-title">{title_text}</h2>
        {infobar_html}

        <div class="student-box">
            <table class="info-table">
                <tr>
                    <td class="label">Student Name:</td>
                    <td><strong>{name}</strong></td>
                    <td class="label">Student ID:</td>
                    <td><strong>{profile.student_id}</strong></td>
                </tr>
                <tr>
                    <td class="label">Academic Program:</td>
                    <td>{profile.program} ({profile.academic_level.value.title()})</td>
                    <td class="label">Current Status:</td>
                    <td><strong>{profile.academic_standing}</strong></td>
                </tr>
                <tr>
                    <td class="label">Institution:</td>
                    <td>{profile.institution_name}</td>
                    <td class="label">Official Term:</td>
                    <td>{term_label} ({term_start_str} &ndash; {term_end_str})</td>
                </tr>
                <tr>
                    <td class="label">Institutional Email:</td>
                    <td>{profile.email}</td>
                    <td class="label">Academic Advisor:</td>
                    <td>{profile.advisor_name or academic_state.advisor}</td>
                </tr>
            </table>
        </div>

        <table class="schedule-table">
            <thead>
                <tr>
                    <th>Course</th>
                    <th>Title</th>
                    <th>{crn_header}</th>
                    <th>{credits_header}</th>
                    <th>Days &amp; Times</th>
                    <th>Location</th>
                    <th>Instructor</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <div class="summary-bar">
            <strong>Total Enrolled {credits_header}:</strong> {academic_state.total_credits} &nbsp;|&nbsp;
            <strong>Enrollment Classification:</strong> {profile.enrollment_type} &nbsp;|&nbsp;
            <strong>Official Term Window:</strong> {term_start_str} to {term_end_str}
        </div>

        <div class="footer">
            <div style="float: left;">
                Document Generated: {print_date_str} &bull; Portal: {inst.portal_name}<br>
                {inst.registrar_title} &bull; Security Seal: {profile.document_seal_hash}
            </div>
            <div style="float: right; text-align: right;">
                Page 1 of 1 &bull; Certified Student Record &bull; {inst.domain}
            </div>
            <div style="clear: both;"></div>
        </div>
    </div>
</body>
</html>
"""

    fields = {
        "Student Name": name,
        "Student ID": profile.student_id,
        "Institution": profile.institution_name,
        "Portal": profile.institution.portal_name,
        "Program": profile.program,
        "Term": term_label,
        "Term Start Date": term_start_str,
        "Term End Date": term_end_str,
        "Enrollment Type": profile.enrollment_type,
        "Academic Standing": profile.academic_standing,
        "Total Credits": str(academic_state.total_credits),
        "Email": profile.email,
        "Retrieval Date": retrieved_str,
        "Document Print Date": print_date_str,
    }

    return Document(
        kind=DocumentKind.SCHEDULE,
        title=f"Class Schedule - {name}",
        profile=profile,
        fields=fields,
        html_content=html,
    )


def generate_tuition_receipt_document(
    profile: SyntheticProfile, academic_state: AcademicState, temporal: TemporalAnchor
) -> Document:
    name = f"{profile.first_name} {profile.last_name}"
    pay_date_str = temporal.payment_date.strftime("%B %d, %Y")
    retrieved_str = temporal.retrieval_date.strftime("%B %d, %Y")
    term_start = (
        profile.term_start_date or temporal.term_start_date or temporal.retrieval_date
    )
    term_start_str = term_start.strftime("%m/%d/%Y")
    term_label = profile.current_term_label or academic_state.term_name
    print_date = profile.document_print_date or temporal.retrieval_date
    print_date_str = print_date.strftime("%B %d, %Y")
    inst = profile.institution
    brand_color = inst.primary_color or "#1E407C"
    id_label = inst.student_id_label or "Student ID"
    credit_label = inst.credit_label or "Credits"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Tuition Receipt - {name}</title>
    <style>
        body {{
            font-family: Helvetica, Arial, sans-serif;
            color: var(--text-primary);
            margin: 0;
            padding: 24px;
            background: #fff;
        }}
        .header {{
            border-bottom: 3px solid {brand_color};
            padding-bottom: 12px;
            margin-bottom: 20px;
        }}
        .brand {{
            font-size: 24px;
            font-weight: bold;
            color: {brand_color};
        }}
        .sub-brand {{
            font-size: 14px;
            color: var(--text-muted);
            margin-top: 4px;
        }}
        h2 {{
            color: {brand_color};
            margin-bottom: 15px;
            font-size: 18px;
        }}
        .receipt-box {{
            border: 2px solid {brand_color};
            padding: 20px;
            background: var(--bg-light);
        }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .table th, .table td {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-subtle);
            font-size: 13px;
            text-align: left;
        }}
        .table th {{
            background: {brand_color};
            color: #fff;
        }}
        .status-badge {{
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            padding: 12px;
            text-align: center;
            font-weight: bold;
            font-size: 15px;
            margin-top: 20px;
        }}
        .footer {{
            margin-top: 30px;
            font-size: 11px;
            color: var(--text-muted);
            border-top: 1px solid var(--border-subtle);
            padding-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">{profile.institution_name}</div>
        <div class="sub-brand">{profile.institution.portal_name} &mdash; Official Bursar Account Statement & Payment Receipt</div>
    </div>

    <h2>Bursar Statement & Payment Confirmation</h2>

    <div class="receipt-box">
        <table style="width: 100%; margin-bottom: 15px; font-size: 13px;">
            <tr>
                <td><strong>Student Name:</strong> {name}</td>
                <td><strong>{id_label}:</strong> {profile.student_id}</td>
            </tr>
            <tr>
                <td><strong>Term / Session:</strong> {term_label} (Starts: {term_start_str})</td>
                <td><strong>Enrollment Status:</strong> {profile.enrollment_type}</td>
            </tr>
            <tr>
                <td><strong>Transaction ID:</strong> {academic_state.transaction_id}</td>
                <td><strong>Payment Date:</strong> {pay_date_str}</td>
            </tr>
            <tr>
                <td><strong>Campus / College:</strong> {profile.campus}</td>
                <td><strong>Payment Method:</strong> Electronic ACH / Campus Portal</td>
            </tr>
        </table>

        <table class="table">
            <thead>
                <tr>
                    <th>Item Description</th>
                    <th>Category</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Undergraduate Instructional Tuition ({academic_state.total_credits} {credit_label.lower()})</td>
                    <td>Instructional Tuition</td>
                    <td>$7,450.00</td>
                </tr>
                <tr>
                    <td>University Technology Fee</td>
                    <td>Mandatory Fee</td>
                    <td>$250.00</td>
                </tr>
                <tr>
                    <td>Student Activity & Recreation Fee</td>
                    <td>Mandatory Fee</td>
                    <td>$175.00</td>
                </tr>
                <tr>
                    <td>Financial Aid / Scholarship Grant Credit</td>
                    <td>Credit / Grant</td>
                    <td>-$7,875.00</td>
                </tr>
            </tbody>
        </table>

        <div class="status-badge">
            STATUS: PAID IN FULL &mdash; BALANCE DUE: $0.00
        </div>
    </div>

    <div class="footer">
        <div style="float: left;">
            Statement Generated: {print_date_str} &bull; Office of the Bursar, {profile.institution_name}<br>
            Portal: {profile.institution.portal_name} &bull; Security Seal: {profile.document_seal_hash}
        </div>
        <div style="float: right; text-align: right;">
            Record ID: {academic_state.transaction_id} &bull; {profile.institution.domain}
        </div>
        <div style="clear: both;"></div>
    </div>
</body>
</html>
"""

    fields = {
        "Student Name": name,
        "Student ID": profile.student_id,
        "Institution": profile.institution_name,
        "Portal": profile.institution.portal_name,
        "Term": term_label,
        "Term Start Date": term_start_str,
        "Enrollment Type": profile.enrollment_type,
        "Payment Date": pay_date_str,
        "Transaction ID": academic_state.transaction_id,
        "Tuition Balance": "$0.00",
        "Status": "PAID IN FULL",
        "Retrieval Date": retrieved_str,
        "Document Print Date": print_date_str,
    }

    return Document(
        kind=DocumentKind.TUITION_RECEIPT,
        title=f"Tuition Receipt - {name}",
        profile=profile,
        fields=fields,
        html_content=html,
    )


def generate_id_card_document(
    profile: SyntheticProfile, temporal: TemporalAnchor
) -> Document:
    name = f"{profile.first_name} {profile.last_name}"
    issue_str = temporal.issue_date.strftime("%m/%d/%Y")
    exp_str = temporal.expiration_date.strftime("%m/%d/%Y")
    inst = profile.institution
    brand_color = inst.primary_color or "#1E407C"
    id_label = inst.student_id_label or "Student ID"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Student ID Card - {name}</title>
    <style>
        body {{
            font-family: Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 30px;
            background: #eaedf1;
        }}
        .card {{
            width: 480px;
            height: 300px;
            border: 2px solid {brand_color};
            background: #ffffff;
            position: relative;
            box-sizing: border-box;
            padding: 15px;
        }}
        .card-header {{
            background: {brand_color};
            color: #ffffff;
            padding: 10px;
            font-weight: bold;
            font-size: 16px;
            text-align: center;
            letter-spacing: 0.5px;
        }}
        .card-body {{
            margin-top: 15px;
        }}
        .photo-box {{
            width: 100px;
            height: 120px;
            background: #dcdcdc;
            border: 1px solid #999;
            float: left;
            text-align: center;
            line-height: 120px;
            font-size: 12px;
            color: #555;
            font-weight: bold;
        }}
        .info-section {{
            margin-left: 115px;
        }}
        .name {{
            font-size: 18px;
            font-weight: bold;
            color: {brand_color};
            margin-bottom: 5px;
        }}
        .detail {{
            font-size: 13px;
            color: #333;
            margin-bottom: 3px;
        }}
        .barcode-section {{
            margin-top: 20px;
            text-align: center;
            font-family: monospace;
            font-size: 18px;
            letter-spacing: 3px;
            border-top: 1px dashed #ccc;
            padding-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="card-header">
            {profile.institution_name.upper()} &mdash; OFFICIAL IDENTIFICATION
        </div>
        <div class="card-body">
            <div class="photo-box">
                PHOTO
            </div>
            <div class="info-section">
                <div class="name">{name}</div>
                <div class="detail"><strong>{id_label}:</strong> {profile.student_id}</div>
                <div class="detail"><strong>Role:</strong> {profile.role.value.title()}</div>
                <div class="detail"><strong>Program:</strong> {profile.program}</div>
                <div class="detail"><strong>Campus:</strong> {profile.campus}</div>
                <div class="detail"><strong>Issue Date:</strong> {issue_str}</div>
                <div class="detail" style="color: #b30000; font-weight: bold;">Expiration Date: {exp_str}</div>
            </div>
        </div>
        <div class="barcode-section">
            ||||||| | |||| ||||| ||| ||||
            <div style="font-size: 10px; color: #666; letter-spacing: normal; margin-top: 2px;">
                {profile.student_id} &bull; {profile.institution.portal_name} &bull; {profile.document_seal_hash[:8]}
            </div>
        </div>
    </div>
</body>
</html>
"""

    fields = {
        "Student Name": name,
        "Student ID": profile.student_id,
        "Institution": profile.institution_name,
        "Portal": profile.institution.portal_name,
        "Role": profile.role.value,
        "Campus": profile.campus,
        "Issue Date": issue_str,
        "Expiration Date": exp_str,
        "Security Seal": profile.document_seal_hash,
    }

    return Document(
        kind=DocumentKind.ID_CARD,
        title=f"Student ID Card - {name}",
        profile=profile,
        fields=fields,
        html_content=html,
    )


def generate_faculty_summary_document(
    profile: SyntheticProfile, temporal: TemporalAnchor
) -> Document:
    name = f"{profile.first_name} {profile.last_name}"
    issue_str = temporal.issue_date.strftime("%B %d, %Y")
    term_label = profile.current_term_label or temporal.term_name
    inst = profile.institution
    brand_color = inst.primary_color or "#1E407C"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Faculty Summary - {name}</title>
    <style>
        body {{ font-family: Helvetica, Arial, sans-serif; padding: 20px; color: var(--text-primary); }}
        .header {{ border-bottom: 3px solid {brand_color}; padding-bottom: 10px; margin-bottom: 20px; }}
        .brand {{ font-size: 22px; font-weight: bold; color: {brand_color}; }}
        .sub-brand {{ font-size: 14px; color: var(--text-muted); margin-top: 4px; }}
        .box {{ background: var(--bg-light); border: 1px solid var(--border-subtle); padding: 15px; margin-top: 15px; }}
        .footer {{ margin-top: 40px; font-size: 12px; color: var(--text-muted); text-align: right; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">{profile.institution_name}</div>
        <div class="sub-brand">{profile.institution.portal_name} &mdash; Faculty & Academic Staff Record</div>
    </div>
    <h2>Employee Verification Certificate</h2>
    <div class="box">
        <p>This document verifies that <strong>{name}</strong> (Employee ID: <strong>{profile.student_id}</strong>) is actively employed at {profile.institution_name} in good standing.</p>
        <p><strong>Position / Department:</strong> {profile.program}</p>
        <p><strong>Campus / Location:</strong> {profile.campus}</p>
        <p><strong>Institutional Email:</strong> {profile.email}</p>
        <p><strong>Active Term:</strong> {term_label}</p>
        <p><strong>Appointment Academic Year:</strong> {profile.academic_year}</p>
        <p><strong>Employment Status:</strong> {profile.enrollment_type}</p>
    </div>
    <div class="footer">
        Issued on: {issue_str} | Verified via {profile.institution.portal_name} | Seal: {profile.document_seal_hash}
    </div>
</body>
</html>
"""

    fields = {
        "Employee Name": name,
        "Employee ID": profile.student_id,
        "Institution": profile.institution_name,
        "Portal": profile.institution.portal_name,
        "Department": profile.program,
        "Email": profile.email,
        "Issue Date": issue_str,
        "Term": term_label,
        "Enrollment Type": profile.enrollment_type,
    }

    return Document(
        kind=DocumentKind.FACULTY_SUMMARY,
        title=f"Faculty Summary - {name}",
        profile=profile,
        fields=fields,
        html_content=html,
    )


def generate_enrollment_certificate_document(
    profile: SyntheticProfile, temporal: TemporalAnchor
) -> Document:
    name = f"{profile.first_name} {profile.last_name}"
    issue_str = temporal.issue_date.strftime("%B %d, %Y")
    term_start = (
        profile.term_start_date or temporal.term_start_date or temporal.retrieval_date
    )
    term_end = (
        profile.term_end_date or temporal.term_end_date or temporal.expiration_date
    )
    term_start_str = term_start.strftime("%m/%d/%Y")
    term_end_str = term_end.strftime("%m/%d/%Y")
    term_label = profile.current_term_label or temporal.term_name
    print_date = profile.document_print_date or temporal.retrieval_date
    print_date_str = print_date.strftime("%B %d, %Y")
    inst = profile.institution
    brand_color = inst.primary_color or "#1E407C"
    id_label = inst.student_id_label or "Student ID"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Enrollment Certificate - {name}</title>
    <style>
        body {{
            font-family: Helvetica, Arial, sans-serif;
            padding: 30px;
            color: var(--text-primary);
        }}
        .certificate {{
            border: 3px double {brand_color};
            padding: 40px;
            background: white;
        }}
        h1 {{
            text-align: center;
            color: {brand_color};
            margin-bottom: 5px;
            font-size: 26px;
        }}
        h3 {{
            text-align: center;
            color: var(--text-muted);
            font-weight: normal;
            margin-top: 0;
            border-bottom: 1px solid var(--border-subtle);
            padding-bottom: 15px;
            font-size: 15px;
        }}
        .details {{
            margin-top: 25px;
            line-height: 1.8;
            font-size: 15px;
        }}
        .field-table {{
            width: 100%;
            margin-top: 20px;
            border-collapse: collapse;
        }}
        .field-table td {{
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-subtle);
            font-size: 14px;
        }}
        .field-table td.label {{
            font-weight: bold;
            color: {brand_color};
            width: 35%;
        }}
        .seal-box {{
            margin-top: 35px;
            border-top: 1px solid var(--border-subtle);
            padding-top: 15px;
            font-size: 12px;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
<div class="certificate">
    <h1>{profile.institution_name}</h1>
    <h3>{profile.institution.registrar_title} &mdash; Official Enrollment Verification ({profile.institution.portal_name})</h3>

    <div class="details">
        <p>This official document certifies that the student named below is actively registered and enrolled in good academic standing at {profile.institution_name} for the specified academic term.</p>

        <table class="field-table">
            <tr>
                <td class="label">Student Full Name:</td>
                <td><strong>{name}</strong></td>
            </tr>
            <tr>
                <td class="label">{id_label}:</td>
                <td><strong>{profile.student_id}</strong></td>
            </tr>
            <tr>
                <td class="label">Current Academic Term:</td>
                <td><strong>{term_label}</strong> (Term Dates: {term_start_str} &ndash; {term_end_str})</td>
            </tr>
            <tr>
                <td class="label">Enrollment Classification:</td>
                <td><strong>{profile.enrollment_type}</strong></td>
            </tr>
            <tr>
                <td class="label">Academic Standing:</td>
                <td>{profile.academic_standing}</td>
            </tr>
            <tr>
                <td class="label">Campus Location:</td>
                <td>{profile.campus}</td>
            </tr>
            <tr>
                <td class="label">Academic Degree & Major:</td>
                <td>{profile.program}</td>
            </tr>
            <tr>
                <td class="label">Academic Career Level:</td>
                <td>{profile.academic_level.value.title()}</td>
            </tr>
            <tr>
                <td class="label">Anticipated Graduation Date:</td>
                <td>{profile.expected_graduation.strftime("%B %d, %Y")}</td>
            </tr>
            <tr>
                <td class="label">Official Certification Date:</td>
                <td>{issue_str}</td>
            </tr>
        </table>
    </div>

    <div class="seal-box">
        <div style="float: left;">
            Electronic Certification Seal: {profile.document_seal_hash}<br>
            Verified via {profile.institution.portal_name} &bull; Printed: {print_date_str}
        </div>
        <div style="float: right; text-align: right;">
            {profile.institution.registrar_title}<br>
            {profile.institution_name} &bull; {profile.institution.domain}
        </div>
        <div style="clear: both;"></div>
    </div>
</div>
</body>
</html>
"""

    fields = {
        "Student Name": name,
        "Student ID": profile.student_id,
        "Institution": profile.institution_name,
        "Portal": profile.institution.portal_name,
        "Program": profile.program,
        "Academic Level": profile.academic_level.value,
        "Term": term_label,
        "Term Start Date": term_start_str,
        "Term End Date": term_end_str,
        "Enrollment Type": profile.enrollment_type,
        "Academic Standing": profile.academic_standing,
        "Expected Graduation": profile.expected_graduation.strftime("%Y-%m-%d"),
        "Issue Date": issue_str,
        "Document Print Date": print_date_str,
    }

    return Document(
        kind=DocumentKind.ENROLLMENT_CERTIFICATE,
        title=f"Enrollment Certificate - {name}",
        profile=profile,
        fields=fields,
        html_content=html,
    )


def generate_document(
    profile: SyntheticProfile,
    doc_kind: DocumentKind = DocumentKind.SCHEDULE,
    seed: int = 42,
) -> Document:
    rng = random.Random(seed)
    anchor_dt = profile.document_print_date or profile.enrollment_date
    temporal = get_temporal_anchor(rng, anchor_date=anchor_dt)
    academic_state = generate_academic_state(
        rng,
        profile.program,
        temporal,
        institution_id=profile.institution_id,
        profile=profile,
    )

    if doc_kind == DocumentKind.SCHEDULE:
        return generate_schedule_document(profile, academic_state, temporal)
    elif doc_kind == DocumentKind.TUITION_RECEIPT:
        return generate_tuition_receipt_document(profile, academic_state, temporal)
    elif doc_kind == DocumentKind.ID_CARD:
        return generate_id_card_document(profile, temporal)
    elif doc_kind == DocumentKind.FACULTY_SUMMARY:
        return generate_faculty_summary_document(profile, temporal)
    elif doc_kind == DocumentKind.ENROLLMENT_CERTIFICATE:
        return generate_enrollment_certificate_document(profile, temporal)
    else:
        return generate_schedule_document(profile, academic_state, temporal)


# =====================================================================
# CSS VARIABLE RESOLVER & PDF METADATA SPOOFING
# =====================================================================

_CSS_TOKENS: dict[str, str] = {
    "--psu-blue": "#1E407C",
    "--psu-light-blue": "#96BEE6",
    "--psu-gold": "#BF9B2F",
    "--accent-gray": "#6c757d",
    "--bg-light": "#f4f6f9",
    "--border-subtle": "#dee2e6",
    "--text-primary": "#212529",
    "--text-muted": "#6c757d",
    "--badge-enrolled": "#198754",
    "--badge-waitlist": "#dc3545",
    "--nyu-purple": "#57068C",
    "--nyu-light-purple": "#f8f5fc",
    "--umich-blue": "#00274C",
    "--umich-maize": "#FFCB05",
    "--ucla-blue": "#2D68C4",
    "--ucla-gold": "#F2A900",
    "--ut-orange": "#BF5700",
    "--ut-gray": "#333F48",
}


def _resolve_css_vars(html: str, tokens: dict[str, str] | None = None) -> str:
    """Pre-resolve CSS var() calls to concrete values before rendering."""
    tok = {**_CSS_TOKENS, **(tokens or {})}

    def _replacer(m: re.Match[str]) -> str:
        name = m.group(1).strip()
        fallback = (m.group(2) or "").strip().lstrip(",").strip()
        return tok.get(name, fallback or "inherit")

    return re.sub(r"var\(\s*(--[\w-]+)\s*(?:,([^)]*))?\)", _replacer, html)


def _spoof_pdf_metadata(
    pdf_bytes: bytes,
    institution: Institution | None = None,
    profile: SyntheticProfile | None = None,
    term_label: str = "",
) -> bytes:
    """
    Rewrite PDF /Info dictionary to match real institutional producers.

    Real Penn State LionPATH PDFs show:
      /Producer  (Oracle PeopleTools 8.59.15)
      /Creator   (PeopleSoft Enterprise)
      /Author    ()           [blank — system-generated]
      /Subject   (Class Schedule)
      /Keywords  (Student Schedule Penn State)
      /CreationDate (D:20260915143022-05'00')
      /ModDate      (D:20260915143022-05'00')
    """
    if isinstance(institution, SyntheticProfile):
        if profile is None:
            profile = institution
        institution = profile.institution

    inst = institution or (profile.institution if profile else INSTITUTIONS["psu"])
    is_letter = inst.document_archetype == DocumentArchetype.REGISTRAR_LETTER
    if profile:
        season, term_year, term_start, _ = _current_term(
            profile.document_print_date, institution_id=inst.id
        )
        print_date = profile.document_print_date or term_start
        h = abs(hash(profile.first_name)) % 8 + 8  # 8am–4pm
        m = abs(hash(profile.last_name)) % 59
        s = abs(hash(profile.email)) % 59
        fake_dt = datetime.combine(print_date, datetime.min.time()) + timedelta(
            hours=h, minutes=m, seconds=s
        )
        active_term = (
            term_label or profile.current_term_label or f"{season} {term_year}"
        )
        if is_letter:
            subject_str = f"Enrollment Verification - {active_term}"
            keywords_str = f"Enrollment Verification {inst.name}"
            title_str = f"{inst.portal_name} - Enrollment Verification"
        else:
            subject_str = f"Class Schedule - {active_term}"
            keywords_str = f"Student Schedule {inst.name}"
            title_str = f"{inst.portal_name} - Student Schedule"
    else:
        season, term_year, term_start, _ = _current_term(institution_id=inst.id)
        fake_dt = datetime.combine(
            term_start + timedelta(days=15), datetime.min.time()
        ) + timedelta(hours=10, minutes=24, seconds=12)
        active_term = term_label or f"{season} {term_year}"
        if is_letter:
            subject_str = f"Enrollment Verification - {active_term}"
            keywords_str = f"Enrollment Verification {inst.name}"
            title_str = f"{inst.portal_name} - Enrollment Verification"
        else:
            subject_str = f"Class Schedule - {active_term}"
            keywords_str = f"Student Schedule {inst.name}"
            title_str = f"{inst.portal_name} - Student Schedule"

    fake_dt = min(
        fake_dt, datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    )
    pdf_date = fake_dt.strftime("D:%Y%m%d%H%M%S-05'00'")

    try:
        reader = pypdf.PdfReader(BytesIO(pdf_bytes))
        writer = pypdf.PdfWriter()
        writer.append_pages_from_reader(reader)
        writer.add_metadata(
            {
                "/Producer": inst.producer_string,
                "/Creator": inst.pdf_creator,
                "/Author": "",
                "/Subject": subject_str,
                "/Keywords": keywords_str,
                "/CreationDate": pdf_date,
                "/ModDate": pdf_date,
                "/Title": title_str,
            }
        )
        out = BytesIO()
        writer.write(out)
        return out.getvalue()
    except (PyPdfError, ValueError, KeyError, OSError, TypeError) as exc:
        logger.debug("Failed to spoof PDF metadata with pypdf: %s", exc)

    # Fallback: byte-level substitution
    result = pdf_bytes
    producer_str = inst.pdf_producer or "Oracle PeopleTools 8.59"
    for old, new_s in [
        (b"WeasyPrint", producer_str[:10].encode()),
        (b"xhtml2pdf", producer_str[:9].encode()),
        (b"ReportLab", producer_str[:9].encode()),
    ]:
        if old in result:
            result = result.replace(old, new_s.ljust(len(old)))
    return result


# =====================================================================
# RENDERING ENGINE (HTML, PDF, PNG, JPEG)
# =====================================================================


def render_pdf(
    html_content: str,
    institution: Institution | None = None,
    profile: SyntheticProfile | None = None,
    term_label: str = "",
) -> bytes:
    """Render HTML string to PDF bytes with institutional metadata spoofing."""
    if isinstance(institution, SyntheticProfile):
        if profile is None:
            profile = institution
        institution = profile.institution

    html = _resolve_css_vars(html_content)
    pdf_bytes: bytes | None = None

    try:
        from xhtml2pdf import pisa

        output = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=output, encoding="utf-8")
        if not pisa_status.err:
            pdf_bytes = output.getvalue()
    except (ImportError, RuntimeError, ValueError, TypeError, OSError) as exc:
        logger.debug("xhtml2pdf rendering failed: %s", exc)

    if pdf_bytes is None:
        try:
            import weasyprint  # type: ignore

            pdf_bytes = weasyprint.HTML(string=html).write_pdf()
        except (ImportError, RuntimeError, ValueError, TypeError, OSError) as exc:
            logger.debug("weasyprint rendering failed: %s", exc)

    if pdf_bytes is None:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            output = BytesIO()
            c = canvas.Canvas(output, pagesize=letter)
            c.drawString(100, 750, "Document Summary")
            clean_text = re.sub(r"<[^>]+>", "\n", html)
            lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
            y = 720
            for line in lines[:35]:
                c.drawString(50, y, line[:90])
                y -= 18
            c.save()
            pdf_bytes = output.getvalue()
        except (ImportError, RuntimeError, ValueError, TypeError, OSError) as exc:
            raise RuntimeError(f"Failed to render PDF: {exc}") from exc

    inst = institution or (profile.institution if profile else None)
    return _spoof_pdf_metadata(pdf_bytes, inst, profile, term_label)


_html_to_pdf = render_pdf


def render_png(
    html_content: str,
    width: int = 1280,
    height: int = 900,
    require_high_fidelity: bool = True,
) -> bytes:
    """Render HTML string to PNG bytes using Playwright retina capture with high-fidelity guard."""
    html = _resolve_css_vars(html_content)
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=2.0,
            )
            page = ctx.new_page()
            page.set_content(html, wait_until="load")
            page.wait_for_timeout(300)
            png_bytes = page.screenshot(full_page=True, type="png")
            browser.close()
            return png_bytes
    except Exception as exc:
        if require_high_fidelity:
            raise RuntimeError(
                f"High-fidelity PNG rendering failed: {exc}. "
                "PIL fallback is forensically detectable as a synthetic image."
            ) from exc

    # Fallback via PIL when require_high_fidelity is explicitly disabled
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (width, height), color=(245, 247, 250))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, width, 60], fill=(30, 64, 124))
        draw.text((20, 20), "SYNTHETIC DOCUMENT PREVIEW", fill=(255, 255, 255))

        clean_text = re.sub(r"<[^>]+>", "\n", html)
        lines = [line.strip() for line in clean_text.splitlines() if line.strip()]

        y = 80
        for line in lines[:30]:
            draw.text((30, y), line[:110], fill=(30, 30, 30))
            y += 22

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    except (ImportError, OSError, ValueError, TypeError) as exc:
        raise RuntimeError(f"Failed to render PNG image: {exc}") from exc


def render_jpeg(html_content: str, width: int = 1280, height: int = 900) -> bytes:
    """Render HTML string to JPEG bytes."""
    html = _resolve_css_vars(html_content)
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=2.0,
            )
            page = ctx.new_page()
            page.set_content(html, wait_until="load")
            page.wait_for_timeout(300)
            jpg_bytes = page.screenshot(full_page=True, type="jpeg", quality=92)
            browser.close()
            return jpg_bytes
    except (ImportError, RuntimeError, OSError) as exc:
        logger.debug("Playwright JPEG rendering failed, using PIL fallback: %s", exc)

    # Fallback via PIL from PNG
    png_b = render_png(html, width, height, require_high_fidelity=False)
    try:
        from PIL import Image

        img = Image.open(BytesIO(png_b))
        buf = BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except (ImportError, OSError, ValueError) as exc:
        raise RuntimeError(f"Failed to render JPEG image: {exc}") from exc


# =====================================================================
# VALIDATION LAYER & READ-BACK INSPECTION
# =====================================================================


def validate_profile(profile: SyntheticProfile) -> ValidationResult:
    errors: list[ValidationError] = []
    warnings: list[str] = []

    if not profile.first_name or not profile.last_name:
        errors.append(
            ValidationError("INVALID_NAME", "name", "Profile name is missing or empty")
        )

    if not profile.student_id:
        errors.append(
            ValidationError("INVALID_ID", "student_id", "Student ID is missing")
        )

    if profile.enrollment_date <= profile.date_of_birth:
        errors.append(
            ValidationError(
                "INVALID_DATES",
                "enrollment_date",
                "Enrollment date precedes date of birth",
            )
        )

    if profile.expected_graduation <= profile.enrollment_date:
        errors.append(
            ValidationError(
                "INVALID_DATES", "expected_graduation", "Graduation precedes enrollment"
            )
        )

    if "@" not in profile.email or not profile.email.endswith(profile.domain):
        errors.append(
            ValidationError(
                "INVALID_EMAIL",
                "email",
                f"Email does not match domain '{profile.domain}'",
            )
        )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_document(
    doc: Document, profile: SyntheticProfile | None = None
) -> ValidationResult:
    errors: list[ValidationError] = []
    warnings: list[str] = []
    target_profile = profile if profile is not None else doc.profile

    if not doc.fields:
        errors.append(
            ValidationError("EMPTY_FIELDS", "fields", "Document fields are empty")
        )

    if not doc.html_content or len(doc.html_content) < 50:
        errors.append(
            ValidationError(
                "EMPTY_HTML",
                "html_content",
                "Rendered HTML content is missing or trivial",
            )
        )

    field_text = " ".join(doc.fields.values())

    if (
        target_profile.first_name not in field_text
        or target_profile.last_name not in field_text
    ):
        errors.append(
            ValidationError(
                "FIELD_MISMATCH", "fields", "Profile name missing from document fields"
            )
        )

    if target_profile.student_id not in field_text:
        errors.append(
            ValidationError(
                "FIELD_MISMATCH",
                "student_id",
                "Profile ID missing from document fields",
            )
        )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_artifact(
    artifact_path: str | Path, expected_type: ArtifactType
) -> ValidationResult:
    path = Path(artifact_path)
    errors: list[ValidationError] = []
    warnings: list[str] = []

    if not path.exists():
        errors.append(
            ValidationError(
                "FILE_NOT_FOUND", "path", f"Artifact file '{path}' does not exist"
            )
        )
        return ValidationResult(valid=False, errors=errors)

    size = path.stat().st_size
    if size == 0:
        errors.append(
            ValidationError(
                "ZERO_BYTE_FILE", "size", f"Artifact file '{path}' is empty"
            )
        )
        return ValidationResult(valid=False, errors=errors)

    if expected_type == ArtifactType.PDF:
        header = path.read_bytes()[:5]
        if not header.startswith(b"%PDF-"):
            errors.append(
                ValidationError(
                    "INVALID_PDF_HEADER",
                    "header",
                    "File does not start with valid %PDF- header",
                )
            )
    elif expected_type == ArtifactType.PNG:
        header = path.read_bytes()[:8]
        if not header.startswith(b"\x89PNG\r\n\x1a\n"):
            warnings.append("PNG header magic bytes not strictly matched")
    elif expected_type == ArtifactType.JPEG:
        header = path.read_bytes()[:2]
        if not header.startswith(b"\xff\xd8"):
            warnings.append("JPEG header magic bytes not strictly matched")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._pieces: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._pieces.append(text)

    def get_text(self) -> str:
        return " ".join(self._pieces)


def _extract_html_text(raw_html: str) -> str:
    parser = _HTMLTextExtractor()
    try:
        parser.feed(raw_html)
        return parser.get_text()
    except (ValueError, TypeError, RuntimeError) as exc:
        logger.debug("HTML text extractor encountered parsing error: %s", exc)
        return re.sub(r"<[^>]+>", " ", raw_html)


def _validate_pdf_metadata(
    pdf_bytes: bytes,
    institution: Institution | None = None,
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    try:
        reader = pypdf.PdfReader(BytesIO(pdf_bytes))
        info = reader.metadata or {}
        producer = str(info.get("/Producer", "")).lower()
        creator = str(info.get("/Creator", "")).lower()

        bad_fingerprints = [
            "weasyprint",
            "xhtml2pdf",
            "reportlab",
            "fpdf",
            "wkhtmltopdf",
            "pdfkit",
            "pyppeteer",
            "puppeteer",
            "playwright",
        ]
        for fp in bad_fingerprints:
            if fp in producer or fp in creator:
                errors.append(
                    ValidationError(
                        "PDF_PRODUCER_FINGERPRINT",
                        "producer",
                        f"PDF /Producer or /Creator contains '{fp}' — identifiable as synthetic. "
                        "Run _spoof_pdf_metadata() before submission.",
                    )
                )
                break

        creation_raw = str(info.get("/CreationDate", ""))
        if creation_raw:
            m = re.match(r"D:(\d{4})(\d{2})(\d{2})", creation_raw)
            if m:
                pdf_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                today = datetime.now(timezone.utc).date()
                if pdf_date > today:
                    errors.append(
                        ValidationError(
                            "PDF_FUTURE_DATE",
                            "creation_date",
                            f"PDF /CreationDate {pdf_date} is in the future",
                        )
                    )
                if (today - pdf_date).days > 90:
                    errors.append(
                        ValidationError(
                            "PDF_DATE_TOO_OLD",
                            "creation_date",
                            f"PDF /CreationDate {pdf_date} is >90 days old",
                        )
                    )
    except (PyPdfError, ValueError, KeyError, OSError, TypeError) as exc:
        errors.append(
            ValidationError(
                "PDF_METADATA_PARSE_ERROR",
                "metadata",
                f"Failed to parse PDF metadata: {exc}",
            )
        )
    return errors


def inspect_readback_artifact(
    artifact_path: str | Path,
    profile: SyntheticProfile,
    courses: list[CourseRecord] | None = None,
    institution: Institution | None = None,
    preflight_mode: bool = True,
) -> ValidationResult:
    path = Path(artifact_path)
    errors: list[ValidationError] = []
    warnings: list[str] = []

    if not path.exists():
        errors.append(
            ValidationError("FILE_NOT_FOUND", "path", f"Artifact '{path}' not found")
        )
        return ValidationResult(valid=False, errors=errors)

    if path.stat().st_size == 0:
        errors.append(
            ValidationError("EMPTY_FILE", "path", f"Artifact '{path}' is empty")
        )
        return ValidationResult(valid=False, errors=errors)

    inst = institution or profile.institution
    suffix = path.suffix.lower()

    if suffix == ".html":
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            errors.append(
                ValidationError(
                    "TEXT_READ_ERROR", "path", f"Failed to read file: {exc}"
                )
            )
            return ValidationResult(valid=False, errors=errors)

        if profile.first_name not in raw or profile.last_name not in raw:
            errors.append(
                ValidationError(
                    "READBACK_NAME_MISSING",
                    "text",
                    "Profile name could not be read back from artifact",
                )
            )
        if profile.student_id not in raw:
            errors.append(
                ValidationError(
                    "READBACK_ID_MISSING",
                    "text",
                    "Profile ID could not be read back from artifact",
                )
            )

        is_id_card = (
            "OFFICIAL IDENTIFICATION" in raw
            or "Student ID Card" in raw
            or "id_card" in str(path).lower()
        )

        if preflight_mode:
            if (
                not is_id_card
                and profile.current_term_label
                and profile.current_term_label not in raw
            ):
                errors.append(
                    ValidationError(
                        "VERIFY_MISSING_TERM",
                        "current_term_label",
                        f"Term label '{profile.current_term_label}' not in document — "
                        "the Intelligent Document Verification (IDV) layer requires current term enrollment date.",
                    )
                )
            if not is_id_card and profile.term_start_date:
                term_str = profile.term_start_date.strftime("%m/%d/%Y")
                if term_str not in raw:
                    warnings.append(
                        f"Term start date {term_str} not visible — the verification platform checks enrollment date, not print date."
                    )
            if inst and inst.name not in raw and profile.institution_name not in raw:
                errors.append(
                    ValidationError(
                        "VERIFY_INSTITUTION_MISMATCH",
                        "institution_name",
                        f"Institution name '{inst.name}' not found. Must exactly match form submission.",
                    )
                )
            if inst and inst.portal_name not in raw:
                warnings.append(
                    f"Portal name '{inst.portal_name}' not in document — the verification platform knows which portal label each institution uses."
                )
            if (
                not is_id_card
                and profile.enrollment_type
                and profile.enrollment_type not in raw
            ):
                warnings.append(
                    f"Enrollment type '{profile.enrollment_type}' not in document."
                )

        if courses and (
            not inst or inst.document_archetype != DocumentArchetype.REGISTRAR_LETTER
        ):
            for c in courses:
                if c.crn and c.crn not in raw:
                    warnings.append(f"Course CRN '{c.crn}' not found in artifact")

    elif suffix == ".pdf":
        content = path.read_bytes()
        if not content.startswith(b"%PDF-"):
            errors.append(
                ValidationError(
                    "PDF_MAGIC_INVALID",
                    "magic",
                    "File does not start with valid PDF magic header (%PDF-)",
                )
            )

        if preflight_mode:
            errors.extend(_validate_pdf_metadata(content, inst))

        text = ""
        try:
            reader = pypdf.PdfReader(BytesIO(content))
            text = "".join([page.extract_text() or "" for page in reader.pages])
        except (PyPdfError, ValueError, KeyError, OSError, TypeError) as exc:
            logger.debug("Failed to extract PDF text with pypdf: %s", exc)

        if not text:
            try:
                text = content.decode("latin1", errors="ignore")
            except (UnicodeDecodeError, ValueError) as exc:
                errors.append(
                    ValidationError(
                        "PDF_READ_ERROR", "path", f"Failed to read PDF text: {exc}"
                    )
                )
                return ValidationResult(valid=False, errors=errors)

        if profile.first_name not in text or profile.last_name not in text:
            errors.append(
                ValidationError(
                    "READBACK_NAME_MISSING",
                    "text",
                    "Profile name could not be read back from artifact",
                )
            )
        if profile.student_id not in text:
            errors.append(
                ValidationError(
                    "READBACK_ID_MISSING",
                    "text",
                    "Profile ID could not be read back from artifact",
                )
            )

        is_id_card = (
            "OFFICIAL IDENTIFICATION" in text
            or "Student ID Card" in text
            or "id_card" in str(path).lower()
        )

        if preflight_mode:
            if (
                not is_id_card
                and profile.current_term_label
                and profile.current_term_label not in text
            ):
                warnings.append(
                    f"Term label '{profile.current_term_label}' not found in PDF text extract."
                )
            if inst and inst.name not in text and profile.institution_name not in text:
                warnings.append(
                    f"Institution name '{inst.name}' not found in PDF text extract."
                )

    elif suffix in (".png", ".jpg", ".jpeg"):
        content = path.read_bytes()
        if suffix == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            errors.append(
                ValidationError("PNG_MAGIC_INVALID", "magic", "Invalid PNG header")
            )
        elif suffix in (".jpg", ".jpeg") and not content.startswith(b"\xff\xd8"):
            errors.append(
                ValidationError("JPEG_MAGIC_INVALID", "magic", "Invalid JPEG header")
            )

        if preflight_mode:
            try:
                from PIL import Image

                img = Image.open(BytesIO(content))
                w, _ = img.size
                if w < 1000:
                    errors.append(
                        ValidationError(
                            "PNG_RESOLUTION_LOW",
                            "width",
                            f"PNG width {w}px below 1000px threshold. Real portal screenshots are 1280px+.",
                        )
                    )
            except (ImportError, OSError, ValueError) as exc:
                warnings.append(f"Could not inspect image dimensions: {exc}")

    else:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            errors.append(
                ValidationError(
                    "TEXT_READ_ERROR", "path", f"Failed to read file: {exc}"
                )
            )
            return ValidationResult(valid=False, errors=errors)

        if profile.first_name not in text or profile.last_name not in text:
            errors.append(
                ValidationError(
                    "READBACK_NAME_MISSING",
                    "text",
                    "Profile name could not be read back from artifact",
                )
            )
        if profile.student_id not in text:
            errors.append(
                ValidationError(
                    "READBACK_ID_MISSING",
                    "text",
                    "Profile ID could not be read back from artifact",
                )
            )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def readback_validate_html(
    html_str: str,
    profile: SyntheticProfile,
    institution: Institution | None = None,
    preflight_mode: bool = True,
) -> ValidationResult:
    base_dir = Path("/tmp/opencode") if Path("/tmp/opencode").exists() else Path("/tmp")
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", profile.student_id)
    tmp = base_dir / f"rb_{safe_id}_{uuid.uuid4().hex[:8]}.html"
    tmp.write_text(html_str, encoding="utf-8")
    try:
        return inspect_readback_artifact(
            tmp, profile, institution=institution, preflight_mode=preflight_mode
        )
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError as exc:
            logger.debug("Failed to remove temp file %s: %s", tmp, exc)


def readback_validate_pdf(
    pdf_bytes: bytes,
    profile: SyntheticProfile,
    institution: Institution | None = None,
    preflight_mode: bool = True,
) -> ValidationResult:
    base_dir = Path("/tmp/opencode") if Path("/tmp/opencode").exists() else Path("/tmp")
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", profile.student_id)
    tmp = base_dir / f"rb_{safe_id}_{uuid.uuid4().hex[:8]}.pdf"
    tmp.write_bytes(pdf_bytes)
    try:
        return inspect_readback_artifact(
            tmp, profile, institution=institution, preflight_mode=preflight_mode
        )
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError as exc:
            logger.debug("Failed to remove temp file %s: %s", tmp, exc)


# =====================================================================
# FIXTURE & BUNDLE GENERATION
# =====================================================================


def generate_fixture_bundle(
    scenario_name: str = "undergraduate",
    seed: int = 42,
    output_dir: str | Path = "output/fixture",
    override_institution_id: str | None = None,
    doc_kind: DocumentKind = DocumentKind.SCHEDULE,
    formats: tuple[ArtifactType, ...] = (
        ArtifactType.HTML,
        ArtifactType.PDF,
        ArtifactType.PNG,
    ),
) -> GenerationResult:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    profile = generate_profile(
        scenario_name=scenario_name,
        seed=seed,
        override_institution_id=override_institution_id,
    )
    doc = generate_document(profile, doc_kind=doc_kind, seed=seed)

    profile_val = validate_profile(profile)
    doc_val = validate_document(doc)

    artifacts: list[GeneratedArtifact] = []

    if ArtifactType.HTML in formats:
        html_path = out_dir / "document.html"
        html_path.write_text(doc.html_content, encoding="utf-8")
        artifacts.append(
            GeneratedArtifact(
                kind=doc.kind,
                path=str(html_path),
                byte_size=len(doc.html_content.encode("utf-8")),
                sha256=hashlib.sha256(doc.html_content.encode("utf-8")).hexdigest(),
                artifact_type=ArtifactType.HTML,
            )
        )

    if ArtifactType.PDF in formats:
        pdf_path = out_dir / "document.pdf"
        pdf_bytes = render_pdf(
            doc.html_content,
            institution=profile.institution,
            profile=profile,
            term_label=profile.current_term_label,
        )
        pdf_path.write_bytes(pdf_bytes)
        artifacts.append(
            GeneratedArtifact(
                kind=doc.kind,
                path=str(pdf_path),
                byte_size=len(pdf_bytes),
                sha256=hashlib.sha256(pdf_bytes).hexdigest(),
                artifact_type=ArtifactType.PDF,
            )
        )

    if ArtifactType.PNG in formats:
        png_path = out_dir / "document.png"
        png_bytes = render_png(doc.html_content)
        png_path.write_bytes(png_bytes)
        artifacts.append(
            GeneratedArtifact(
                kind=doc.kind,
                path=str(png_path),
                byte_size=len(png_bytes),
                sha256=hashlib.sha256(png_bytes).hexdigest(),
                artifact_type=ArtifactType.PNG,
            )
        )

    if ArtifactType.JPEG in formats:
        jpg_path = out_dir / "document.jpg"
        jpg_bytes = render_jpeg(doc.html_content)
        jpg_path.write_bytes(jpg_bytes)
        artifacts.append(
            GeneratedArtifact(
                kind=doc.kind,
                path=str(jpg_path),
                byte_size=len(jpg_bytes),
                sha256=hashlib.sha256(jpg_bytes).hexdigest(),
                artifact_type=ArtifactType.JPEG,
            )
        )

    # Save profile JSON
    profile_json_path = out_dir / "profile.json"
    profile_json_path.write_text(
        json.dumps(profile.to_dict(), indent=2), encoding="utf-8"
    )

    all_errors = list(profile_val.errors) + list(doc_val.errors)
    validated_artifacts = 0
    for art in artifacts:
        art_val = validate_artifact(art.path, art.artifact_type)
        if art_val.valid:
            validated_artifacts += 1
        else:
            all_errors.extend(art_val.errors)

        rb_val = inspect_readback_artifact(art.path, profile)
        if not rb_val.valid:
            all_errors.extend(rb_val.errors)

    report = GenerationReport(
        profile_valid=profile_val.valid,
        documents_generated=1,
        documents_validated=1 if doc_val.valid else 0,
        artifacts_validated=validated_artifacts,
        errors=all_errors,
        seed=seed,
        scenario=scenario_name,
        generator_version=GENERATOR_VERSION,
    )

    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    validation_result = ValidationResult(valid=len(all_errors) == 0, errors=all_errors)

    return GenerationResult(
        profile=profile,
        document=doc,
        artifacts=artifacts,
        validation=validation_result,
        report=report,
        seed=seed,
        scenario=scenario_name,
    )


def generate_document_bundle(
    profile: SyntheticProfile,
    output_dir: str | Path = "output/bundle",
    seed: int = 42,
    formats: tuple[ArtifactType, ...] = (
        ArtifactType.HTML,
        ArtifactType.PDF,
        ArtifactType.PNG,
        ArtifactType.JPEG,
    ),
) -> dict[str, Any]:
    """
    Generates a complete multi-document bundle (Schedule, Tuition Receipt, ID Card)
    bound to the identical synthetic profile with 100% cross-document consistency.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    kinds = [DocumentKind.SCHEDULE, DocumentKind.TUITION_RECEIPT, DocumentKind.ID_CARD]
    results = {}
    all_valid = True

    for kind in kinds:
        sub_dir = out_dir / kind.value
        sub_res = generate_fixture_bundle(
            scenario_name="undergraduate",
            seed=seed,
            output_dir=sub_dir,
            override_institution_id=profile.institution_id,
            doc_kind=kind,
            formats=formats,
        )
        results[kind.value] = sub_res.to_dict()
        if not sub_res.validation.valid:
            all_valid = False

    bundle_summary = {
        "synthetic": True,
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "profile": profile.to_dict(),
        "bundle_valid": all_valid,
        "documents": results,
    }

    summary_path = out_dir / "bundle_summary.json"
    summary_path.write_text(json.dumps(bundle_summary, indent=2), encoding="utf-8")
    return bundle_summary


def generate_batch(
    scenario_name: str = "undergraduate",
    count: int = 10,
    base_seed: int = 1000,
    output_dir: str | Path = "output/batch",
    override_institution_id: str | None = None,
) -> dict[str, Any]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    valid_count = 0
    invalid_count = 0
    failure_categories: dict[str, int] = {}
    results_summary = []

    for i in range(count):
        derived_seed = base_seed + i
        sub_dir = out_dir / f"item_{i + 1}_seed_{derived_seed}"
        try:
            res = generate_fixture_bundle(
                scenario_name=scenario_name,
                seed=derived_seed,
                output_dir=sub_dir,
                override_institution_id=override_institution_id,
            )
            is_valid = res.validation.valid
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                for err in res.validation.errors:
                    failure_categories[err.code] = (
                        failure_categories.get(err.code, 0) + 1
                    )

            results_summary.append(
                {
                    "index": i + 1,
                    "seed": derived_seed,
                    "profile_id": res.profile.student_id,
                    "name": f"{res.profile.first_name} {res.profile.last_name}",
                    "valid": is_valid,
                    "errors": [e.code for e in res.validation.errors],
                    "path": str(sub_dir),
                }
            )
        except (RuntimeError, ValueError, OSError, TypeError, KeyError) as exc:
            invalid_count += 1
            err_code = "EXCEPTION"
            failure_categories[err_code] = failure_categories.get(err_code, 0) + 1
            results_summary.append(
                {
                    "index": i + 1,
                    "seed": derived_seed,
                    "valid": False,
                    "errors": [f"EXCEPTION: {exc}"],
                }
            )

    summary = {
        "synthetic": True,
        "generator_version": GENERATOR_VERSION,
        "scenario": scenario_name,
        "base_seed": base_seed,
        "total": count,
        "valid": valid_count,
        "invalid": invalid_count,
        "failure_categories": failure_categories,
        "batch_output_dir": str(out_dir),
        "items": results_summary,
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
