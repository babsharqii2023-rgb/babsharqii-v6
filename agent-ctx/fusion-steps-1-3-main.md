# Task: Mamoun v40.0 Fusion Plan Steps 1-3

## Agent: Main Implementation Agent
## Date: 2026-03-05

## Summary

Successfully implemented all 3 steps of the Mamoun v40.0 Fusion Plan, connecting the deliberation room to the frontend, enabling the auto-research-heal loop, and adding API key diversification with brain status reporting.

## Changes Made

### Step 1: ربط غرفة المداولة بالفرونت إند (Connect Deliberation Room to Frontend)

1. **`src/lib/brains.ts`** — Added `deliberateViaBackend(query, context?)` function:
   - POSTs to `http://localhost:8000/api/brains/deliberate` with `{ query, context }`
   - Parses SSE stream from backend to extract `deliberation_complete` event
   - Maps backend response to `BrainRoutingResult`-compatible object
   - Falls back to local `determinePrimaryBrain()` if backend is unavailable

2. **`src/app/api/chat/route.ts`** — Modified the `needsFullDeliberation` block:
   - Step 1: Tries `deliberateViaBackend()` FIRST to get routing from the real deliberation room
   - Step 2: Tries kernel chat (`/api/kernel/chat`) for full 5-brain response
   - Step 3: If deliberation data was received but kernel failed, enriches local LLM call with deliberation routing
   - Includes `deliberationData` in the response with all 5 brain responses, consensus level, CJS, conflict detection, and mirror reflection

3. **`src/app/api/deliberation/route.ts`** — Updated to proxy to backend's `/api/brains/deliberate`:
   - Tries backend deliberation endpoint FIRST (SSE stream parsing)
   - Falls back to kernel chat
   - Falls back to local LLM-based deliberation

### Step 2: تفعيل حلقة البحث-التعلم-الإصلاح التلقائية (Auto-Research-Heal Loop)

1. **`backend/mamoun/api/health_monitor.py`** — Major modifications:

   - Added `AUTO_RESEARCH_HEAL_ENABLED` config flag (default True, env `AUTO_RESEARCH_HEAL_ENABLED`)
   
   - In `auto_heal_component()`:
     - After Step 1 (re-import) and Step 2 (SelfModifier) fail, added **Step 3**: AutoResearchHealLoop
     - Imports `AutoResearchHealLoop` from `mamoun.evolution.auto_research_heal`
     - Imports `Weakness` from `mamoun.evolution.live_self_modifier`
     - Creates/gets loop instance (from kernel or new with LLM client)
     - Calls `heal_with_research()` with a Weakness object
     - If research heal succeeds, marks component as healed
     - Kept legacy kernel fallback as additional safety net
   
   - In `check_all_components()`:
     - After the health check loop, if any component is unhealthy and not already being healed
     - Automatically triggers `auto_heal_component()` as a background task
     - Adds alerts for unhealthy components with auto-research-heal info

### Step 3: تنويع مفاتيح API للأدمغة (API Key Diversification + Brain Status Report)

1. **`backend/mamoun/brains/brain_router.py`** — Major modifications:

   - Added `BRAIN_MODEL_REGISTRY` dict mapping brain_id → {original_model, fallback_model, api_key_env, name_ar}
   
   - In `route()` method:
     - After executing brains, calls `_check_fallback_models()` to detect brains using fallback models
     - If any brain is on fallback, adds `"fallback_warnings"` list to response metadata
     - Warning format: "Brain X (name_ar) is using fallback model Y instead of original model Z. Set API_KEY to enable original model."
   
   - Added `get_brain_status()` method:
     - Returns detailed status for each brain: original model, actual model used, is_on_fallback, api_key_env, has_api_key, confidence, weight, error_count, fallback_warning
     - Includes unregistered brains from registry with "not_registered" status

2. **`backend/mamoun/api/brain_status.py`** — NEW file:
   - GET `/api/brains/status` endpoint
   - Returns detailed brain status with summary (total, active, on_fallback, missing_api_keys)
   - Falls back gracefully to registry-only data if BrainRouter is unavailable

3. **`backend/mamoun/api/routes.py`** — Registered the new brain_status router

4. **`src/lib/command-parser.ts`** — Added `BRAIN_STATUS` command:
   - Added to `CommandAction` type
   - Arabic patterns: "حالة الأدمغة", "أظهر حالة الأدمغة", "تقرير الأدمغة", "ما حالة الأدمغة", "هل الأدمغة تعمل"
   - English patterns: "brain status", "brains status", "brain health", "show brain status", "brain report"

5. **`src/lib/chat-governor.ts`** — Added `brain_status` handling:
   - Added `brain_status` to `GovernorAction` type
   - Handles `BRAIN_STATUS` command action → sets action to `brain_status`, no full deliberation needed

6. **`src/app/api/chat/route.ts`** — Added brain_status execution bridge:
   - Fetches `/api/brains/status` from backend
   - Formats detailed status message with icons (🟢🟡🟠🔴), fallback warnings, and API key requirements
   - Falls back to local BRAIN_PERSONAS data if backend is unavailable

## TypeScript Verification

- Ran `tsc --noEmit` — no errors in modified source files (only pre-existing test file errors)
