# EasyMeals Backend Guide

This guide explains how the backend works end-to-end, with emphasis on meal-plan generation order, persistence, and runtime behavior.

## 1) Backend entry points

- Python API server: `backend/backend.py`
- Core generation logic: `backend/db/plan_service.py`
- Gemini integration: `backend/db/gemini_service.py`
- Firestore client bootstrap: `backend/db/firestore_client.py`
- Ingredient canonicalization and cost recalculation: `backend/db/ingredient_service.py`
- Rating system: `backend/db/rating_service.py`
- Diversity scoring helpers: `backend/db/diversity_service.py`
- Canonical ingredient/price catalog for Gemini prompting: `backend/accurate_ingredients.json`

## 2) Request path from UI to Python backend

The frontend does not call Python directly from React components. It goes through Next.js API proxy routes first:

1. Wizard submits `POST /api/plan/generate` from `frontend/app/components/MealPlanWizard.tsx`.
2. Next route `frontend/app/api/plan/generate/route.ts` validates bearer header and forwards to Python `POST /api/generate-plan`.
3. Python FastAPI route `backend/backend.py`:
   - validates payload using `PlanGenerationRequest`
   - verifies Firebase ID token unless `TESTING=true`
   - calls `generate_and_store_plan(...)`
4. UI polls `GET /api/plan/latest?userId=...` via `frontend/app/context/MealPlanContext.tsx`, proxied by `frontend/app/api/plan/latest/route.ts` to Python `GET /api/get-plan/{user_id}`.

Backend startup details that affect production behavior:
- Firebase credentials are loaded from `FIREBASE_SERVICE_ACCOUNT` (JSON string) when present, otherwise local `secrets/serviceAccountKey.json`.
- CORS is currently open (`allow_origins=["*"]`).

## 3) Meal plan generation order (exact backend sequence)

The generation pipeline is intentionally split into a fast synchronous phase and a longer async background phase.

### Phase A: synchronous request (returns quickly with placeholders)

Implemented in `generate_and_store_plan(...)` in `backend/db/plan_service.py`.

1. Validate Firestore client exists.
2. Create IDs and planning metadata:
   - `plan_id = plan_<uuid>`
   - `target_month = resolve_target_month(user_id)`
   - `plan_version = get_next_plan_version(user_id, target_month)`
3. Acquire user-level generation lock (`acquire_generation_lock`):
   - transaction writes `users/{uid}.activeGeneration = running`
   - rejects if existing non-expired lock (`GenerationConflictError`)
4. Build preference dict from request.
5. First Gemini pass: `generate_meal_name_plan(preferences)`:
   - generates exactly 28 meal outlines (name/day/type/description only)
6. Build placeholder meals (`_build_placeholder_meals`) with:
   - `status="pending"`
   - `imageGenStatus="pending"`
   - empty nutrition/cost/details
7. Chunk into 4 week docs (`chunk_meals_into_weeks`).
8. Persist initial plan (`persist_user_plan`) with status `generating` and zero costs.
9. Persist progress snapshot (`_set_plan_progress`) so UI can render immediately.
10. Submit background job (`_submit_plan_generation_job`) to thread pool.
11. Return HTTP response with:
   - `status="generating"`
   - placeholder weeks
   - metadata (request ID, month, version, timings)

Result: client gets a plan immediately, then polls for completed cards.

### Phase B: background completion (fills details per meal)

Implemented in `_complete_plan_details_in_background(...)` in `backend/db/plan_service.py`.

1. Copy working weeks in memory.
2. Process meal details in waves:
   - submit at most `MEAL_DETAIL_PARALLELISM` futures at a time (default 3)
   - wait for the entire batch to finish
   - sleep for `MEAL_DETAIL_SUBMIT_STAGGER_SECONDS` (default 2.0s) before the next batch
3. For each completed future in the active batch (`as_completed`):
   - call `generate_meal_details(preferences, outline)`
   - upsert ingredient docs from Gemini `ingredientPrices` (`upsert_ingredient_prices`)
   - build mapping/hints (`build_normalized_name_map`, `build_price_hint_map`)
   - recalculate trusted meal cost server-side (`recalculate_meal_costs`)
   - dedupe or create recipe doc (`dedupe_or_create_recipes`)
   - merge completed meal back into plan slot
   - strip `recipeRef` before writing the meal into the `weeks` array (prevents Firestore embedded-reference path errors)
   - preserve image fields if image pipeline already touched the meal
   - mark meal `status="completed"`
4. If a meal detail task fails:
   - generate deterministic fallback meal (`_build_fallback_meal`)
   - mark it completed with warning/error fields
5. After every meal completion/fallback:
   - call `_set_plan_progress(...)`
   - recompute `estimatedTotalCost`, grocery list, and progress counters
6. Finalization:
   - if all 28 meals are in completed state:
     - supersede older ready plans for same month (`supersede_ready_plans_for_month`)
     - append entries to `users/{uid}/mealHistory` (`append_meal_history`)
     - set plan status `ready`
     - sync day docs (`_sync_day_docs`)
     - write completion metadata (timings, fallback count, superseded count, budget target/final/budget headroom fields)
     - release lock as `ready`
   - otherwise set status `failed` and release lock as `failed`
7. Any unexpected top-level exception:
   - best effort set plan status `failed`
   - release lock

## 4) Gemini call behavior and guardrails

Implemented in `backend/db/gemini_service.py`.

