"""Artifact-backed scholarship retrieval and conservative eligibility checks."""
from __future__ import annotations

import math
import re
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer


BASE = Path(__file__).resolve().parent / "trained_models_A5"
CATALOG_PATH = BASE / "agent5_scholarship_catalog.joblib"
VECTORIZER_PATH = BASE / "agent5_tfidf_vectorizer.joblib"
MATRIX_PATH = BASE / "agent5_tfidf_matrix.joblib"
CONFIG_PATH = BASE / "agent5_config.joblib"


class ScholarshipUnavailable(FileNotFoundError):
    """Raised when the supplied Agent 5 artifacts cannot be loaded."""


def _text(value: Any) -> str:
    if value is None or (not isinstance(value, (list, tuple, set)) and pd.isna(value)):
        return ""
    return str(value).strip()


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _norm(value: Any) -> str:
    value = _text(value).casefold()
    return {
        "usa": "united states", "us": "united states", "u.s.": "united states",
        "uk": "united kingdom", "u.k.": "united kingdom",
        "indian": "india", "american": "united states",
    }.get(value, value)


def _tokens(value: Any) -> set[str]:
    return {_norm(item) for item in re.split(r"[|;,]", _text(value)) if _text(item)}


def _degree(value: Any) -> str:
    return {
        "ms": "masters", "msc": "masters", "master": "masters",
        "master of science": "masters", "mba": "mba",
        "bsc": "bachelors", "bachelor": "bachelors", "phd": "phd",
    }.get(_text(value).casefold().replace(".", ""), _text(value).casefold())


def _field(profile: dict[str, Any]) -> str:
    return _text(profile.get("field") or profile.get("field_of_study") or profile.get("target_program"))


def _load_artifacts() -> tuple[pd.DataFrame, Any, Any, dict[str, Any]]:
    try:
        catalog = joblib.load(CATALOG_PATH)
    except (OSError, ValueError, EOFError, ImportError, AttributeError) as exc:
        raise ScholarshipUnavailable("Agent 5 scholarship artifacts are unavailable.") from exc
    if not isinstance(catalog, pd.DataFrame):
        raise ScholarshipUnavailable("Agent 5 artifacts have an invalid schema.")
    retrieval_loaded = False
    if VECTORIZER_PATH.is_file() and MATRIX_PATH.is_file():
        try:
            vectorizer = joblib.load(VECTORIZER_PATH)
            matrix_bundle = joblib.load(MATRIX_PATH)
            if isinstance(matrix_bundle, dict):
                matrix = matrix_bundle.get("matrix")
                ids = matrix_bundle.get("scholarship_ids")
                retrieval_loaded = matrix is not None and ids is not None
        except (OSError, ValueError, EOFError, ImportError, AttributeError, TypeError):
            retrieval_loaded = False
    if not retrieval_loaded:
        text_columns = [column for column in catalog.columns if catalog[column].dtype == "object"]
        corpus = catalog[text_columns].fillna("").astype(str).agg(" ".join, axis=1)
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        matrix = vectorizer.fit_transform(corpus)
        ids = catalog["scholarship_id"].astype(str).tolist() if "scholarship_id" in catalog else list(range(len(catalog)))
    matrix_rows = getattr(matrix, "shape", (None,))[0] if matrix is not None else None
    if matrix is None or ids is None or len(catalog) != len(ids) or matrix_rows != len(catalog):
        raise ScholarshipUnavailable("Agent 5 retrieval artifacts do not match the scholarship catalog.")
    required = {"scholarship_id", "scholarship_name"}
    if not required.issubset(catalog.columns):
        raise ScholarshipUnavailable("Agent 5 catalog is missing required columns.")
    config = {}
    if CONFIG_PATH.is_file():
        try:
            loaded_config = joblib.load(CONFIG_PATH)
            config = loaded_config if isinstance(loaded_config, dict) else {}
        except (OSError, ValueError, EOFError, ImportError, AttributeError):
            config = {}
    return catalog, vectorizer, matrix, config


def _eligibility(row: dict[str, Any], profile: dict[str, Any], finance: dict[str, Any], today: date) -> tuple[str, list[str]]:
    failed: list[str] = []
    unknown: list[str] = []

    def requirement(label: str, allowed: Any, actual: Any) -> None:
        choices = _tokens(allowed)
        if "all" in choices:
            return
        if not choices or not _text(actual):
            unknown.append(label)
            return
        if label == "degree":
            actual_degree = _degree(actual)
            if actual_degree in choices or ("masters" in choices and actual_degree in {"ms", "mba", "meng"}):
                return
        elif label == "field":
            actual_field = re.sub(r"[^a-z0-9 ]", "", _field(profile).casefold()).strip()
            if actual_field and any(actual_field == re.sub(r"[^a-z0-9 ]", "", item).strip() for item in choices):
                return
            unknown.append("field equivalence requires review")
            return
        elif _norm(actual) in choices:
            return
        failed.append(label)

    requirement("nationality", row.get("eligible_nationalities"), profile.get("nationality"))
    requirement("field", row.get("eligible_fields"), _field(profile))
    requirement("degree", row.get("eligible_degrees"), profile.get("degree_goal"))

    minimum = _number(row.get("min_gpa"))
    if minimum is not None and minimum > 0:
        gpa, scale, required_scale = (_number(profile.get("gpa")), _number(profile.get("gpa_scale")), _number(row.get("gpa_scale")))
        if gpa is None or scale is None or required_scale is None:
            unknown.append("GPA or GPA scale")
        elif gpa / scale + 1e-12 < minimum / required_scale:
            failed.append("GPA cutoff")

    deadline = _text(row.get("deadline"))
    policy = _text(row.get("deadline_policy")).casefold()
    if policy == "fixed":
        try:
            if pd.Timestamp(deadline).date() < today:
                failed.append("expired deadline")
        except (TypeError, ValueError):
            unknown.append("deadline")
    elif policy != "open":
        unknown.append("deadline policy")

    status = "ineligible" if failed else ("unknown" if unknown else "eligible")
    return status, failed + [f"unknown: {reason}" for reason in unknown]


