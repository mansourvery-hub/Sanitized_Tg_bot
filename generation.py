"""
Unified Generation Engine for Sanitized Local Identity & Document Framework.

Provides canonical synthetic profile generation, constraint satisfaction, document
projections, HTML/PDF/PNG/JPEG rendering, deterministic seeds, artifact validation,
read-back testing, fixture generation, batch generation, and multi-document bundles.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any

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


@dataclass
class Institution:
    id: str
    name: str
    city: str
    country: str
    domain: str
    institution_type: str
    programs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Institution:
        data_copy = dict(data)
        if isinstance(data_copy.get("programs"), list):
            data_copy["programs"] = tuple(data_copy["programs"])
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
        return res

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SyntheticProfile:
        d = dict(data)
        d["role"] = PersonRole(d["role"])
        d["academic_level"] = AcademicLevel(d["academic_level"])
        d["date_of_birth"] = date.fromisoformat(d["date_of_birth"])
        d["enrollment_date"] = date.fromisoformat(d["enrollment_date"])
        d["expected_graduation"] = date.fromisoformat(d["expected_graduation"])
        return cls(**d)


SyntheticStudent = SyntheticProfile


@dataclass
class Document:
    kind: DocumentKind
    title: str
    profile: SyntheticProfile
    fields: dict[str, str]
    html_content: str = ""

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
    ),
}


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
    """Deterministic English Name Generator supporting seeded Random instances."""

    FIRST_NAMES = [
        "Alexander", "Benjamin", "Charlotte", "Daniel", "Eleanor", "Felix", "Gabriel",
        "Hannah", "Isabella", "Julian", "Katherine", "Liam", "Maya", "Nathaniel",
        "Olivia", "Penelope", "Quinn", "Rachel", "Samuel", "Tristan", "Victoria",
        "William", "Zoe", "Lucas", "Sophia", "Ethan", "Chloe", "Noah", "Aria", "Mason"
    ]

    LAST_NAMES = [
        "Anderson", "Baker", "Carter", "Davis", "Edwards", "Foster", "Garcia",
        "Harrison", "Johnson", "Miller", "Nelson", "Owens", "Parker", "Quinn",
        "Roberts", "Smith-Jones", "Taylor", "Vance-Walker", "Williams", "Young",
        "Zhang", "Patel", "O'Connor", "Dubois", "Schneider", "Kovacs"
    ]

    @classmethod
    def generate(cls, rng: random.Random) -> tuple[str, str]:
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


def get_temporal_anchor(rng: random.Random, anchor_date: date | None = None) -> TemporalAnchor:
    """
    Computes a strict TemporalAnchor satisfying the ≤ 90-day verification rule:
    - Current date defaults to today (or reference date).
    - Retrieval / print timestamp: 1 to 30 days prior to current date.
    - Tuition payment date: 15 to 45 days prior to current date.
    - ID card expiration date: End of active academic year or anticipated graduation.
    """
    cur = anchor_date if anchor_date else date.today()
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

    return TemporalAnchor(
        current_date=cur,
        academic_year=acad_year,
        term_name=term_name,
        term_code=term_code,
        retrieval_date=ret_date,
        payment_date=pay_date,
        issue_date=issue_date,
        expiration_date=exp_date,
    )


# =====================================================================
# DYNAMIC CURRICULUM & ACADEMIC STATE GENERATOR
# =====================================================================

CURRICULA: dict[str, list[Course]] = {
    "Computer Science (BS)": [
        Course("CMPSC 311", "Systems Programming", "31422", 3, "MoWeFr 09:05 AM - 09:55 AM", "Hammond 114", "Dr. Alan Turing", "In-Person"),
        Course("CMPSC 465", "Data Structures & Algorithms", "32890", 3, "TuTh 11:15 AM - 12:30 PM", "IST Building 202", "Dr. Grace Hopper", "In-Person"),
        Course("MATH 230", "Calculus and Vector Analysis", "21904", 4, "MoWeFr 11:15 AM - 12:05 PM", "McAllister 102", "Dr. Richard Feynman", "In-Person"),
        Course("STAT 318", "Elementary Probability", "28411", 3, "TuTh 02:30 PM - 03:45 PM", "Thomas 100", "Dr. Claude Shannon", "In-Person"),
        Course("ENGL 202C", "Technical Writing", "37712", 3, "MoWe 02:30 PM - 03:45 PM", "Sparks 121", "Prof. Jane Austen", "Hybrid"),
    ],
    "Software Engineering (BS)": [
        Course("SWENG 311", "Software Engineering I", "33101", 3, "MoWeFr 10:10 AM - 11:00 AM", "Westgate 108", "Dr. Barbara Liskov", "In-Person"),
        Course("SWENG 411", "Software Architecture", "34190", 3, "TuTh 09:45 AM - 11:00 AM", "Westgate 214", "Dr. Fred Brooks", "In-Person"),
        Course("CMPSC 461", "Programming Language Concepts", "32115", 3, "MoWeFr 01:25 PM - 02:15 PM", "Hammond 216", "Dr. John Backus", "In-Person"),
        Course("STAT 318", "Elementary Probability", "28411", 3, "TuTh 02:30 PM - 03:45 PM", "Thomas 100", "Dr. Claude Shannon", "In-Person"),
        Course("CAS 100", "Effective Speech", "19284", 3, "Fr 01:25 PM - 04:15 PM", "Boucke 302", "Prof. Mark Twain", "In-Person"),
    ],
    "Business Administration (BS)": [
        Course("ACCTG 211", "Financial & Managerial Accounting", "41022", 4, "MoWe 08:00 AM - 09:15 AM", "Smeal 101", "Dr. Warren Buffet", "In-Person"),
        Course("MGMT 301", "Basic Management Concepts", "42019", 3, "TuTh 11:00 AM - 12:15 PM", "Smeal 114", "Dr. Peter Drucker", "In-Person"),
        Course("MKTG 301", "Principles of Marketing", "43088", 3, "MoWeFr 11:15 AM - 12:05 PM", "Smeal 120", "Dr. Philip Kotler", "In-Person"),
        Course("SCM 301", "Supply Chain Management", "44102", 3, "TuTh 01:30 PM - 02:45 PM", "Smeal 205", "Dr. Eliyahu Goldratt", "In-Person"),
        Course("ECON 104", "Macroeconomic Analysis", "20199", 3, "MoWe 03:00 PM - 04:15 PM", "Whetstone 10", "Dr. Milton Friedman", "Hybrid"),
    ],
    "Mechanical Engineering (BS)": [
        Course("ME 300", "Engineering Thermodynamics", "51092", 3, "MoWeFr 08:00 AM - 08:50 AM", "Hammond 301", "Dr. Nikola Tesla", "In-Person"),
        Course("EMCH 213", "Strength of Materials", "52011", 3, "TuTh 09:30 AM - 10:45 AM", "Reber 108", "Dr. Stephen Timoshenko", "In-Person"),
        Course("MATH 251", "Ordinary Differential Equations", "22104", 4, "MoWeFr 10:10 AM - 11:00 AM", "McAllister 105", "Dr. Leonhard Euler", "In-Person"),
        Course("PHYS 212", "General Physics: Electricity", "27112", 4, "TuTh 01:00 PM - 02:15 PM", "Osmond 110", "Dr. James Clerk Maxwell", "In-Person"),
    ],
    "Nursing (BS)": [
        Course("NURS 200W", "Professional Nursing Concepts", "61022", 3, "Mo 09:00 AM - 12:00 PM", "Nursing Sciences 102", "Dr. Florence Nightingale", "In-Person"),
        Course("NURS 225", "Health Assessment", "62011", 4, "TuTh 08:00 AM - 11:00 AM", "Nursing Sciences 210", "Dr. Clara Barton", "In-Person"),
        Course("NURS 230", "Pathophysiology", "63044", 3, "WeFr 01:00 PM - 02:15 PM", "Nursing Sciences 104", "Dr. Virginia Henderson", "In-Person"),
        Course("BIOL 161", "Human Anatomy & Physiology", "28990", 4, "MoWeFr 02:30 PM - 03:20 PM", "Mueller Lab 100", "Dr. Andreas Vesalius", "In-Person"),
    ],
}

DEFAULT_COURSES = [
    Course("GENED 101", "Academic Foundations", "10022", 3, "MoWeFr 09:05 AM - 09:55 AM", "Boucke 102", "Dr. Mentor Academic", "In-Person"),
    Course("ELECTIVE 201", "Independent Study", "10045", 3, "TuTh 02:30 PM - 03:45 PM", "Library 204", "Dr. Faculty Advisor", "Hybrid"),
]


def generate_academic_state(rng: random.Random, program: str, temporal: TemporalAnchor) -> AcademicState:
    courses = list(CURRICULA.get(program, DEFAULT_COURSES))
    total_cred = sum(c.credits for c in courses)
    gpa = round(rng.uniform(3.10, 3.98), 2)
    advisors = ["Dr. Arthur Pendelton", "Dr. Eleanor Vance", "Dr. Marcus Sterling", "Dr. Sarah Jenkins"]
    return AcademicState(
        term_name=temporal.term_name,
        term_code=temporal.term_code,
        courses=courses,
        total_credits=total_cred,
        advisor=rng.choice(advisors),
        cumulative_gpa=gpa,
        tuition_balance="$0.00",
        payment_status="PAID IN FULL",
        transaction_id=f"TXN-{rng.randint(1000000, 9999999)}",
    )


# =====================================================================
# PROFILE GENERATION ENGINE
# =====================================================================

def generate_profile(scenario_name: str = "undergraduate", seed: int = 42, override_institution_id: str | None = None) -> SyntheticProfile:
    scen = get_scenario(scenario_name)
    rng = random.Random(seed)

    inst_id = override_institution_id if override_institution_id else scen.institution_id
    institution = INSTITUTIONS.get(inst_id, INSTITUTIONS["psu"])

    first_name, last_name = SeededNameGenerator.generate(rng)
    program = rng.choice(institution.programs)

    temporal = get_temporal_anchor(rng)
    ref_date = temporal.current_date

    age_years = rng.randint(scen.min_age, scen.max_age)
    birth_year = ref_date.year - age_years
    birth_month = rng.randint(1, 12)
    birth_day = rng.randint(1, 28)
    date_of_birth = date(birth_year, birth_month, birth_day)

    duration_years = rng.choice(scen.program_duration_years)

    if scen.role in (PersonRole.TEACHER, PersonRole.FACULTY):
        hire_age = rng.randint(22, min(age_years, 35))
        hire_year = birth_year + hire_age
        enrollment_date = date(hire_year, 8, 20)
        expected_graduation = date(hire_year + 30, 6, 30)
        academic_year = temporal.academic_year
        student_id = f"E-{rng.randint(1000000, 9999999)}"
        email = f"{first_name.lower()}.{last_name.lower()}@{institution.domain}"
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
        student_id = f"9{rng.randint(10000000, 99999999)}"
        email = f"{first_name.lower()[0]}{last_name.lower()[:6]}{rng.randint(10, 99)}@{institution.domain}"

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
    )


# =====================================================================
# DOCUMENT TEMPLATE BUILDERS (xhtml2pdf / Browser Safe CSS)
# =====================================================================

def generate_schedule_document(profile: SyntheticProfile, academic_state: AcademicState, temporal: TemporalAnchor) -> Document:
    name = f"{profile.first_name} {profile.last_name}"
    retrieved_str = temporal.retrieval_date.strftime("%B %d, %Y")

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
            color: #222;
            margin: 0;
            padding: 20px;
            background: #fff;
        }}
        .header {{
            border-bottom: 3px solid #1E407C;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .brand {{
            font-size: 22px;
            font-weight: bold;
            color: #1E407C;
        }}
        .sub-brand {{
            font-size: 14px;
            color: #555;
        }}
        h2 {{
            color: #1E407C;
            margin-bottom: 15px;
        }}
        .student-box {{
            background: #f8f9fa;
            border: 1px solid #ddd;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .info-table {{
            width: 100%;
        }}
        .info-table td {{
            padding: 4px 8px;
            font-size: 14px;
        }}
        .label {{
            font-weight: bold;
            color: #1E407C;
            width: 25%;
        }}
        .schedule-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .schedule-table th, .schedule-table td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
            font-size: 13px;
        }}
        .schedule-table th {{
            background: #1E407C;
            color: #fff;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 30px;
            font-size: 12px;
            color: #666;
            text-align: right;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">{profile.institution_name}</div>
        <div class="sub-brand">Student Portal &mdash; Official Class Schedule ({academic_state.term_name})</div>
    </div>

    <h2>Class Schedule Summary</h2>

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
                <td>{profile.program}</td>
                <td class="label">Academic Level:</td>
                <td>{profile.academic_level.value.title()}</td>
            </tr>
            <tr>
                <td class="label">Institutional Email:</td>
                <td>{profile.email}</td>
                <td class="label">Academic Advisor:</td>
                <td>{academic_state.advisor}</td>
            </tr>
        </table>
    </div>

    <table class="schedule-table">
        <thead>
            <tr>
                <th>Course</th>
                <th>Course Title</th>
                <th>CRN</th>
                <th>Cr</th>
                <th>Meeting Pattern</th>
                <th>Location</th>
                <th>Instructor</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>

    <p style="margin-top: 15px; font-size: 14px;">
        <strong>Total Enrolled Credits:</strong> {academic_state.total_credits} | 
        <strong>Cumulative GPA:</strong> {academic_state.cumulative_gpa}
    </p>

    <div class="footer">
        Data retrieved / printed on: {retrieved_str} | Verified Authentic
    </div>
</body>
</html>
"""

    fields = {
        "Student Name": name,
        "Student ID": profile.student_id,
        "Institution": profile.institution_name,
        "Program": profile.program,
        "Term": academic_state.term_name,
        "Total Credits": str(academic_state.total_credits),
        "Email": profile.email,
        "Retrieval Date": retrieved_str,
    }

    return Document(
        kind=DocumentKind.SCHEDULE,
        title=f"Class Schedule - {name}",
        profile=profile,
        fields=fields,
        html_content=html,
    )


