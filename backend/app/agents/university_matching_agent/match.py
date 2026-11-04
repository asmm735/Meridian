def match_universities(payload):
    """Return a filtered university list using a simple tier-based heuristic."""
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    academic_score = float(payload.get("gpa", 0.0) or 0.0)
    target_tier = payload.get("tier", "medium")
    preferred_country = payload.get("country", "USA")

    dataset = [
        {"name": "Harvard University", "country": "USA", "tier": "elite", "gpa": 3.9},
        {"name": "Stanford University", "country": "USA", "tier": "elite", "gpa": 3.8},
        {"name": "University of Michigan", "country": "USA", "tier": "high", "gpa": 3.7},
        {"name": "Northeastern University", "country": "USA", "tier": "medium", "gpa": 3.4},
        {"name": "University of Toronto", "country": "Canada", "tier": "high", "gpa": 3.6},
        {"name": "University of Manchester", "country": "UK", "tier": "medium", "gpa": 3.3},
        {"name": "Monash University", "country": "Australia", "tier": "medium", "gpa": 3.5},
    ]

    allowed_tiers = {
        "low": ["medium", "high", "elite"],
        "medium": ["medium", "high", "elite"],
        "high": ["high", "elite"],
        "elite": ["elite"],
    }

    matches = []
    for university in dataset:
        if university["country"].lower() != preferred_country.lower() and preferred_country.lower() != "all":
            continue
        if university["tier"] not in allowed_tiers.get(target_tier.lower(), [target_tier.lower()]):
            continue
        if academic_score >= university["gpa"] - 0.2:
            matches.append(university)

    notice = ""
    if not matches:
        candidates = [
            university for university in dataset
            if preferred_country.lower() == "all"
            or university["country"].lower() == preferred_country.lower()
        ]
        candidates.sort(key=lambda university: abs(academic_score - university["gpa"]))
        matches = candidates[:2]
        notice = (
            "No universities met the selected tier and GPA threshold. "
            "Showing the closest catalog options so program and financial analysis can continue."
        )

    return {
        "tier": target_tier,
        "country": preferred_country,
        "matched_universities": matches,
        "count": len(matches),
        **({"notice": notice} if notice else {}),
    }
