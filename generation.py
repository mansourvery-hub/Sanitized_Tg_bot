"""
Unified Generation Engine for Sanitized Local Identity & Document Framework.

Provides canonical synthetic profile generation, constraint satisfaction, document
projections, HTML/PDF/PNG rendering, deterministic seeds, artifact validation,
read-back testing, fixture generation, and batch generation.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any

GENERATOR_VERSION = "1.0.0"


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
    FACULTY_SUMMARY = "faculty_summary"
    ENROLLMENT_CERTIFICATE = "enrollment_certificate"


class ArtifactType(str, Enum):
    HTML = "html"
    PDF = "pdf"
    PNG = "png"
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


# Alias for backwards compatibility / canonical specification
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
class ScenarioConfig:
    name: str
    description: str
    role: PersonRole
    academic_level: AcademicLevel
    min_age: int
    max_age: int
    program_duration_years: tuple[int, ...]
    institution_id: str | None = None


@dataclass
class GenerationReport:
    profile_valid: bool
    documents_generated: int
    documents_validated: int
    artifacts_validated: int
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    seed: int = 0
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
    """Return list of available scenario names."""
    return list(SCENARIOS.keys())


def get_scenario(name: str) -> ScenarioConfig:
    """Retrieve scenario configuration by name."""
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario '{name}'. Available: {list_scenarios()}")
    return SCENARIOS[name]


# =====================================================================
# SEEDED NAME GENERATOR
# =====================================================================

class SeededNameGenerator:
    """Deterministic English Name Generator supporting seeded Random instances."""

    ROOTS = {
        "prefixes": ["Al", "Bri", "Car", "Dan", "El", "Fer", "Gar", "Har", "Jes", "Kar",
                    "Lar", "Mar", "Nor", "Par", "Quin", "Ros", "Sar", "Tar", "Val", "Wil"],
        "middles": ["an", "en", "in", "on", "ar", "er", "or", "ur", "al", "el",
                   "il", "ol", "am", "em", "im", "om", "ay", "ey", "oy", "ian"],
        "suffixes": ["ton", "son", "man", "ley", "field", "ford", "wood", "stone", "worth", "berg",
                    "stein", "bach", "heim", "gard", "land", "wick", "shire", "dale", "brook", "ridge"],
        "name_roots": ["Alex", "Bern", "Crist", "Dav", "Edw", "Fred", "Greg", "Henr", "Ivan", "John",
                      "Ken", "Leon", "Mich", "Nick", "Oliv", "Paul", "Rich", "Step", "Thom", "Will"],
        "name_endings": ["a", "e", "i", "o", "y", "ie", "ey", "an", "en", "in",
                        "on", "er", "ar", "or", "el", "al", "iel", "ael", "ine", "lyn"],
    }

    PATTERNS = {
        "first_name": [
            ["prefix", "ending"],
            ["name_root", "ending"],
            ["prefix", "middle", "ending"],
            ["name_root", "middle", "ending"],
        ],
        "last_name": [
            ["prefix", "suffix"],
            ["name_root", "suffix"],
            ["prefix", "middle", "suffix"],
        ],
    }

    def __init__(self, rng: random.Random):
        self.rng = rng

    def _generate_component(self, pattern: list[str]) -> str:
        components = []
        for part in pattern:
            if part == "prefix":
                components.append(self.rng.choice(self.ROOTS["prefixes"]))
            elif part == "middle":
                components.append(self.rng.choice(self.ROOTS["middles"]))
            elif part == "suffix":
                components.append(self.rng.choice(self.ROOTS["suffixes"]))
            elif part == "name_root":
                components.append(self.rng.choice(self.ROOTS["name_roots"]))
            elif part == "ending":
                components.append(self.rng.choice(self.ROOTS["name_endings"]))
        return "".join(components).capitalize()

    def generate_name(self) -> tuple[str, str]:
        first_pat = self.rng.choice(self.PATTERNS["first_name"])
        last_pat = self.rng.choice(self.PATTERNS["last_name"])
        first_name = self._generate_component(first_pat)
        last_name = self._generate_component(last_pat)
        return first_name, last_name


# =====================================================================
# PROFILE GENERATION WITH CONSTRAINT SATISFACTION
# =====================================================================

def generate_profile(
    scenario_name: str = "undergraduate",
    seed: int | None = None,
    override_institution_id: str | None = None,
) -> SyntheticProfile:
    """
    Generate a SyntheticProfile satisfying all domain invariants and constraints.
    Deterministic when seed is provided.
    """
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario '{scenario_name}'. Options: {list(SCENARIOS.keys())}")

    scen = SCENARIOS[scenario_name]
    actual_seed = seed if seed is not None else random.randint(10000, 999999)
    rng = random.Random(actual_seed)

    # Name generation
    name_gen = SeededNameGenerator(rng)
    first_name, last_name = name_gen.generate_name()

    # Institution
    inst_id = override_institution_id or scen.institution_id or "psu"
    institution = INSTITUTIONS.get(inst_id, INSTITUTIONS["psu"])

    # Program selection
    program = rng.choice(institution.programs)

    # Date constraints calculation
    # Reference current date for scenario calculation
    ref_date = date(2025, 9, 1)

    # Age constraint
    age_years = rng.randint(scen.min_age, scen.max_age)
    birth_year = ref_date.year - age_years
    birth_month = rng.randint(1, 12)
    birth_day = rng.randint(1, 28)
    date_of_birth = date(birth_year, birth_month, birth_day)

    # Role specific enrollment/hire calculations
    duration_years = rng.choice(scen.program_duration_years)

    if scen.role in (PersonRole.TEACHER, PersonRole.FACULTY):
        # Hire date when age was at least 22
        hire_age = rng.randint(22, min(age_years, 35))
        hire_year = birth_year + hire_age
        enrollment_date = date(hire_year, 8, 20)
        expected_graduation = date(hire_year + 30, 6, 30)  # Extended tenure horizon
        academic_year = f"{ref_date.year}-{ref_date.year + 1} Academic Year"
        student_id = f"E-{rng.randint(1000000, 9999999)}"
        email = f"{first_name.lower()}.{last_name.lower()}@{institution.domain}"
    else:
        if scenario_name == "recent-enrollment":
            start_year = ref_date.year
        elif scenario_name == "near-graduation":
            start_year = ref_date.year - (duration_years - 1)
        else:
            elapsed = rng.randint(0, duration_years - 1)
            start_year = ref_date.year - elapsed

        enrollment_date = date(start_year, 8, 25)
        grad_year = start_year + duration_years
        expected_graduation = date(grad_year, 5, 15)

        current_study_year = (ref_date.year - start_year) + 1
        year_terms = {1: "Freshman", 2: "Sophomore", 3: "Junior", 4: "Senior"}
        academic_year = f"Fall {ref_date.year} ({year_terms.get(current_study_year, 'Enrolled')})"

        # ID and Email formatting
        digits = "".join([str(rng.randint(0, 9)) for _ in range(rng.choice([3, 4]))])
        student_id = f"9{rng.randint(10000000, 99999999)}"
        email = f"{first_name.lower()}.{last_name.lower()}{digits}@{institution.domain}"

    profile = SyntheticProfile(
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

    return profile


# =====================================================================
# DOCUMENT GENERATION PROJECTIONS
# =====================================================================

def generate_document(
    profile: SyntheticProfile,
    doc_kind: DocumentKind | None = None,
) -> Document:
    """
    Project a canonical profile into a Document object with fields & HTML content.
    """
    if doc_kind is None:
        if profile.role in (PersonRole.TEACHER, PersonRole.FACULTY):
            doc_kind = DocumentKind.FACULTY_SUMMARY
        else:
            doc_kind = DocumentKind.SCHEDULE

    if doc_kind == DocumentKind.SCHEDULE:
        title = f"{profile.institution_name} - Student Home & Schedule"
        fields = {
            "Student Name": f"{profile.first_name} {profile.last_name}",
            "PSU ID": profile.student_id,
            "Academic Program": profile.program,
            "Enrollment Status": "Enrolled",
            "Term": profile.academic_year,
            "Email": profile.email,
            "Institution": profile.institution_name,
        }
        html_content = _render_schedule_html(profile, fields)

    elif doc_kind == DocumentKind.FACULTY_SUMMARY:
        title = f"{profile.institution_name} - Employee Access Center"
        fields = {
            "Employee Name": f"{profile.first_name} {profile.last_name}",
            "Employee ID": profile.student_id,
            "Department/Assignment": profile.program,
            "Status": "Active Employee",
            "Hire Date": profile.enrollment_date.strftime("%m/%d/%Y"),
            "Email": profile.email,
            "District": profile.institution_name,
        }
        html_content = _render_faculty_html(profile, fields)

    elif doc_kind == DocumentKind.ENROLLMENT_CERTIFICATE:
        title = f"{profile.institution_name} - Official Verification Summary"
        fields = {
            "Student Name": f"{profile.first_name} {profile.last_name}",
            "ID Number": profile.student_id,
            "Program": profile.program,
            "Level": profile.academic_level.value.capitalize(),
            "Enrollment Date": profile.enrollment_date.strftime("%m/%d/%Y"),
            "Expected Graduation": profile.expected_graduation.strftime("%m/%d/%Y"),
            "Verification Status": "Confirmed Active",
        }
        html_content = _render_certificate_html(profile, fields)
    else:
        raise ValueError(f"Unsupported document kind '{doc_kind}'")

    return Document(
        kind=doc_kind,
        title=title,
        profile=profile,
        fields=fields,
        html_content=html_content,
    )


def _render_schedule_html(profile: SyntheticProfile, fields: dict[str, str]) -> str:
    name = f"{profile.first_name} {profile.last_name}"
    psu_id = profile.student_id
    major = profile.program
    retrieved_time = datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LionPATH - Student Home</title>
    <style>
        :root {{
            --psu-blue: #1E407C;
            --psu-light-blue: #96BEE6;
            --bg-gray: #f4f4f4;
            --text-color: #333;
        }}
        body {{
            font-family: "Segoe UI", Arial, sans-serif;
            background-color: #e0e0e0;
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .viewport {{
            max-width: 1000px;
            margin: 0 auto;
            background: #fff;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            border-radius: 4px;
            overflow: hidden;
        }}
        .header {{
            background-color: var(--psu-blue);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .brand {{
            font-size: 20px;
            font-weight: bold;
        }}
        .content {{
            padding: 25px;
        }}
        .student-card {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 20px;
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .info-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            font-weight: bold;
        }}
        .info-val {{
            font-size: 16px;
            font-weight: 600;
            color: #1E407C;
        }}
        .schedule-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .schedule-table th, .schedule-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .schedule-table th {{
            background: #f1f3f5;
            font-weight: bold;
        }}
    </style>
</head>
<body>
<div class="viewport">
    <div class="header">
        <div class="brand">{profile.institution_name} - LionPATH</div>
        <div>Welcome, <strong>{name}</strong></div>
    </div>
    <div class="content">
        <h2>My Class Schedule</h2>
        <div class="student-card">
            <div>
                <div class="info-label">Student Name</div>
                <div class="info-val">{name}</div>
            </div>
            <div>
                <div class="info-label">Student ID</div>
                <div class="info-val">{psu_id}</div>
            </div>
            <div>
                <div class="info-label">Academic Program</div>
                <div class="info-val">{major}</div>
            </div>
            <div>
                <div class="info-label">Email</div>
                <div class="info-val">{profile.email}</div>
            </div>
        </div>
        <div style="font-size: 12px; color: #666; text-align: right; margin-bottom: 10px;">
            Data retrieved: {retrieved_time}
        </div>
        <table class="schedule-table">
            <thead>
                <tr>
                    <th>Class Nbr</th>
                    <th>Course</th>
                    <th>Title</th>
                    <th>Days & Times</th>
                    <th>Units</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>14920</td>
                    <td>CMPSC 465</td>
                    <td>Data Structures & Algorithms</td>
                    <td>MoWeFr 10:10AM - 11:00AM</td>
                    <td>3.00</td>
                </tr>
                <tr>
                    <td>18233</td>
                    <td>MATH 230</td>
                    <td>Calculus and Vector Analysis</td>
                    <td>TuTh 01:35PM - 02:50PM</td>
                    <td>4.00</td>
                </tr>
            </tbody>
        </table>
    </div>
</div>
</body>
</html>"""