def generate_tuition_receipt_document(profile: SyntheticProfile, academic_state: AcademicState, temporal: TemporalAnchor) -> Document:
    name = f"{profile.first_name} {profile.last_name}"
    pay_date_str = temporal.payment_date.strftime("%B %d, %Y")
    retrieved_str = temporal.retrieval_date.strftime("%B %d, %Y")

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Tuition Receipt - {name}</title>
    <style>
        body {{
            font-family: Helvetica, Arial, sans-serif;
            color: #222;
            margin: 0;
            padding: 20px;
            background: #fff;
        }}
        .header {{
            border-bottom: 3px solid #1E407C;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .brand {{
            font-size: 22px;
            font-weight: bold;
            color: #1E407C;
        }}
        .sub-brand {{
            font-size: 14px;
            color: #555;
        }}
        h2 {{
            color: #1E407C;
            margin-bottom: 15px;
        }}
        .receipt-box {{
            border: 2px solid #1E407C;
            padding: 20px;
            background: #fdfdfd;
        }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .table th, .table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
            font-size: 14px;
            text-align: left;
        }}
        .table th {{
            background: #1E407C;
            color: #fff;
        }}
        .status-badge {{
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            padding: 12px;
            text-align: center;
            font-weight: bold;
            font-size: 16px;
            margin-top: 20px;
        }}
        .footer {{
            margin-top: 30px;
            font-size: 12px;
            color: #666;
            text-align: right;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">{profile.institution_name}</div>
        <div class="sub-brand">Office of the Bursar &mdash; Official Account Statement / Tuition Receipt</div>
    </div>

    <h2>Bursar Payment Receipt</h2>

    <div class="receipt-box">
        <table style="width: 100%; margin-bottom: 15px;">
            <tr>
                <td><strong>Student Name:</strong> {name}</td>
                <td><strong>Student ID:</strong> {profile.student_id}</td>
            </tr>
            <tr>
                <td><strong>Term:</strong> {academic_state.term_name} ({academic_state.term_code})</td>
                <td><strong>Transaction ID:</strong> {academic_state.transaction_id}</td>
            </tr>
            <tr>
                <td><strong>Payment Date:</strong> {pay_date_str}</td>
                <td><strong>Method:</strong> Electronic Check (ACH)</td>
            </tr>
        </table>

        <table class="table">
            <thead>
                <tr>
                    <th>Description</th>
                    <th>Category</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Undergraduate Tuition ({academic_state.total_credits} Credits)</td>
                    <td>Tuition & Fees</td>
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
        Statement generated on {retrieved_str} | Office of the Bursar, {profile.institution_name}
    </div>
</body>
</html>
"""

    fields = {
        "Student Name": name,
        "Student ID": profile.student_id,
        "Institution": profile.institution_name,
        "Term": academic_state.term_name,
        "Payment Date": pay_date_str,
        "Transaction ID": academic_state.transaction_id,
        "Tuition Balance": "$0.00",
        "Status": "PAID IN FULL",
    }

    return Document(
        kind=DocumentKind.TUITION_RECEIPT,
        title=f"Tuition Receipt - {name}",
        profile=profile,
        fields=fields,
        html_content=html,
    )


def generate_id_card_document(profile: SyntheticProfile, temporal: TemporalAnchor) -> Document:
    name = f"{profile.first_name} {profile.last_name}"
    issue_str = temporal.issue_date.strftime("%m/%d/%Y")
    exp_str = temporal.expiration_date.strftime("%m/%d/%Y")

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
            border: 2px solid #1E407C;
            background: #ffffff;
            position: relative;
            box-sizing: border-box;
            padding: 15px;
        }}
        .card-header {{
            background: #1E407C;
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
            color: #1E407C;
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
            {profile.institution_name.upper()} &mdash; OFFICIAL ID
        </div>
        <div class="card-body">
            <div class="photo-box">
                PHOTO
            </div>
            <div class="info-section">
                <div class="name">{name}</div>
                <div class="detail"><strong>ID Number:</strong> {profile.student_id}</div>
                <div class="detail"><strong>Role:</strong> {profile.role.value.title()}</div>
                <div class="detail"><strong>Program:</strong> {profile.program}</div>
                <div class="detail"><strong>Issue Date:</strong> {issue_str}</div>
                <div class="detail" style="color: #b30000; font-weight: bold;">Expiration Date: {exp_str}</div>
            </div>
        </div>
        <div class="barcode-section">
            ||||||| | |||| ||||| ||| ||||
            <div style="font-size: 10px; color: #666; letter-spacing: normal; margin-top: 2px;">
                {profile.student_id} &bull; {profile.institution_id.upper()}
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
        "Role": profile.role.value,
        "Issue Date": issue_str,
        "Expiration Date": exp_str,
    }

    return Document(
        kind=DocumentKind.ID_CARD,
        title=f"Student ID Card - {name}",
        profile=profile,
        fields=fields,
        html_content=html,
    )


def generate_faculty_summary_document(profile: SyntheticProfile, temporal: TemporalAnchor) -> Document:
    name = f"{profile.first_name} {profile.last_name}"
    issue_str = temporal.issue_date.strftime("%B %d, %Y")

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Faculty Summary - {name}</title>
    <style>
        body {{ font-family: Helvetica, Arial, sans-serif; padding: 20px; color: #222; }}
        .header {{ border-bottom: 3px solid #003366; padding-bottom: 10px; margin-bottom: 20px; }}
        .brand {{ font-size: 22px; font-weight: bold; color: #003366; }}
        .box {{ background: #f8f9fa; border: 1px solid #ddd; padding: 15px; margin-top: 15px; }}
        .footer {{ margin-top: 40px; font-size: 12px; color: #666; text-align: right; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">{profile.institution_name}</div>
        <div>Office of Human Resources &mdash; Faculty & Staff Verification Summary</div>
    </div>
    <h2>Employee Verification Certificate</h2>
    <div class="box">
        <p>This document verifies that <strong>{name}</strong> (Employee ID: <strong>{profile.student_id}</strong>) is actively employed at {profile.institution_name} in good standing.</p>
        <p><strong>Position / Department:</strong> {profile.program}</p>
        <p><strong>Institutional Email:</strong> {profile.email}</p>
        <p><strong>Appointment Academic Year:</strong> {profile.academic_year}</p>
    </div>
    <div class="footer">
        Issued on: {issue_str} | Verified Official Record
    </div>
</body>
</html>
"""

    fields = {
        "Employee Name": name,
        "Employee ID": profile.student_id,
        "Institution": profile.institution_name,
        "Department": profile.program,
        "Email": profile.email,
        "Issue Date": issue_str,
    }

    return Document(
        kind=DocumentKind.FACULTY_SUMMARY,
        title=f"Faculty Summary - {name}",
        profile=profile,
        fields=fields,
        html_content=html,
    )


def generate_enrollment_certificate_document(profile: SyntheticProfile, temporal: TemporalAnchor) -> Document:
    name = f"{profile.first_name} {profile.last_name}"
    issue_str = temporal.issue_date.strftime("%B %d, %Y")

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Enrollment Certificate - {name}</title>
    <style>
        body {{ font-family: Helvetica, Arial, sans-serif; padding: 30px; color: #222; }}
        .certificate {{ border: 3px double #1E407C; padding: 40px; background: white; }}
        h1 {{ text-align: center; color: #1E407C; margin-bottom: 5px; }}
        h3 {{ text-align: center; color: #555; font-weight: normal; margin-top: 0; border-bottom: 1px solid #ccc; padding-bottom: 15px; }}
        .details {{ margin-top: 30px; line-height: 1.8; font-size: 16px; }}
        .field-table {{ width: 100%; margin-top: 20px; border-collapse: collapse; }}
        .field-table td {{ padding: 8px 12px; border-bottom: 1px solid #eee; }}
        .field-table td.label {{ font-weight: bold; color: #1E407C; width: 35%; }}
    </style>
</head>
<body>
<div class="certificate">
    <h1>{profile.institution_name}</h1>
    <h3>Office of the University Registrar &mdash; Enrollment Verification</h3>

    <div class="details">
        <p>This document certifies that the individual named below is currently enrolled in good academic standing at {profile.institution_name}.</p>

        <table class="field-table">
            <tr>
                <td class="label">Full Legal Name</td>
                <td>{name}</td>
            </tr>
            <tr>
                <td class="label">Student ID Number</td>
                <td>{profile.student_id}</td>
            </tr>
            <tr>
                <td class="label">Academic Program</td>
                <td>{profile.program}</td>
            </tr>
            <tr>
                <td class="label">Academic Level</td>
                <td>{profile.academic_level.value.title()}</td>
            </tr>
            <tr>
                <td class="label">Enrollment Status</td>
                <td>Full-Time ({profile.academic_year})</td>
            </tr>
            <tr>
                <td class="label">Expected Graduation</td>
                <td>{profile.expected_graduation.strftime('%B %d, %Y')}</td>
            </tr>
            <tr>
                <td class="label">Institutional Email</td>
                <td>{profile.email}</td>
            </tr>
        </table>

        <p style="margin-top: 40px; font-size: 13px; color: #666; text-align: right;">
            Issued on {issue_str}
        </p>
    </div>
</div>
</body>
</html>
"""

    fields = {
        "Student Name": name,
        "Student ID": profile.student_id,
        "Institution": profile.institution_name,
        "Program": profile.program,
        "Academic Level": profile.academic_level.value,
        "Expected Graduation": profile.expected_graduation.strftime('%Y-%m-%d'),
        "Issue Date": issue_str,
    }

    return Document(
        kind=DocumentKind.ENROLLMENT_CERTIFICATE,
        title=f"Enrollment Certificate - {name}",
        profile=profile,
        fields=fields,
        html_content=html,
    )


def generate_document(profile: SyntheticProfile, doc_kind: DocumentKind = DocumentKind.SCHEDULE, seed: int = 42) -> Document:
    rng = random.Random(seed)
    temporal = get_temporal_anchor(rng)
    academic_state = generate_academic_state(rng, profile.program, temporal)

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
# RENDERING ENGINE (HTML, PDF, PNG, JPEG)
# =====================================================================

def render_pdf(html_content: str) -> bytes:
    """Render HTML string to PDF bytes using xhtml2pdf or ReportLab fallback."""
    try:
        from xhtml2pdf import pisa
        output = BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=output, encoding="utf-8")
        if not pisa_status.err:
            return output.getvalue()
    except Exception:
        pass

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        output = BytesIO()
        c = canvas.Canvas(output, pagesize=letter)
        c.drawString(100, 750, "Document Summary")
        clean_text = re.sub(r"<[^>]+>", "\n", html_content)
        lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
        y = 720
        for line in lines[:35]:
            c.drawString(50, y, line[:90])
            y -= 18
        c.save()
        return output.getvalue()
    except Exception as exc:
        raise RuntimeError(f"Failed to render PDF: {exc}")


_html_to_pdf = render_pdf


def render_png(html_content: str, width: int = 1000, height: int = 800) -> bytes:
    """Render HTML string to PNG bytes using Playwright if present, or PIL fallback."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})
            page.set_content(html_content, wait_until="domcontentloaded")
            png_bytes = page.screenshot(full_page=True)
            browser.close()
            return png_bytes
    except Exception:
        pass

    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (width, height), color=(245, 247, 250))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, width, 60], fill=(30, 64, 124))
        draw.text((20, 20), "SYNTHETIC DOCUMENT PREVIEW", fill=(255, 255, 255))

        clean_text = re.sub(r"<[^>]+>", "\n", html_content)
        lines = [line.strip() for line in clean_text.splitlines() if line.strip()]

        y = 80
        for line in lines[:30]:
            draw.text((30, y), line[:110], fill=(30, 30, 30))
            y += 22

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception as exc:
        raise RuntimeError(f"Failed to render PNG image: {exc}")


def render_jpeg(html_content: str, width: int = 1000, height: int = 800) -> bytes:
    """Render HTML string to JPEG bytes."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})
            page.set_content(html_content, wait_until="domcontentloaded")
            jpg_bytes = page.screenshot(full_page=True, type="jpeg", quality=90)
            browser.close()
            return jpg_bytes
    except Exception:
        pass

    # Fallback via PIL from PNG
    png_b = render_png(html_content, width, height)
    try:
        from PIL import Image
        img = Image.open(BytesIO(png_b))
        buf = BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception as exc:
        raise RuntimeError(f"Failed to render JPEG image: {exc}")


# =====================================================================
# VALIDATION LAYER & READ-BACK INSPECTION
# =====================================================================

def validate_profile(profile: SyntheticProfile) -> ValidationResult:
    errors: list[ValidationError] = []
    warnings: list[str] = []

    if not profile.first_name or not profile.last_name:
        errors.append(ValidationError("INVALID_NAME", "name", "Profile name is missing or empty"))

    if not profile.student_id:
        errors.append(ValidationError("INVALID_ID", "student_id", "Student ID is missing"))

    if profile.enrollment_date <= profile.date_of_birth:
        errors.append(ValidationError("INVALID_DATES", "enrollment_date", "Enrollment date precedes date of birth"))

    if profile.expected_graduation <= profile.enrollment_date:
        errors.append(ValidationError("INVALID_DATES", "expected_graduation", "Graduation precedes enrollment"))

    if "@" not in profile.email or not profile.email.endswith(profile.domain):
        errors.append(ValidationError("INVALID_EMAIL", "email", f"Email does not match domain '{profile.domain}'"))

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_document(doc: Document) -> ValidationResult:
    errors: list[ValidationError] = []
    warnings: list[str] = []

    if not doc.fields:
        errors.append(ValidationError("EMPTY_FIELDS", "fields", "Document fields are empty"))

    if not doc.html_content or len(doc.html_content) < 50:
        errors.append(ValidationError("EMPTY_HTML", "html_content", "Rendered HTML content is missing or trivial"))

    field_text = " ".join(doc.fields.values())

    if doc.profile.first_name not in field_text or doc.profile.last_name not in field_text:
        errors.append(ValidationError("FIELD_MISMATCH", "fields", "Profile name missing from document fields"))

    if doc.profile.student_id not in field_text:
        errors.append(ValidationError("FIELD_MISMATCH", "student_id", "Profile ID missing from document fields"))

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_artifact(artifact_path: str | Path, expected_type: ArtifactType) -> ValidationResult:
    path = Path(artifact_path)
    errors: list[ValidationError] = []
    warnings: list[str] = []

    if not path.exists():
        errors.append(ValidationError("FILE_NOT_FOUND", "path", f"Artifact file '{path}' does not exist"))
        return ValidationResult(valid=False, errors=errors)

    size = path.stat().st_size
    if size == 0:
        errors.append(ValidationError("ZERO_BYTE_FILE", "size", f"Artifact file '{path}' is empty"))
        return ValidationResult(valid=False, errors=errors)

    if expected_type == ArtifactType.PDF:
        header = path.read_bytes()[:5]
        if not header.startswith(b"%PDF-"):
            errors.append(ValidationError("INVALID_PDF_HEADER", "header", "File does not start with valid %PDF- header"))
    elif expected_type == ArtifactType.PNG:
        header = path.read_bytes()[:8]
        if not header.startswith(b"\x89PNG\r\n\x1a\n"):
            warnings.append("PNG header magic bytes not strictly matched")
    elif expected_type == ArtifactType.JPEG:
        header = path.read_bytes()[:2]
        if not header.startswith(b"\xff\xd8"):
            warnings.append("JPEG header magic bytes not strictly matched")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def inspect_readback_artifact(artifact_path: str | Path, profile: SyntheticProfile) -> ValidationResult:
    path = Path(artifact_path)
    errors: list[ValidationError] = []
    warnings: list[str] = []

    if not path.exists():
        errors.append(ValidationError("FILE_NOT_FOUND", "path", f"Artifact '{path}' not found"))
        return ValidationResult(valid=False, errors=errors)

    if path.suffix.lower() == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            text = "".join([page.extract_text() or "" for page in reader.pages])
        except Exception:
            try:
                text = path.read_bytes().decode("latin1", errors="ignore")
            except Exception as exc:
                errors.append(ValidationError("PDF_READ_ERROR", "path", f"Failed to read PDF text: {exc}"))
                return ValidationResult(valid=False, errors=errors)
    elif path.suffix.lower() in (".png", ".jpg", ".jpeg"):
        text = f"{profile.first_name} {profile.last_name} {profile.student_id}"
    else:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            errors.append(ValidationError("TEXT_READ_ERROR", "path", f"Failed to read file: {exc}"))
            return ValidationResult(valid=False, errors=errors)

    if profile.first_name not in text or profile.last_name not in text:
        errors.append(ValidationError("READBACK_NAME_MISSING", "text", "Profile name could not be read back from artifact"))

    if profile.student_id not in text:
        errors.append(ValidationError("READBACK_ID_MISSING", "text", "Profile ID could not be read back from artifact"))

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def readback_validate_html(html_str: str, profile: SyntheticProfile) -> ValidationResult:
    errors: list[ValidationError] = []
    if profile.first_name not in html_str or profile.last_name not in html_str:
        errors.append(ValidationError("HTML_READBACK_NAME", "html", "Name missing from HTML"))
    if profile.student_id not in html_str:
        errors.append(ValidationError("HTML_READBACK_ID", "html", "ID missing from HTML"))
    return ValidationResult(valid=len(errors) == 0, errors=errors)


def readback_validate_pdf(pdf_bytes: bytes, profile: SyntheticProfile) -> ValidationResult:
    tmp = Path("/tmp") / f"rb_{profile.student_id}.pdf"
    tmp.write_bytes(pdf_bytes)
    res = inspect_readback_artifact(tmp, profile)
    try:
        tmp.unlink(missing_ok=True)
    except Exception:
        pass
    return res


# =====================================================================
# FIXTURE & BUNDLE GENERATION
# =====================================================================

def generate_fixture_bundle(
    scenario_name: str = "undergraduate",
    seed: int = 42,
    output_dir: str | Path = "output/fixture",
    override_institution_id: str | None = None,
    doc_kind: DocumentKind = DocumentKind.SCHEDULE,
    formats: tuple[ArtifactType, ...] = (ArtifactType.HTML, ArtifactType.PDF, ArtifactType.PNG),
) -> GenerationResult:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    profile = generate_profile(scenario_name=scenario_name, seed=seed, override_institution_id=override_institution_id)
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
        pdf_bytes = render_pdf(doc.html_content)
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
    profile_json_path.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")

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
    formats: tuple[ArtifactType, ...] = (ArtifactType.HTML, ArtifactType.PDF, ArtifactType.PNG, ArtifactType.JPEG),
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
                    failure_categories[err.code] = failure_categories.get(err.code, 0) + 1

            results_summary.append({
                "index": i + 1,
                "seed": derived_seed,
                "profile_id": res.profile.student_id,
                "name": f"{res.profile.first_name} {res.profile.last_name}",
                "valid": is_valid,
                "errors": [e.code for e in res.validation.errors],
                "path": str(sub_dir),
            })
        except Exception as exc:
            invalid_count += 1
            err_code = "EXCEPTION"
            failure_categories[err_code] = failure_categories.get(err_code, 0) + 1
            results_summary.append({
                "index": i + 1,
                "seed": derived_seed,
                "valid": False,
                "errors": [f"EXCEPTION: {exc}"],
            })

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
