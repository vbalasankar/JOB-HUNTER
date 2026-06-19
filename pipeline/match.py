"""
Match scoring — blends semantic similarity with keyword overlap.

Embedding providers:
  - "openai": OpenAI text-embedding-3-small via API
  - "gemini": Google text-embedding-004 via API
  - "keyword": TF-IDF + keyword overlap (no API key required)

Score formula:
  match_score = 0.7 * semantic_similarity + 0.3 * keyword_overlap
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import httpx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine

from config import get_settings
from storage.models import Job

logger = logging.getLogger(__name__)

# Weight blend
SEMANTIC_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3


# ===== Resume Loading =====


def load_resume(path: str) -> str:
    """Load resume text from .txt, .pdf, or .docx."""
    p = Path(path)
    if not p.exists():
        logger.info(
            f"No resume found at {path} — scoring will use keyword-only mode. Add a resume.txt for better matching."
        )
        return ""

    suffix = p.suffix.lower()

    if suffix == ".txt":
        return p.read_text(encoding="utf-8")

    elif suffix == ".pdf":
        try:
            import pdfplumber

            with pdfplumber.open(p) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except ImportError:
            logger.warning("pdfplumber not installed, cannot read PDF resume")
            return ""

    elif suffix in (".docx", ".doc"):
        try:
            from docx import Document

            doc = Document(str(p))
            return "\n".join(para.text for para in doc.paragraphs)
        except ImportError:
            logger.warning("python-docx not installed, cannot read DOCX resume")
            return ""

    else:
        logger.warning(f"Unsupported resume format: {suffix}")
        return p.read_text(encoding="utf-8", errors="ignore")


# ===== Embedding Providers =====


async def _embed_openai(
    texts: list[str], api_key: str, model: str
) -> list[list[float]]:
    """Get embeddings from OpenAI API."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": texts,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        # Sort by index to ensure order matches input
        embeddings = sorted(data["data"], key=lambda x: x["index"])
        return [e["embedding"] for e in embeddings]


async def _embed_gemini(
    texts: list[str], api_key: str, model: str
) -> list[list[float]]:
    """Get embeddings from Google Gemini API."""
    async with httpx.AsyncClient() as client:
        embeddings = []
        # Gemini embedContent works one at a time; use batchEmbedContents for efficiency
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents",
            params={"key": api_key},
            json={
                "requests": [
                    {
                        "model": f"models/{model}",
                        "content": {
                            "parts": [{"text": t[:8000]}]
                        },  # Truncate long texts
                    }
                    for t in texts
                ]
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        for emb in data.get("embeddings", []):
            embeddings.append(emb["values"])
        return embeddings


def _embed_tfidf(texts: list[str]) -> np.ndarray:
    """Fallback: TF-IDF embeddings (no API key needed)."""
    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",
        ngram_range=(1, 2),
    )
    return vectorizer.fit_transform(texts).toarray()


