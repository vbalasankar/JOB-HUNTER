"""
server.py — FastAPI backend serving the job crawler frontend.

Endpoints:
  GET  /api/jobs          Paginated job listings with filtering
  GET  /api/jobs/stats    Summary statistics
  GET  /api/news          Tech news feed
  GET  /api/sources       List of configured sources
  GET  /api/profile       Get saved user preferences
  POST /api/profile       Save user preferences
  GET  /                  Serve frontend

Usage:
  python server.py
  # or: uvicorn server:app --reload
"""

from __future__ import annotations

import logging
import io
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import PyPDF2
from fastapi import FastAPI, Query, File, Form, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
from sqlmodel import select, func, col

from config import get_settings
from news.aggregator import get_news
from storage.db import get_engine, get_session
from storage.models import Job

from pipeline.ats.models import AtsScoreResponse
from pipeline.ats import compute_ats_score as run_ats_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("server")

app = FastAPI(title="JobHunter", version="2.0.0")

# Security & Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Gzip Compression for large payloads
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Restricted to safe methods
    allow_headers=["Authorization", "Content-Type"],  # Restricted headers
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# API Endpoints


# ---------- Pydantic models ----------


class JobResponse(BaseModel):
    id: str
    source: str
    title: str
    company: str
    location: Optional[str]
    remote_type: Optional[str]
    url: str
    posted_date: Optional[datetime]
    salary_min: Optional[float]
    salary_max: Optional[float]
    match_score: Optional[float]
    match_reasons: Optional[str]
    fetched_at: datetime


class JobsListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    page: int
    per_page: int


class StatsResponse(BaseModel):
    total_jobs: int
    by_source: dict[str, int]
    by_remote_type: dict[str, int]
    avg_match_score: Optional[float]
    latest_fetch: Optional[datetime]


class NewsItemResponse(BaseModel):
    id: str
    title: str
    url: str
    source: str
    published_at: Optional[datetime]
    summary: str
    tags: list[str]
    author: str
    points: Optional[int]
    comment_count: Optional[int]


class ProfileRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    roles: list[str] = []
    skills: list[str] = []
    locations: list[str] = []
    experienceLevel: Optional[str] = None
    minSalary: Optional[str] = None
    resumeFileName: Optional[str] = None


class SourceInfo(BaseModel):
    name: str
    enabled: bool
    type: str  # "ats", "aggregator", "rss", "api"


# In-memory profile storage (simple for now)
_profile: dict[str, Any] = {
    "firstName": "",
    "lastName": "",
    "email": "",
    "roles": [],
    "skills": [],
    "locations": [],
    "experienceLevel": "",
    "minSalary": "",
    "resumeFileName": ""
}


# ---------- API endpoints ----------


