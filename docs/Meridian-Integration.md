# Meridian backend integration

## Foundation and scope

The branch `meridian-backend-integration` starts from `origin/meridian-redesign`.
The original landing composition, scene JavaScript, interactive globe, passport,
boarding pass, opening overlay, theme and brand assets are preserved. This is a
selective integration, not a merge of the teammate's frontend. No Streamlit app is used.

Imported from `jalaja-backend`: `backend/` (excluding a Windows shortcut), `data/`,
`docs/`, `tests/`, supporting scripts, and the Agent 2/7 service/worker modules.
All imported trained artifacts retain their original names and paths. No training,
artifact substitution or model repair was performed. The earlier documents describe
the teammate's branch; this document describes the delivered application.

## Implemented

- CSS 3D dossier with spine, page edges, float, hover tilt, navy/gold cover;
  new editorial chapter section without changing the existing opening sequence.
- Split-screen registration/login, show/hide password, email/password validation,
  loading/errors, logout, protected pages, 24-hour opaque sessions and server-side
  per-account persistence. Production uses Supabase PostgreSQL through
  `MERIDIAN_DATABASE_URL`; local development falls back to SQLite. Argon2id password
  hashes; hashed session tokens; persistent login throttling. No plaintext credentials
  or demonstration login.
- Dashboard showing the saved name, goals, completion, regions and last results.
- Original profile fields plus board, degree level, calling code, residence,
  internship details, funding choices, accommodation and commute preferences.
  Searchable country inputs, searchable/custom multiregion chips, inline validation,
  save/cancel and save-on-next-section. MBA essay input is conditional.
- Real synchronous HTTP requests with request-level loading, a maximum 50-second
  deadline per request, failure messages, retry and independent matching after a
  failed profile prediction. Five unsupported API agents are marked unavailable.
- Live matching cards and raw response inspection in the original dossier styling.
  PDF download and printable route contain only saved real results. Original demo
  components remain in source for future visual adaptations, but are not routed.
- Profile edits invalidate saved results; an in-flight result is discarded if the
  saved profile changes. Logout clears the visible state and revokes the session.
- Responsive layout CSS, keyboard focus, accessible labels and reduced-motion rules.

## Verified contracts and hard limitations

| Endpoint | Request | Actual behavior |
| --- | --- | --- |
| GET `/health` | none | Service health, not model readiness |
| POST `/predict/ms` | gpa, gre_score, toefl_score, research_experience, work_experience | Requires missing `ms_model.pkl`; returns explicit 503 for missing export |
| POST `/predict/mba` | gpa, gmat_score, work_experience, essay_score | Requires missing `mba_model.pkl`; returns explicit 503 for missing export |
| POST `/match` | gpa on 4-point scale, country, tier | Existing seven-entry heuristic catalog; returns matched_universities and count |
| POST `/agent3/program` | saved profile plus `/match` matched_universities | Ranks catalog programs for the Agent 2 shortlist using the extracted Agent 3 lexical/TF-IDF ranker |

The adapter converts explicit 4/10/100 GPA scales to 4-point GPA before calling
the backend. GRE total is verbal + quantitative. Numeric research/essay inputs
must be supplied explicitly; no score is inferred from prose or documents.

The supplied profile tier joblibs are not the MS/MBA pipeline files expected by
the routes. Agent 2 requires a complete `trained_models_local` bundle and checksum
manifest; Agent 7 expects its verified `trained_models` directory. Those bundles
are absent. The available older artifacts are retained but never substituted.
The matching API returns **no program details, scores, admission probabilities,
or explanations**. Its results are labeled rule-based catalog matches.
Agent 3 consumes those university names and resolves their programs from
`data/raw/agent2/agent2_enhanced_program_catalog.csv`. The compatible
`agent3_tfidf_fields.joblib` artifact is reused when its matrix shape matches
the normalized catalog. The serialized ranker/config artifacts are not loaded
because their original `agent3` module and serialization environment are absent.
Agent 3 scores are relevance rankings, not admission probabilities; missing
admission estimates remain unavailable.

Documents are uploaded directly to the authenticated frontend's private database-backed
metadata storage. TXT, DOCX and PDF files receive a bounded text preview and a processed status;
image files are retained but report that OCR is unavailable. Documents are not sent to
the analysis API or used by prediction/matching. There is no email delivery/reset
provider, so forgot-password is not offered. Regions, funding and commute preferences
persist but are not consumed by the current matcher (which only accepts country/tier/GPA).

## Windows / VS Code

