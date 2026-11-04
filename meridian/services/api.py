"""HTTP boundary with finite deadlines and explicit profile input mapping."""
import os
import math
import logging
import asyncio
import httpx


class AgentUnavailable(ValueError):
    """Service or required artifacts are unavailable, rather than a bad analysis."""


def number(profile, key, low, high):
    try:
        value = float(profile.get(key, ''))
    except (ValueError, TypeError):
        raise ValueError(f'Enter {key.replace("_", " ")} in your profile.') from None
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{key} must be between {low:g} and {high:g}.')
    return value


def gpa(profile):
    scale = number(profile, 'gpa_scale', 4, 100)
    if scale not in (4, 10, 100):
        raise ValueError('Choose GPA scale 4, 10, or 100.')
    return number(profile, 'gpa', 0, scale) / scale * 4


def prediction_payload(profile):
    payload = {'gpa': gpa(profile), 'work_experience': number(profile, 'work_years', 0, math.inf)}
    if profile.get('degree_goal') == 'MBA':
        payload.update(gmat_score=number(profile, 'gmat', 200, 800), essay_score=number(profile, 'essay_score', -math.inf, math.inf))
    elif profile.get('degree_goal') == 'MS':
        payload.update(gre_score=number(profile, 'gre_verbal', 130, 170)+number(profile, 'gre_quant', 130, 170),
                       toefl_score=number(profile, 'toefl', 0, 120), research_experience=number(profile, 'research_experience', 0, math.inf))
    else:
        raise ValueError('Select MS or MBA in Study goals.')
    return payload


def agent1_payload(profile):
    degree = str(profile.get("degree_goal", "")).upper()
    if degree not in {"MS", "MBA"}:
        raise ValueError("Select MS or MBA in Study goals.")
    payload = {
        "track": degree,
        "gpa_normalized_4": gpa(profile),
        "toefl_score": number(profile, "toefl", 0, 120) if profile.get("toefl") else 0,
        "has_research": 1 if profile.get("research_experience", "").strip() not in ("", "0") else 0,
        "work_experience_months": number(profile, "work_years", 0, math.inf) * 12 if profile.get("work_years") else 0,
        "major": "Business" if "business" in profile.get("field", "").lower() else
                 "STEM" if profile.get("field") else "NA",
    }
    if degree == "MS":
        payload["gre_score"] = (
            number(profile, "gre_verbal", 130, 170)
            + number(profile, "gre_quant", 130, 170)
            if profile.get("gre_verbal") and profile.get("gre_quant") else 0
        )
    else:
        payload["gmat_score"] = number(profile, "gmat", 200, 800) if profile.get("gmat") else 0
    return payload