@app.get("/api/jobs", response_model=JobsListResponse)
@limiter.limit("100/minute")
async def list_jobs(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    role: Optional[str] = None,
    skill: Optional[str] = None,
    source: Optional[str] = None,
    remote_type: Optional[str] = None,
    min_score: Optional[float] = None,
    search: Optional[str] = None,
):
    """Get paginated job listings with optional filters."""
    with get_session() as session:
        stmt = select(Job)

        # Apply filters
        if source:
            stmt = stmt.where(Job.source == source)
        if remote_type:
            stmt = stmt.where(Job.remote_type == remote_type)
        if min_score is not None:
            stmt = stmt.where(col(Job.match_score) >= min_score)

        # Text search in title and description
        if search:
            search_lower = f"%{search.lower()}%"
            stmt = stmt.where(
                col(Job.title).ilike(search_lower)
                | col(Job.company).ilike(search_lower)
                | col(Job.description_raw).ilike(search_lower)
            )

        # Role filter (search in title)
        if role:
            role_terms = [r.strip() for r in role.split(",") if r.strip()]
            if role_terms:
                from sqlalchemy import or_

                conditions = [col(Job.title).ilike(f"%{term}%") for term in role_terms]
                stmt = stmt.where(or_(*conditions))

        # Skill filter (search in description)
        if skill:
            skill_terms = [s.strip() for s in skill.split(",") if s.strip()]
            if skill_terms:
                from sqlalchemy import or_

                conditions = [
                    col(Job.description_raw).ilike(f"%{term}%") for term in skill_terms
                ]
                stmt = stmt.where(or_(*conditions))

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.exec(count_stmt).one()

        # Order and paginate
        stmt = stmt.order_by(col(Job.match_score).desc().nullslast())
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)

        jobs = list(session.exec(stmt).all())

    return JobsListResponse(
        jobs=[
            JobResponse(
                id=j.id,
                source=j.source,
                title=j.title,
                company=j.company,
                location=j.location,
                remote_type=j.remote_type,
                url=j.url,
                posted_date=j.posted_date,
                salary_min=j.salary_min,
                salary_max=j.salary_max,
                match_score=j.match_score,
                match_reasons=j.match_reasons,
                fetched_at=j.fetched_at,
            )
            for j in jobs
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@app.get("/api/jobs/stats", response_model=StatsResponse)
@limiter.limit("100/minute")
async def job_stats(request: Request):
    """Get summary statistics about crawled jobs."""
    with get_session() as session:
        total = session.exec(select(func.count()).select_from(Job)).one()

        # By source
        source_rows = session.exec(
            select(Job.source, func.count()).group_by(Job.source)
        ).all()
        by_source = {row[0]: row[1] for row in source_rows}

        # By remote type
        remote_rows = session.exec(
            select(Job.remote_type, func.count())
            .where(Job.remote_type.is_not(None))
            .group_by(Job.remote_type)
        ).all()
        by_remote_type = {row[0]: row[1] for row in remote_rows}

        # Average match score
        avg_score = session.exec(
            select(func.avg(Job.match_score)).where(Job.match_score.is_not(None))
        ).one()

        # Latest fetch
        latest = session.exec(select(func.max(Job.fetched_at))).one()

    return StatsResponse(
        total_jobs=total,
        by_source=by_source,
        by_remote_type=by_remote_type,
        avg_match_score=round(avg_score, 3) if avg_score else None,
        latest_fetch=latest,
    )


@app.get("/api/news")
@limiter.limit("100/minute")
async def news_feed(
    request: Request,
    skills: Optional[str] = None,
    roles: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
):
    """Get tech news feed, optionally filtered by skills/roles."""
    skill_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else None
    role_list = [r.strip() for r in roles.split(",") if r.strip()] if roles else None

    # Use profile if no explicit filters
    if not skill_list and _profile["skills"]:
        skill_list = _profile["skills"]
    if not role_list and _profile["roles"]:
        role_list = _profile["roles"]

    items = await get_news(skills=skill_list, roles=role_list, limit=limit)
    return [
        NewsItemResponse(
            id=item.id,
            title=item.title,
            url=item.url,
            source=item.source,
            published_at=item.published_at,
            summary=item.summary,
            tags=item.tags,
            author=item.author,
            points=item.points,
            comment_count=item.comment_count,
        )
        for item in items
    ]


@app.get("/api/sources")
@limiter.limit("100/minute")
async def list_sources(request: Request):
    """List all configured job sources and their status."""
    settings = get_settings()
    sources: list[dict] = []

    # ATS sources
    if settings.greenhouse_companies_list:
        sources.append(
            {
                "name": "Greenhouse",
                "enabled": True,
                "type": "ats",
                "count": len(settings.greenhouse_companies_list),
            }
        )
    if settings.lever_companies_list:
        sources.append(
            {
                "name": "Lever",
                "enabled": True,
                "type": "ats",
                "count": len(settings.lever_companies_list),
            }
        )
    if settings.ashby_companies_list:
        sources.append(
            {
                "name": "Ashby",
                "enabled": True,
                "type": "ats",
                "count": len(settings.ashby_companies_list),
            }
        )

    # Aggregators
    aggregators = [
        ("RemoteOK", settings.enable_remoteok),
        ("WeWorkRemotely", settings.enable_weworkremotely),
        ("Hacker News", settings.enable_hackernews),
        ("Arbeitnow", settings.enable_arbeitnow),
        ("Wellfound", settings.enable_wellfound),
        ("YC Work at a Startup", settings.enable_ycombinator),
        ("Built In", settings.enable_builtin),
        ("Himalayas", settings.enable_himalayas),
        ("Dynamite Jobs", settings.enable_dynamite_jobs),
        ("Remotive", settings.enable_remotive),
        ("Arc.dev", settings.enable_arc_dev),
        ("Jobspresso", settings.enable_jobspresso),
        ("CryptoJobsList", settings.enable_crypto_jobs),
        ("AI Jobs", settings.enable_ai_jobs),
        ("Golang Cafe", settings.enable_golang_cafe),
        ("Rust Jobs", settings.enable_rustjobs),
        ("Python.org Jobs", settings.enable_python_jobs),
        ("Dribbble", settings.enable_dribbble),
    ]

    for name, enabled in aggregators:
        sources.append(
            {
                "name": name,
                "enabled": enabled,
                "type": "aggregator",
            }
        )

    return sources


@app.get("/api/profile")
@limiter.limit("100/minute")
async def get_profile(request: Request):
    """Get the saved user profile (roles and skills)."""
    return _profile


@app.post("/api/profile")
@limiter.limit("60/minute")
async def save_profile(request: Request, profile: ProfileRequest):
    """Save user profile preferences."""
    _profile["firstName"] = profile.firstName
    _profile["lastName"] = profile.lastName
    _profile["email"] = profile.email
    _profile["roles"] = profile.roles
    _profile["skills"] = profile.skills
    _profile["locations"] = profile.locations
    _profile["experienceLevel"] = profile.experienceLevel
    _profile["minSalary"] = profile.minSalary
    _profile["resumeFileName"] = profile.resumeFileName
    return {"status": "saved", "profile": _profile}


@app.post("/api/ats-score", response_model=AtsScoreResponse)
@limiter.limit("20/minute")
async def compute_ats_score(
    request: Request,
    resume_text: str = Form(""),
    job_description: str = Form(""),
    resume_file: Optional[UploadFile] = File(None),
):
    """Compute ATS score comparing a resume (text or file) to a job description."""
    # Validate inputs
    if len(job_description) > 100000:
        raise HTTPException(status_code=400, detail="Job description is too long.")

    final_resume_text = resume_text

    if resume_file and resume_file.filename:
        # Read the uploaded file
        try:
            content = await resume_file.read()
            if len(content) > 5 * 1024 * 1024:  # 5MB limit
                raise HTTPException(
                    status_code=400, detail="Resume file is too large (max 5MB)."
                )

            filename_lower = resume_file.filename.lower()
            if filename_lower.endswith(".pdf"):
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                extracted_text = []
                for page in pdf_reader.pages:
                    extracted_text.append(page.extract_text() or "")
                final_resume_text = "\n".join(extracted_text)
            elif filename_lower.endswith(".txt"):
                final_resume_text = content.decode("utf-8", errors="ignore")
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file format. Please upload PDF or TXT.",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reading resume file: {e}")
            raise HTTPException(
                status_code=400, detail="Could not parse the uploaded resume file."
            )

    if not final_resume_text.strip() or not job_description.strip():
        raise HTTPException(
            status_code=400, detail="Both resume and job description are required."
        )

    if len(final_resume_text) > 100000:
        raise HTTPException(status_code=400, detail="Resume is too long.")

    # Call the new Enterprise ATS Engine
    try:
        result = run_ats_pipeline(final_resume_text, job_description)
        return result
    except Exception as e:
        logger.error(f"Error computing ATS score: {e}")
        raise HTTPException(status_code=500, detail="Error computing ATS score. Check server logs.")


@app.get("/")
async def root():
    """Root endpoint for the API."""
    return {
        "status": "ok",
        "message": "JobHunter API is running. Visit the Next.js frontend to use the app.",
    }


# ---------- Main ----------


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    # Ensure DB is initialized
    get_engine()

    print(f"Starting server at http://localhost:{settings.server_port} with 4 workers")
    uvicorn.run(
        "server:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,  # Reload cannot be true with workers
        workers=4,
    )