Open the repository folder in VS Code. Use Python 3.11 and Node.js. Two environments
are required: Reflex and the backend's pinned FastAPI have conflicting Starlette
requirements. From a PowerShell terminal at repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pytest
py -3.11 -m venv .venv-backend
.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements-test.txt
```

Terminal 1:

```powershell
.\scripts\start_meridian.ps1 -Service backend
```

Terminal 2:

```powershell
$env:MERIDIAN_API_URL = 'http://127.0.0.1:8001'
.\scripts\start_meridian.ps1 -Service frontend
```

Visit http://localhost:3000. Start Journey opens the dossier transition and takes
you to sign-in. Register a real local account, save profile and matching country/tier,
then select Run / retry analysis. API docs: http://127.0.0.1:8001/docs.
Reflex initializes its frontend automatically on first run.

`.env.example` documents settings; set them in PowerShell (it is not automatically
loaded). For Render, add `MERIDIAN_DATABASE_URL` to the **meridian-frontend** service
using the Supabase session-pooler PostgreSQL URI; adding it only to `meridian-api`
does not persist accounts because account storage runs in the frontend process.
SQLite is stored under `.meridian/`, excluded from Git, and is suitable only for local
development/tests. Use HTTPS and `MERIDIAN_SECURE_COOKIE=1` when deployed. Reflex client-storage cookies
cannot be HttpOnly; this implementation uses SameSite=Strict, short-lived revocable
opaque tokens, and server-side authorization on persistence/report/analysis events.
For public production deployment, a vetted identity provider or an HttpOnly-cookie
gateway and verified email/reset delivery are still recommended. Keep the analysis
API private; it has no independent user authentication and is called server-to-server.

## Executed verification

- Dependency install in one environment: failed due to FastAPI/Starlette conflict;
  resolved by separate environments. Installed Reflex 0.10.0 and pinned it.
- `python -c "from meridian.meridian import app; app._compile()"`: passed.
- `.venv\Scripts\python.exe -m reflex export --frontend-only --no-zip`: passed,
  production compilation and all four build stages.
- `.venv\Scripts\python.exe -m pytest tests/test_meridian_integration.py -q`:
  **7 passed** (accounts, hashing, session expiry/revocation, isolation, throttling,
  validation, timeouts, actual state-handler progression with a test API double,
  result invalidation and protected events).
- `.venv-backend\Scripts\python.exe -m pytest backend/tests -q`: **3 passed**, two
  dependency deprecation warnings. The original health test was corrected from
  Flask's test client to FastAPI's TestClient; root imports are configured.
- `.venv\Scripts\python.exe scripts/smoke_integration.py`: **passed** against the
  running FastAPI server. Actual health request, both missing-model 503 responses,
  Reflex analysis handler -> HTTP matching -> saved result -> PDF creation -> logout.
  Disposable temporary test account, no user data or permanent test credentials.
- `.venv\Scripts\python.exe -m pytest tests -q --tb=short`: **10 failed, 12 passed,
  4 errors, 26 subtests passed** in the preserved teammate suite. Failures include
  missing ML runtime/bundles and tests coupled to the teammate's different state
  model/report shape. These have not been hidden, deleted or claimed as passing.
- Browser inventory exposed no browser or native app. Visual inspection, actual
  browser registration/login, mobile rendering and keyboard walkthrough remain
  unverified. Responsive CSS and all page components compiled successfully.

The first targeted run had a floating-point equality failure (3.3600000000000003
versus 3.36); the test now uses an appropriate tolerance. Initial backend collection
failed without its app import path; `backend/tests/conftest.py` fixes that path.

## Review files

See `docs/Integration-Files.txt` for every added/modified path relative to the original
frontend. Key implementation paths:

- `meridian/state.py`: auth, profile persistence, request lifecycle and real report.
- `meridian/services/storage.py`, `api.py`: account storage and API boundary.
- `meridian/pages/account.py`: authentication and dashboard.
- `meridian/data/profile.py`, `meridian/pages/profile.py`: profile schema/controls.
- `meridian/components/book.py`, `assets/enhancements.css`: 3D book and responsive CSS.
- `meridian/pages/landing.py`, `analysis.py`, `documents.py`, `results.py`: original
  layouts augmented with the new journey section and honest live/empty states.
- `meridian/meridian.py`, `meridian/components/navbar.py`: routes and navigation.
- `backend/app/__init__.py`, `config.py`: previously missing API startup/configuration.
- `backend/app/routes/profile_routes.py`: missing exports become explicit 503 errors.
- `tests/test_meridian_integration.py`, `backend/tests/`: executed regression tests.
- `scripts/start_meridian.ps1`, `smoke_integration.py`: launch and live verification.

No original branch was overwritten, force-pushed or deleted.
