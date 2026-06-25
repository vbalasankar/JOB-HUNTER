"""
Hybrid skill ontology: curated core + alias layer + auto noun-phrase extraction.

Three layers:
  1. SKILL_GRAPH — ~400 curated skills with parent-child relationships
  2. ALIAS_MAP — 200+ alias → canonical skill mappings
  3. Auto-extracted noun phrases for emerging tech not in the ontology

Matching uses longest-match-first scanning so multi-word terms like
"machine learning" are matched before "machine" and "learning" individually.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Layer 1: Curated Skill Graph ─────────────────────────────────────

SKILL_GRAPH: dict[str, dict] = {
    # ─── Programming Languages ───
    "python": {
        "category": "language",
        "aliases": ["python3", "py"],
        "children": ["django", "flask", "fastapi", "celery", "sqlalchemy",
                      "pandas", "numpy", "scipy", "pydantic", "asyncio"],
        "base_importance": 8,
    },
    "javascript": {
        "category": "language",
        "aliases": ["js", "ecmascript", "es6", "es2015"],
        "children": ["react", "vue", "angular", "svelte", "nodejs", "express",
                      "nextjs", "nuxt", "webpack", "vite", "bun", "deno"],
        "base_importance": 8,
    },
    "typescript": {
        "category": "language",
        "aliases": ["ts"],
        "children": [],
        "base_importance": 8,
    },
    "go": {
        "category": "language",
        "aliases": ["golang"],
        "children": ["gin", "echo", "fiber", "gorilla"],
        "base_importance": 8,
    },
    "java": {
        "category": "language",
        "aliases": [],
        "children": ["spring", "spring boot", "hibernate", "maven", "gradle",
                      "quarkus", "micronaut"],
        "base_importance": 8,
    },
    "rust": {
        "category": "language",
        "aliases": [],
        "children": ["actix", "tokio", "warp", "axum", "serde", "cargo"],
        "base_importance": 7,
    },
    "c++": {
        "category": "language",
        "aliases": ["cpp", "c plus plus"],
        "children": ["boost", "cmake", "stl"],
        "base_importance": 7,
    },
    "c#": {
        "category": "language",
        "aliases": ["csharp", "c sharp"],
        "children": [".net", "asp.net", "entity framework", "unity"],
        "base_importance": 7,
    },
    "scala": {
        "category": "language",
        "aliases": [],
        "children": ["akka", "play framework", "cats", "zio"],
        "base_importance": 6,
    },
    "kotlin": {
        "category": "language",
        "aliases": [],
        "children": ["ktor", "jetpack compose"],
        "base_importance": 6,
    },
    "swift": {
        "category": "language",
        "aliases": [],
        "children": ["swiftui", "uikit", "combine"],
        "base_importance": 6,
    },
    "ruby": {
        "category": "language",
        "aliases": ["rb"],
        "children": ["rails", "ruby on rails", "sinatra", "sidekiq"],
        "base_importance": 6,
    },
    "php": {
        "category": "language",
        "aliases": [],
        "children": ["laravel", "symfony", "wordpress", "composer"],
        "base_importance": 5,
    },
    "r": {
        "category": "language",
        "aliases": ["r language", "rlang"],
        "children": ["tidyverse", "ggplot2", "shiny", "dplyr"],
        "base_importance": 5,
    },
    "sql": {
        "category": "language",
        "aliases": [],
        "children": [],
        "base_importance": 7,
    },
    "bash": {
        "category": "language",
        "aliases": ["shell", "shell scripting", "sh"],
        "children": [],
        "base_importance": 4,
    },
    "elixir": {
        "category": "language",
        "aliases": [],
        "children": ["phoenix", "ecto", "otp"],
        "base_importance": 5,
    },
    "haskell": {
        "category": "language",
        "aliases": [],
        "children": [],
        "base_importance": 5,
    },
    "lua": {
        "category": "language",
        "aliases": [],
        "children": [],
        "base_importance": 4,
    },
    "dart": {
        "category": "language",
        "aliases": [],
        "children": ["flutter"],
        "base_importance": 5,
    },

    # ─── Frontend ───
    "react": {
        "category": "hard_skill",
        "aliases": ["reactjs", "react.js"],
        "children": ["react hooks", "react router", "redux", "zustand",
                      "react query", "react native"],
        "base_importance": 9,
    },
    "vue": {
        "category": "hard_skill",
        "aliases": ["vuejs", "vue.js"],
        "children": ["vuex", "pinia", "vue router"],
        "base_importance": 7,
    },
    "angular": {
        "category": "hard_skill",
        "aliases": ["angularjs"],
        "children": ["rxjs", "ngrx", "angular material"],
        "base_importance": 7,
    },
    "svelte": {
        "category": "hard_skill",
        "aliases": ["sveltekit"],
        "children": [],
        "base_importance": 6,
    },
    "nextjs": {
        "category": "hard_skill",
        "aliases": ["next.js", "next js"],
        "children": [],
        "base_importance": 7,
    },
    "html": {
        "category": "hard_skill",
        "aliases": ["html5"],
        "children": [],
        "base_importance": 4,
    },
    "css": {
        "category": "hard_skill",
        "aliases": ["css3"],
        "children": ["sass", "less", "tailwindcss", "styled-components",
                      "css modules", "postcss"],
        "base_importance": 5,
    },
    "webpack": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 4,
    },
    "vite": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 4,
    },
    "figma": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 4,
    },

    # ─── Backend Frameworks ───
    "django": {
        "category": "hard_skill",
        "aliases": [],
        "children": ["django rest framework", "drf", "celery"],
        "base_importance": 7,
    },
    "flask": {
        "category": "hard_skill",
        "aliases": [],
        "children": [],
        "base_importance": 6,
    },
    "fastapi": {
        "category": "hard_skill",
        "aliases": ["fast api"],
        "children": [],
        "base_importance": 7,
    },
    "spring": {
        "category": "hard_skill",
        "aliases": ["spring framework"],
        "children": ["spring boot", "spring cloud", "spring security"],
        "base_importance": 7,
    },
    "express": {
        "category": "hard_skill",
        "aliases": ["expressjs", "express.js"],
        "children": [],
        "base_importance": 6,
    },
    "nodejs": {
        "category": "hard_skill",
        "aliases": ["node.js", "node js", "node"],
        "children": ["express", "nestjs", "koa", "fastify"],
        "base_importance": 7,
    },
    "graphql": {
        "category": "hard_skill",
        "aliases": [],
        "children": ["apollo", "relay", "hasura"],
        "base_importance": 6,
    },
    "rest": {
        "category": "hard_skill",
        "aliases": ["rest api", "restful", "rest apis", "restful api"],
        "children": [],
        "base_importance": 6,
    },
    "grpc": {
        "category": "hard_skill",
        "aliases": ["g-rpc"],
        "children": ["protobuf", "protocol buffers"],
        "base_importance": 6,
    },

    # ─── Cloud: AWS ───
    "aws": {
        "category": "hard_skill",
        "aliases": ["amazon web services", "amazon cloud"],
        "children": [
            "ec2", "s3", "lambda", "iam", "rds", "sqs", "sns",
            "dynamodb", "cloudfront", "ecs", "eks", "fargate",
            "cloudwatch", "cloudformation", "cdk", "step functions",
            "api gateway", "kinesis", "redshift", "athena",
            "sagemaker", "bedrock", "glue", "emr", "eventbridge",
            "route 53", "elasticache", "aurora", "msk",
        ],
        "base_importance": 9,
    },
    "gcp": {
        "category": "hard_skill",
        "aliases": ["google cloud", "google cloud platform"],
        "children": [
            "bigquery", "cloud run", "cloud functions", "gke",
            "pub/sub", "cloud storage", "cloud sql", "dataflow",
            "vertex ai", "cloud spanner", "firestore", "bigtable",
            "cloud composer", "dataproc", "cloud build",
        ],
        "base_importance": 8,
    },
    "azure": {
        "category": "hard_skill",
        "aliases": ["microsoft azure"],
        "children": [
            "azure devops", "azure functions", "aks",
            "azure sql", "cosmos db", "azure blob storage",
            "azure pipelines", "azure ad", "azure cognitive services",
        ],
        "base_importance": 8,
    },

    # ─── Containers & Orchestration ───
    "docker": {
        "category": "hard_skill",
        "aliases": ["containers", "containerization"],
        "children": ["docker compose", "dockerfile", "docker swarm"],
        "base_importance": 7,
    },
    "kubernetes": {
        "category": "hard_skill",
        "aliases": ["k8s", "kube"],
        "children": [
            "helm", "istio", "argocd", "kustomize", "kubectl",
            "keda", "k3s", "k9s", "rancher", "operator",
        ],
        "base_importance": 8,
    },

    # ─── DevOps & CI/CD ───
    "terraform": {
        "category": "hard_skill",
        "aliases": ["tf", "hcl"],
        "children": ["terragrunt", "terraform cloud"],
        "base_importance": 7,
    },
    "ansible": {
        "category": "hard_skill",
        "aliases": [],
        "children": [],
        "base_importance": 6,
    },
    "ci/cd": {
        "category": "methodology",
        "aliases": ["continuous integration", "continuous delivery",
                    "continuous deployment", "cicd"],
        "children": ["github actions", "gitlab ci", "jenkins", "circleci",
                      "travis ci", "argocd", "spinnaker", "buildkite"],
        "base_importance": 7,
    },
    "github actions": {
        "category": "tool",
        "aliases": ["gh actions"],
        "children": [],
        "base_importance": 5,
    },
    "gitlab ci": {
        "category": "tool",
        "aliases": ["gitlab ci/cd"],
        "children": [],
        "base_importance": 5,
    },
    "jenkins": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 5,
    },

    # ─── Databases ───
    "postgresql": {
        "category": "hard_skill",
        "aliases": ["postgres", "pg", "psql"],
        "children": [],
        "base_importance": 8,
    },
    "mysql": {
        "category": "hard_skill",
        "aliases": ["mariadb"],
        "children": [],
        "base_importance": 6,
    },
    "mongodb": {
        "category": "hard_skill",
        "aliases": ["mongo"],
        "children": ["mongoose"],
        "base_importance": 6,
    },
    "redis": {
        "category": "hard_skill",
        "aliases": [],
        "children": [],
        "base_importance": 7,
    },
    "elasticsearch": {
        "category": "hard_skill",
        "aliases": ["elastic", "es", "opensearch"],
        "children": ["kibana", "logstash", "elk stack"],
        "base_importance": 6,
    },
    "cassandra": {
        "category": "hard_skill",
        "aliases": [],
        "children": ["scylladb"],
        "base_importance": 6,
    },
    "neo4j": {
        "category": "hard_skill",
        "aliases": [],
        "children": ["cypher"],
        "base_importance": 5,
    },
    "sqlite": {
        "category": "hard_skill",
        "aliases": [],
        "children": [],
        "base_importance": 4,
    },
    "dynamodb": {
        "category": "hard_skill",
        "aliases": ["dynamo db"],
        "children": [],
        "base_importance": 6,
    },

    # ─── Data Engineering ───
    "spark": {
        "category": "hard_skill",
        "aliases": ["apache spark", "pyspark"],
        "children": ["spark sql", "spark streaming", "spark mllib"],
        "base_importance": 8,
    },
    "airflow": {
        "category": "hard_skill",
        "aliases": ["apache airflow"],
        "children": [],
        "base_importance": 7,
    },
    "kafka": {
        "category": "hard_skill",
        "aliases": ["apache kafka"],
        "children": ["kafka streams", "kafka connect", "ksql",
                      "confluent", "schema registry"],
        "base_importance": 8,
    },
    "dbt": {
        "category": "hard_skill",
        "aliases": ["data build tool"],
        "children": [],
        "base_importance": 7,
    },
    "snowflake": {
        "category": "hard_skill",
        "aliases": [],
        "children": [],
        "base_importance": 7,
    },
    "databricks": {
        "category": "hard_skill",
        "aliases": [],
        "children": ["delta lake", "mlflow"],
        "base_importance": 7,
    },
    "flink": {
        "category": "hard_skill",
        "aliases": ["apache flink"],
        "children": [],
        "base_importance": 6,
    },
    "etl": {
        "category": "methodology",
        "aliases": ["elt", "data pipelines", "data pipeline"],
        "children": [],
        "base_importance": 6,
    },
    "data modeling": {
        "category": "hard_skill",
        "aliases": ["data model", "dimensional modeling"],
        "children": [],
        "base_importance": 6,
    },
    "data warehouse": {
        "category": "hard_skill",
        "aliases": ["data warehousing", "dwh"],
        "children": ["snowflake", "bigquery", "redshift"],
        "base_importance": 6,
    },

    # ─── ML / AI ───
    "machine learning": {
        "category": "hard_skill",
        "aliases": ["ml"],
        "children": [
            "supervised learning", "unsupervised learning",
            "reinforcement learning", "feature engineering",
            "model training", "model serving", "model evaluation",
        ],
        "base_importance": 9,
    },
    "deep learning": {
        "category": "hard_skill",
        "aliases": ["dl"],
        "children": [
            "cnn", "rnn", "lstm", "transformer", "attention mechanism",
            "gan", "vae", "diffusion models",
        ],
        "base_importance": 8,
    },
    "pytorch": {
        "category": "hard_skill",
        "aliases": ["torch"],
        "children": ["pytorch lightning"],
        "base_importance": 8,
    },
    "tensorflow": {
        "category": "hard_skill",
        "aliases": ["tf framework"],
        "children": ["keras", "tf lite", "tf serving"],
        "base_importance": 7,
    },
    "nlp": {
        "category": "hard_skill",
        "aliases": ["natural language processing"],
        "children": ["tokenization", "ner", "sentiment analysis",
                      "text classification", "language model"],
        "base_importance": 7,
    },
    "computer vision": {
        "category": "hard_skill",
        "aliases": ["cv"],
        "children": ["object detection", "image segmentation",
                      "image classification", "ocr"],
        "base_importance": 7,
    },
    "llm": {
        "category": "hard_skill",
        "aliases": ["large language model", "large language models"],
        "children": ["gpt", "claude", "gemini", "llama",
                      "fine-tuning", "rag", "prompt engineering",
                      "langchain", "llamaindex"],
        "base_importance": 8,
    },
    "mlops": {
        "category": "hard_skill",
        "aliases": [],
        "children": ["mlflow", "kubeflow", "sagemaker", "vertex ai",
                      "model monitoring", "feature store"],
        "base_importance": 7,
    },
    "scikit-learn": {
        "category": "hard_skill",
        "aliases": ["sklearn", "scikit learn"],
        "children": [],
        "base_importance": 6,
    },
    "huggingface": {
        "category": "tool",
        "aliases": ["hugging face", "hf"],
        "children": ["transformers library"],
        "base_importance": 6,
    },

    # ─── Monitoring & Observability ───
    "monitoring": {
        "category": "hard_skill",
        "aliases": ["observability"],
        "children": ["prometheus", "grafana", "datadog", "new relic",
                      "splunk", "pagerduty", "opsgenie", "jaeger",
                      "opentelemetry"],
        "base_importance": 6,
    },
    "prometheus": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 5,
    },
    "grafana": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 5,
    },
    "datadog": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 5,
    },

    # ─── Messaging & Queues ───
    "rabbitmq": {
        "category": "hard_skill",
        "aliases": ["rabbit mq"],
        "children": [],
        "base_importance": 5,
    },
    "celery": {
        "category": "hard_skill",
        "aliases": [],
        "children": [],
        "base_importance": 5,
    },

    # ─── Architecture / Methodologies ───
    "microservices": {
        "category": "methodology",
        "aliases": ["micro services", "microservice architecture"],
        "children": ["service mesh", "api gateway", "event-driven"],
        "base_importance": 7,
    },
    "distributed systems": {
        "category": "hard_skill",
        "aliases": ["distributed computing"],
        "children": ["consensus", "cap theorem", "eventual consistency",
                      "distributed databases", "replication"],
        "base_importance": 8,
    },
    "system design": {
        "category": "hard_skill",
        "aliases": ["systems design", "architecture design"],
        "children": [],
        "base_importance": 7,
    },
    "event-driven": {
        "category": "methodology",
        "aliases": ["event driven architecture", "eda",
                    "event sourcing", "cqrs"],
        "children": [],
        "base_importance": 6,
    },
    "agile": {
        "category": "methodology",
        "aliases": [],
        "children": ["scrum", "kanban", "sprint", "retrospective"],
        "base_importance": 3,
    },
    "tdd": {
        "category": "methodology",
        "aliases": ["test driven development"],
        "children": [],
        "base_importance": 4,
    },
    "devops": {
        "category": "methodology",
        "aliases": [],
        "children": ["ci/cd", "infrastructure as code", "iac"],
        "base_importance": 6,
    },
    "sre": {
        "category": "methodology",
        "aliases": ["site reliability engineering", "site reliability"],
        "children": ["slo", "sla", "sli", "error budget",
                      "incident response", "postmortem"],
        "base_importance": 6,
    },

    # ─── Testing ───
    "testing": {
        "category": "hard_skill",
        "aliases": ["software testing"],
        "children": ["unit testing", "integration testing", "e2e testing",
                      "load testing", "performance testing"],
        "base_importance": 5,
    },
    "pytest": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 4,
    },
    "jest": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 4,
    },
    "cypress": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 4,
    },
    "selenium": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 4,
    },

    # ─── Version Control ───
    "git": {
        "category": "tool",
        "aliases": [],
        "children": ["github", "gitlab", "bitbucket"],
        "base_importance": 2,
    },

    # ─── Generic low-importance tools ───
    "jira": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 1,
    },
    "slack": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 1,
    },
    "confluence": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 1,
    },
    "notion": {
        "category": "tool",
        "aliases": [],
        "children": [],
        "base_importance": 2,
    },
    "linux": {
        "category": "hard_skill",
        "aliases": ["unix"],
        "children": [],
        "base_importance": 4,
    },

    # ─── Security ───
    "security": {
        "category": "hard_skill",
        "aliases": ["application security", "appsec", "infosec",
                    "information security"],
        "children": ["oauth", "jwt", "owasp", "encryption",
                      "penetration testing", "vulnerability assessment"],
        "base_importance": 6,
    },

    # ─── Mobile ───
    "ios": {
        "category": "hard_skill",
        "aliases": ["ios development"],
        "children": ["swift", "swiftui", "uikit", "xcode"],
        "base_importance": 7,
    },
    "android": {
        "category": "hard_skill",
        "aliases": ["android development"],
        "children": ["kotlin", "jetpack compose", "android studio"],
        "base_importance": 7,
    },
    "react native": {
        "category": "hard_skill",
        "aliases": [],
        "children": [],
        "base_importance": 6,
    },
    "flutter": {
        "category": "hard_skill",
        "aliases": [],
        "children": [],
        "base_importance": 6,
    },

    # ─── Soft Skills ───
    "leadership": {
        "category": "soft_skill",
        "aliases": ["team leadership", "technical leadership"],
        "children": [],
        "base_importance": 5,
    },
    "communication": {
        "category": "soft_skill",
        "aliases": ["written communication", "verbal communication",
                    "communication skills"],
        "children": [],
        "base_importance": 3,
    },
    "mentoring": {
        "category": "soft_skill",
        "aliases": ["mentorship", "coaching"],
        "children": [],
        "base_importance": 4,
    },
    "collaboration": {
        "category": "soft_skill",
        "aliases": ["teamwork", "team player", "cross-functional"],
        "children": [],
        "base_importance": 3,
    },
    "problem-solving": {
        "category": "soft_skill",
        "aliases": ["problem solving", "analytical thinking",
                    "critical thinking"],
        "children": [],
        "base_importance": 3,
    },
    "project management": {
        "category": "soft_skill",
        "aliases": [],
        "children": [],
        "base_importance": 4,
    },
    "stakeholder management": {
        "category": "soft_skill",
        "aliases": ["stakeholder communication"],
        "children": [],
        "base_importance": 4,
    },

    # ─── Certifications ───
    "aws certified": {
        "category": "certification",
        "aliases": ["aws certification", "aws certified solutions architect",
                    "aws certified developer"],
        "children": [],
        "base_importance": 5,
    },
    "cka": {
        "category": "certification",
        "aliases": ["certified kubernetes administrator"],
        "children": [],
        "base_importance": 5,
    },
    "ckad": {
        "category": "certification",
        "aliases": ["certified kubernetes application developer"],
        "children": [],
        "base_importance": 5,
    },
    "pmp": {
        "category": "certification",
        "aliases": ["project management professional"],
        "children": [],
        "base_importance": 4,
    },
    "scrum master": {
        "category": "certification",
        "aliases": ["csm", "certified scrum master"],
        "children": [],
        "base_importance": 3,
    },
    "cissp": {
        "category": "certification",
        "aliases": ["certified information systems security professional"],
        "children": [],
        "base_importance": 5,
    },

    # ─── Data Science ───
    "statistics": {
        "category": "hard_skill",
        "aliases": ["statistical analysis", "statistical modeling"],
        "children": ["hypothesis testing", "regression", "bayesian"],
        "base_importance": 6,
    },
    "data visualization": {
        "category": "hard_skill",
        "aliases": ["data viz"],
        "children": ["tableau", "power bi", "matplotlib", "d3.js",
                      "plotly", "seaborn"],
        "base_importance": 5,
    },
    "a/b testing": {
        "category": "hard_skill",
        "aliases": ["ab testing", "experimentation"],
        "children": [],
        "base_importance": 5,
    },

    # ─── Product ───
    "product strategy": {
        "category": "hard_skill",
        "aliases": ["product vision", "product roadmap", "roadmap"],
        "children": [],
        "base_importance": 7,
    },
    "user research": {
        "category": "hard_skill",
        "aliases": ["ux research", "customer research"],
        "children": [],
        "base_importance": 5,
    },
    "analytics": {
        "category": "hard_skill",
        "aliases": ["data analytics", "product analytics"],
        "children": ["google analytics", "mixpanel", "amplitude",
                      "segment"],
        "base_importance": 5,
    },
}


# ── Layer 2: Alias Resolution ────────────────────────────────────────

def _build_alias_map() -> dict[str, str]:
    """Build alias → canonical skill mapping from SKILL_GRAPH."""
    aliases: dict[str, str] = {}
    for skill_name, info in SKILL_GRAPH.items():
        for alias in info.get("aliases", []):
            aliases[alias.lower()] = skill_name
    return aliases


ALIAS_MAP: dict[str, str] = _build_alias_map()


# ── Layer 3: Noun Phrase Extraction ──────────────────────────────────

# Patterns for auto-detecting technical noun phrases not in the ontology
_TECH_NOUN_PHRASE_PATTERNS = [
    # "Apache X", "Google X", "Amazon X" etc.
    re.compile(r"\b((?:Apache|Google|Amazon|Microsoft|Meta|Oracle|IBM|HashiCorp|"
               r"JetBrains|Elastic|Confluent|Cloudflare)\s+[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)?)\b"),
    # "X Framework", "X Engine", "X Platform", "X SDK", "X API"
    re.compile(r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)?\s+"
               r"(?:Framework|Engine|Platform|SDK|API|Library|Runtime|Server|Client|CLI|Protocol))\b"),
    # Version-bearing: "X N.N", "X vN"
    re.compile(r"\b([A-Z][a-zA-Z0-9]+(?:\.\w+)?\s+(?:v?\d+(?:\.\d+)*))\b"),
]


def extract_noun_phrases(text: str) -> set[str]:
    """
    Extract technical noun phrases from text that are NOT in the curated ontology.
    Returns lowercased phrases.
    """
    all_known = set(SKILL_GRAPH.keys()) | set(ALIAS_MAP.keys())
    # Also collect children
    for info in SKILL_GRAPH.values():
        for child in info.get("children", []):
            all_known.add(child.lower())

    extracted: set[str] = set()
    for pattern in _TECH_NOUN_PHRASE_PATTERNS:
        for match in pattern.finditer(text):
            phrase = match.group(1).strip().lower()
            if phrase not in all_known and len(phrase) > 3:
                extracted.add(phrase)

    return extracted


# ── Skill Info Lookup ────────────────────────────────────────────────


@dataclass
class SkillInfo:
    """Resolved skill information."""
    canonical_name: str
    category: str = "hard_skill"
    base_importance: int = 5
    children: list[str] = field(default_factory=list)
    is_noun_phrase: bool = False


def resolve_skill(term: str) -> SkillInfo | None:
    """
    Resolve a term to its canonical skill info.
    Checks: exact match → alias → child lookup.
    Returns None if the term is not in the ontology.
    """
    term_lower = term.lower().strip()

    # Exact match
    if term_lower in SKILL_GRAPH:
        info = SKILL_GRAPH[term_lower]
        return SkillInfo(
            canonical_name=term_lower,
            category=info.get("category", "hard_skill"),
            base_importance=info.get("base_importance", 5),
            children=info.get("children", []),
        )

    # Alias match
    if term_lower in ALIAS_MAP:
        canonical = ALIAS_MAP[term_lower]
        info = SKILL_GRAPH[canonical]
        return SkillInfo(
            canonical_name=canonical,
            category=info.get("category", "hard_skill"),
            base_importance=info.get("base_importance", 5),
            children=info.get("children", []),
        )

    # Check if it's a child of some parent
    for parent_name, parent_info in SKILL_GRAPH.items():
        children_lower = [c.lower() for c in parent_info.get("children", [])]
        if term_lower in children_lower:
            return SkillInfo(
                canonical_name=term_lower,
                category=parent_info.get("category", "hard_skill"),
                base_importance=max(1, parent_info.get("base_importance", 5) - 1),
                children=[],
            )

    return None


def get_parent_of(child_term: str) -> str | None:
    """Find the parent skill of a child term."""
    child_lower = child_term.lower().strip()
    for parent_name, parent_info in SKILL_GRAPH.items():
        children_lower = [c.lower() for c in parent_info.get("children", [])]
        if child_lower in children_lower:
            return parent_name
    return None


def get_children_of(parent_term: str) -> list[str]:
    """Get all children of a parent skill."""
    parent_lower = parent_term.lower().strip()

    # Resolve aliases first
    if parent_lower in ALIAS_MAP:
        parent_lower = ALIAS_MAP[parent_lower]

    if parent_lower in SKILL_GRAPH:
        return [c.lower() for c in SKILL_GRAPH[parent_lower].get("children", [])]

    return []


# ── All Known Terms (sorted longest-first for matching) ──────────────


def _build_all_terms() -> list[str]:
    """Build sorted list of all known terms for longest-match-first scanning."""
    terms: set[str] = set()

    for skill_name, info in SKILL_GRAPH.items():
        terms.add(skill_name)
        for alias in info.get("aliases", []):
            terms.add(alias.lower())
        for child in info.get("children", []):
            terms.add(child.lower())

    # Sort by number of words (descending), then length (descending)
    # This ensures "machine learning" matches before "machine"
    return sorted(terms, key=lambda t: (-len(t.split()), -len(t)))


ALL_KNOWN_TERMS: list[str] = _build_all_terms()


def find_skills_in_text(text: str) -> dict[str, str]:
    """
    Find all known skills in text using longest-match-first scanning.

    Returns dict of {matched_term: canonical_name}.
    Multi-word terms are matched before single-word terms.
    """
    text_lower = text.lower()
    found: dict[str, str] = {}
    # Track matched positions to avoid double-counting
    matched_positions: list[tuple[int, int]] = []

    for term in ALL_KNOWN_TERMS:
        # Use word boundary matching
        pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
        for match in pattern.finditer(text_lower):
            start, end = match.start(), match.end()

            # Check if this position overlaps with an already-matched term
            overlap = False
            for ms, me in matched_positions:
                if start < me and end > ms:
                    overlap = True
                    break

            if not overlap:
                matched_positions.append((start, end))
                # Resolve to canonical name
                resolved = resolve_skill(term)
                if resolved:
                    found[term] = resolved.canonical_name
                else:
                    found[term] = term

    return found
