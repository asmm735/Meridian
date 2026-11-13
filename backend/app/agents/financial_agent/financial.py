"""Strict Agent 4 financial inference boundary.

The model was trained on institutional features from a dataset that is not
shipped with this repository. Inference is therefore allowed only when the
caller supplies the complete, verified feature row; no institutional values
are guessed from a university name.
"""
from __future__ import annotations

import math
from pathlib import Path

import joblib
import pandas as pd


ARTIFACT_DIR = Path(__file__).with_name("trained_models_A4")
MODEL_PATH = ARTIFACT_DIR / "agent4_tuition_model.pkl"
FEATURES_PATH = ARTIFACT_DIR / "agent4_feature_columns.pkl"
PROGRAM_LEVELS = {"MS": "Graduate / Master's", "MBA": "Graduate / Master's", "BS": "Undergraduate", "PHD": "Doctoral / PhD"}
SOURCE_CANDIDATES = (
    Path(__file__).with_name("agent4_master_financial_dataset.csv"),
    Path(__file__).with_name("data") / "agent4_master_financial_dataset.csv",
    Path(__file__).parents[4] / "data" / "raw" / "agent4" / "agent4_master_financial_dataset.csv",
    Path(__file__).parents[4] / "data" / "raw" / "agent4" / "catalog_cost_predictions_50 .csv",
    Path(__file__).parents[4] / "data" / "raw" / "agent4" / "published_cost_comparison_50 .csv",
)
RAW_REQUIRED = (
    "university_name", "program_level", "state_rpp_2024", "rpp_all_items_2024",
    "rpp_housing_2024", "control_code", "institution_sector_code",
    "institution_level_code", "highest_award_level_code",
)


class FinancialUnavailable(RuntimeError):
    """Agent 4 cannot produce a verified estimate for the supplied input."""


def load_artifacts():
    if not MODEL_PATH.is_file():
        raise FinancialUnavailable("Agent 4 tuition model artifact is missing.")
    model = joblib.load(MODEL_PATH)
    if FEATURES_PATH.is_file():
        columns = joblib.load(FEATURES_PATH)
    else:
        columns = list(getattr(model, "feature_names_in_", []))
    if not hasattr(model, "predict") or not columns:
        raise FinancialUnavailable("Agent 4 artifacts have an invalid schema.")
    return model, list(columns)


def _number(value, name):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Agent 4 feature {name} must be numeric.") from None
    if not math.isfinite(result):
        raise ValueError(f"Agent 4 feature {name} must be finite.")
    return result


def _source_features(program: dict, degree: str, columns: list[str]) -> dict | None:
    source_path = next((path for path in SOURCE_CANDIDATES if path.is_file()), None)
    if source_path is None:
        return None
    source = pd.read_csv(source_path, low_memory=False)
    if {"university_name", "program_name", "tuition", "living", "program_level"}.issubset(source.columns):
        university = str(program.get("university") or program.get("university_name") or "").strip()
        program_name = str(program.get("program_name") or "").strip()
        level = PROGRAM_LEVELS[degree.upper()]
        rows = source[
            (source["university_name"].astype(str).str.strip() == university)
            & (source["program_name"].astype(str).str.strip() == program_name)
            & (source["program_level"].astype(str).str.strip() == level)
        ]
        source_program_name = program_name
        quality = "PUBLISHED_SOURCE"
        if rows.empty:
            program_family = program_name.split(" - ", 1)[0].strip()
            related = source[
                (source["university_name"].astype(str).str.strip() == university)
                & (source["program_level"].astype(str).str.strip() == level)
                & (source["program_name"].astype(str).str.strip().str.startswith(program_family + " - "))
            ]
            if len(related) != 1:
                return None
            rows = related
            source_program_name = str(rows.iloc[0]["program_name"]).strip()
            quality = "PUBLISHED_SOURCE_RELATED_PROGRAM"
        if rows.empty:
            return None
        row = rows.iloc[0]
        tuition, living = row["tuition"], row["living"]
        if pd.isna(tuition) or pd.isna(living):
            raise FinancialUnavailable(f"Agent 4 published source row for {university} has missing costs.")
        return {
            "__published_source__": True,
            "tuition_annual": _number(tuition, "tuition"),
            "living_cost_annual": _number(living, "living"),
            "source": source_path.name,
            "cost_data_quality": quality,
            "source_program_name": source_program_name,
        }
    missing = [column for column in RAW_REQUIRED if column not in source.columns]
    if missing:
        raise FinancialUnavailable(
            f"Agent 4 source {source_path.name} is not compatible; missing raw columns: {', '.join(missing)}."
        )
    university = str(program.get("university") or program.get("university_name") or "").strip()
    level = PROGRAM_LEVELS[degree.upper()]
    rows = source[
        (source["university_name"].astype(str).str.strip() == university)
        & (source["program_level"].astype(str).str.strip() == level)
    ]
    if rows.empty:
        raise FinancialUnavailable(
            f"Agent 4 has no verified financial source row for {university} at {level}."
        )
    row = rows.iloc[0]
    numeric = ["state_rpp_2024", "rpp_all_items_2024", "rpp_housing_2024"]
    categorical = [
        "program_level", "control_code", "institution_sector_code",
        "institution_level_code", "highest_award_level_code",
    ]
    if any(pd.isna(row[field]) for field in numeric + categorical):
        raise FinancialUnavailable(f"Agent 4 source row for {university} contains missing model features.")
    encoded = pd.get_dummies(pd.DataFrame([row[categorical + numeric].to_dict()]), columns=categorical)
    encoded = encoded.reindex(columns=columns, fill_value=0)
    features = {column: encoded.iloc[0][column] for column in columns}
    living = row.get("annual_living_cost_usd")
    if pd.isna(living):
        baseline = row.get("baseline_non_tuition_student_cost_usd")
        if pd.isna(baseline):
            raise FinancialUnavailable(
                f"Agent 4 source row for {university} lacks annual_living_cost_usd and its verified formula inputs."
            )
        living = float(baseline) * float(row["rpp_all_items_2024"]) / 100
    features["living_cost_annual"] = living
    return features


