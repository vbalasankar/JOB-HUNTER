"""
Domain matching between JD and resume.

Detects industry domains (fintech, healthcare, SaaS, etc.) from
keyword clusters and company mentions, then scores overlap.
"""

from __future__ import annotations

import re
from pipeline.ats.models import DomainMatchResult


DOMAIN_TAXONOMY: dict[str, dict] = {
    "fintech": {
        "keywords": [
            "payments", "banking", "trading", "financial", "lending",
            "credit", "debit", "transactions", "compliance", "kyc", "aml",
            "pci", "pci-dss", "fintech", "neobank", "wealth management",
            "capital markets", "settlement", "clearing", "brokerage",
            "underwriting", "risk management", "regulatory",
        ],
        "companies": [
            "stripe", "paypal", "square", "plaid", "brex", "ramp",
            "robinhood", "coinbase", "wise", "revolut", "chime",
            "affirm", "sofi", "marqeta", "adyen", "checkout.com",
            "razorpay", "paytm", "phonepe",
        ],
        "adjacent": ["crypto", "insurance"],
    },
    "healthcare": {
        "keywords": [
            "hipaa", "ehr", "clinical", "patient", "medical", "pharmaceutical",
            "fda", "telehealth", "health records", "hl7", "fhir",
            "healthcare", "hospital", "diagnosis", "treatment",
            "clinical trials", "drug discovery", "biotech", "genomics",
        ],
        "companies": [
            "epic", "cerner", "veracyte", "tempus", "flatiron",
        ],
        "adjacent": ["biotech"],
    },
    "saas": {
        "keywords": [
            "multi-tenant", "subscription", "b2b", "crm", "erp",
            "saas", "recurring revenue", "churn", "onboarding",
            "self-serve", "freemium", "enterprise software",
            "platform", "product-led growth", "plg",
        ],
        "adjacent": ["enterprise", "devtools"],
    },
    "cybersecurity": {
        "keywords": [
            "soc", "siem", "penetration testing", "zero trust", "vulnerability",
            "threat", "encryption", "firewall", "ids", "ips",
            "cybersecurity", "infosec", "security operations",
            "incident response", "forensics", "malware",
        ],
        "adjacent": [],
    },
    "ai_ml": {
        "keywords": [
            "machine learning", "deep learning", "llm", "generative ai",
            "computer vision", "nlp", "model training", "inference",
            "transformers", "gpt", "fine-tuning", "rag",
            "artificial intelligence", "neural network", "ai research",
            "foundation model", "large language model",
        ],
        "adjacent": ["data"],
    },
    "ecommerce": {
        "keywords": [
            "shopify", "cart", "marketplace", "fulfillment", "inventory",
            "catalog", "checkout", "merchants", "ecommerce", "e-commerce",
            "retail", "supply chain", "logistics", "warehousing",
        ],
        "adjacent": ["logistics"],
    },
    "gaming": {
        "keywords": [
            "unreal", "unity", "game engine", "multiplayer", "rendering",
            "shader", "physics engine", "matchmaking", "gaming",
            "game development", "game server", "real-time",
        ],
        "adjacent": ["metaverse"],
    },
    "crypto": {
        "keywords": [
            "blockchain", "defi", "smart contracts", "web3", "solidity",
            "ethereum", "consensus", "tokenomics", "dao",
            "cryptocurrency", "nft", "layer 2", "rollup",
            "decentralized", "on-chain", "off-chain",
        ],
        "adjacent": ["fintech"],
    },
    "devtools": {
        "keywords": [
            "developer tools", "sdk", "api platform", "ide", "cli",
            "developer experience", "dx", "open source",
            "infrastructure", "devops", "cicd platform",
            "developer productivity", "code review",
        ],
        "adjacent": ["saas"],
    },
    "data": {
        "keywords": [
            "data platform", "data infrastructure", "data pipeline",
            "analytics platform", "data warehouse", "data lake",
            "business intelligence", "bi", "data engineering",
            "etl", "elt", "real-time analytics",
        ],
        "adjacent": ["ai_ml"],
    },
    "edtech": {
        "keywords": [
            "education", "learning", "courseware", "lms",
            "ed-tech", "edtech", "tutoring", "curriculum",
            "online learning", "e-learning",
        ],
        "adjacent": [],
    },
    "logistics": {
        "keywords": [
            "logistics", "supply chain", "fleet", "delivery",
            "routing", "warehousing", "freight", "shipping",
            "last mile", "transportation",
        ],
        "adjacent": ["ecommerce"],
    },
}


def match_domains(resume_text: str, jd_text: str) -> DomainMatchResult:
    """
    Detect domains in both JD and resume, compute overlap score.
    """
    jd_domains = _detect_domains(jd_text)
    resume_domains = _detect_domains(resume_text)

    if not jd_domains:
        return DomainMatchResult(
            jd_domains=[],
            resume_domains=list(resume_domains.keys()),
            overlap_score=0.5,  # No domain signal in JD → neutral
            confidence=0.2,
            detail="No specific industry domain detected in JD",
        )

    if not resume_domains:
        return DomainMatchResult(
            jd_domains=list(jd_domains.keys()),
            resume_domains=[],
            overlap_score=0.4,
            confidence=0.3,
            detail="No specific industry domain detected in resume",
        )

    # Compute overlap
    jd_domain_set = set(jd_domains.keys())
    resume_domain_set = set(resume_domains.keys())

    # Direct overlap
    direct_overlap = jd_domain_set & resume_domain_set

    # Adjacent overlap
    adjacent_overlap: set[str] = set()
    for jd_domain in jd_domain_set:
        adjacents = set(DOMAIN_TAXONOMY.get(jd_domain, {}).get("adjacent", []))
        adjacent_match = adjacents & resume_domain_set
        adjacent_overlap |= adjacent_match

    if direct_overlap:
        score = 1.0
        detail = f"Direct domain match: {', '.join(direct_overlap)}"
    elif adjacent_overlap:
        score = 0.70
        detail = f"Adjacent domain match: resume has {', '.join(adjacent_overlap)} (JD: {', '.join(jd_domain_set)})"
    else:
        score = 0.35
        detail = f"No domain overlap (JD: {', '.join(jd_domain_set)}, Resume: {', '.join(resume_domain_set)})"

    # Confidence based on how many keywords matched
    jd_max_hits = max(jd_domains.values()) if jd_domains else 0
    confidence = min(0.90, 0.40 + jd_max_hits * 0.08)

    return DomainMatchResult(
        jd_domains=list(jd_domains.keys()),
        resume_domains=list(resume_domains.keys()),
        overlap_score=score,
        confidence=confidence,
        detail=detail,
    )


def _detect_domains(text: str) -> dict[str, int]:
    """
    Detect domains in text by counting keyword hits.
    Returns dict of {domain: hit_count} for domains with >= 3 hits.
    """
    text_lower = text.lower()
    domain_hits: dict[str, int] = {}

    for domain_name, domain_info in DOMAIN_TAXONOMY.items():
        count = 0

        # Count keyword hits
        for keyword in domain_info.get("keywords", []):
            if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
                count += 1

        # Count company mentions (worth 2 hits each)
        for company in domain_info.get("companies", []):
            if re.search(r"\b" + re.escape(company) + r"\b", text_lower):
                count += 2

        if count >= 3:
            domain_hits[domain_name] = count

    return domain_hits
