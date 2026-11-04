import os
import math
import joblib
import pandas as pd

from app.config import Config
from app.utils.preprocessing import validate_profile_input, normalize_gpa


def _get_model_path(program_type: str):
    if program_type not in {"ms", "mba"}:
        raise ValueError(f"Unsupported program type: {program_type}")
    model_name = "ms_model.pkl" if program_type == "ms" else "mba_model.pkl"
    path = os.path.join(Config.MODEL_DIR, model_name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{model_name} is unavailable in {Config.MODEL_DIR}. "
            "The bundled *_tier_model.joblib artifacts are candidate-tier models "
            "with a different feature contract and cannot be used as MS/MBA outcome models."
        )
    return path


def predict_profile_outcome(payload, program_type: str):
    """Load trained model and return a prediction payload."""
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    validated = validate_profile_input(payload, program_type)
    cleaned = normalize_gpa(validated)

    model_path = _get_model_path(program_type)
    model = joblib.load(model_path)

    feature_names = getattr(model, "feature_names_in_", None)
    if feature_names is not None:
        dataframe = pd.DataFrame([cleaned], columns=feature_names)
        prediction = model.predict(dataframe)[0]
        probability = None
        if hasattr(model, "predict_proba"):
            probability = model.predict_proba(dataframe)[0].max()
        return {
            "program_type": program_type,
            "prediction": str(prediction),
            "probability": float(probability) if probability is not None else None,
            "input": cleaned,
        }

    dataframe = pd.DataFrame([cleaned])
    prediction = model.predict(dataframe)[0]
    return {
        "program_type": program_type,
        "prediction": str(prediction),
        "input": cleaned,
    }


def predict_candidate_tier(payload):
    """Run the bundled Agent 1 candidate-tier classifier."""
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    required = ("track", "gpa_normalized_4")
    missing = [key for key in required if payload.get(key) in (None, "")]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    track = str(payload["track"]).upper()
    if track not in {"MS", "MBA"}:
        raise ValueError("Agent 1 track must be MS or MBA.")

    model_dir = os.path.join(Config.MODEL_DIR)
    feature_path = os.path.join(model_dir, "feature_columns.joblib")
    model_path = os.path.join(model_dir, "rf_tier_model.joblib")
    if not os.path.isfile(model_path):
        raise FileNotFoundError("Agent 1 candidate-tier model artifacts are missing.")

    try:
        gpa = float(payload["gpa_normalized_4"])
        if not 0 <= gpa <= 4:
            raise ValueError("GPA must be between 0 and 4.")
    except (TypeError, ValueError):
        raise ValueError("gpa_normalized_4 must be a number between 0 and 4.") from None

    numeric = {
        "gpa_normalized_4": gpa,
        "gre_score": float(payload.get("gre_score") or 0),
        "toefl_score": float(payload.get("toefl_score") or 0),
        "has_research": float(payload.get("has_research") or 0),
        "university_rating": float(payload.get("university_rating") or 0),
        "admit_probability": float(payload.get("admit_probability") or 0),
        "gmat_score": float(payload.get("gmat_score") or 0),
        "work_experience_months": float(payload.get("work_experience_months") or 0),
    }
    if any(not math.isfinite(value) or value < 0 for value in numeric.values()):
        raise ValueError("Agent 1 numeric inputs must be finite and nonnegative.")
    row = {key: numeric[key] for key in numeric}
    row.update({
        "track": track,
        "admission_status": str(payload.get("admission_status") or "NA"),
        "major": str(payload.get("major") or "NA"),
        "work_industry": str(payload.get("work_industry") or "NA"),
    })
    if os.path.isfile(feature_path):
        columns = joblib.load(feature_path)
    else:
        model = joblib.load(model_path)
        columns = getattr(model, "feature_names_in_", None)
        if columns is None:
            raise FileNotFoundError("Agent 1 feature columns are unavailable.")
    encoded = pd.get_dummies(pd.DataFrame([row]), columns=["track", "admission_status", "major", "work_industry"])
    encoded = encoded.reindex(columns=columns, fill_value=0)
    model = joblib.load(model_path)
    prediction = int(model.predict(encoded)[0])
    probability = float(model.predict_proba(encoded)[0, 1]) if hasattr(model, "predict_proba") else None
    return {
        "agent": "profile",
        "analysis": "candidate_tier",
        "prediction": "Tier1" if prediction == 1 else "Tier2",
        "probability": probability,
        "input": row,
        "notice": "Agent 1 candidate-tier classification; this is not an admission probability.",
    }
