/**
 * Backend Capabilities Knowledge Layer v59
 * 
 * CRITICAL ADDITION from v59:
 * - v58: Frontend was a blind proxy — no knowledge of backend structure
 * - v59: Frontend now knows what backend can do, which endpoints exist,
 *   and how to route requests intelligently
 * - Smart proxy with caching and fallback
 * - Structural knowledge of backend API routes
 * 
 * v59 — Super Mind العقل الخارق مامون
 */

// Backend API capabilities map
export const BACKEND_CAPABILITIES = {
  brains: {
    route: '/api/brains',
    methods: ['GET', 'POST'],
    description: 'Brain routing with 5 cognitive brains',
    components: ['neural', 'causal', 'symbolic', 'bayesian', 'world_model'],
  },
  chat: {
    route: '/api/chat',
    methods: ['POST'],
    description: 'Main chat endpoint with brain routing',
  },
  mamounChat: {
    route: '/api/mamoun-chat',
    methods: ['POST'],
    description: 'Mamoun chat with streaming support',
    streaming: '/api/mamoun-chat/stream',
  },
  evolution: {
    route: '/api/evolution',
    methods: ['GET', 'POST'],
    description: 'Self-evolution loop (v2 available)',
    v2: '/api/evolution/current',
  },
  consciousness: {
    route: '/api/consciousness',
    methods: ['GET'],
    description: 'Consciousness state monitoring',
    state: '/api/consciousness/state',
  },
  health: {
    route: '/api/health',
    methods: ['GET'],
    description: 'System health check',
  },
  kernel: {
    route: '/api/kernel',
    methods: ['GET'],
    description: 'Kernel status and management',
    status: '/api/kernel/status',
    projects: '/api/kernel/projects',
    tools: '/api/kernel/tools',
    workspace: '/api/kernel/workspace',
  },
  selfHeal: {
    route: '/api/self-heal',
    methods: ['GET', 'POST'],
    description: 'Self-healing system',
    patch: '/api/self-heal/patch',
    sandbox: '/api/self-heal/sandbox',
  },
  selfModify: {
    route: '/api/self-modify',
    methods: ['POST'],
    description: 'Self-modification with safety checks',
  },
  capabilities: {
    route: '/api/capabilities',
    methods: ['GET'],
    description: 'System capabilities overview',
    code: '/api/capabilities/code',
    browser: '/api/capabilities/browser',
    terminal: '/api/capabilities/terminal',
    trading: '/api/capabilities/trading',
    sandbox: '/api/capabilities/sandbox',
    projects: '/api/capabilities/projects',
  },
  agi: {
    route: '/api/agi',
    methods: ['GET', 'POST'],
    description: 'AGI pillars and capabilities',
    attention: '/api/agi/attention',
    capabilities: '/api/agi/capabilities',
    causal: '/api/agi/causal',
    commonSense: '/api/agi/common-sense',
    continualLearning: '/api/agi/continual-learning',
    fluidReasoner: '/api/agi/fluid-reasoner',
    hallucination: '/api/agi/hallucination',
    intentDrift: '/api/agi/intent-drift',
    learn: '/api/agi/learn',
    memory: '/api/agi/memory',
    meta: '/api/agi/meta',
    plan: '/api/agi/plan',
    privacy: '/api/agi/privacy',
    skillDiscovery: '/api/agi/skill-discovery',
    status: '/api/agi/status',
    system2: '/api/agi/system2',
    theoryOfMind: '/api/agi/theory-of-mind',
    uncertainty: '/api/agi/uncertainty',
    world: '/api/agi/world',
  },
  living: {
    route: '/api/living',
    methods: ['GET'],
    description: 'Living system vitals',
    bonding: '/api/living/bonding',
    emotions: '/api/living/emotions',
    event: '/api/living/event',
    heartbeat: '/api/living/heartbeat',
    identity: '/api/living/identity',
    memory: '/api/living/memory',
    reflexes: '/api/living/reflexes',
    vitals: '/api/living/vitals',
  },
  awareness: {
    route: '/api/awareness',
    methods: ['GET'],
    description: 'System awareness',
    meta: '/api/awareness/meta',
    state: '/api/awareness/state',
    vitality: '/api/awareness/vitality',
  },
  update: {
    route: '/api/update',
    methods: ['GET', 'POST'],
    description: 'System update management',
    check: '/api/update/check',
    improve: '/api/update/improve',
    mirror: '/api/update/mirror',
    status: '/api/update/status',
    rollback: '/api/update/rollback',
    quality: '/api/update/quality',
  },
  deliberation: {
    route: '/api/deliberation',
    methods: ['POST'],
    description: 'Brain deliberation room',
  },
  safety: {
    route: '/api/safety',
    methods: ['GET'],
    description: 'Safety system',
    laws: '/api/safety/laws',
  },
} as const;