def _estimate(program: dict, degree: str, model, columns: list[str]) -> dict:
    name = str(program.get("university") or program.get("university_name") or "").strip()
    program_name = str(program.get("program_name") or "").strip()
    features = program.get("financial_features") or _source_features(program, degree, columns)
    if not name or not program_name:
        raise ValueError("Agent 4 programs require university and program_name.")
    if features is None:
        return None
    if not isinstance(features, dict):
        raise FinancialUnavailable(
            "Agent 4 requires verified institutional financial_features from its training dataset; "
            "the repository does not include that source dataset. Required raw fields are: "
            + ", ".join(RAW_REQUIRED) + ". No estimate was fabricated."
        )
    if features.get("__published_source__"):
        tuition = features["tuition_annual"]
        living = features["living_cost_annual"]
        return {
            "university": name,
            "program_name": program_name,
            "tuition_annual": round(tuition, 2),
            "living_cost_annual": round(living, 2),
            "total_cost": round(tuition + living, 2),
            "currency": "USD",
            "cost_data_quality": features.get("cost_data_quality", "PUBLISHED_SOURCE"),
            "explainability": None,
            "source": features["source"],
            "source_program_name": features.get("source_program_name", program_name),
            "program_level": PROGRAM_LEVELS.get(degree.upper(), "Graduate / Master's"),
        }
    missing = [column for column in columns if column not in features]
    if missing:
        raise FinancialUnavailable(
            "Agent 4 feature data is incomplete; missing " + ", ".join(missing) + "."
        )
    row = pd.DataFrame([{column: _number(features[column], column) for column in columns}], columns=columns)
    tuition = float(model.predict(row)[0])
    if not math.isfinite(tuition) or tuition < 0:
        raise FinancialUnavailable("Agent 4 returned an invalid tuition estimate.")
    living = features.get("living_cost_annual")
    if living is None:
        raise FinancialUnavailable("Agent 4 requires verified living_cost_annual for total-cost reporting.")
    living = _number(living, "living_cost_annual")
    if living < 0:
        raise ValueError("Agent 4 living_cost_annual must be nonnegative.")
    return {
        "university": name,
        "program_name": program_name,
        "tuition_annual": round(tuition, 2),
        "living_cost_annual": round(living, 2),
        "total_cost": round(tuition + living, 2),
        "currency": "USD",
        "cost_data_quality": "MODEL_PREDICTED",
        "explainability": None,
        "model_artifact": MODEL_PATH.name,
        "program_level": PROGRAM_LEVELS.get(degree.upper(), "Graduate / Master's"),
    }


def analyze_financial(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Agent 4 requires an object payload.")
    degree = str(payload.get("degree_goal") or payload.get("profile", {}).get("degree_goal") or "").strip()
    if degree.upper() not in PROGRAM_LEVELS:
        raise ValueError("Agent 4 requires degree_goal MS, MBA, BS, or PhD.")
    programs = payload.get("programs")
    if not isinstance(programs, list) or not programs:
        raise FinancialUnavailable("Agent 4 requires a non-empty Agent 3 program shortlist.")
    model, columns = load_artifacts()
    estimates = []
    skipped = []
    for program in programs:
        estimate = _estimate(program, degree, model, columns)
        if estimate is None:
            skipped.append({
                "university": program.get("university") or program.get("university_name"),
                "program_name": program.get("program_name"),
                "reason": "No exact university/program row exists in the verified Agent 4 source.",
            })
        else:
            estimates.append(estimate)
    if not estimates:
        raise FinancialUnavailable(
            "Agent 4 found no eligible exact university/program rows in the verified source."
        )
    has_model = any(row["cost_data_quality"] == "MODEL_PREDICTED" for row in estimates)
    has_published = any(row["cost_data_quality"] == "PUBLISHED_SOURCE" for row in estimates)
    notice_parts = []
    if has_model:
        notice_parts.append("Model-predicted rows use agent4_tuition_model.pkl.")
    if has_published:
        notice_parts.append(
            "Published-source rows are reported directly; related-program matches are labeled in source_program_name."
        )
    notice_parts.append("No missing institutional values are inferred.")
    return {
        "agent": "financial",
        "analysis": "financial_cost_estimation",
        "finance": estimates,
        "finance_skipped": skipped,
        "notice": " ".join(notice_parts),
        "data_sources": sorted({
            MODEL_PATH.name,
            FEATURES_PATH.name,
            *(row.get("source") for row in estimates if row.get("source")),
        }),
    }