def _render_faculty_html(profile: SyntheticProfile, fields: dict[str, str]) -> str:
    name = f"{profile.first_name} {profile.last_name}"
    emp_id = profile.student_id
    hire_date = profile.enrollment_date.strftime("%m/%d/%Y")
    current_date = datetime.now().strftime("%m/%d/%Y %I:%M %p")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Employee Access Center - Job Summary</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background-color: #e9ecef;
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .browser-mockup {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border-radius: 4px;
            overflow: hidden;
        }}
        .system-header {{
            background: #0056b3;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .district-name {{
            font-size: 18px;
            font-weight: bold;
        }}
        .content {{
            padding: 25px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 20px;
            border-radius: 4px;
        }}
        .label {{ font-size: 12px; color: #666; font-weight: bold; }}
        .value {{ font-size: 15px; font-weight: 600; color: #0056b3; }}
    </style>
</head>
<body>
<div class="browser-mockup">
    <div class="system-header">
        <div class="district-name">{profile.institution_name} - Employee Access Center</div>
        <div>Welcome, {name}</div>
    </div>
    <div class="content">
        <h2>Job Summary & Employee Verification</h2>
        <div class="info-grid">
            <div>
                <div class="label">Employee Name</div>
                <div class="value">{name}</div>
            </div>
            <div>
                <div class="label">Employee ID</div>
                <div class="value">{emp_id}</div>
            </div>
            <div>
                <div class="label">Assignment / Department</div>
                <div class="value">{profile.program}</div>
            </div>
            <div>
                <div class="label">Hire Date</div>
                <div class="value">{hire_date}</div>
            </div>
            <div>
                <div class="label">Official Email</div>
                <div class="value">{profile.email}</div>
            </div>
            <div>
                <div class="label">Status</div>
                <div class="value">Active Full-Time Faculty</div>
            </div>
        </div>
        <p style="font-size: 11px; color: #888; margin-top: 20px;">
            Generated on <span id="currentDate">{current_date}</span>. Official document for internal reference.
        </p>
    </div>
</div>
</body>
</html>"""


def _render_certificate_html(profile: SyntheticProfile, fields: dict[str, str]) -> str:
    name = f"{profile.first_name} {profile.last_name}"
    issue_date = datetime.now().strftime("%B %d, %Y")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Official Enrollment Verification</title>
    <style>
        body {{
            font-family: 'Georgia', serif;
            background: #fdfdfd;
            padding: 40px;
            color: #222;
        }}
        .certificate {{
            max-width: 800px;
            margin: 0 auto;
            border: 3px double #1E407C;
            padding: 40px;
            background: white;
        }}
        h1 {{
            text-align: center;
            color: #1E407C;
            margin-bottom: 5px;
        }}
        h3 {{
            text-align: center;
            color: #555;
            font-weight: normal;
            margin-top: 0;
            border-bottom: 1px solid #ccc;
            padding-bottom: 15px;
        }}
        .details {{
            margin-top: 30px;
            line-height: 1.8;
            font-size: 16px;
        }}
        .field-table {{
            width: 100%;
            margin-top: 20px;
            border-collapse: collapse;
        }}
        .field-table td {{
            padding: 8px 12px;
            border-bottom: 1px solid #eee;
        }}
        .field-table td.label {{
            font-weight: bold;
            color: #1E407C;
            width: 35%;
        }}
    </style>
</head>
<body>
<div class="certificate">
    <h1>{profile.institution_name}</h1>
    <h3>Office of the University Registrar - Verification Summary</h3>
    
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
                <td>{profile.academic_level.value.capitalize()}</td>
            </tr>
            <tr>
                <td class="label">Initial Enrollment Date</td>
                <td>{profile.enrollment_date.strftime("%B %d, %Y")}</td>
            </tr>
            <tr>
                <td class="label">Expected Graduation</td>
                <td>{profile.expected_graduation.strftime("%B %d, %Y")}</td>
            </tr>
            <tr>
                <td class="label">Institutional Email</td>
                <td>{profile.email}</td>
            </tr>
        </table>
        
        <p style="margin-top: 40px; font-size: 13px; color: #666; text-align: right;">
            Issued on {issue_date}
        </p>
    </div>
</div>
</body>
</html>"""


# =====================================================================
# RENDERING ENGINE (HTML, PDF, PNG)
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

    # Fallback ReportLab basic PDF generator
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        output = BytesIO()
        c = canvas.Canvas(output, pagesize=letter)
        c.drawString(100, 750, "Document Summary")
        # Extract text simple lines
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


def render_png(html_content: str, width: int = 1000, height: int = 800) -> bytes:
    """
    Render HTML string to PNG bytes using Playwright if present, or PIL fallback image.
    """
    # Try Playwright
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

    # Pure Python PIL Fallback
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (width, height), color=(245, 247, 250))
        draw = ImageDraw.Draw(img)
        
        # Simple header rectangle
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


# =====================================================================
# VALIDATION LAYER & READ-BACK INSPECTION
# =====================================================================

def validate_profile(profile: SyntheticProfile) -> ValidationResult:
    """Validate profile fields, date invariants, age limits, and format rules."""
    errors: list[ValidationError] = []
    warnings: list[str] = []

    # DOB vs Enrollment invariant
    if profile.enrollment_date <= profile.date_of_birth:
        errors.append(ValidationError("DATE_ORDER", "enrollment_date", "Enrollment date must be after birth date"))

    # Enrollment vs Expected Graduation invariant
    if profile.expected_graduation <= profile.enrollment_date:
        errors.append(ValidationError("DATE_ORDER", "expected_graduation", "Expected graduation must be after enrollment date"))

    # Age check
    age = (profile.enrollment_date - profile.date_of_birth).days // 365
    if profile.role in (PersonRole.STUDENT,) and age < 16:
        errors.append(ValidationError("AGE_TOO_YOUNG", "date_of_birth", f"Student age at enrollment ({age}) is unusually young"))
    elif profile.role in (PersonRole.TEACHER, PersonRole.FACULTY) and age < 20:
        errors.append(ValidationError("AGE_TOO_YOUNG", "date_of_birth", f"Faculty age at hire ({age}) is invalid"))

    # Email format check
    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_pattern, profile.email):
        errors.append(ValidationError("EMAIL_FORMAT", "email", f"Email '{profile.email}' is invalid"))

    # Student ID format check
    if not profile.student_id or len(profile.student_id) < 3:
        errors.append(ValidationError("ID_FORMAT", "student_id", "ID number is missing or too short"))

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_document(doc: Document) -> ValidationResult:
    """Validate logical document completeness and coherence with profile."""
    errors: list[ValidationError] = []
    warnings: list[str] = []

    if not doc.fields:
        errors.append(ValidationError("EMPTY_FIELDS", "fields", "Document fields are empty"))

    if not doc.html_content or len(doc.html_content) < 50:
        errors.append(ValidationError("EMPTY_HTML", "html_content", "Rendered HTML content is missing or trivial"))

    # Verify key profile values are present in fields
    full_name = f"{doc.profile.first_name} {doc.profile.last_name}"
    field_text = " ".join(doc.fields.values())

    if doc.profile.first_name not in field_text or doc.profile.last_name not in field_text:
        errors.append(ValidationError("FIELD_MISMATCH", "fields", "Profile name missing from document fields"))

    if doc.profile.student_id not in field_text:
        errors.append(ValidationError("FIELD_MISMATCH", "student_id", "Profile ID missing from document fields"))

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_artifact(artifact_path: str | Path, expected_type: ArtifactType) -> ValidationResult:
    """Validate artifact file existence, non-zero size, format header, and structure."""
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

    content = path.read_bytes()

    if expected_type == ArtifactType.PDF:
        if not content.startswith(b"%PDF"):
            errors.append(ValidationError("BAD_MAGIC_HEADER", "header", "PDF file missing %PDF header"))
    elif expected_type == ArtifactType.PNG:
        if not content.startswith(b"\x89PNG"):
            errors.append(ValidationError("BAD_MAGIC_HEADER", "header", "PNG file missing \\x89PNG header"))
    elif expected_type == ArtifactType.HTML or path.suffix == ".html":
        text = content.decode("utf-8", errors="ignore")
        if "<html" not in text.lower() and "<!doctype" not in text.lower():
            errors.append(ValidationError("BAD_HTML_STRUCTURE", "structure", "HTML file missing html/doctype tag"))
    elif expected_type == ArtifactType.JSON:
        try:
            json.loads(content.decode("utf-8"))
        except Exception as exc:
            errors.append(ValidationError("BAD_JSON", "json", f"Invalid JSON artifact: {exc}"))

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def readback_validate_html(html_str: str, profile: SyntheticProfile) -> ValidationResult:
    """Validate that HTML content contains expected profile fields."""
    errors: list[ValidationError] = []
    warnings: list[str] = []

    if profile.first_name not in html_str:
        errors.append(ValidationError("READBACK_MISSING_FIRSTNAME", "first_name", f"First name '{profile.first_name}' not found in HTML"))
    if profile.last_name not in html_str:
        errors.append(ValidationError("READBACK_MISSING_LASTNAME", "last_name", f"Last name '{profile.last_name}' not found in HTML"))
    if profile.student_id not in html_str:
        errors.append(ValidationError("READBACK_MISSING_STUDENT_ID", "student_id", f"Student/Employee ID '{profile.student_id}' not found in HTML"))

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def readback_validate_pdf(pdf_bytes: bytes, profile: SyntheticProfile) -> ValidationResult:
    """Validate that PDF bytes contain expected profile fields or valid PDF structure."""
    errors: list[ValidationError] = []
    warnings: list[str] = []

    if not pdf_bytes.startswith(b"%PDF-"):
        errors.append(ValidationError("INVALID_PDF_HEADER", "pdf", "PDF data missing %PDF- header"))
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    raw_text = pdf_bytes.decode("latin-1", errors="ignore")
    # In uncompressed or simple PDF, text strings appear in plain latin-1
    if profile.first_name not in raw_text and profile.last_name not in raw_text:
        warnings.append("PDF text readback check could not verify uncompressed name stream directly")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def inspect_readback_artifact(
    artifact_path: str | Path,
    profile: SyntheticProfile,
) -> ValidationResult:
    """
    Read back generated artifact from disk and compare contents against expected profile.
    Catch missing names, broken interpolation, and formatting errors.
    """
    path = Path(artifact_path)
    if path.suffix == ".html" or path.suffix == ".json" or path.name.endswith(".json"):
        art_type = ArtifactType.JSON if path.suffix == ".json" or path.name.endswith(".json") else ArtifactType.HTML
    elif path.suffix == ".pdf":
        art_type = ArtifactType.PDF
    elif path.suffix == ".png":
        art_type = ArtifactType.PNG
    else:
        art_type = ArtifactType.JSON

    val = validate_artifact(path, art_type)
    if not val.valid:
        return val

    errors: list[ValidationError] = []
    warnings: list[str] = []

    if path.suffix in (".html", ".json"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if profile.first_name not in text:
            errors.append(ValidationError("READBACK_MISSING_FIRSTNAME", "first_name", f"First name '{profile.first_name}' not found in artifact text"))
        if profile.last_name not in text:
            errors.append(ValidationError("READBACK_MISSING_LASTNAME", "last_name", f"Last name '{profile.last_name}' not found in artifact text"))
        if profile.student_id not in text:
            errors.append(ValidationError("READBACK_MISSING_ID", "student_id", f"ID '{profile.student_id}' not found in artifact text"))
    elif path.suffix == ".pdf":
        content = path.read_bytes()
        # Search PDF stream or text strings
        text = content.decode("latin-1", errors="ignore")
        if profile.last_name not in text and profile.first_name not in text:
            warnings.append("PDF text readback check could not verify uncompressed name stream directly")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


# =====================================================================
# FIXTURE & BATCH GENERATOR ORCHESTRATION
# =====================================================================

def generate_fixture_bundle(
    scenario_name: str = "undergraduate",
    seed: int = 12345,
    output_dir: str | Path | None = None,
    formats: tuple[ArtifactType, ...] = (ArtifactType.HTML, ArtifactType.PDF, ArtifactType.PNG),
    override_institution_id: str | None = None,
) -> GenerationResult:
    """
    Generate an isolated local fixture folder containing profile.json, document.html, pdf, png, and report.json.
    """
    if output_dir is None:
        target_dir = Path("output") / f"fixture-{scenario_name}-{seed}"
    else:
        target_dir = Path(output_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate Profile
    profile = generate_profile(scenario_name=scenario_name, seed=seed, override_institution_id=override_institution_id)
    profile_val = validate_profile(profile)

    # 2. Generate Document
    doc = generate_document(profile)
    doc_val = validate_document(doc)

    artifacts: list[GeneratedArtifact] = []

    # Write profile.json
    prof_path = target_dir / "profile.json"
    prof_bytes = json.dumps(profile.to_dict(), indent=2).encode("utf-8")
    prof_path.write_bytes(prof_bytes)
    artifacts.append(
        GeneratedArtifact(
            kind=doc.kind,
            path=str(prof_path),
            byte_size=len(prof_bytes),
            sha256=hashlib.sha256(prof_bytes).hexdigest(),
            artifact_type=ArtifactType.JSON,
        )
    )

    # Write HTML if requested
    if ArtifactType.HTML in formats:
        html_path = target_dir / "document.html"
        html_bytes = doc.html_content.encode("utf-8")
        html_path.write_bytes(html_bytes)
        artifacts.append(
            GeneratedArtifact(
                kind=doc.kind,
                path=str(html_path),
                byte_size=len(html_bytes),
                sha256=hashlib.sha256(html_bytes).hexdigest(),
                artifact_type=ArtifactType.HTML,
            )
        )

    # Write PDF if requested
    if ArtifactType.PDF in formats:
        pdf_path = target_dir / "document.pdf"
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

    # Write PNG if requested
    if ArtifactType.PNG in formats:
        png_path = target_dir / "document.png"
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

    # Validate artifacts
    all_errors = list(profile_val.errors) + list(doc_val.errors)
    all_warnings = list(profile_val.warnings) + list(doc_val.warnings)

    validated_artifacts = 0
    for art in artifacts:
        art_val = validate_artifact(art.path, art.artifact_type)
        if art_val.valid:
            validated_artifacts += 1
        else:
            all_errors.extend(art_val.errors)

        # Read-back test
        rb_val = inspect_readback_artifact(art.path, profile)
        if not rb_val.valid:
            all_errors.extend(rb_val.errors)

    overall_valid = len(all_errors) == 0

    report = GenerationReport(
        profile_valid=profile_val.valid,
        documents_generated=1,
        documents_validated=1 if doc_val.valid else 0,
        artifacts_validated=validated_artifacts,
        errors=all_errors,
        warnings=all_warnings,
        seed=seed,
        scenario=scenario_name,
        generator_version=GENERATOR_VERSION,
    )

    result = GenerationResult(
        profile=profile,
        document=doc,
        artifacts=artifacts,
        validation=ValidationResult(valid=overall_valid, errors=all_errors, warnings=all_warnings),
        report=report,
        seed=seed,
        scenario=scenario_name,
        generator_version=GENERATOR_VERSION,
    )

    # Write report.json
    report_path = target_dir / "report.json"
    report_bytes = json.dumps(result.to_dict(), indent=2).encode("utf-8")
    report_path.write_bytes(report_bytes)

    return result


def generate_batch(
    scenario_name: str = "undergraduate",
    count: int = 10,
    base_seed: int = 1000,
    output_dir: str | Path | None = None,
    override_institution_id: str | None = None,
) -> dict[str, Any]:
    """
    Generate a batch of synthetic fixtures with deterministic derived seeds.
    Tracks success/failure statistics and produces machine-readable summary.
    """
    out_dir = Path(output_dir) if output_dir else Path("output") / f"batch-{scenario_name}-{base_seed}"
    out_dir.mkdir(parents=True, exist_ok=True)

    valid_count = 0
    invalid_count = 0
    failure_categories: dict[str, int] = {}
    results_summary = []

    for i in range(count):
        derived_seed = base_seed + i
        sub_dir = out_dir / f"item-{i+1:04d}-{derived_seed}"

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
        "total_generated": count,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "failure_categories": failure_categories,
        "batch_output_dir": str(out_dir),
        "items": results_summary,
    }

    summary_path = out_dir / "batch_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return summary
