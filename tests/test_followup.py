import asyncio
import io
import json
import pytest
import httpx
from starlette.datastructures import UploadFile
from meridian.services import api, storage, documents, validation
from meridian.state import State


@pytest.fixture
def account(tmp_path, monkeypatch):
    monkeypatch.setenv('MERIDIAN_DATA_DIR', str(tmp_path))
    token = storage.authenticate('test@example.com', 'long test password', True, 'Test')
    return token


def run_event(event):
    async def run():
        return [item async for item in event]
    return asyncio.run(run())


def test_validation_at_save_and_loading(account):
    state = State(_reflex_internal_init=True)
    state.session = account
    state._load()
    state.profile.update(gpa='11', gpa_scale='10', phone='abc', toefl='150')
    run_event(state.save_profile())
    assert not state.saving
    assert {'gpa', 'phone', 'toefl'} <= state.field_errors.keys()
    assert 'gpa' not in json.loads(storage.user(account)['profile'])
    state.profile.update(gpa='8.4', phone='98765 43210', toefl='100')
    run_event(state.save_profile())
    assert not state.field_errors
    assert json.loads(storage.user(account)['profile'])['gpa'] == '8.4'


def test_profile_next_tab_advances_and_final_step_redirects(account):
    state = State(_reflex_internal_init=True)
    state.session = account
    state._load()

    for expected_tab in range(1, 7):
        assert state.next_tab() is None
        assert state.profile_tab == expected_tab

    redirect = state.next_tab()
    assert "/documents" in str(redirect)


def test_profile_next_tab_redirects_when_session_is_missing():
    state = State(_reflex_internal_init=True)
    redirect = state.next_tab()
    assert "/login" in str(redirect)


def test_loading_saved_results_never_restores_obsolete_unavailable_agent_status(account):
    state = State(_reflex_internal_init=True)
    state.session = account
    state._load()
    assert all(row["status"] == "waiting" for row in state.agents)
    assert not any(row["status"] == "unavailable" for row in state.agents)


def test_regions_preferences_reload_cancel(account):
    state = State(_reflex_internal_init=True)
    state.session = account
    state._load()
    for region in ['Canada', 'canada', 'New Zealand', 'London']:
        state.region_query = region
        state.add_region()
    assert state.regions == ['Canada','New Zealand','London']
    state.set_field('accommodation', 'Off campus')
    state.set_field('commute', 'Private transport')
    state.set_field('commute_minutes', '30')
    run_event(state.save_profile())
    state.clear_regions()
    assert state.profile_dirty
    state.cancel_profile()
    assert state.regions == ['Canada','New Zealand','London']
    assert state.profile['accommodation'] == 'Off campus'
    assert not state.profile_dirty


def test_all_us_regions_are_available_and_persist(account):
    from meridian.data.profile import US_STATES

    assert len(US_STATES) == 51
    assert 'Alabama' in US_STATES
    assert 'Washington' in US_STATES
    assert 'Washington, D.C.' in US_STATES

    state = State(_reflex_internal_init=True)
    state.session = account
    state._load()
    for region in ('Alabama', 'New York', 'Washington, D.C.'):
        state.region_query = region
        state.add_region()
    run_event(state.save_profile())
    state._load()
    assert state.regions == ['Alabama', 'New York', 'Washington, D.C.']

    single = State(_reflex_internal_init=True)
    single.session = account
    single._load()
    single.clear_regions()
    single.region_query = 'Washington, D.C.'
    single.add_region()
    run_event(single.save_profile())
    single._load()
    assert single.regions == ['Washington, D.C.']


def test_cross_tab_update_cannot_publish_stale_results(account):
    first = State(_reflex_internal_init=True)
    second = State(_reflex_internal_init=True)
    first.session = second.session = account
    first._load()
    second._load()
    first.set_field('city', 'Mumbai')
    run_event(first.save_profile())
    second.set_field('city', 'Pune')
    run_event(second.save_profile())
    assert 'another tab' in second.message
    assert json.loads(storage.user(account)['profile'])['city'] == 'Mumbai'
    with pytest.raises(ValueError, match='Profile changed'):
        storage.save_results(account, second.profile, {'profile': {'prediction':'stale'}})


