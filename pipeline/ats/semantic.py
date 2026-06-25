"""
Chunk-level semantic matching using sentence-transformers.

Instead of computing one embedding for the entire resume and JD,
splits both into sections and computes pairwise similarities:
  - resume.skills ↔ jd.requirements
  - resume.experience ↔ jd.responsibilities
  - resume.projects ↔ jd.requirements
  - resume.summary ↔ jd.requirements

Falls back gracefully if sentence-transformers is not installed.
"""

from __future__ import annotations

import logging
from typing import Optional

from pipeline.ats.models import SemanticChunkResult
from pipeline.ats.section_parser import Section, get_section_text

logger = logging.getLogger(__name__)

# Model name — small, fast, local
_MODEL_NAME = "all-MiniLM-L6-v2"
_model = None
_model_load_attempted = False


def _get_model():
    """Lazy-load the sentence transformer model."""
    global _model, _model_load_attempted

    if _model_load_attempted:
        return _model

    _model_load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_MODEL_NAME)
        logger.info(f"Loaded sentence-transformers model: {_MODEL_NAME}")
    except ImportError:
        logger.info(
            "sentence-transformers not installed. "
            "Semantic matching disabled. Install with: "
            "pip install 'job-crawler[local-embeddings]'"
        )
        _model = None
    except Exception as e:
        logger.warning(f"Failed to load sentence-transformers: {e}")
        _model = None

    return _model


def _cosine_similarity(a, b) -> float:
    """Compute cosine similarity between two vectors."""
    import numpy as np
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def compute_semantic_chunks(
    resume_sections: list[Section],
    jd_sections: list[Section],
) -> Optional[SemanticChunkResult]:
    """
    Compute chunk-level semantic similarity between resume and JD sections.

    Returns None if sentence-transformers is not available.
    """
    model = _get_model()
    if model is None:
        return None

    # Extract text for each section type
    resume_skills = get_section_text(resume_sections, "skills")
    resume_experience = get_section_text(resume_sections, "experience")
    resume_projects = get_section_text(resume_sections, "projects")
    resume_summary = get_section_text(resume_sections, "summary")

    jd_requirements = get_section_text(jd_sections, "requirement")
    jd_responsibilities = get_section_text(jd_sections, "responsibility")

    # Fallback: if no sections found, use full text
    if not jd_requirements:
        jd_requirements = " ".join(s.text for s in jd_sections)
    if not resume_skills and not resume_experience:
        full_resume = " ".join(s.text for s in resume_sections)
        resume_skills = full_resume
        resume_experience = full_resume

    # Truncate long texts
    max_len = 2000
    resume_skills = resume_skills[:max_len] if resume_skills else ""
    resume_experience = resume_experience[:max_len] if resume_experience else ""
    resume_projects = resume_projects[:max_len] if resume_projects else ""
    resume_summary = resume_summary[:max_len] if resume_summary else ""
    jd_requirements = jd_requirements[:max_len] if jd_requirements else ""
    jd_responsibilities = jd_responsibilities[:max_len] if jd_responsibilities else ""

    # Collect all non-empty texts to embed in one batch
    texts_to_embed: list[str] = []
    labels: list[str] = []

    for text, label in [
        (resume_skills, "resume_skills"),
        (resume_experience, "resume_experience"),
        (resume_projects, "resume_projects"),
        (resume_summary, "resume_summary"),
        (jd_requirements, "jd_requirements"),
        (jd_responsibilities, "jd_responsibilities"),
    ]:
        if text.strip():
            texts_to_embed.append(text)
            labels.append(label)

    if len(texts_to_embed) < 2:
        return None

    try:
        embeddings = model.encode(texts_to_embed, show_progress_bar=False)
        emb_map = dict(zip(labels, embeddings))
    except Exception as e:
        logger.warning(f"Semantic embedding failed: {e}")
        return None

    # Compute pairwise similarities
    def _sim(a_label: str, b_label: str) -> float:
        if a_label in emb_map and b_label in emb_map:
            return max(0.0, _cosine_similarity(emb_map[a_label], emb_map[b_label]))
        return 0.0

    skills_vs_req = _sim("resume_skills", "jd_requirements")
    exp_vs_resp = _sim("resume_experience", "jd_responsibilities")
    proj_vs_req = _sim("resume_projects", "jd_requirements")
    summary_vs_req = _sim("resume_summary", "jd_requirements")

    # Weighted overall (requirements pairs weighted highest)
    weights = {
        "skills_vs_req": 1.0,
        "exp_vs_resp": 0.7,
        "proj_vs_req": 0.5,
        "summary_vs_req": 0.3,
    }
    scores = {
        "skills_vs_req": skills_vs_req,
        "exp_vs_resp": exp_vs_resp,
        "proj_vs_req": proj_vs_req,
        "summary_vs_req": summary_vs_req,
    }

    total_weight = sum(w for k, w in weights.items() if scores[k] > 0)
    if total_weight > 0:
        overall = sum(scores[k] * weights[k] for k in weights if scores[k] > 0) / total_weight
    else:
        overall = 0.0

    return SemanticChunkResult(
        skills_vs_requirements=round(skills_vs_req, 4),
        experience_vs_responsibilities=round(exp_vs_resp, 4),
        projects_vs_requirements=round(proj_vs_req, 4),
        summary_vs_requirements=round(summary_vs_req, 4),
        overall_semantic_fit=round(overall, 4),
        confidence=0.90,  # High confidence when model is available
    )
