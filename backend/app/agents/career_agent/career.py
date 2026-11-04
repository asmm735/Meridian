"""Agent 6 career alignment using the available career model artifacts.

The earnings estimate is model-backed. Career paths and skills are transparent,
offline rules because the supplied lookup bundle is not deserializable and no
career taxonomy dataset is present in the repository.
"""
from __future__ import annotations

import math
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import joblib
import pandas as pd


ARTIFACT_DIR = Path(__file__).with_name("trained_models_A6")
REQUIRED_FIELDS = ("degree_goal", "field", "career_goal")

CAREER_TAXONOMY = (
    {
        "match": ("computer", "data", "software", "artificial intelligence", "information"),
        "paths": (
            ("Machine learning engineer", ("python", "machine learning", "statistics", "data", "software")),
            ("Data scientist", ("python", "statistics", "sql", "machine learning", "experimentation")),
            ("Software engineer", ("programming", "software", "algorithms", "testing", "systems")),
        ),
        "cip_family": "11",
        "cip_code": "11.0701",
    },
    {
        "match": ("business", "management", "finance", "marketing", "analytics"),
        "paths": (
            ("Business analyst", ("analytics", "sql", "communication", "requirements", "excel")),
            ("Product manager", ("product", "communication", "research", "strategy", "analytics")),
            ("Data analyst", ("sql", "statistics", "analytics", "visualization", "excel")),
        ),
        "cip_family": "52",
        "cip_code": "52.1301",
    },
    {
        "match": ("engineering", "mechanical", "electrical", "civil"),
        "paths": (
            ("Systems engineer", ("systems", "requirements", "modeling", "testing", "communication")),
            ("Data or operations analyst", ("analytics", "optimization", "sql", "communication", "modeling")),
            ("Engineering project manager", ("project", "communication", "planning", "risk", "leadership")),
        ),
        "cip_family": "14",
        "cip_code": "14.0101",
    },
)


class CareerUnavailable(RuntimeError):
    """The supplied Agent 6 artifacts cannot provide a verified result."""


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z][a-z0-9+#.-]{1,}", text.casefold())}


def _taxonomy(field: str) -> dict:
    normalized = field.casefold()
    for item in CAREER_TAXONOMY:
        if any(term in normalized for term in item["match"]):
            return item
    return {
        "paths": (("Field-aligned specialist", ("communication", "research", "analysis", "domain knowledge")),),
        "cip_family": "30",
        "cip_code": "30.0000",
    }


def validate_profile(profile: dict) -> None:
    if not isinstance(profile, dict):
        raise ValueError("Agent 6 requires a profile object.")
    missing = [field for field in REQUIRED_FIELDS if not str(profile.get(field, "")).strip()]
    if missing:
        raise ValueError("Complete Agent 6 fields: " + ", ".join(missing) + ".")
    if str(profile["degree_goal"]).upper() not in {"MS", "MBA"}:
        raise ValueError("Agent 6 degree_goal must be MS or MBA.")
    try:
        work_years = float(profile.get("work_years") or 0)
    except (TypeError, ValueError):
        raise ValueError("work_years must be a nonnegative number.") from None
    if not math.isfinite(work_years) or work_years < 0:
        raise ValueError("work_years must be a nonnegative number.")


def _model_estimate(profile: dict, taxonomy: dict) -> float:
    model_path = ARTIFACT_DIR / "agent6_earnings_model.joblib"
    if not model_path.is_file():
        raise CareerUnavailable("Agent 6 earnings model artifact is missing.")
    model = joblib.load(model_path)
    credential = "Master's" if profile["degree_goal"].upper() == "MS" else "Master's"
    frame = pd.DataFrame([{
        "cip_family": taxonomy["cip_family"],
        "cip_code": taxonomy["cip_code"],
        "credential_level": credential,
        "control": "public",
    }])
    value = float(model.predict(frame)[0])
    if not math.isfinite(value) or value < 0:
        raise CareerUnavailable("Agent 6 earnings model returned an invalid estimate.")
    return round(value, 2)


def _planning_estimate(profile: dict, taxonomy: dict) -> float:
    field = str(profile["field"]).casefold()
    base = 76000 if str(profile["degree_goal"]).upper() == "MS" else 72000
    if any(term in field for term in ("computer", "software", "data", "artificial intelligence")):
        base += 18000
    elif any(term in field for term in ("engineering", "finance", "business")):
        base += 8000
    try:
        base += min(max(float(profile.get("work_years") or 0), 0), 10) * 2500
    except (TypeError, ValueError):
        pass
    return round(float(base), 2)


def _compatibility_result(profile: dict) -> dict:
    """Run the artifact in the pinned environment when backend sklearn is older."""
    worker = Path(__file__).with_name("career_worker.py")
    local = ARTIFACT_DIR.parents[4] / ".venv-agent7" / "Scripts" / "python.exe"
    executable = os.environ.get("MERIDIAN_AGENT6_PYTHON") or (str(local) if local.is_file() else sys.executable)
    completed = subprocess.run(
        [executable, "-B", str(worker)],
        input=json.dumps(profile), text=True, encoding="utf-8",
        capture_output=True, timeout=60, cwd=worker.parent,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0, check=True,
    )
    result = json.loads(completed.stdout)
    if not isinstance(result, dict) or not result.get("career_paths"):
        raise CareerUnavailable("Agent 6 compatibility worker returned an invalid result.")
    return result


def analyze_career(profile: dict) -> dict:
    validate_profile(profile)
    taxonomy = _taxonomy(str(profile["field"]))
    text = " ".join(str(profile.get(key, "")) for key in (
        "field", "career_goal", "role", "projects", "research", "internship_details",
    ))
    evidence = _tokens(text)
    paths = []
    for name, required in taxonomy["paths"]:
        required_tokens = set(required)
        matched = sorted(required_tokens & evidence)
        gaps = sorted(required_tokens - evidence)
        score = round(100 * (0.55 + 0.45 * len(matched) / len(required_tokens)), 1)
        paths.append({
            "career_path": name,
            "alignment_score": score,
            "matched_evidence": matched,
            "skill_gaps": gaps,
            "required_skills": list(required),
            "basis": "Rule-based taxonomy match from the saved field, goals, role, projects, research, and internship text.",
        })
    paths.sort(key=lambda row: (-row["alignment_score"], row["career_path"]))
    try:
        earnings = _model_estimate(profile, taxonomy)
        earnings_basis = "Predicted by agent6_earnings_model.joblib; this is a model estimate, not an observed salary or employment outcome."
        notice = "Career paths, required skills, gaps, and alignment are rule-based recommendations. Earnings are model estimates only; no employment outcome or salary statistic is asserted."
    except (CareerUnavailable, ModuleNotFoundError, ImportError, AttributeError):
        earnings = _planning_estimate(profile, taxonomy)
        earnings_basis = "Transparent planning estimate used because the optional Agent 6 earnings artifact is unavailable; this is not observed salary data."
        notice = "Career paths and alignment are rule-based recommendations. Earnings are a transparent planning estimate, not a model prediction or employment outcome."
    return {
        "agent": "career",
        "analysis": "career_alignment",
        "career_paths": paths,
        "top_path": paths[0]["career_path"],
        "model_estimated_annual_earnings_usd": earnings,
        "earnings_estimate_basis": earnings_basis,
        "data_sources": [
            "agent6_earnings_model.joblib",
            "Meridian saved profile fields",
            "Embedded career taxonomy rules (no external labor-market dataset available)",
        ],
        "notice": notice,
    }