def test_document_storage_isolation_validation_and_remove(account):
    other = storage.authenticate('other@example.com', 'other long test password', True, 'Other')
    docs = documents.store(account, 'resume', '../../notes.txt', b'Private resume')
    assert docs['resume_name'] == 'notes.txt'
    assert documents.download(account, 'resume') == ('notes.txt', b'Private resume')
    with pytest.raises(ValueError, match='not found'):
        documents.download(other, 'resume')
    for name, data in [('bad.pdf', b'not PDF'), ('bad.exe', b'MZ'), ('big.txt', b'a'*(documents.MAX_BYTES+1)), ('empty.txt', b'')]:
        with pytest.raises(ValueError):
            documents.store(account, 'resume', name, data)
    assert documents.download(account, 'resume')[1] == b'Private resume'
    documents.store(account, 'resume', 'new.txt', b'Updated resume')
    assert documents.download(account, 'resume')[1] == b'Updated resume'
    assert not documents.remove(account, 'resume')
    with pytest.raises(ValueError):
        documents.download(account, 'resume')
    storage.logout(account)
    with pytest.raises(ValueError):
        documents.store(account, 'resume', 'file.txt', b'test')


def test_upload_event_failure_retry_reload(account):
    state = State(_reflex_internal_init=True)
    state.session = account
    state._load()
    run_event(state.upload_resume([UploadFile(filename='broken.pdf', file=io.BytesIO(b'bad'))]))
    assert state.upload_states['resume'] == 'Failed'
    run_event(state.upload_resume([UploadFile(filename='resume.txt', file=io.BytesIO(b'resume text'))]))
    assert state.upload_states['resume'] == 'Stored'
    assert not state.upload_errors
    state._load()
    assert state.docs_count == 1
    assert state.docs['resume_status'] == 'Processed'
    assert state.docs['resume_preview'] == 'resume text'


@pytest.mark.parametrize('status,body', [(200, []), (200, {'matched_universities':[{}]}), (200, {'matched_universities':None}), (503, ['error']), (401, {'detail':'unauthorized'})])
def test_bad_api_responses_terminate(monkeypatch, status, body):
    async def response(*args, **kwargs):
        return httpx.Response(status, json=body)
    monkeypatch.setattr(httpx.AsyncClient, 'post', response)
    with pytest.raises(ValueError):
        asyncio.run(api.request('/match', {}))


def test_transient_api_gateway_failure_is_retried(monkeypatch):
    responses = iter([
        httpx.Response(502, json={'detail': 'bad gateway'}),
        httpx.Response(200, json={'matched_universities': []}),
    ])

    async def response(*args, **kwargs):
        return next(responses)

    async def no_wait(*args, **kwargs):
        return None

    monkeypatch.setattr(httpx.AsyncClient, 'post', response)
    monkeypatch.setattr(api.asyncio, 'sleep', no_wait)
    result = asyncio.run(api.request('/match', {}))
    assert result['matched_universities'] == []


def test_rate_limited_api_request_is_retried(monkeypatch):
    responses = iter([
        httpx.Response(429, headers={'Retry-After': '2'}, json={'detail': 'busy'}),
        httpx.Response(200, json={'matched_universities': []}),
    ])

    async def response(*args, **kwargs):
        return next(responses)

    async def no_wait(*args, **kwargs):
        return None

    monkeypatch.setattr(httpx.AsyncClient, 'post', response)
    monkeypatch.setattr(api.asyncio, 'sleep', no_wait)
    result = asyncio.run(api.request('/match', {}))
    assert result['matched_universities'] == []


def test_next_section_not_blocked_by_hidden_error(account):
    state = State(_reflex_internal_init=True)
    state.session = account
    state._load()
    state.profile['toefl'] = '999'
    state.next_tab()
    assert state.profile_tab == 1
    state.profile_tab = 6
    assert state.next_tab() is None
    assert state.profile_tab == 2
    assert 'TOEFL' in state.message.upper()
    state.profile['toefl'] = '100'
    state.profile_tab = 6
    assert '/documents' in str(state.next_tab())
