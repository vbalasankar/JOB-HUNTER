"""
Role-specific scorer profiles.

Six archetypes with distinct core skills, weight overrides, and
signal importance distributions. Auto-detects role from JD title.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pipeline.ats.models import RoleDetectionResult


@dataclass
class RoleProfile:
    """Configuration for a role archetype."""
    name: str
    patterns: list[str]
    core_skills: list[str]
    weight_overrides: dict[str, int] = field(default_factory=dict)
    # Signal importance for aggregation (must sum to ~1.0)
    skills_importance: float = 0.30
    experience_importance: float = 0.18
    role_match_importance: float = 0.12
    semantic_importance: float = 0.10
    education_importance: float = 0.08
    impact_importance: float = 0.07
    domain_importance: float = 0.05
    seniority_importance: float = 0.04
    soft_skills_importance: float = 0.03
    leadership_importance: float = 0.03


ROLE_PROFILES: dict[str, RoleProfile] = {
    "backend": RoleProfile(
        name="Backend Engineer",
        patterns=[
            r"\bbackend\b", r"\bback[- ]end\b", r"\bserver[- ]side\b",
            r"\bapi\s+engineer\b", r"\bplatform\s+engineer\b",
            r"\bsystems?\s+engineer\b", r"\binfrastructure\s+engineer\b",
        ],
        core_skills=[
            "python", "go", "java", "rust", "c++",
            "microservices", "rest", "grpc", "graphql",
            "postgresql", "redis", "kafka", "mongodb",
            "docker", "kubernetes", "aws", "distributed systems",
        ],
        weight_overrides={
            "python": 10, "go": 9, "java": 9,
            "microservices": 8, "distributed systems": 9,
            "postgresql": 8, "redis": 7, "kafka": 8,
            "docker": 7, "kubernetes": 8,
        },
        skills_importance=0.35,
        experience_importance=0.20,
    ),
    "frontend": RoleProfile(
        name="Frontend Engineer",
        patterns=[
            r"\bfrontend\b", r"\bfront[- ]end\b", r"\bui\s+engineer\b",
            r"\bux\s+engineer\b", r"\bweb\s+developer\b",
            r"\bfull[- ]stack\b",
        ],
        core_skills=[
            "react", "typescript", "javascript", "css", "html",
            "nextjs", "vue", "angular", "webpack", "vite",
            "figma", "tailwindcss", "nodejs",
        ],
        weight_overrides={
            "react": 10, "typescript": 9, "javascript": 8,
            "css": 7, "nextjs": 8, "html": 5,
        },
        skills_importance=0.40,
        experience_importance=0.15,
    ),
    "data": RoleProfile(
        name="Data Engineer",
        patterns=[
            r"\bdata\s+engineer\b", r"\bdata\s+platform\b",
            r"\banalytics\s+engineer\b", r"\betl\b",
            r"\bdata\s+infrastructure\b",
        ],
        core_skills=[
            "sql", "python", "spark", "airflow", "kafka",
            "dbt", "snowflake", "bigquery", "databricks",
            "data modeling", "etl", "data warehouse",
        ],
        weight_overrides={
            "sql": 10, "spark": 9, "python": 9,
            "airflow": 8, "kafka": 8, "dbt": 7,
            "data modeling": 8,
        },
        skills_importance=0.35,
        experience_importance=0.20,
    ),
    "devops": RoleProfile(
        name="DevOps / SRE",
        patterns=[
            r"\bdevops\b", r"\bsre\b", r"\bsite\s+reliability\b",
            r"\bplatform\s+engineer\b", r"\binfrastructure\b",
            r"\bcloud\s+engineer\b",
        ],
        core_skills=[
            "kubernetes", "terraform", "docker", "ci/cd", "aws",
            "gcp", "azure", "monitoring", "linux", "ansible",
            "prometheus", "grafana",
        ],
        weight_overrides={
            "kubernetes": 10, "terraform": 9, "docker": 8,
            "aws": 9, "ci/cd": 8, "linux": 7,
            "monitoring": 7,
        },
        skills_importance=0.35,
        experience_importance=0.20,
        education_importance=0.05,
    ),
    "ml": RoleProfile(
        name="ML / AI Engineer",
        patterns=[
            r"\bmachine\s+learning\b", r"\bml\s+engineer\b",
            r"\bai\s+engineer\b", r"\bdata\s+scientist\b",
            r"\bdeep\s+learning\b", r"\bnlp\s+engineer\b",
            r"\bcomputer\s+vision\b", r"\bmlops\b",
            r"\bresearch\s+(?:engineer|scientist)\b",
        ],
        core_skills=[
            "pytorch", "tensorflow", "python", "machine learning",
            "deep learning", "statistics", "mlops", "nlp",
            "computer vision", "scikit-learn", "huggingface",
            "llm",
        ],
        weight_overrides={
            "pytorch": 10, "machine learning": 10, "python": 9,
            "deep learning": 9, "statistics": 7, "tensorflow": 8,
        },
        skills_importance=0.35,
        experience_importance=0.15,
        education_importance=0.15,
    ),
    "product": RoleProfile(
        name="Product Manager",
        patterns=[
            r"\bproduct\s+manager\b", r"\bproduct\s+owner\b",
            r"\bprogram\s+manager\b", r"\btechnical\s+pm\b",
            r"\bproduct\s+lead\b",
        ],
        core_skills=[
            "product strategy", "stakeholder management", "analytics",
            "user research", "a/b testing", "roadmap",
            "project management",
        ],
        weight_overrides={
            "product strategy": 10, "stakeholder management": 9,
            "analytics": 8, "user research": 7,
        },
        skills_importance=0.20,
        experience_importance=0.25,
        leadership_importance=0.10,
        soft_skills_importance=0.08,
        impact_importance=0.10,
    ),
}

# Default profile for unrecognized roles
GENERAL_PROFILE = RoleProfile(
    name="General",
    patterns=[],
    core_skills=[],
    weight_overrides={},
)


def detect_role(jd_text: str) -> RoleDetectionResult:
    """
    Auto-detect role archetype from JD title and content.

    Uses the first ~500 chars (typically contains the title and intro)
    for matching.
    """
    search_text = jd_text[:500].lower()

    best_role = "general"
    best_score = 0
    best_patterns: list[str] = []

    for role_name, profile in ROLE_PROFILES.items():
        match_count = 0
        matched: list[str] = []
        for pattern_str in profile.patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            if pattern.search(search_text):
                match_count += 1
                matched.append(pattern_str)

        if match_count > best_score:
            best_score = match_count
            best_role = role_name
            best_patterns = matched

    confidence = min(1.0, best_score * 0.4) if best_score > 0 else 0.0

    return RoleDetectionResult(
        role=best_role,
        confidence=confidence,
        matched_patterns=best_patterns,
    )


def get_role_profile(role: str) -> RoleProfile:
    """Get the role profile for a detected role."""
    return ROLE_PROFILES.get(role, GENERAL_PROFILE)
