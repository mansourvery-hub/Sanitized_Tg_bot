"""SheerID Academic Institution Directory and Organization Resolver.

Provides structured SheerID organization metadata and domain resolution for target
institutions: Penn State (PSU), UCLA, NYU, University of Michigan (UMich), and
The University of Texas at Austin (UT Austin).
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from typing import Any

# Canonical SheerID Organization Metadata for Supported Institutions
TARGET_INSTITUTION_SCHOOLS: dict[str, dict[str, Any]] = {
    # Penn State University - Main Campus
    "2565": {
        "id": 2565,
        "idExtended": "2565",
        "name": "Pennsylvania State University-Main Campus",
        "city": "University Park",
        "state": "PA",
        "country": "US",
        "type": "UNIVERSITY",
        "domain": "PSU.EDU",
        "inst_id": "psu",
    },
    # University of California, Los Angeles (UCLA)
    "285": {
        "id": 285,
        "idExtended": "285",
        "name": "University of California-Los Angeles",
        "city": "Los Angeles",
        "state": "CA",
        "country": "US",
        "type": "UNIVERSITY",
        "domain": "UCLA.EDU",
        "inst_id": "ucla",
    },
    # New York University (NYU)
    "2678": {
        "id": 2678,
        "idExtended": "2678",
        "name": "New York University",
        "city": "New York",
        "state": "NY",
        "country": "US",
        "type": "UNIVERSITY",
        "domain": "NYU.EDU",
        "inst_id": "nyu",
    },
    # University of Michigan - Ann Arbor
    "2027": {
        "id": 2027,
        "idExtended": "2027",
        "name": "University of Michigan-Ann Arbor",
        "city": "Ann Arbor",
        "state": "MI",
        "country": "US",
        "type": "UNIVERSITY",
        "domain": "UMICH.EDU",
        "inst_id": "umich",
    },
    # The University of Texas at Austin (UT Austin)
    "3895": {
        "id": 3895,
        "idExtended": "3895",
        "name": "The University of Texas at Austin",
        "city": "Austin",
        "state": "TX",
        "country": "US",
        "type": "UNIVERSITY",
        "domain": "UTEXAS.EDU",
        "inst_id": "ut_austin",
    },
    # University of the Philippines Diliman (UP Diliman)
    "355870": {
        "id": 355870,
        "idExtended": "355870",
        "name": "University of the Philippines Diliman",
        "city": "Quezon City",
        "state": "NCR",
        "country": "PH",
        "type": "UNIVERSITY",
        "domain": "UP.EDU.PH",
        "inst_id": "up_diliman",
    },
    # Universidade de São Paulo (USP)
    "10042652": {
        "id": 10042652,
        "idExtended": "10042652",
        "name": "Universidade de São Paulo",
        "city": "São Paulo",
        "state": "SP",
        "country": "BR",
        "type": "UNIVERSITY",
        "domain": "USP.BR",
        "inst_id": "usp",
    },
    # Universiti Malaya
    "355254": {
        "id": 355254,
        "idExtended": "355254",
        "name": "Universiti Malaya",
        "city": "Kuala Lumpur",
        "state": "KUL",
        "country": "MY",
        "type": "UNIVERSITY",
        "domain": "UM.EDU.MY",
        "inst_id": "universiti_malaya",
    },
    # Makerere University
    "662864": {
        "id": 662864,
        "idExtended": "662864",
        "name": "Makerere University",
        "city": "Kampala",
        "state": "Central",
        "country": "UG",
        "type": "UNIVERSITY",
        "domain": "MAK.AC.UG",
        "inst_id": "makerere",
    },
    # University of Lagos (UNILAG)
    "660895": {
        "id": 660895,
        "idExtended": "660895",
        "name": "University of Lagos",
        "city": "Lagos",
        "state": "Lagos",
        "country": "NG",
        "type": "UNIVERSITY",
        "domain": "UNILAG.EDU.NG",
        "inst_id": "unilag",
    },
}

# Alias resolution mapping to canonical SheerID numeric IDs
SCHOOL_ALIASES: dict[str, str] = {
    "psu": "2565",
    "penn_state": "2565",
    "pennstate": "2565",
    "penn": "2565",
    "2565": "2565",
    "ucla": "285",
    "uc_la": "285",
    "los_angeles": "285",
    "285": "285",
    "nyu": "2678",
    "new_york_university": "2678",
    "2678": "2678",
    "umich": "2027",
    "michigan": "2027",
    "u_mich": "2027",
    "2027": "2027",
    "ut_austin": "3895",
    "utaustin": "3895",
    "ut": "3895",
    "austin": "3895",
    "texas": "3895",
    "3895": "3895",
    # UP Diliman Aliases
    "up_diliman": "355870",
    "upd": "355870",
    "up": "355870",
    "diliman": "355870",
    "355870": "355870",
    # USP Aliases
    "usp": "10042652",
    "sao_paulo": "10042652",
    "saopaulo": "10042652",
    "10042652": "10042652",
    # Universiti Malaya Aliases
    "universiti_malaya": "355254",
    "um": "355254",
    "malaya": "355254",
    "355254": "355254",
    # Makerere Aliases
    "makerere": "662864",
    "mak": "662864",
    "makerere_university": "662864",
    "662864": "662864",
    # UNILAG Aliases
    "unilag": "660895",
    "lagos": "660895",
    "university_of_lagos": "660895",
    "660895": "660895",
}

DEFAULT_SCHOOL_ID = "2565"


def resolve_sheerid_school(
    school_input: str | int | None,
    fallback_schools: Mapping[str, dict[str, Any]] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Resolve user-supplied school argument or ID to canonical SheerID school structure.

    Args:
        school_input: School slug, numeric ID, or name (e.g. 'ucla', '285', 2678, 'psu').
        fallback_schools: Optional legacy dict (e.g. regional PSU campuses) to fall back on.

    Returns:
        tuple[str, dict]: (canonical_id_str, school_metadata_dict)
    """
    if school_input is None or str(school_input).strip() == "":
        return DEFAULT_SCHOOL_ID, TARGET_INSTITUTION_SCHOOLS[DEFAULT_SCHOOL_ID]

    raw_key = str(school_input).strip().lower().replace("-", "_")

    # 1. Check direct alias
    if raw_key in SCHOOL_ALIASES:
        canonical_id = SCHOOL_ALIASES[raw_key]
        return canonical_id, TARGET_INSTITUTION_SCHOOLS[canonical_id]

    # 2. Check canonical target institutions
    if str(school_input) in TARGET_INSTITUTION_SCHOOLS:
        canonical_id = str(school_input)
        return canonical_id, TARGET_INSTITUTION_SCHOOLS[canonical_id]

    # 3. Check fallback schools dictionary (e.g. regional PSU campuses like 651379, 8387)
    if fallback_schools and str(school_input) in fallback_schools:
        canonical_id = str(school_input)
        entry = dict(fallback_schools[canonical_id])
        if "inst_id" not in entry:
            entry["inst_id"] = "psu"
        return canonical_id, entry

    # 4. Fallback to default (Penn State Main Campus)
    return DEFAULT_SCHOOL_ID, TARGET_INSTITUTION_SCHOOLS[DEFAULT_SCHOOL_ID]


