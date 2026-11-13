"""Meridian state: authenticated persistence and real request-level analysis."""
from __future__ import annotations
import asyncio
import json
import os
import logging
import time
from pathlib import Path
from typing import Any, TypedDict
import reflex as rx
from .data import mock
from .data.profile import FORM_SCHEMA, US_STATES, empty_profile
from .services import storage, api, validation, documents
from .services.agent7 import Agent7Service, Agent7Unavailable, NOTICE as AGENT7_NOTICE
from .services.agent2 import Agent2Service, Agent2Unavailable

logger = logging.getLogger(__name__)


class AnalysisBlocked(ValueError):
    """A dependency produced no usable input; the dependent agent was not run."""

AGENT7_RESULT_KEYS = frozenset({
    "strength_tier", "profile_strength_score", "P(Strong)",
    "achievement_archetype", "has_research_evidence",
})


class ScholarshipRecommendation(TypedDict):
    scholarship_name: str
    eligibility_match: str
    potential_annual_coverage: float
    currency: str
    deadline: str
    match_score: float
    source_url: str


class ScholarshipReview(TypedDict):
    scholarship_name: str
    eligibility_match: str
    reasons: list[str]


class ScholarshipResult(TypedDict):
    university: str
    program_name: str
    currency: str
    funding_gap: float | None
    recommendations: list[ScholarshipRecommendation]
    eligibility_review: list[ScholarshipReview]


def _friendly_review_reason(reason: str) -> str:
    messages = {
        'unknown: GPA or GPA scale': 'Add your GPA and grading scale to check this requirement.',
        'unknown: deadline policy': 'The current application timing is not published; confirm it with the provider.',
        'nonannual or missing award period': 'The award amount or payment period is not clearly published.',
        'unknown: nationality': 'Add your nationality to check this requirement.',
        'unknown: field equivalence requires review': 'Your field needs confirmation against the provider’s eligibility wording.',
        'unknown: degree': 'Add your intended degree level to check this requirement.',
        'currency mismatch': 'The award currency differs from the estimated study-cost currency.',
        'unknown coverage basis or award amount': 'The provider has not clearly published the award amount or coverage basis.',
        'nationality': 'This award is limited to different nationalities.',
        'field equivalence requires review': 'This award’s field requirement does not clearly match your field.',
        'degree': 'This award is for a different degree level.',
        'expired deadline': 'The listed deadline has passed.',
    }
    return messages.get(reason, reason.removeprefix('unknown: ').capitalize())


def _friendly_match(status: str) -> str:
    return {'eligible': 'Potential match', 'unknown': 'Needs confirmation', 'ineligible': 'Not a match'}.get(
        status, 'Needs confirmation'
    )


def agent7_report_text(results):
    result = results.get('extracurricular')
    if not isinstance(result, dict) or not AGENT7_RESULT_KEYS.issubset(result):
        errors = results.get('_errors', [])
        agent7_errors = [error.split(': ', 1)[1] for error in errors
                         if isinstance(error, str) and error.startswith('extracurricular: ')]
        if agent7_errors:
            return f"Agent 7 could not complete: {agent7_errors[-1]}"
        return 'Agent 7: Not scored. Complete the eight structured Experience fields and run analysis. Unknown values should remain blank; zero means known absence.'
    return (f"Agent 7 extracurricular strength: {result['profile_strength_score']} / 100; "
            f"tier: {result['strength_tier']}; P(Strong): {result['P(Strong)']}; "
            f"achievement archetype: Cluster {result['achievement_archetype']}; "
            f"research evidence reported: {'Yes' if result['has_research_evidence'] else 'No'}. "
            + AGENT7_NOTICE)


def initial_agents():
    return [{**a, 'status': 'waiting', 'pct': '', 'progress': 0, 'error': ''} for a in mock.AGENTS]