# ===== Keyword Analysis =====


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text."""
    # Remove common stop words and short words
    words = re.findall(r"\b[a-zA-Z][a-zA-Z+#.-]{2,}\b", text.lower())
    stop_words = {
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "all",
        "can",
        "had",
        "her",
        "was",
        "one",
        "our",
        "out",
        "has",
        "have",
        "been",
        "will",
        "with",
        "this",
        "that",
        "from",
        "they",
        "been",
        "said",
        "each",
        "which",
        "their",
        "about",
        "would",
        "make",
        "like",
        "work",
        "team",
        "experience",
        "looking",
        "join",
        "company",
        "role",
        "position",
        "opportunity",
        "responsibilities",
        "requirements",
        "qualifications",
        "benefits",
        "about",
        "what",
        "your",
        "more",
    }
    return {w for w in words if w not in stop_words}


def _keyword_overlap_score(resume_keywords: set[str], job_keywords: set[str]) -> float:
    """Jaccard similarity between keyword sets."""
    if not resume_keywords or not job_keywords:
        return 0.0
    intersection = resume_keywords & job_keywords
    union = resume_keywords | job_keywords
    return len(intersection) / len(union)


def _find_matching_keywords(
    resume_keywords: set[str],
    job_keywords: set[str],
    include_keywords: list[str],
) -> list[str]:
    """Find the specific keywords that matched."""
    matched = resume_keywords & job_keywords

    # Prioritize configured include_keywords
    reasons: list[str] = []
    include_lower = {kw.lower() for kw in include_keywords}
    for kw in sorted(matched):
        if kw in include_lower:
            reasons.insert(0, f"✓ {kw}")
        elif len(reasons) < 10:
            reasons.append(kw)

    return reasons[:10]


# ===== Main Scoring =====


async def score_jobs(jobs: list[Job], resume_text: str | None = None) -> list[Job]:
    """
    Score a batch of jobs against the resume.

    Computes blended score:
      match_score = 0.7 * semantic_similarity + 0.3 * keyword_overlap

    Modifies jobs in-place and returns them.
    """
    if not jobs:
        return jobs

    settings = get_settings()

    # Load resume
    if resume_text is None:
        resume_text = load_resume(settings.resume_path)

    if not resume_text:
        logger.info("No resume text available — using keyword-only scoring")
        return _score_keyword_only(jobs, settings)

    # Extract keywords for keyword-overlap scoring
    resume_keywords = _extract_keywords(resume_text)

    # Prepare texts for embedding
    job_texts = [f"{j.title} {j.company} {j.description_raw[:2000]}" for j in jobs]
    all_texts = [resume_text[:3000]] + job_texts  # Resume is first

    # Get embeddings
    provider = settings.embedding_provider
    api_key = settings.embedding_api_key

    try:
        if provider == "openai" and api_key:
            logger.info(f"Using OpenAI embeddings ({settings.openai_embedding_model})")
            embeddings = await _embed_openai(
                all_texts, api_key, settings.openai_embedding_model
            )
            resume_emb = np.array(embeddings[0]).reshape(1, -1)
            job_embs = np.array(embeddings[1:])

        elif provider == "gemini" and api_key:
            logger.info(f"Using Gemini embeddings ({settings.gemini_embedding_model})")
            embeddings = await _embed_gemini(
                all_texts, api_key, settings.gemini_embedding_model
            )
            resume_emb = np.array(embeddings[0]).reshape(1, -1)
            job_embs = np.array(embeddings[1:])

        else:
            logger.info("Using TF-IDF embeddings (no API key)")
            tfidf_matrix = _embed_tfidf(all_texts)
            resume_emb = tfidf_matrix[0:1]
            job_embs = tfidf_matrix[1:]

    except Exception as e:
        logger.warning(
            f"Embedding failed ({provider}): {e}. Falling back to keyword-only."
        )
        return _score_keyword_only(jobs, settings)

    # Compute cosine similarities
    similarities = sklearn_cosine(resume_emb, job_embs)[0]

    # Blend scores
    for i, job in enumerate(jobs):
        job_keywords = _extract_keywords(job.description_raw)
        kw_score = _keyword_overlap_score(resume_keywords, job_keywords)
        semantic_score = float(similarities[i])

        # Clamp to [0, 1]
        semantic_score = max(0.0, min(1.0, semantic_score))

        job.match_score = round(
            SEMANTIC_WEIGHT * semantic_score + KEYWORD_WEIGHT * kw_score,
            4,
        )

        # Build match reasons
        matching_kw = _find_matching_keywords(
            resume_keywords, job_keywords, settings.include_keywords_list
        )
        reasons = {
            "semantic_similarity": round(semantic_score, 3),
            "keyword_overlap": round(kw_score, 3),
            "matching_keywords": matching_kw,
        }
        job.match_reasons = json.dumps(reasons)

    # Sort by score descending
    jobs.sort(key=lambda j: j.match_score or 0, reverse=True)

    logger.info(
        f"Scored {len(jobs)} jobs. "
        f"Top: {jobs[0].match_score:.3f} ({jobs[0].title[:50]}), "
        f"Bottom: {jobs[-1].match_score:.3f} ({jobs[-1].title[:50]})"
    )
    return jobs


def _score_keyword_only(jobs: list[Job], settings) -> list[Job]:
    """Fallback: score using only keyword overlap when embeddings aren't available."""
    resume_text = load_resume(settings.resume_path)
    resume_keywords = _extract_keywords(resume_text)

    for job in jobs:
        job_keywords = _extract_keywords(job.description_raw)
        kw_score = _keyword_overlap_score(resume_keywords, job_keywords)
        job.match_score = round(kw_score, 4)

        matching_kw = _find_matching_keywords(
            resume_keywords, job_keywords, settings.include_keywords_list
        )
        reasons = {
            "semantic_similarity": 0.0,
            "keyword_overlap": round(kw_score, 3),
            "matching_keywords": matching_kw,
            "note": "keyword-only scoring (no API key or embedding failure)",
        }
        job.match_reasons = json.dumps(reasons)

    jobs.sort(key=lambda j: j.match_score or 0, reverse=True)
    return jobs