async def request(path, payload):
    base = os.environ.get('MERIDIAN_API_URL', 'http://127.0.0.1:8001').rstrip('/')
    async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10), trust_env=False) as client:
        for attempt in range(3):
            try:
                response = await client.post(base+path, json=payload)
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError):
                if attempt == 2:
                    raise ValueError('Analysis API did not respond. Render may still be waking up; please retry.') from None
                await asyncio.sleep(2 * (attempt + 1))
                continue
            if response.status_code in (502, 503) and attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            if response.status_code >= 400:
                try:
                    body = response.json()
                    detail = body.get('detail', 'Request failed') if isinstance(body, dict) else 'Request failed'
                except ValueError:
                    detail = 'Request failed'
                if response.status_code == 401:
                    detail = 'The analysis service rejected authorization. Check the service configuration.'
                error = AgentUnavailable if response.status_code in (404, 503) else ValueError
                raise error(f'Analysis API ({response.status_code}): {detail}')
            break
        try:
            result = response.json()
        except ValueError:
            raise ValueError('The analysis API returned an unreadable response. Please retry.') from None
        if not isinstance(result, dict):
            raise ValueError('The API returned an invalid response.')
        if path == '/match':
            rows = result.get('matched_universities')
            if not isinstance(rows, list) or any(not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k] for k in ('name', 'country', 'tier')) or not isinstance(row.get('gpa'), (int, float)) or not math.isfinite(row['gpa']) for row in rows):
                raise ValueError('The matching API returned an invalid university list.')
        elif path in ('/predict/ms', '/predict/mba', '/agent1/profile'):
            if not isinstance(result.get('prediction'), str) or not result['prediction']:
                raise ValueError('The profile analysis API returned an empty or invalid result.')
            probability = result.get('probability')
            if probability is not None and (type(probability) not in (int, float) or not math.isfinite(probability) or not 0 <= probability <= 1):
                raise ValueError('The prediction API returned invalid confidence data.')
        elif path == '/agent3/program':
            if not isinstance(result.get('programs'), list):
                raise ValueError('The program API returned an invalid program list.')
            for row in result['programs']:
                if (not isinstance(row, dict) or
                        any(not isinstance(row.get(k), str) for k in ('university', 'program_name', 'duration', 'mode')) or
                        any(type(row.get(k)) not in (int, float) or not math.isfinite(row[k]) or not 0 <= row[k] <= 1
                            for k in ('match_score', 'specialization_fit_score'))):
                    raise ValueError('The program API returned invalid relevance scores or program details.')
        elif path == '/agent6/career':
            paths = result.get('career_paths')
            if (not isinstance(paths, list) or not paths or
                    not isinstance(result.get('top_path'), str) or
                    type(result.get('model_estimated_annual_earnings_usd')) not in (int, float) or
                    not math.isfinite(result['model_estimated_annual_earnings_usd'])):
                raise ValueError('The career API returned an invalid response.')
            for path_result in paths:
                if (not isinstance(path_result, dict) or
                        not isinstance(path_result.get('career_path'), str) or
                        type(path_result.get('alignment_score')) not in (int, float) or
                        not 0 <= path_result['alignment_score'] <= 100 or
                        not isinstance(path_result.get('skill_gaps'), list) or
                        not isinstance(path_result.get('required_skills'), list)):
                    raise ValueError('The career API returned an invalid career path.')
        elif path == '/agent4/financial':
            finance = result.get('finance')
            if not isinstance(finance, list) or not finance:
                raise ValueError('The financial API returned an invalid result list.')
            for row in finance:
                if (not isinstance(row, dict) or not isinstance(row.get('university'), str)
                        or not isinstance(row.get('program_name'), str)
                        or type(row.get('tuition_annual')) not in (int, float)
                        or type(row.get('living_cost_annual')) not in (int, float)
                        or type(row.get('total_cost')) not in (int, float)
                        or any(not math.isfinite(row[key]) or row[key] < 0 for key in ('tuition_annual', 'living_cost_annual', 'total_cost'))):
                    raise ValueError('The financial API returned an invalid cost result.')
            skipped = result.get('finance_skipped', [])
            if not isinstance(skipped, list):
                raise ValueError('The financial API returned invalid skipped-program details.')
        elif path == '/agent5/scholarship':
            scholarships = result.get('scholarships')
            if not isinstance(scholarships, list) or not scholarships:
                raise ValueError('The scholarship API returned an invalid result list.')
            for item in scholarships:
                if (not isinstance(item, dict) or not isinstance(item.get('university'), str)
                        or not isinstance(item.get('program_name'), str)
                        or not isinstance(item.get('recommendations'), list)
                        or not isinstance(item.get('eligibility_review'), list)):
                    raise ValueError('The scholarship API returned an invalid result.')
                for recommendation in item['recommendations']:
                    if (not isinstance(recommendation, dict)
                            or not isinstance(recommendation.get('scholarship_name'), str)
                            or type(recommendation.get('match_score')) not in (int, float)
                            or not 0 <= recommendation['match_score'] <= 1):
                        raise ValueError('The scholarship API returned invalid recommendation details.')
        return result