class State(rx.State):
    session: str = rx.Cookie('', name='meridian_session', max_age=86400, same_site='strict', secure=os.getenv('MERIDIAN_SECURE_COOKIE') == '1')
    authenticated: bool = False
    opening: bool = False
    profile: dict[str, str] = empty_profile()
    profile_tab: int = 0
    docs: dict[str, str] = {}
    uploaded_slots: list[str] = []
    agents: list[dict[str, Any]] = initial_agents()
    event_log: list[str] = []
    agents_running: bool = False
    analysis_error: str = ''
    results: dict[str, Any] = {}
    recommendations: list[dict[str, str]] = []
    selected_uni: str = ''
    message: str = ''
    field_errors: dict[str, str] = {}
    auth_busy: bool = False
    show_password: bool = False
    region_query: str = ''
    saving: bool = False
    _saved_profile: dict[str, str] = {}
    _loaded_session: str = ''
    upload_states: dict[str, str] = {}
    upload_errors: dict[str, str] = {}
    preview_slot: str = ''

    def _error(self, exc):
        if isinstance(exc, (ValueError, Agent7Unavailable)):
            return str(exc)
        logger.exception('Meridian operation failed')
        return 'The operation could not be completed. Please retry; your saved information is retained.'

    @rx.event
    def toggle_password(self):
        self.show_password = not self.show_password

    @rx.event
    async def login(self, form: dict):
        async for event in self._authenticate(form, False):
            yield event

    @rx.event
    async def register(self, form: dict):
        async for event in self._authenticate(form, True):
            yield event

    async def _authenticate(self, form, register):
        self.auth_busy = True
        self.message = ''
        yield
        try:
            token = await asyncio.to_thread(storage.authenticate, form.get('email', ''), form.get('password', ''), register, form.get('name', ''))
            if self.session:
                storage.logout(self.session)
            self.session = token
            self._load()
            yield rx.redirect('/dashboard')
        except Exception as exc:
            self.message = self._error(exc)
        finally:
            self.auth_busy = False

    def _load(self):
        account = storage.user(self.session)
        if self.agents_running and self.session == self._loaded_session:
            # Route on_load must not replace an in-flight run with older DB results.
            return
        self.profile = {**empty_profile(), **json.loads(account['profile'])}
        if self.profile.get('regions', '').strip().casefold() in {state.casefold() for state in US_STATES if ',' in state}:
            self.profile['regions'] = self.profile['regions'].strip() + ';'
        self._saved_profile = dict(self.profile)
        self._loaded_session = self.session
        self.field_errors = {}
        self.docs = json.loads(account['documents'])
        self.uploaded_slots = [s['slot'] for s in mock.DOC_SLOTS if self.docs.get(s['slot']+'_name')]
        self.results = json.loads(account['results'])
        errors = self.results.get('_errors', [])
        self.agents = initial_agents()
        for row in self.agents:
            row['status'] = 'waiting'
            if row['id'] in self.results:
                row['status'] = 'completed'
            elif any(error.startswith(row['id'] + ':') for error in errors):
                row['status'] = 'failed'
            saved_status = self.results.get('_agent_status', {}).get(row['id'], {})
            if isinstance(saved_status, dict) and saved_status.get('status') in ('completed', 'failed', 'unavailable', 'blocked'):
                row.update(status=saved_status['status'], error=saved_status.get('error', ''))
        self.event_log = [f"{row['id']}: completed" for row in self.agents if row['status'] == 'completed'] + errors
        self._recommendations()
        self.authenticated = True

    @rx.event
    def require_auth(self):
        try:
            draft = dict(self.profile)
            dirty = self.profile_dirty and self.session == self._loaded_session
            self._load()
            if dirty:
                self.profile = draft
                self.field_errors = validation.profile_errors(draft)
                self.message = 'You have unsaved profile changes. Save or cancel them in Edit profile.'
        except ValueError:
            self._clear()
            return rx.redirect('/login')
        except Exception as exc:
            self.authenticated = False
            self.message = self._error(exc)

    def _clear(self):
        self.session = ''
        self.authenticated = False
        self.profile = empty_profile()
        self.docs = {}
        self.uploaded_slots = []
        self.results = {}
        self.recommendations = []
        self.agents = initial_agents()
        self.agents_running = False
        self.analysis_error = ''
        self.event_log = []
        self.message = ''
        self.field_errors = {}
        self._saved_profile = {}
        self._loaded_session = ''
        self.upload_states = {}
        self.upload_errors = {}
        self.preview_slot = ''
        self.region_query = ''
        self.show_password = False

    @rx.event
    def logout(self):
        try:
            storage.logout(self.session)
        except Exception as exc:
            self.message = self._error(exc)
            return
        self._clear()
        return rx.redirect('/')

    @rx.event
    async def start_journey(self):
        if self.opening:
            return
        self.opening = True
        yield
        await asyncio.sleep(1.55)
        self.opening = False
        yield rx.redirect('/dashboard' if self.authenticated else '/login')

    @rx.event
    def set_field(self, key: str, value: str):
        if key not in validation.FIELDS:
            return
        self.profile[key] = '' if value is None else str(value)
        self.field_errors = validation.profile_errors(self.profile)

    @rx.event
    def set_region_query(self, value: str):
        self.region_query = value

    @rx.var
    def regions(self) -> list[str]:
        raw = self.profile.get('regions', '')
        normalized = raw.strip().rstrip(';').strip()
        if normalized.casefold() in {state.casefold() for state in US_STATES}:
            return [normalized]
        separator = ';' if ';' in raw else ','
        return [v.strip() for v in raw.split(separator) if v.strip()]

    @rx.event
    def add_region(self):
        value = ' '.join(self.region_query.strip().split())
        if value and value.casefold() not in [r.casefold() for r in self.regions]:
            regions = self.regions + [value]
            self.profile['regions'] = '; '.join(regions)
            if len(regions) == 1 and ',' in value:
                self.profile['regions'] += ';'
        self.region_query = ''

    @rx.event
    def remove_region(self, value: str):
        self.profile['regions'] = '; '.join(r for r in self.regions if r != value)

    @rx.event
    def clear_regions(self):
        self.profile['regions'] = ''
        self.region_query = ''

    @rx.var
    def profile_dirty(self) -> bool:
        return bool(self._saved_profile) and self.profile != self._saved_profile

    def _save_profile(self):
        storage.user(self.session)
        self.field_errors = validation.profile_errors(self.profile)
        if self.field_errors:
            raise ValueError('Please correct the highlighted fields before saving.')
        storage.save_profile(self.session, self.profile, self._saved_profile)
        if self._saved_profile != self.profile:
            self.results = {}
            self.recommendations = []
            self.event_log = []
        self._saved_profile = dict(self.profile)
        self.message = 'Profile saved.'

    @rx.event
    async def save_profile(self):
        self.saving = True
        yield
        try:
            self._save_profile()
        except Exception as exc:
            self.message = self._error(exc)
        finally:
            self.saving = False

    @rx.event
    def cancel_profile(self):
        try:
            self._load()
            self.field_errors = {}
            self.message = 'Unsaved changes discarded.'
            return rx.redirect('/dashboard')
        except ValueError:
            self._clear()
            return rx.redirect('/login')
        except Exception as exc:
            self.message = self._error(exc)

    @rx.event
    def navigate_to(self, path: str):
        try:
            if self.profile_dirty and self.session == self._loaded_session:
                self._save_profile()
            return rx.redirect(path)
        except Exception as exc:
            self.message = self._error(exc)

    @rx.event
    def set_tab(self, index: int):
        self.profile_tab = max(0, min(index, len(FORM_SCHEMA)-1))

    @rx.event
    def next_tab(self):
        if self.profile_tab < len(FORM_SCHEMA)-1:
            self.profile_tab += 1
            self.message = 'Draft retained. Save changes or continue to documents when finished.'
            return
        try:
            self.field_errors = validation.profile_errors(self.profile)
            blocking = set(self.field_errors)
            if blocking:
                self.profile_tab = next((i for i, section in enumerate(FORM_SCHEMA)
                    if any(field['key'] in blocking for field in section['fields'])), self.profile_tab)
                self.message = 'Please correct: ' + ', '.join(
                    field['label'] for section in FORM_SCHEMA for field in section['fields']
                    if field['key'] in blocking) + '.'
                return
            self._save_profile()
            return rx.redirect('/documents')
        except Exception as exc:
            self.message = self._error(exc)

    @rx.event
    def prev_tab(self):
        self.profile_tab = max(0, self.profile_tab-1)

    @rx.var
    def profile_completion(self) -> int:
        keys = ['full_name', 'email', 'degree_goal', 'field', 'gpa', 'gpa_scale', 'regions']
        return round(100*sum(bool(self.profile.get(k, '').strip()) for k in keys)/len(keys))

    @rx.var
    def completion_str(self) -> str:
        return f'{self.profile_completion}%'

    @rx.var
    def student_name(self) -> str:
        return self.profile.get('full_name') or 'Your dossier'

    @rx.var
    def target_program(self) -> str:
        return ' '.join(filter(None, [self.profile.get('degree_goal'), self.profile.get('field')])) or 'Choose your study goals'

    async def _save(self, slot, files):
        token = self.session
        self.upload_states[slot] = 'Uploading'
        self.upload_errors.pop(slot, None)
        yield
        try:
            storage.user(token)
            if len(files) != 1:
                raise ValueError('Choose one file per document slot.')
            data = await files[0].read(documents.MAX_BYTES + 1)
            self.upload_states[slot] = 'Processing'
            yield
            docs = await asyncio.to_thread(documents.store, token, slot, files[0].filename or 'document', data)
            if token == self.session:
                self.docs = docs
                self.uploaded_slots = [s for s in documents.SLOTS if docs.get(s+'_name')]
                self.upload_states[slot] = 'Stored'
                self.results = {}
                self.recommendations = []
                self.event_log = []
                self.message = 'File stored privately. ' + docs[slot+'_status'] + '. Run analysis to use readable text.'
        except Exception as exc:
            if token == self.session:
                self.upload_states[slot] = 'Failed'
                self.upload_errors[slot] = self._error(exc)
        finally:
            for file in files:
                await file.close()

    @rx.event
    async def upload_resume(self, files: list[rx.UploadFile]):
        async for event in self._save('resume', files):
            yield event

    @rx.event
    async def upload_transcript(self, files: list[rx.UploadFile]):
        async for event in self._save('transcript', files):
            yield event

    @rx.event
    async def upload_sop(self, files: list[rx.UploadFile]):
        async for event in self._save('sop', files):
            yield event

    @rx.event
    async def upload_lor(self, files: list[rx.UploadFile]):
        async for event in self._save('lor', files):
            yield event

    @rx.event
    async def upload_other(self, files: list[rx.UploadFile]):
        async for event in self._save('other', files):
            yield event

    @rx.event
    def remove_document(self, slot: str):
        try:
            self.docs = documents.remove(self.session, slot)
            self.uploaded_slots = [s for s in self.uploaded_slots if s != slot]
            self.upload_states.pop(slot, None)
            self.results = {}
            self.recommendations = []
            self.event_log = []
            self.message = 'Document removed.'
        except Exception as exc:
            self.message = self._error(exc)

    @rx.event
    def toggle_preview(self, slot: str):
        self.preview_slot = '' if self.preview_slot == slot else slot

    @rx.event
    def download_document(self, slot: str):
        try:
            name, data = documents.download(self.session, slot)
            return rx.download(data=data, filename=name)
        except Exception as exc:
            self.message = self._error(exc)

    @rx.var
    def docs_count(self) -> int:
        return len(self.uploaded_slots)

    def _recommendations(self):
        result = self.results.get('university', {})
        rows = result.get('matched_universities', []) if isinstance(result, dict) else []
        self.recommendations = [{**{k: str(v) for k, v in row.items()},
                                 'gpa': str(row.get('gpa', 'Not supplied')),
                                 'match_score': str(row.get('match_score', 'Not supplied'))} for row in rows]

    @staticmethod
    def _agent2_rows(result: dict) -> list[dict[str, Any]]:
        """Adapt the verified Agent 2 schema to Agent 3's shortlist contract."""
        rows = result.get('universities')
        if not isinstance(rows, list):
            raise ValueError('Agent 2 returned an invalid university shortlist.')
        return [
            {
                'name': row['name'],
                'country': row['country'],
                'tier': row['tier'],
                'match_score': row['match_score'],
                'agent2_id': row['id'],
                'agent2_note': row['note'],
                'agent2_probability': row['probability'],
            }
            for row in rows
        ]

    @rx.var
    def program_results(self) -> list[dict[str, Any]]:
        result = self.results.get('program', {})
        rows = result.get('programs', []) if isinstance(result, dict) else []
        formatted = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            for key in ('specialization_fit_score', 'match_score'):
                value = item.get(key)
                if isinstance(value, (int, float)):
                    item[key] = f'{float(value) * 100:.0f}%'
            item['duration'] = item.get('duration') or 'Duration not listed'
            item['mode'] = item.get('mode') or 'Study format not listed'
            formatted.append(item)
        return formatted

    @rx.var
    def financial_available(self) -> bool:
        result = self.results.get('financial')
        return isinstance(result, dict) and isinstance(result.get('finance'), list) and bool(result.get('finance'))

    @rx.var
    def financial_results(self) -> list[dict[str, Any]]:
        result = self.results.get('financial', {})
        rows = result.get('finance', []) if isinstance(result, dict) else []
        return [{**row, 'currency': row.get('currency') or 'Currency unspecified'}
                for row in rows if isinstance(row, dict)]

    @rx.var
    def financial_summary(self) -> str:
        saved = self._result_status('financial')
        if saved:
            return saved
        for error in self.results.get('_errors', []):
            if error.startswith('financial:'):
                return error.split(': ', 1)[-1]
        return 'Agent 4 financial analysis is unavailable for this saved analysis.'

    @rx.var
    def financial_skipped(self) -> list[dict[str, Any]]:
        result = self.results.get('financial', {})
        return result.get('finance_skipped', []) if isinstance(result, dict) else []

    @rx.var
    def scholarship_available(self) -> bool:
        result = self.results.get('scholarship')
        return isinstance(result, dict) and isinstance(result.get('scholarships'), list) and bool(result.get('scholarships'))

    @rx.var
    def scholarship_results(self) -> list[ScholarshipResult]:
        result = self.results.get('scholarship', {})
        if not isinstance(result, dict):
            return []
        return [
            {
                'university': str(item.get('university', '')),
                'program_name': str(item.get('program_name', '')),
                'currency': str(item.get('currency', '')),
                'funding_gap': item.get('funding_gap'),
                'recommendations': [
                    {**recommendation, 'eligibility_match': 'Potential match'}
                    for recommendation in item.get('recommendations', [])
                    if isinstance(recommendation, dict)
                ],
                'eligibility_review': [
                    {
                        **review,
                        'eligibility_match': _friendly_match(str(review.get('eligibility_match', ''))),
                        'reasons': [
                            _friendly_review_reason(str(reason))
                            for reason in review.get('reasons', [])
                        ],
                    }
                    for review in item.get('eligibility_review', [])
                    if isinstance(review, dict)
                ],
            }
            for item in result.get('scholarships', [])
            if isinstance(item, dict)
        ]

    @rx.var
    def scholarship_summary(self) -> str:
        result = self.results.get('scholarship', {})
        if isinstance(result, dict) and result.get('notice'):
            return str(result['notice'])
        return self._result_status('scholarship') or 'Agent 5 scholarship analysis is unavailable for this saved analysis.'

    @rx.var
    def career_available(self) -> bool:
        result = self.results.get('career')
        return isinstance(result, dict) and isinstance(result.get('career_paths'), list) and bool(result.get('career_paths'))

    @rx.var
    def career_paths(self) -> list[dict[str, Any]]:
        result = self.results.get('career', {})
        return result.get('career_paths', []) if isinstance(result, dict) else []

    @rx.var
    def career_summary(self) -> str:
        result = self.results.get('career', {})
        if isinstance(result, dict) and result.get('notice'):
            return str(result['notice'])
        return self._result_status('career') or 'Agent 6 career alignment is unavailable for this saved analysis.'

    @rx.var
    def university_summary(self) -> str:
        result = self.results.get('university', {})
        if isinstance(result, dict) and result.get('notice'):
            return str(result['notice'])
        return self._result_status('university') or 'University matching returned no rows.'

    @rx.var
    def program_summary(self) -> str:
        result = self.results.get('program', {})
        if isinstance(result, dict) and result.get('notice'):
            return str(result['notice'])
        return self._result_status('program') or 'Program ranking returned no rows.'

    def _result_status(self, agent: str) -> str:
        if agent in self.results:
            return ''
        saved = self.results.get('_agent_status', {}).get(agent, {})
        if isinstance(saved, dict) and saved.get('status'):
            status = str(saved['status']).capitalize()
            detail = str(saved.get('error') or '')
            return f'{status}: {detail}' if detail else f'{status}: no result was saved.'
        for error in self.results.get('_errors', []):
            if isinstance(error, str) and error.startswith(agent + ':'):
                return 'Failed: ' + error.split(':', 1)[1].strip()
        return 'Unavailable: this agent has no saved result.'

    @rx.var
    def career_earnings_estimate(self) -> str:
        result = self.results.get('career', {})
        if isinstance(result, dict) and result.get('model_estimated_annual_earnings_usd') is not None:
            return f"${float(result['model_estimated_annual_earnings_usd']):,.2f} model estimate"
        return 'Not available'

    @rx.event(background=True)
    async def run_agents(self):
        async with self:
            if self.agents_running:
                return
            try:
                if self.profile_dirty:
                    self.message = 'Save or cancel your profile changes before running analysis.'
                    return
                self._load()
            except ValueError:
                self._clear()
                yield rx.redirect('/login')
                return
            self.agents_running = True
            self.analysis_error = ''
            self.agents = initial_agents()
            self.results = {}
            self.recommendations = []
            self.event_log = []
            profile = dict(self.profile)
            document_snapshot = dict(self.docs)
            token = self.session
        try:
            document_text, evidence = await asyncio.to_thread(documents.analysis_inputs, token, document_snapshot)
            text_profile = dict(profile)
            text_profile['interests_text'] = '\n'.join(filter(None, [profile.get('field'), profile.get('programs'), document_text]))
            text_profile['projects'] = '\n'.join(filter(None, [profile.get('projects'), document_text]))
            async with self:
                self.results['_documents'] = evidence
                self.event_log.append(f'Documents: {sum(item["status"] == "extracted" for item in evidence)} readable; {sum(item["status"] != "extracted" for item in evidence)} unavailable. Structured scores use the saved profile only.')
            for agent in ('profile', 'extracurricular', 'university', 'program', 'financial', 'scholarship', 'career'):
                index = next(i for i, row in enumerate(self.agents) if row['id'] == agent)
                started_at = time.time()
                storage.record_analysis_event(token, agent, 'running', started_at)
                async with self:
                    if token != self.session:
                        return
                    self.agents[index]['status'] = 'processing'
                try:
                    if agent == 'profile':
                        payload = api.agent1_payload(profile)
                        result = await asyncio.wait_for(api.request('/agent1/profile', payload), timeout=50)
                        if 'prediction' not in result:
                            raise ValueError('Agent 1 returned an invalid response.')
                    elif agent == 'extracurricular':
                        result = await asyncio.to_thread(Agent7Service().score_profile, profile)
                    elif agent == 'university':
                        if not profile.get('match_country') or not profile.get('match_tier'):
                            raise ValueError('Choose matching country and catalog tier in Study goals.')
                        agent1_result = self.results.get('profile')
                        agent7_result = self.results.get('extracurricular')
                        if isinstance(agent7_result, dict) and AGENT7_RESULT_KEYS.issubset(agent7_result):
                            try:
                                verified = await asyncio.wait_for(
                                    asyncio.to_thread(
                                        Agent2Service().match_profile,
                                        profile,
                                        agent7_result,
                                        agent1_result,
                                    ),
                                    timeout=100,
                                )
                                result = {
                                    **verified,
                                    'matched_universities': self._agent2_rows(verified),
                                    'source': 'verified_agent2_bundle',
                                }
                            except Agent2Unavailable as exc:
                                # The repository's legacy /match route remains
                                # the supported fallback when the optional
                                # verified Agent 2 export is absent.
                                result = await asyncio.wait_for(
                                    api.request('/match', {
                                        'gpa': api.gpa(profile),
                                        'country': profile['match_country'],
                                        'tier': profile['match_tier'],
                                    }),
                                    timeout=50,
                                )
                                result['source'] = 'legacy_match_route'
                                result['notice'] = str(exc) + ' Using the existing GPA/country/tier catalog matcher; no admission probability.'
                        else:
                            result = await asyncio.wait_for(
                                api.request('/match', {
                                    'gpa': api.gpa(profile),
                                    'country': profile['match_country'],
                                    'tier': profile['match_tier'],
                                }),
                                timeout=50,
                            )
                            result['source'] = 'legacy_match_route'
                        if not isinstance(result.get('matched_universities'), list):
                            raise ValueError('Matching API returned an invalid response.')
                    elif agent == 'program':
                        university_result = self.results.get('university', {})
                        matches = university_result.get('matched_universities', []) if isinstance(university_result, dict) else []
                        if not matches:
                            raise AnalysisBlocked('Agent 3 requires a nonempty university shortlist.')
                        result = await asyncio.wait_for(
                            api.request('/agent3/program', {
                                'profile': text_profile,
                                'matched_universities': matches,
                            }),
                            timeout=50,
                        )
                        if not isinstance(result.get('programs'), list):
                            raise ValueError('Program API returned an invalid response.')
                    elif agent == 'financial':
                        program_result = self.results.get('program', {})
                        programs = program_result.get('programs', []) if isinstance(program_result, dict) else []
                        result = await asyncio.wait_for(
                            api.request('/agent4/financial', {
                                'degree_goal': profile.get('degree_goal', ''),
                                'programs': programs,
                            }),
                            timeout=50,
                        )
                        if not isinstance(result.get('finance'), list):
                            raise ValueError('Financial API returned an invalid response.')
                    elif agent == 'scholarship':
                        financial_result = self.results.get('financial', {})
                        finance = financial_result.get('finance', []) if isinstance(financial_result, dict) else []
                        if not finance:
                            raise AnalysisBlocked('Agent 5 requires successful Agent 4 financial results; its service was not executed.')
                        result = await asyncio.wait_for(
                            api.request('/agent5/scholarship', {
                                'profile': profile,
                                'finance': finance,
                            }),
                            timeout=50,
                        )
                        if not isinstance(result.get('scholarships'), list):
                            raise ValueError('Scholarship API returned an invalid response.')
                    else:
                        result = await asyncio.wait_for(
                            api.request('/agent6/career', {'profile': text_profile}),
                            timeout=50,
                        )
                        if not isinstance(result.get('career_paths'), list):
                            raise ValueError('Career API returned an invalid response.')
                    async with self:
                        account = storage.user(token)
                        if token != self.session:
                            return
                        if ({**empty_profile(), **json.loads(account['profile'])} != profile or
                                json.loads(account['documents']) != document_snapshot):
                            self.results = {}
                            self.recommendations = []
                            self.event_log.append('Profile or documents changed. Run analysis again for the saved inputs.')
                            self.agents[index]['status'] = 'cancelled'
                            return
                        self.results[agent] = result
                        if agent in ('program', 'career'):
                            for item in evidence:
                                if item['status'] == 'extracted':
                                    item['consumed_by'].append(agent)
                            self.results['_documents'] = evidence
                        self.agents[index]['status'] = 'completed'
                        self.event_log.append(f'{agent}: completed')
                        storage.record_analysis_event(token, agent, 'completed', started_at, time.time(), result=result)
                except Exception as exc:
                    async with self:
                        if token != self.session:
                            return
                        status = ('blocked' if isinstance(exc, AnalysisBlocked) else
                                  'unavailable' if isinstance(exc, (api.AgentUnavailable, Agent7Unavailable, Agent2Unavailable)) else 'failed')
                        self.agents[index]['status'] = status
                        detail = self._error(exc) if not isinstance(exc, asyncio.TimeoutError) else "Request timed out; retry."
                        self.agents[index]['error'] = detail
                        if not self.analysis_error:
                            self.analysis_error = detail
                        self.event_log.append(f'{agent}: {detail}')
                        storage.record_analysis_event(token, agent, status, started_at, time.time(), error=detail)
            async with self:
                if token == self.session:
                    self._recommendations()
                    self.results['_errors'] = [f"{a['id']}: {a['error']}" for a in self.agents if a['error']]
                    self.results['_agent_status'] = {a['id']: {'status': a['status'], 'error': a['error']} for a in self.agents}
                    self.results['_analysed_at'] = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
                    storage.save_results(token, profile, self.results, document_snapshot)
        except Exception as exc:
            async with self:
                if token == self.session:
                    self.results = {}
                    self.recommendations = []
                    self.message = self._error(exc)
                    self.analysis_error = self.message
                    self.event_log.append(self.message)
        finally:
            async with self:
                self.agents_running = False

    @rx.var
    def agent7_summary(self) -> str:
        return agent7_report_text(self.results)

    @rx.var
    def agent7_available(self) -> bool:
        result = self.results.get("extracurricular")
        return isinstance(result, dict) and AGENT7_RESULT_KEYS.issubset(result)

    @rx.var
    def agent7_score(self) -> str:
        result = self.results.get("extracurricular", {})
        return str(result.get("profile_strength_score", "Not scored")) if self.agent7_available and isinstance(result, dict) else "Not scored"

    @rx.var
    def agent7_tier(self) -> str:
        result = self.results.get("extracurricular", {})
        return str(result.get("strength_tier", "Not scored")) if self.agent7_available and isinstance(result, dict) else "Not scored"

    @rx.var
    def agent7_probability(self) -> str:
        result = self.results.get("extracurricular", {})
        return str(result.get("P(Strong)", "Not scored")) if self.agent7_available and isinstance(result, dict) else "Not scored"

    @rx.var
    def agent7_archetype(self) -> str:
        result = self.results.get("extracurricular", {})
        return str(result.get("achievement_archetype", "Not scored")) if self.agent7_available and isinstance(result, dict) else "Not scored"

    @rx.var
    def agent7_research_evidence(self) -> str:
        result = self.results.get("extracurricular", {})
        return "Yes" if self.agent7_available and isinstance(result, dict) and result.get("has_research_evidence") else "No"

    @rx.var
    def agents_done(self) -> bool:
        return not self.agents_running and bool(self.event_log)

    @rx.var
    def agents_completed_count(self) -> int:
        return sum(a['status'] == 'completed' for a in self.agents)

    @rx.var
    def overall_pct(self) -> str:
        if self.agents_running:
            return 'Running'
        if not self.event_log:
            return 'Pending'
        return 'Complete' if self.agents_completed_count == 7 else 'Partial' if self.agents_completed_count else 'No results'

    @rx.var
    def profile_analysis_available(self) -> bool:
        return isinstance(self.results.get("profile"), dict) and bool(self.results.get("profile", {}).get("prediction"))

    @rx.var
    def profile_analysis_summary(self) -> str:
        result = self.results.get("profile", {})
        if not isinstance(result, dict):
            return "No Agent 1 result available."
        probability = result.get("probability")
        confidence = f" · Tier 1 probability {probability:.1%}" if isinstance(probability, (float, int)) else ""
        return f"{result.get('prediction', 'No result')}{confidence}"

    @rx.var
    def matching_ready(self) -> bool:
        return bool(self.profile.get('match_country')) and bool(self.profile.get('match_tier'))

    @rx.var
    def prediction_unavailable(self) -> bool:
        return 'profile' not in self.results

    @rx.var
    def prediction_text(self) -> str:
        result = self.results.get('profile', {})
        return str(result.get('prediction', self._result_status('profile')))

    @rx.var
    def prediction_confidence(self) -> str:
        probability = self.results.get('profile', {}).get('probability')
        return f'Tier 1 class probability: {probability:.1%} (not admission probability)' if isinstance(probability, (float, int)) else ''

    @rx.var
    def result_json(self) -> str:
        return json.dumps(self.results, indent=2, ensure_ascii=False) if self.results else 'No saved analysis yet.'

    @rx.var
    def report_sections(self) -> list[dict[str, str]]:
        from .services.report_pdf import saved_report_sections
        return [{'no': f'{index:02d}', 'title': title, 'body': '\n'.join(lines)}
                for index, (title, lines) in enumerate(saved_report_sections(self.results), 1)]

    @rx.var
    def saved_agent_count(self) -> int:
        return sum(agent in self.results for agent in ('profile', 'university', 'program', 'financial', 'scholarship', 'career', 'extracurricular'))

    @rx.event
    def select_uni(self, uni_id: str):
        self.selected_uni = uni_id

    @rx.event
    def download_report(self):
        try:
            account = storage.user(self.session)
        except Exception as exc:
            self.message = self._error(exc)
            return
        profile = json.loads(account['profile'])
        results = json.loads(account['results'])
        from .services.report_pdf import render_saved_report_pdf
        return rx.download(data=render_saved_report_pdf(profile, results), filename='Meridian-Dossier.pdf')
