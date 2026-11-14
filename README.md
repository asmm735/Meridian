# MERIDIAN

MERIDIAN is a study-abroad planning workspace for students applying to
international graduate programs. It turns a student's profile, goals, documents,
university shortlist, finances, scholarships, career interests, and
extracurricular experience into one saved, downloadable dossier.

## Why MERIDIAN is useful

Applying abroad usually means switching between spreadsheets, university pages,
scholarship portals, cost calculators, and career research. MERIDIAN brings those
steps into one workflow:

- **Profile** — save academic, test, experience, goals, budget, and preference data.
- **Documents** — privately upload resumes, transcripts, statements, and other
  application material. Supported text previews help you check what was stored.
- **University matching** — find universities that fit the selected country,
  catalog tier, GPA, and profile information.
- **Program recommendations** — rank programs from the university shortlist by
  profile relevance.
- **Financial planning** — show verified or model-backed tuition and living-cost
  estimates when the required source data is available.
- **Scholarship discovery** — identify potential scholarships and clearly show
  which eligibility details still need confirmation.
- **Career alignment** — suggest career paths and skills to build after graduation.
- **Extracurricular strength** — summarize structured research, projects,
  leadership, and experience inputs.
- **Saved dossier** — preserve results by account and export a printable PDF.

MERIDIAN is a planning aid, not an admissions authority. Scores are fit or
strength indicators, not guarantees of admission, funding, employment, or salary.
Students should verify current requirements, costs, deadlines, and awards with
each university or provider.

## Product flow

```text
Landing page
    ↓
Create account / sign in
    ↓
Complete and save profile
    ↓
Upload documents
    ↓
Run analysis
    ↓
Review results and download dossier
```

The application has separate Profile, Documents, Analysis, Results, and Report
pages. Profile and document changes invalidate old analysis results so a dossier
cannot silently mix old and new inputs.

## Architecture

MERIDIAN is a Python application with two services:

```text
meridian/                  Reflex frontend, state, pages, persistence
backend/app/               FastAPI analysis API
backend/app/agents/        Agent implementations and verified artifacts
data/                      Catalog and supporting data
tests/                     Frontend/integration tests
backend/tests/             FastAPI tests
docs/                      Detailed integration and agent documentation
render.yaml                Render deployment definition
Dockerfile                 Production frontend image
```

The frontend runs the authenticated user workflow and calls the FastAPI service
for analysis. Local development uses SQLite by default. Production can use
PostgreSQL/Supabase through `MERIDIAN_DATABASE_URL`.

The analysis sequence is:

1. Profile classification
2. University matching
3. Program ranking
4. Financial analysis
5. Scholarship analysis
6. Career analysis
7. Extracurricular scoring

Some agents depend on earlier results. For example, scholarship analysis requires
successful financial results. When verified data is unavailable, MERIDIAN reports
that limitation instead of fabricating a score or cost.

## Requirements

- Windows PowerShell, macOS, or Linux
- Python **3.11**
- Node.js/npm (required by Reflex during frontend setup)
- Git

Python 3.11 is recommended because the frontend and backend intentionally use
separate dependency environments. Reflex and the backend FastAPI stack have
conflicting dependency constraints.

## Clone and install

From a terminal:

```bash
git clone https://github.com/asmm735/Meridian.git
cd Meridian
```

### Windows PowerShell

Create the frontend environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create the separate backend environment:

```powershell
py -3.11 -m venv .venv-backend
.\.venv-backend\Scripts\python.exe -m pip install --upgrade pip
.\.venv-backend\Scripts\python.exe -m pip install -r backend\requirements.txt
```

If you want to run the test suites, install the test dependencies too:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv-backend\Scripts\python.exe -m pip install -r backend\requirements-test.txt
```

### macOS/Linux

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python3.11 -m venv .venv-backend
. .venv-backend/bin/activate
python -m pip install -r backend/requirements.txt
```

Use the equivalent `bin/python` paths for the test dependencies.

## Configure the environment

Copy the example file:

```powershell
Copy-Item .env.example .env
```

```bash
cp .env.example .env
```

Important local variables:

```dotenv
MERIDIAN_API_URL=http://127.0.0.1:8001
MERIDIAN_DATA_DIR=.meridian
MERIDIAN_SECURE_COOKIE=0
```

The local start script sets the API URL automatically. Do not commit `.env`,
database files, passwords, API keys, or other secrets.

### Production database

Set `MERIDIAN_DATABASE_URL` on the **frontend service**, because authentication,
profiles, documents, and saved results are managed by the frontend process.
SQLite is appropriate for local development only. Render filesystems are
ephemeral, so production accounts and document bytes require an external
persistent database.

## Run locally

Start the backend first in PowerShell terminal 1:

```powershell
.\scripts\start_meridian.ps1 -Service backend
```

This starts FastAPI at:

```text
http://127.0.0.1:8001
```

Start the Reflex frontend in PowerShell terminal 2:

```powershell
.\scripts\start_meridian.ps1 -Service frontend
```

Open:

```text
http://localhost:3000
```

Create a local account, complete the profile, select the matching country and
tier, upload documents if needed, save the profile, and run the analysis.

### Manual start commands

Backend:

```powershell
.\.venv-backend\Scripts\python.exe -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8001
```

Frontend:

```powershell
$env:MERIDIAN_API_URL = 'http://127.0.0.1:8001'
.\.venv\Scripts\python.exe -m reflex run --frontend-port 3000 --backend-port 8000 --backend-host 127.0.0.1
```

FastAPI documentation is available at:

```text
http://127.0.0.1:8001/docs
```

## Run tests

Frontend and integration tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Backend tests:

```powershell
.\.venv-backend\Scripts\python.exe -m pytest backend\tests -q
```

Useful focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_agent5_scholarship.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_meridian_integration.py -q
```

Health check:

```powershell
Invoke-WebRequest http://127.0.0.1:8001/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "study-abroad-ai-backend",
  "message": "API is running successfully."
}
```

## Deploying to Render

The repository includes [`render.yaml`](./render.yaml), which defines:

- `meridian-api` — FastAPI analysis service
- `meridian-frontend` — Dockerized Reflex application

To deploy:

1. Push the repository to GitHub.
2. Create a new Render Blueprint.
3. Select the GitHub repository.
4. Apply `render.yaml`.
5. Add `MERIDIAN_DATABASE_URL` to the `meridian-frontend` service.
6. Deploy both services.
7. Check the API `/health` endpoint and open the frontend URL.

The frontend is configured to call the API over Render's private service
network. Keep the API service private where possible; it is intended to be
called server-to-server by the frontend.

For production, also set:

```text
MERIDIAN_SECURE_COOKIE=1
MERIDIAN_DATABASE_URL=<your external PostgreSQL connection string>
```

Never place database credentials or private keys in GitHub, `render.yaml`, or
the frontend bundle.

## Documents and privacy

Documents belong to the authenticated account. Metadata and extracted content
are stored through the application storage layer. PDF, DOCX, and TXT files can
provide bounded text previews; image OCR is not currently available.

Document text is used for relevance/context features where supported. Structured
grades, budgets, and explicit experience values should be entered in the
profile; they are not silently inferred from document text.

For a production launch, add a vetted identity provider, password-reset/email
delivery, monitoring, backups, and a formal privacy policy before handling
sensitive student documents at scale.

## Known limitations

- Results depend on the quality and coverage of the available catalogs and
  verified model artifacts.
- Missing provider fields remain visible as confirmation tasks rather than
  guessed values.
- Fit, strength, cost, and salary outputs are estimates or rankings and are not
  guarantees.
- Image OCR is not available.
- The production analysis API must be monitored for cold starts and resource
  limits on free hosting plans.
- Missing or incompatible model artifacts produce an explicit unavailable result;
  MERIDIAN does not substitute unrelated models.

## Additional documentation

- [Integration and Windows run guide](./docs/Meridian-Integration.md)
- [Agent 7 application integration](./docs/Agent7-Application-Integration.md)
- [Environment example](./.env.example)
- [Render deployment definition](./render.yaml)

## License

No license is currently declared in this repository. Add a license before
redistributing the project or accepting external contributions.
