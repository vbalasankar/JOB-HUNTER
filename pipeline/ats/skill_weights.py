"""
Dynamic skill importance weighting.

Instead of treating every skill equally, weights are computed from:
  1. Position in JD (skills mentioned first in Requirements → higher weight)
  2. Frequency (skills mentioned 3+ times → boosted)
  3. Category (hard_skill > tool > soft_skill)
  4. Ontology base importance
  5. Role-specific overrides
"""

from __future__ import annotations

import re
from pipeline.ats.taxonomy import resolve_skill, SKILL_GRAPH, ALIAS_MAP


def compute_skill_weight(
    skill: str,
    jd_text: str,
    jd_skills_ordered: list[str],
    role_overrides: dict[str, int] | None = None,
) -> int:
    """
    Compute dynamic importance weight (1–10) for a skill in context.

    Args:
        skill: The canonical skill name.
        jd_text: Full JD text (for frequency counting).
        jd_skills_ordered: Skills found in JD, in order of appearance.
        role_overrides: Role-specific weight overrides.
    """
    # 1. Ontology base importance
    info = resolve_skill(skill)
    base = info.base_importance if info else 5

    # 2. Role override
    if role_overrides and skill in role_overrides:
        base = role_overrides[skill]

    # 3. Position bonus: skills earlier in the JD get a boost
    position_bonus = 0
    if skill in jd_skills_ordered:
        idx = jd_skills_ordered.index(skill)
        total = len(jd_skills_ordered)
        if total > 0:
            # First skill gets +2, last gets +0
            position_bonus = round(2 * (1 - idx / max(total, 1)))

    # 4. Frequency bonus: mentioned multiple times
    freq_bonus = 0
    skill_lower = skill.lower()
    # Count occurrences (including aliases)
    count = len(re.findall(r"\b" + re.escape(skill_lower) + r"\b", jd_text.lower()))
    # Also count aliases
    if skill_lower in SKILL_GRAPH:
        for alias in SKILL_GRAPH[skill_lower].get("aliases", []):
            count += len(re.findall(r"\b" + re.escape(alias) + r"\b", jd_text.lower()))
    if count >= 3:
        freq_bonus = 2
    elif count >= 2:
        freq_bonus = 1

    # 5. Category adjustment: cap low-value tools
    category = info.category if info else "hard_skill"
    category_cap = {
        "hard_skill": 10,
        "language": 10,
        "methodology": 8,
        "certification": 7,
        "tool": 6,
        "soft_skill": 5,
    }.get(category, 8)

    # Generic tools auto-cap
    generic_tools = {"git", "jira", "slack", "confluence", "notion", "trello", "asana"}
    if skill_lower in generic_tools:
        category_cap = 2

    final = min(base + position_bonus + freq_bonus, category_cap)
    return max(1, min(10, final))


def compute_weights_for_skills(
    jd_skills: list[str],
    jd_text: str,
    role_overrides: dict[str, int] | None = None,
) -> dict[str, int]:
    """
    Compute weights for all skills found in a JD.

    Returns dict of {skill: weight}.
    """
    weights: dict[str, int] = {}
    for skill in jd_skills:
        weights[skill] = compute_skill_weight(
            skill, jd_text, jd_skills, role_overrides
        )
    return weights
