# JobHunter

JobHunter is an intelligent, AI-powered job aggregator and personalized recommendation engine. It autonomously crawls over 20+ sources (including direct ATS platforms and global aggregators), parses your resume, and uses semantic embedding models to score and rank jobs based on how well they match your unique experience.

> **Note:** The semantic similarity implementation utilizes OpenAI or Gemini embedding models, adapted for strict resume-to-job recommendation use cases.

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Components](#components)
  - [Next.js Dashboard](#nextjs-dashboard)
  - [FastAPI Orchestrator](#fastapi-orchestrator)
  - [Storage Pipeline](#storage-pipeline)
  - [Candidate Sources](#candidate-sources)
- [How It Works](#how-it-works)
  - [Pipeline Stages](#pipeline-stages)
  - [Scoring and Ranking](#scoring-and-ranking)
  - [Filtering](#filtering)
- [Getting Started](#getting-started)
- [Key Design Decisions](#key-design-decisions)
- [License](#license)

---

## Overview

The JobHunter feed algorithm retrieves, ranks, and filters job postings from two primary pipelines:

1. **Direct Sources**: Posts parsed directly from Greenhouse, Lever, Ashby, and individual company career pages.
2. **Global Aggregators**: Posts discovered from global job boards, developer platforms, and RSS feeds.

Both pipelines are combined and ranked together using the **JobHunter Matcher**, an AI-powered engine that calculates compatibility scores for each job. We have eliminated reliance on pure keyword matching alone. The AI embeddings do the heavy lifting by understanding the semantic meaning behind your resume experience and using that to determine what roles are truly relevant to you.

---

## System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    JOBHUNTER WEB CLIENT                                     │
│                         (Next.js 16 • React 19 • Firebase Auth)                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
                                 │                           │
                   [Job Feed Request]                  [Resume & JD Analysis]
                                 ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    FASTAPI BACKEND CORE                                     │
│                                    (Async REST API)                                         │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│   ┌────────────────────────────────┐                 ┌──────────────────────────────────┐   │
│   │        NEWS AGGREGATOR         │                 │    ENTERPRISE ATS ENGINE         │   │
│   │  (Hacker News & Startup RSS)   │                 │ (10-Signal Intelligence Engine)  │   │
│   └────────────────────────────────┘                 └──────────────────────────────────┘   │
│                                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────────────────────┐   │
│   │                                    ORCHESTRATOR                                     │   │
│   │                              (Main Execution Pipeline)                              │   │
│   ├─────────────────────────────────────────────────────────────────────────────────────┤   │
│   │                                                                                     │   │
│   │   ┌─────────────────────────────────────────────────────────────────────────────┐   │   │
│   │   │                                QUERY HYDRATION                              │   │   │
│   │   │  ┌──────────────────────────┐    ┌───────────────────────────────────────┐  │   │   │
│   │   │  │ Extracted Resume Context │    │ User Preferences (Roles, Locations)   │  │   │   │
│   │   │  └──────────────────────────┘    └───────────────────────────────────────┘  │   │   │
│   │   └─────────────────────────────────────────────────────────────────────────────┘   │   │
│   │                                          │                                          │   │
│   │                                          ▼                                          │   │
│   │   ┌─────────────────────────────────────────────────────────────────────────────┐   │   │
│   │   │                               CANDIDATE SOURCES                             │   │   │
│   │   │         ┌─────────────────────────────┐    ┌─────────────────────────────┐  │   │   │
│   │   │         │        DIRECT ATS           │    │     GLOBAL AGGREGATORS      │  │   │   │
│   │   │         │    (Greenhouse, Lever)      │    │  (RemoteOK, HN, Built In)   │  │   │   │
│   │   │         └─────────────────────────────┘    └─────────────────────────────┘  │   │   │
│   │   └─────────────────────────────────────────────────────────────────────────────┘   │   │
│   │                                          │                                          │   │
│   │                                          ▼                                          │   │
│   │   ┌─────────────────────────────────────────────────────────────────────────────┐   │   │
│   │   │                                  FILTERING                                  │   │   │
│   │   │  Remove: Exact/Fuzzy Duplicates, Location/Seniority Mismatches, Keywords    │   │   │
│   │   └─────────────────────────────────────────────────────────────────────────────┘   │   │
│   │                                          │                                          │   │
│   │                                          ▼                                          │   │
│   │   ┌─────────────────────────────────────────────────────────────────────────────┐   │   │
│   │   │                                   SCORING                                   │   │   │
│   │   │  ┌──────────────────────────┐    ┌───────────────────────────────────────┐  │   │   │
│   │   │  │  Semantic Distance       │    │  Keyword Validation                   │  │   │   │
│   │   │  │  (OpenAI/Gemini Embeds)  │    │  (Jaccard similarity on tech stack)   │  │   │   │
│   │   │  └──────────────────────────┘    └───────────────────────────────────────┘  │   │   │
│   │   │                                      │                                      │   │   │
│   │   │  ┌───────────────────────────────────────────────────────────────────────┐  │   │   │
│   │   │  │                           Final Weighted Score                        │  │   │   │
│   │   │  └───────────────────────────────────────────────────────────────────────┘  │   │   │
│   │   └─────────────────────────────────────────────────────────────────────────────┘   │   │
│   │                                          │                                          │   │
│   │                                          ▼                                          │   │
│   │   ┌─────────────────────────────────────────────────────────────────────────────┐   │   │
│   │   │                                  SELECTION                                  │   │   │
│   │   │               Sort by final score and filter by minimum threshold           │   │   │
│   │   └─────────────────────────────────────────────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────────────────────────────────────────────┘   │
│                                              │                                              │
└──────────────────────────────────────────────┼──────────────────────────────────────────────┘
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    STORAGE & CACHE (SQLite)                                 │
│                   (Deduplication, Historical Persistence, Embedding Cache)                  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### Next.js Dashboard

**Location:** [`web/`](web/)

The presentation layer that serves the JobHunter user interface. It is built with:
- Next.js 16 (App Router)
- React 19
- TailwindCSS v4
- Firebase Authentication

It provides real-time ATS resume analysis, tech news aggregation, and a highly polished, responsive dashboard.

---

### FastAPI Orchestrator

**Location:** `server.py` and `main.py`

The asynchronous execution loop that drives the data retrieval and ML inference. It exposes robust REST API endpoints to the frontend, protected by `slowapi` rate limiting. It handles the heavy lifting of parsing PDFs, hydrating embeddings, and executing concurrent API calls to job sources.

---

### Enterprise ATS Engine

**Location:** [`pipeline/ats/`](pipeline/ats/)

A completely decoupled, recruiter-grade ATS matching engine. Unlike standard keyword counters, this 4-phase local engine computes a 10-signal analysis using:
1. **Dynamic Skill Weighting**: Weights skills based on JD placement, frequency, and 6 role-specific profiles.
2. **Semantic Extraction**: Uses `sentence-transformers` for section-aware semantic similarity.
3. **Trust & Consistency**: Checks parseability, detects contradictions, and extracts quantified achievements/leadership verbs.
4. **Actionable Suggestions**: Generates context-aware rewrite suggestions to fix critical resume gaps.

---

### Storage Pipeline

**Location:** [`storage/`](storage/)

A local SQLite database utilizing SQLModel (SQLAlchemy). It maintains historical scraped jobs, prevents duplicate rendering across sessions, and caches previously calculated embeddings to bypass rate limits and speed up subsequent runs.

---

### Candidate Sources

**Location:** [`sources/`](sources/)

A collection of ingestion plugins mapping external job boards into a canonical internal schema. It handles concurrent HTTP requests, API compliance, rate limiting, and raw HTML parsing using BeautifulSoup.

---

## How It Works

### Pipeline Stages

1. **User Hydration**: Fetch the user's uploaded resume and active configuration profile.
2. **Candidate Sourcing**: Retrieve candidates concurrently from all active sourcing modules.
3. **Data Hydration**: Enrich candidates with extracted salaries, standardized remote types, and core HTML descriptions.
4. **Pre-Scoring Filters**: Remove posts that violate hard constraints (e.g., location, seniority, explicitly excluded keywords).
5. **Scoring**: Compute the semantic distance using language models, followed by a hard-skills keyword extraction check. 
6. **Selection**: Sort jobs by their aggregate match score and apply minimum thresholds.
7. **Post-Selection Processing**: Final database persistence to ensure UI consistency.

---

### Scoring and Ranking

The Matcher calculates two distinct scores before producing a final rank:

1. **Semantic Score**: Uses high-dimensional embedding vectors (e.g., `text-embedding-3-small`) to find the mathematical cosine similarity between the candidate's experience and the job's requirements.
2. **Keyword Overlap**: Extracts recognized technologies from both texts and calculates their Jaccard similarity index to ensure critical "must-have" tools are present.

The **Weighted Scorer** combines these into a final score:

```text
Final Match Score = (Semantic Score × 0.8) + (Keyword Score × 0.2)
```

---

### Filtering

Filters run at two stages to prevent wasted ML inference and ensure high-quality output:

**Pre-Scoring Filters:**
| Filter | Purpose |
|--------|---------|
| `DropDuplicatesFilter` | Removes exact duplicate IDs across API responses |
| `FuzzyDeduplicationFilter` | Removes visually identical posts based on title and company overlap |
| `LocationFilter` | Drops jobs not matching the user's allowed regions |
| `SeniorityFilter` | Drops jobs outside the user's experience tier |
| `KeywordExclusionFilter` | Drops jobs containing explicitly banned red-flag keywords |

**Post-Selection Filters:**
| Filter | Purpose |
|--------|---------|
| `DatabaseDedupFilter` | Prevents rendering jobs that have already been dismissed or saved |

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 20+
- A Firebase Project (for web authentication)
- An OpenAI or Gemini API Key (for semantic scoring)

### 1. Backend Setup
Navigate to the root directory and set up your Python environment:

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure your environment variables
cp .env.example .env
# Edit .env with your LLM API keys

# Start the API server
uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
Open a new terminal window, navigate to the `web/` directory:

```bash
cd web

# Install dependencies
npm install

# Configure your Firebase credentials
cp .env.local.example .env.local
# Edit .env.local with your Firebase config

# Start the Next.js development server
npm run dev
```

Visit `http://localhost:3000` to access your JobHunter dashboard.


## Key Design Decisions

### 1. No Bloated Frameworks
The backend avoids massive ML abstraction frameworks in favor of simple, concurrent Python routines (`asyncio`). This keeps inference fast and the codebase understandable.

### 2. Candidate Isolation
During embedding inference, job candidates are processed completely independently of each other. This ensures that the score for a post doesn't drift depending on which other jobs are currently in the batch, making scores consistent and highly cacheable.

### 3. Graceful ML Degradation
Rather than relying solely on expensive and potentially unreliable LLM APIs, the system can gracefully degrade to a fast keyword overlap scoring model if API keys are missing or rate limits are exceeded.

### 4. Multi-Tier Sourcing Architecture
By defining strict API sources alongside broad RSS aggregators, the system casts a wide net without sacrificing the data quality of direct ATS connections.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
