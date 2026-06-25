"""
Section-aware parsing for both resumes and job descriptions.

Splits text into typed sections so downstream modules can:
  - Weight JD "Requirements" at 1.0 but "Benefits" at 0.0
  - Target resume "Experience" for date extraction, "Skills" for skill scanning
  - Enable chunk-level semantic matching between specific section pairs
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ── Section Types ────────────────────────────────────────────────────

JD_SECTION_TYPES = {
    "requirement": 1.0,
    "responsibility": 0.8,
    "nice_to_have": 0.5,
    "fluff": 0.0,
}

RESUME_SECTION_TYPES = {
    "summary", "skills", "experience", "projects",
    "education", "certifications", "other",
}


@dataclass
class Section:
    """A parsed section from a resume or JD."""
    section_type: str
    text: str
    weight: float = 1.0
    start_line: int = 0
    end_line: int = 0


# ── JD Section Patterns ─────────────────────────────────────────────

_JD_SECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("requirement", re.compile(
        r"^\s*(?:requirements?|required\s+(?:skills?|qualifications?|experience)|"
        r"must[\s-]+have|minimum\s+qualifications?|what\s+we(?:'re|\s+are)\s+looking\s+for|"
        r"you(?:'ll|\s+will)\s+need|what\s+you\s+(?:need|bring)|essential\s+(?:skills?|qualifications?)|"
        r"key\s+(?:requirements?|qualifications?)|who\s+you\s+are)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )),
    ("responsibility", re.compile(
        r"^\s*(?:responsibilities|what\s+you(?:'ll|\s+will)\s+do|"
        r"the\s+role|your\s+role|day[\s-]+to[\s-]+day|"
        r"role\s+(?:description|overview)|in\s+this\s+role|"
        r"key\s+responsibilities|job\s+duties|"
        r"what\s+(?:you'll|you\s+will)\s+(?:work\s+on|be\s+doing))\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )),
    ("nice_to_have", re.compile(
        r"^\s*(?:nice[\s-]+to[\s-]+have|bonus(?:es)?|preferred\s+(?:skills?|qualifications?|experience)|"
        r"plus(?:es)?|ideal(?:ly)?|it(?:'s|\s+is)\s+a\s+plus|"
        r"additional\s+(?:skills?|qualifications?)|desired\s+(?:skills?|qualifications?)|"
        r"preferred\s+but\s+not\s+required|we(?:'d|\s+would)\s+love\s+if)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )),
    ("fluff", re.compile(
        r"^\s*(?:about\s+(?:us|the\s+company|the\s+team)|who\s+we\s+are|"
        r"benefits(?:\s+and\s+perks)?|perks|compensation|"
        r"why\s+(?:join|work\s+(?:with|at|for))|our\s+(?:culture|mission|values|story)|"
        r"what\s+we\s+offer|equal\s+opportunity|eeo|"
        r"salary\s+(?:range|band)|pay\s+(?:range|band))\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )),
]

# ── Resume Section Patterns ──────────────────────────────────────────

_RESUME_SECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("summary", re.compile(
        r"^\s*(?:summary|objective|profile|about\s+me|professional\s+summary|"
        r"career\s+(?:summary|objective|profile)|overview)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )),
    ("skills", re.compile(
        r"^\s*(?:skills?|technical\s+skills?|technologies|tech\s+stack|"
        r"core\s+competenc(?:ies|y)|tools?\s*(?:&|and)\s*technologies|"
        r"programming\s+(?:languages?|skills?)|expertise|"
        r"areas?\s+of\s+expertise|proficienc(?:ies|y))\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )),
    ("experience", re.compile(
        r"^\s*(?:experience|work\s+experience|employment(?:\s+history)?|"
        r"professional\s+experience|career\s+history|"
        r"relevant\s+experience|work\s+history)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )),
    ("projects", re.compile(
        r"^\s*(?:projects?|personal\s+projects?|side\s+projects?|"
        r"open\s+source|portfolio|notable\s+projects?|"
        r"selected\s+projects?|key\s+projects?)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )),
    ("education", re.compile(
        r"^\s*(?:education|academic(?:\s+background)?|qualifications?|"
        r"degrees?|schooling|academic\s+credentials?)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )),
    ("certifications", re.compile(
        r"^\s*(?:certifications?|certificates?|licenses?|"
        r"awards?(?:\s*(?:&|and)\s*certifications?)?|"
        r"professional\s+(?:certifications?|development)|"
        r"accreditations?|honors?)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )),
]


# ── Parsing Functions ────────────────────────────────────────────────


def parse_jd_sections(text: str) -> list[Section]:
    """
    Parse a job description into weighted sections.

    If no section headers are detected, the entire text is treated as
    a single 'requirement' section (weight 1.0).
    """
    return _parse_sections(text, _JD_SECTION_PATTERNS, default_type="requirement", is_jd=True)


def parse_resume_sections(text: str) -> list[Section]:
    """
    Parse a resume into typed sections.

    If no section headers are detected, the entire text is treated as
    a single 'other' section.
    """
    return _parse_sections(text, _RESUME_SECTION_PATTERNS, default_type="other", is_jd=False)


def _parse_sections(
    text: str,
    patterns: list[tuple[str, re.Pattern]],
    default_type: str,
    is_jd: bool,
) -> list[Section]:
    """Generic section parser used by both JD and resume parsers."""
    lines = text.split("\n")
    if not lines:
        return [Section(section_type=default_type, text=text, weight=1.0)]

    # Find all section boundaries
    boundaries: list[tuple[int, str]] = []

    for line_idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        for section_type, pattern in patterns:
            if pattern.match(stripped):
                boundaries.append((line_idx, section_type))
                break
        else:
            # Also detect section headers by format:
            # ALL CAPS lines, lines ending with colon, short bold-like lines
            if (len(stripped) < 60
                    and stripped == stripped.upper()
                    and len(stripped.split()) <= 5
                    and stripped.replace(" ", "").isalpha()):
                # ALL CAPS header — try to classify
                classified = _classify_header(stripped, patterns)
                if classified:
                    boundaries.append((line_idx, classified))

    # If no sections found, return entire text as one block
    if not boundaries:
        weight = JD_SECTION_TYPES.get(default_type, 1.0) if is_jd else 1.0
        return [Section(
            section_type=default_type,
            text=text,
            weight=weight,
            start_line=0,
            end_line=len(lines) - 1,
        )]

    # Build sections from boundaries
    sections: list[Section] = []

    # Content before first section header
    if boundaries[0][0] > 0:
        preamble_text = "\n".join(lines[:boundaries[0][0]]).strip()
        if preamble_text:
            preamble_type = "fluff" if is_jd else "summary"
            weight = JD_SECTION_TYPES.get(preamble_type, 0.0) if is_jd else 1.0
            sections.append(Section(
                section_type=preamble_type,
                text=preamble_text,
                weight=weight,
                start_line=0,
                end_line=boundaries[0][0] - 1,
            ))

    # Each section from header to next header (or end)
    for i, (line_idx, section_type) in enumerate(boundaries):
        start = line_idx + 1  # Skip the header line itself
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(lines)

        section_text = "\n".join(lines[start:end]).strip()
        if section_text:
            weight = JD_SECTION_TYPES.get(section_type, 1.0) if is_jd else 1.0
            sections.append(Section(
                section_type=section_type,
                text=section_text,
                weight=weight,
                start_line=start,
                end_line=end - 1,
            ))

    return sections if sections else [Section(
        section_type=default_type,
        text=text,
        weight=JD_SECTION_TYPES.get(default_type, 1.0) if is_jd else 1.0,
    )]


def _classify_header(header: str, patterns: list[tuple[str, re.Pattern]]) -> str | None:
    """Try to classify an ALL CAPS header against known patterns."""
    header_lower = header.lower()
    for section_type, pattern in patterns:
        # Check the pattern against the lowercase version
        if pattern.match(header_lower):
            return section_type
    return None


# ── Helpers ──────────────────────────────────────────────────────────


def get_section_text(sections: list[Section], section_type: str) -> str:
    """Get concatenated text from all sections of a given type."""
    parts = [s.text for s in sections if s.section_type == section_type]
    return "\n\n".join(parts)


def get_weighted_text(sections: list[Section], min_weight: float = 0.0) -> str:
    """Get concatenated text from sections above a weight threshold."""
    parts = [s.text for s in sections if s.weight > min_weight]
    return "\n\n".join(parts)


def has_section_headers(sections: list[Section], default_type: str) -> bool:
    """Check if the parser found any actual section headers (not just the default block)."""
    if len(sections) == 1 and sections[0].section_type == default_type:
        return False
    return len(sections) > 1