def generate_institutional_student_email(
    first_name: str,
    last_name: str,
    domain: str = "PSU.EDU",
) -> str:
    """Generate a realistic student email for the given institution domain."""
    digit_count = random.choice([3, 4])
    digits = "".join(str(random.randint(0, 9)) for _ in range(digit_count))
    clean_domain = domain.lower().strip()
    return f"{first_name.lower()}.{last_name.lower()}{digits}@{clean_domain}"


def get_available_institutions_summary() -> list[dict[str, str]]:
    """Return a summary list of supported institutions for CLI and Telegram bot help."""
    return [
        {
            "slug": "psu",
            "name": "Penn State University",
            "domain": "psu.edu",
            "sheerid_id": "2565",
        },
        {
            "slug": "ucla",
            "name": "Univ. of California, Los Angeles",
            "domain": "ucla.edu",
            "sheerid_id": "285",
        },
        {
            "slug": "nyu",
            "name": "New York University",
            "domain": "nyu.edu",
            "sheerid_id": "2678",
        },
        {
            "slug": "umich",
            "name": "University of Michigan",
            "domain": "umich.edu",
            "sheerid_id": "2027",
        },
        {
            "slug": "ut_austin",
            "name": "Univ. of Texas at Austin",
            "domain": "utexas.edu",
            "sheerid_id": "3895",
        },
        {
            "slug": "up_diliman",
            "name": "Univ. of the Philippines Diliman",
            "domain": "up.edu.ph",
            "sheerid_id": "355870",
        },
        {
            "slug": "usp",
            "name": "Universidade de São Paulo",
            "domain": "usp.br",
            "sheerid_id": "10042652",
        },
        {
            "slug": "universiti_malaya",
            "name": "Universiti Malaya",
            "domain": "um.edu.my",
            "sheerid_id": "355254",
        },
        {
            "slug": "makerere",
            "name": "Makerere University",
            "domain": "mak.ac.ug",
            "sheerid_id": "662864",
        },
        {
            "slug": "unilag",
            "name": "University of Lagos",
            "domain": "unilag.edu.ng",
            "sheerid_id": "660895",
        },
    ]