def _coverage(row: dict[str, Any], finance: dict[str, Any]) -> tuple[float | None, str | None]:
    total = _number(finance.get("total_cost"))
    if total is None or total < 0:
        return None, "missing or invalid annual cost"
    currency = _text(finance.get("currency")).upper()
    if not currency or _text(row.get("currency")).upper() != currency:
        return None, "currency mismatch"
    if _text(row.get("amount_period")).casefold() != "annual":
        return None, "nonannual or missing award period"
    basis = _text(row.get("coverage_basis")).casefold()
    base = _number(finance.get("tuition_annual" if basis == "tuition" else "total_cost")) if basis in {"tuition", "total"} else None
    percent, amount = _number(row.get("coverage_percent")), _number(row.get("amount"))
    if base is None or ((percent is None) == (amount is None)):
        return None, "unknown coverage basis or award amount"
    if percent is not None:
        if not 0 <= percent <= 100:
            return None, "coverage percent outside 0-100"
        amount = base * percent / 100
    if amount is None or amount < 0:
        return None, "invalid award amount"
    return min(amount, base, total), None


def analyze_scholarships(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("profile"), dict):
        raise ValueError("Agent 5 requires a profile object.")
    finance = payload.get("finance")
    if not isinstance(finance, list) or not finance:
        raise ValueError("Agent 5 requires Agent 4 financial results.")
    top_k = payload.get("top_k", 10)
    if type(top_k) is not int or not 1 <= top_k <= 50:
        raise ValueError("top_k must be an integer from 1 to 50.")
    catalog, vectorizer, matrix, config = _load_artifacts()
    profile = payload["profile"]
    query = " ".join(_text(profile.get(key)) for key in ("field", "field_of_study", "interests_text", "programs"))
    query += " " + " ".join(_text(item.get("program_name")) for item in finance if isinstance(item, dict))
    query_vector = vectorizer.transform([query])
    scores = cosine_similarity(query_vector, matrix)[0] if query.strip() else [0.0] * len(catalog)
    today = pd.Timestamp.now(tz="Asia/Kolkata").date()
    outputs = []
    for item in finance:
        if not isinstance(item, dict):
            raise ValueError("Agent 5 finance entries must be objects.")
        recommendations, review = [], []
        for index, row in catalog.iterrows():
            record = row.to_dict()
            status, reasons = _eligibility(record, profile, item, today)
            coverage, coverage_error = _coverage(record, item)
            if status == "eligible" and coverage_error is None:
                recommendations.append({
                    "scholarship_id": _text(record.get("scholarship_id")),
                    "scholarship_name": _text(record.get("scholarship_name")),
                    "eligibility_match": "eligible",
                    "potential_annual_coverage": round(coverage or 0, 2),
                    "coverage_%": round(100 * (coverage or 0) / max(float(item["total_cost"]), 1), 2),
                    "currency": _text(item.get("currency")).upper(),
                    "deadline": _text(record.get("deadline")),
                    "source_url": _text(record.get("source_url") or record.get("application_url")),
                    "match_score": round(float(scores[index]), 6),
                })
            else:
                review.append({
                    "scholarship_id": _text(record.get("scholarship_id")),
                    "scholarship_name": _text(record.get("scholarship_name")),
                    "eligibility_match": status,
                    "reasons": reasons + ([coverage_error] if coverage_error else []),
                    "match_score": round(float(scores[index]), 6),
                    "source_url": _text(record.get("source_url") or record.get("application_url")),
                })
        recommendations.sort(key=lambda row: (-row["match_score"], -row["potential_annual_coverage"], row["scholarship_id"]))
        review.sort(key=lambda row: (-row["match_score"], row["scholarship_id"]))
        budget = _number(profile.get("budget"))
        if budget is None:
            budget = _number(profile.get("budget_annual"))
        total = _number(item.get("total_cost"))
        currency = _text(profile.get("budget_currency") or profile.get("currency")).upper()
        valid_budget = budget is not None and budget >= 0 and total is not None and currency == _text(item.get("currency")).upper()
        outputs.append({
            "university": _text(item.get("university")),
            "program_name": _text(item.get("program_name")),
            "currency": _text(item.get("currency")).upper(),
            "funding_gap": round(max(0, total - budget), 2) if valid_budget else None,
            "funding_status": "calculated_from_supplied_costs" if valid_budget else "unknown: verify annual budget and currency",
            "recommendations": recommendations[:top_k],
            "eligibility_review": review[:top_k],
            "catalog_counts": {"examined": len(catalog), "fully_recommendable": len(recommendations), "needs_review": len(review)},
            "retrieval": "tfidf",
            "catalogue_status": "supplied",
            "artifact_accuracy_status": config.get("accuracy_status", "NOT MEASURED"),
            "as_of": today.isoformat(),
        })
    return {"agent": "scholarship", "scholarships": outputs, "notice": "Agent 5 uses catalog retrieval and rule-based eligibility. Match scores are retrieval scores, not award probabilities."}