// Cache for backend responses
const responseCache = new Map<string, { data: any; timestamp: number }>();
const CACHE_TTL = 30000; // 30 seconds

/**
 * Get the list of available backend capabilities
 */
export function getBackendCapabilities(): typeof BACKEND_CAPABILITIES {
  return BACKEND_CAPABILITIES;
}

/**
 * Check if a specific backend endpoint exists
 */
export function hasBackendEndpoint(path: string): boolean {
  const normalizedPath = path.replace('/api/', '');
  for (const capability of Object.values(BACKEND_CAPABILITIES)) {
    const capPath = capability.route.replace('/api/', '');
    if (normalizedPath === capPath || normalizedPath.startsWith(capPath + '/')) {
      return true;
    }
    // Check sub-routes
    for (const [key, value] of Object.entries(capability)) {
      if (typeof value === 'string' && value.startsWith('/api/')) {
        const subPath = value.replace('/api/', '');
        if (normalizedPath === subPath) {
          return true;
        }
      }
    }
  }
  return false;
}

/**
 * Create a smart proxy that knows about backend capabilities
 */
export async function smartProxy(
  apiPath: string,
  options: RequestInit = {}
): Promise<Response> {
  const cacheKey = `${apiPath}:${JSON.stringify(options)}`;
  
  // Check cache for GET requests
  if (!options.method || options.method === 'GET') {
    const cached = responseCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      return new Response(JSON.stringify(cached.data), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  // Check if endpoint exists in our knowledge
  const isKnown = hasBackendEndpoint(apiPath);

  try {
    const response = await fetch(apiPath, options);

    if (!response.ok) {
      // If endpoint is known but failed, try fallback
      if (isKnown) {
        console.warn(`Backend endpoint ${apiPath} failed (${response.status}), using fallback`);
        return createFallbackResponse(apiPath);
      }
      return response;
    }

    // Cache successful GET responses
    if (!options.method || options.method === 'GET') {
      try {
        const data = await response.clone().json();
        responseCache.set(cacheKey, { data, timestamp: Date.now() });
      } catch {
        // Not JSON, skip caching
      }
    }

    return response;
  } catch (error) {
    // Network error — try fallback if known endpoint
    if (isKnown) {
      console.warn(`Backend unavailable for ${apiPath}, using local fallback`);
      return createFallbackResponse(apiPath);
    }
    throw error;
  }
}

/**
 * Create a fallback response when backend is unavailable
 */
function createFallbackResponse(apiPath: string): Response {
  const fallbackData: Record<string, any> = {
    '/api/health': { status: 'degraded', backend: 'unavailable', mode: 'fallback' },
    '/api/kernel/status': { version: 'v59', state: 'fallback', backend_connected: false },
    '/api/brains': { brains: [], message: 'Backend unavailable — using fallback' },
    '/api/consciousness/state': { state: 'dormant', backend_connected: false },
    '/api/awareness/vitality': { vitality: 0, backend_connected: false },
  };

  const data = fallbackData[apiPath] || {
    error: 'Backend unavailable',
    path: apiPath,
    mode: 'fallback',
    timestamp: Date.now(),
  };

  return new Response(JSON.stringify(data), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'X-Fallback': 'true',
    },
  });
}

/**
 * Get a summary of all available backend routes
 */
export function getBackendRouteSummary(): { total: number; categories: string[] } {
  const categories = Object.keys(BACKEND_CAPABILITIES);
  let total = categories.length;
  for (const cap of Object.values(BACKEND_CAPABILITIES)) {
    for (const [key, value] of Object.entries(cap)) {
      if (typeof value === 'string' && value.startsWith('/api/') && key !== 'route') {
        total++;
      }
    }
  }
  return { total, categories };
}
