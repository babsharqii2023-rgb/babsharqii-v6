# Steps 4-6 Fusion Implementation — Main Agent

## Task ID: fusion-steps-4-6

## Summary
Implemented Steps 4-6 of the Mamoun v40.0 Fusion Plan.

## Step 4: TypeScript Validator in SelfModifier
**File Modified:** `backend/mamoun/core/self_modifier.py`

### Changes:
1. Added imports: `re`, `subprocess`, `tempfile`, `Tuple` type
2. Added `_validate_syntax()` method that dispatches to the right validator based on file extension:
   - `.py` → `ast.parse()` (existing behavior)
   - `.ts`, `.tsx` → `_validate_typescript()`
   - `.js`, `.jsx` → `_validate_javascript()`
   - Unknown → `_validate_unknown()` (basic check)
3. Added `_validate_typescript()` method:
   - Writes content to a temp file
   - Runs `npx tsc --noEmit --noEmitOnError` on it
   - Falls back to `_validate_typescript_regex()` if npx tsc is unavailable
   - Cleans up temp file
4. Added `_validate_typescript_regex()` method:
   - Checks matched braces/brackets/parentheses
   - Handles strings, template literals, and comments
   - Basic structural validation
5. Added `_validate_javascript()` method:
   - Writes content to a temp file
   - Runs `node --check` on it
   - Falls back to regex check if node is unavailable
   - Cleans up temp file
6. Updated `validate_modification()` to use `_validate_syntax()` instead of direct `ast.parse()`
7. Updated `_dev_sandbox_bypass()` to use `_validate_syntax()` instead of direct `ast.parse()`

## Step 5: Connect Consciousness Panel to Real Data
**File Modified:** `src/lib/jarvis-api.ts`

### Changes:
1. Added `RealSystemData` interface with kernel, health, brains, and brainStatus fields
2. Added `fetchRealSystemData()` function that:
   - Calls 4 backend endpoints concurrently: `/api/kernel/status`, `/api/health-monitor`, `/api/brains`, `/api/brains/status`
   - Uses `Promise.allSettled` for resilience
   - Falls back to fallback data when backend is unreachable
   - Caches results and notifies subscribers
   - Uses relative paths for client-side requests (gateway compatibility)
3. Added `getCachedRealData()` helper
4. Added `startRealDataPolling()` function:
   - Registers callback for data updates
   - Fetches data immediately on start
   - Sets up 5-second polling interval
   - Returns cleanup function to stop polling
5. Added `stopRealDataPolling()` function
6. All data includes `_isOffline` flag for graceful degradation

## Step 6: Capability Assessor System

### New Files:
1. **`backend/mamoun/core/capability_assessor.py`**:
   - `CapabilityAssessor` class with `assess()` async method
   - Pipeline: API keys → Brains → Commands → Bridges → Overall fusion % → Summary + Recommendations
   - API key registry (GLM, DeepSeek, Gemini, OpenAI)
   - Command registry (search, self_modify, terminal, code_generation, etc.)
   - Bridge registry (execution, deliberation, monitoring)
   - Overall fusion calculation: 55% base + up to 45% bonus
   - Arabic summaries and recommendations

2. **`backend/mamoun/api/capability_assessor.py`**:
   - GET `/api/capabilities/assess` endpoint
   - Creates assessor with available components (LLM client, brain router, self modifier)
   - Registered in routes.py

### Modified Files:
3. **`backend/mamoun/api/routes.py`**:
   - Added import and registration for `capability_assessor_router`

4. **`src/lib/command-parser.ts`**:
   - Added `ASSESS_CAPABILITIES` to `CommandAction` type
   - Added command patterns for Arabic (قيّم قدراتك, ماذا تستطيع, تقييم القدرات, etc.)
   - Added command patterns for English (assess capabilities, what can you do, etc.)

5. **`src/lib/chat-governor.ts`**:
   - Added `assess_capabilities` to `GovernorAction` type
   - Added handling for `ASSESS_CAPABILITIES` parsed command → `assess_capabilities` action

6. **`src/app/api/chat/route.ts`**:
   - Added `assess_capabilities` execution bridge
   - Calls `${BACKEND_URL}/api/capabilities/assess`
   - Formats detailed assessment response with emojis and sections:
     - Overall fusion percent
     - Brains status (original vs fallback)
     - Bridges operational status
     - Available capabilities
     - Missing capabilities
     - Arabic summary
     - Recommendations
   - Falls back to local assessment when backend is unavailable