- Uses model constant `gemini-3.1-flash-lite-preview`.
- Name pass and detail pass use different prompts.
- Detail pass uses a focused ingredient subset selected from `accurate_ingredients.json` (keyword + fallback selection) to reduce ID drift/hallucinated ingredient IDs.
- `_call_and_parse(...)`:
  - executes model call with timeout (`GEMINI_CALL_TIMEOUT_SECONDS`, default 40s for detail pass)
  - name pass uses `GEMINI_NAME_PASS_TIMEOUT_SECONDS` (default 40s)
  - retries parse/model failures (default 3 attempts)
  - applies retry backoff (`GEMINI_RETRY_BACKOFF_SECONDS`)
  - strips markdown fences before JSON parse
- In detail pass, cost is recomputed in Python from canonical ingredient prices (with alias/suffix ID resolution), then plan service recalculates trusted meal costs again from Firestore ingredient docs.
- Forces dinner-only normalization:
  - `mealType` always set to `"Dinner"`
- Normalizes instruction text:
  - converts numbered instructions into a single sentence string when needed

## 5) Firestore data model written during generation

Primary writes:

- `users/{uid}`
  - `activeGeneration` lock block
  - `mealPlanProfile` snapshot
- `users/{uid}/plans/{planId}`
  - request inputs, status, versioning, month, weeks, groceryList, progress, metadata
- `users/{uid}/plans/{planId}/days/day_XX`
  - flattened per-day view for query convenience
- `ingredients/{ingredientId}`
  - canonical ingredient docs created or reused
- `recipes/{recipeId}`
  - deduped recipe docs with nutrition/instructions/rating fields
- `users/{uid}/mealHistory/*`
  - one entry per completed meal when plan finalizes ready

## 6) Plan status lifecycle

Plan statuses seen in code:

- `generating`: initial persisted plan and in-progress background updates
- `ready`: all meal slots completed and finalization succeeded
- `failed`: unrecoverable failure in generation/finalization
- `superseded`: older ready plan for same month replaced by newer ready plan

Meal statuses inside `weeks[*].meals[*]`:

- `pending`: placeholder not yet filled
- `completed`: detail generated or fallback created

## 7) Concurrency and locking model

- One active generation per user is enforced with a transactional lock in `users/{uid}.activeGeneration`.
- Lock timeout defaults to 10 minutes to recover from abandoned jobs.
- FastAPI request thread returns after Phase A; Phase B runs in background pool.
- Per-meal detail generation is batch-parallelized:
  - max concurrent detail requests equals `MEAL_DETAIL_PARALLELISM`
  - batches are sequential with a configurable stagger delay
  - completion order is non-deterministic inside each batch
- Progress writes are incremental, enabling UI card-by-card unlock.

## 8) How latest plan is selected during polling

`GET /api/get-plan/{user_id}` in `backend/backend.py`:

1. load all plans for user
2. prefer plans in `{"generating", "ready"}`
3. sort by `(createdAt, version)` descending
4. return top plan

This is why a newer generating plan is shown even when an older ready plan exists.

## 9) Error mapping and HTTP behavior

From `backend/backend.py`:

- `400`:
  - request validation failures
  - value errors (invalid precision/range/etc.)
- `401`:
  - missing/invalid bearer token
- `403`:
  - token uid mismatch with requested `userId`
- `409`:
  - generation lock conflict (already running)
- `404`:
  - no plan found for `GET /api/get-plan/{user_id}`
- `500`:
  - internal generation/read/write errors

## 10) Related backend features beyond plan generation

### Meal rating

- Endpoint: `POST /api/rate-meal` (`backend/backend.py`)
- Logic: `backend/db/rating_service.py`
- Behavior:
  - validates rating 1..5
  - updates `recipes/{mealId}` aggregate rating fields
  - writes user rating event under `recipes/{mealId}/ratings`
  - updates global stats in `meta/globalStats`

### Diversity scoring helpers

- File: `backend/db/diversity_service.py`
- Functions compute recency-penalized score using recent `mealHistory`.
- In current code, helper `apply_diversity_selection(...)` exists in `plan_service.py` but is not in the active generation execution path.

### Image generation pipeline (post-plan)

- Triggered by frontend route `frontend/app/api/generate-meal-images/route.ts`
- Runs Python script `backend/generate_meal_images.py` as detached job
- Fills missing plan meal images and syncs recipe image URLs
- Tracks per-meal image fields:
  - `imageGenStatus`, `imageGenAttempts`, `imageGenError`

## 11) Environment variables that affect backend behavior

Primary runtime knobs:

- `TESTING=true` bypasses Firebase auth token verification in API routes
- `FIREBASE_SERVICE_ACCOUNT` Firebase credential JSON string (server/cloud deployments)
- `GEMINI_API_KEY` required for Gemini calls
- `PLAN_GENERATION_MAX_WORKERS` size of global plan background executor
- `MEAL_DETAIL_PARALLELISM` per-plan detail fanout
- `MEAL_DETAIL_SUBMIT_STAGGER_SECONDS` delay between detail batches
- `GEMINI_CALL_TIMEOUT_SECONDS` detail-pass timeout
- `GEMINI_NAME_PASS_TIMEOUT_SECONDS` name-pass timeout
- `GEMINI_RETRY_BACKOFF_SECONDS` retry backoff between Gemini attempts

Frontend proxy knobs that impact backend access:

- `BACKEND_API_URL` Python API base URL
- `BACKEND_PROXY_TIMEOUT_MS` Next proxy timeout

## 12) Practical debugging checklist for generation issues

1. Confirm `POST /api/generate-plan` returns `200` with `status=generating`.
2. Confirm lock is set under `users/{uid}.activeGeneration`.
3. Confirm placeholder plan doc exists under `users/{uid}/plans/{planId}`.
4. Watch `generationProgress` and meal-level `status` fields advance.
5. If stuck, inspect fallback/error fields on meals.
6. Verify ingredient and recipe docs are being created/reused.
7. Check final status transitions to `ready` or `failed`.
8. Verify lock release (`activeGeneration.status=idle`).
