# Agent 7 integration — 2026-10-23

Agent 7 now runs in the authenticated Meridian analysis workflow alongside the existing Agent 1, Agent 2 catalog matcher and Agent 3 program ranker. No predictions are substituted when inputs, models or the runtime are unavailable.

## Artifact inspection and recovery

`docs/model-artifact-audit.json` records direct load attempts, actual types, feature schemas, dependency warnings and SHA-256 hashes for all 42 original repository `.joblib` files, plus the eight supplemental Agent 7 files. The audit used an isolated runtime; no original artifact was modified. The user’s pre-existing move from `joblibs/` to `trained_models_A7/` was preserved.

The Agent 7 filenames do not describe their contents. Four usable objects were recovered byte-for-byte into `backend/app/agents/extracurricular_agent/trained_models/`:

| Canonical artifact | Original file in trained_models_A7 |
| --- | --- |
| agent7_feature_columns.joblib | agent7_archetype_scaler (2).joblib |
| agent7_gbr_score_model.joblib | agent7_scaler (2).joblib |
| agent7_archetype_kmeans.joblib | agent7_resume_archetype_kmeans (2).joblib |
| agent7_archetype_scaler.joblib | agent7_real_p90_thresholds (2).joblib |

The supposed XGBoost artifact contains logistic regression. It needs a missing 22-feature input scaler; the supplied other scalers have five or six inputs. No compatible Agent 7 XGBoost exists among the supplied files. Only `agent7_xgb_tier_model.joblib` was regenerated, using the notebook’s actual synthetic generator, seed 42, 4,000 rows, training/test split and classifier parameter literal. The notebook itself was preserved. The recovered regressor and clustering models were not retrained.

The original models record scikit-learn 1.8.0. The previous requirements specified 1.7.2; the app environment uses 1.4.2. Agent 7 now uses an isolated `.venv-agent7`, with exact dependency pins. The feature builder now follows the recovered model’s categorical column order, matching notebook `get_dummies` ordering. Inference validates manifest hashes, runtime versions, object types, classes, feature ordering, dimensions and finite predictions. The worker imports the agent package without initializing the unrelated FastAPI application.

`trained_models/manifest.json` records all hashes, recovered source filenames, the reason for the single replacement, notebook hash, training indices and synthetic-only diagnostics. Original regressor/clustering split provenance is unavailable; their diagnostic errors are not claimed as held-out accuracy.

## Application flow

- Experience collects four documented scores (0–10), publication and patent counts, and explicit degree/field categories. Values start blank. Unknown values are never changed to zero or inferred from free text/uploads. Supplied values are validated on save; all eight are required for Agent 7 inference.
- Run/retry analysis invokes the real worker off the event loop. Agent 7 has an independent status and error; its failure does not prevent Agent 2/3 from completing.
- The account database stores the result under `results.extracurricular` and records running/completed/failed events in `analysis_runs`. Reloading restores the same result. Saving profile changes invalidates results; concurrent saved edits prevent old inference from being published.
- Analysis, results, the active `/report` printable route and downloadable PDF use the saved result, including tier, score, P(Strong), cluster and reported research evidence. The probability is clearly identified as a synthetic class probability, not an admission probability.
- Completed and failed agent statuses are restored on reload. Browser verification also exposed profile overflow on small screens; grid children can now shrink and form navigation buttons wrap.
- The existing Agent 2 `/match` contract remains GPA/country/catalog-tier filtering. It has no compatible Agent 7 input, so no score is injected into it. Agent 3 receives its unchanged shortlist. The separate experimental five-feature Agent 2 adapter can map a real Agent 7 score, and that contract is tested, but its required local export is absent. The supplied 19-feature Agent 2 model is not interchangeable with it.

## Run

Create the isolated runtime once (use your installed Python):

```powershell
python -m venv .venv-agent7
.venv-agent7/Scripts/python.exe -m pip install -r backend/app/agents/extracurricular_agent/requirements.txt
```

The app automatically selects `.venv-agent7`; `MERIDIAN_AGENT7_PYTHON` overrides it. If neither is available, the current interpreter must satisfy the pins. Start Meridian normally. No training runs during application startup or requests.

The recovery pipeline is available, but the current checkout does not contain the four source artifacts it expects under `trained_models_A7`, so it cannot produce a verified bundle. Only after those original artifacts are restored should `scripts/prepare_agent7_bundle.py` be run in the Agent 7 runtime. It refuses to overwrite an existing bundle. `repair.py` delegates to this minimal recovery pipeline rather than rebuilding all models.

## Verification

- Full application suite: 44 passed, 4 skipped, 14 subtests passed. The skips are for the absent optional five-feature Agent 2 export, not the working catalog matcher.
- Backend contracts: 12 passed, including Agent 2 matching and Agent 3 ranking. Existing dependency warnings for Agent 1/3 remain.
- Model verification: 8 passed, covering fresh-process/foreign-directory determinism, invalid input, missing/corrupt models, wrong types and existing SOP behavior. Exact inputs and outputs: `docs/agent7-model-verification.json`.
- Reflex application compilation passed.
- Real Agent 7 integration tests cover database events, reload, PDF text, score variation, input validation, unavailable runtime, retry, Agent 2 input compatibility and concurrent saved profile changes. Other services are contract fixtures in these state tests; backend tests separately exercise real Agent 2/3 code.

For the constructed test input leadership 6, research 9, competition 5, volunteering 4, publications 3, patents 0, Masters/STEM, real inference returns Moderate, 60.9/100, P(Strong) 0.154371, cluster 0, reported research evidence 1. These are software test predictions, not accuracy evidence.

## Remaining limitations

Resume/NER extraction cannot be treated as validated from the scrambled/incomplete supplemental bundle. Uploaded text is not used to invent structured scores. SOP helpers remain separately tested and are not part of the structured application score. No LOR model was recovered. Synthetic training labels do not establish admissions accuracy.

Other agents’ artifacts were inspected but not rewritten. The audit records version warnings, Agent 3’s unavailable serialized `agent3` module and pandas compatibility errors for its unused catalog export. The active Agent 3 implementation uses its existing catalog/ranker path and passes backend tests. The optional experimental Agent 2 export remains unavailable; the current rule-based Agent 2 integration is preserved.
