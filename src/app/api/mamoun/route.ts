// =============================================================================
// API Proxy Route — /api/mamoun
// Bridges frontend requests to the Python FastAPI backend
// =============================================================================
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';
const REQUEST_TIMEOUT = 15000; // 15 seconds

// Allowed endpoints whitelist for security
const ALLOWED_ENDPOINTS = [
  'awareness/state',
  'awareness/vitality',
  'awareness/meta',
  'brains',
  'consciousness',
  'evolution',
  'evolution/current',
  'safety/laws',
  'security',
  'kernel/status',
  'kernel/workspace',
  'kernel/llm-stats',
  'self-heal',
  'self-heal/patch',
  'auto-improve',
  'deliberation',
  'creativity',
  'agi',
  'agi/causal',
  'agi/memory',
  'agi/meta',
  'agi/plan',
  'agi/world',
  'agi/learn',
  'agi/attention',
  'agi/fluid-reasoner',
  'agi/theory-of-mind',
  'agi/common-sense',
  'agi/continual-learning',
  'agi/skill-discovery',
  'agi/privacy',
  'agi/hallucination',
  'agi/intent-drift',
  'agi/system2',
  'temporal',
  'sleep',
  'auth',
  'events',
  'predictions',
  'settings',
  'emotion',
  'terminal',
  'v23/neural-bus',
  'v23/healing/autonomous-update',
  'v24/self-modify',
  'v24/monologue',
  'v25/neural',
  'v25/transfer',
  'v25/bridge',
  'hyperagent/meta',
  'hyperagent/supra',
  'hyperagent/status',
  'hyperagent/curriculum',
  'hyperagent/archive',
  'mamoun',
  'mamoun/kernel/capabilities',
  'mamoun/kernel/working-memory',
  'mamoun/instincts',
  'living/vitals',
  'living/emotions',
  'living/bonding',
  'living/reflexes',
  'living/heartbeat',
  'living/memory',
  'living/identity',
  'capabilities/code',
  'capabilities/laptop-control',
  'capabilities/projects',
  'capabilities/browser',
  'capabilities/sandbox',
  'capabilities/blender',
  'capabilities/instagram',
  'capabilities/trading',
  'capabilities/orchestrator',
  'swarm',
  'a2ui',
  'build-project',
  'self-modify',
  'autonomy',
  'awareness',
  'evolution-v19',
  'admin/backup',
];

async function proxyRequest(request: NextRequest) {
  const endpoint = request.nextUrl.searchParams.get('endpoint');

  if (!endpoint) {
    return NextResponse.json(
      { error: 'Missing endpoint parameter', source: 'proxy' },
      { status: 400 }
    );
  }

  // Security: Validate endpoint against whitelist
  const normalizedEndpoint = endpoint.replace(/^\//, '').replace(/\/+$/, '');
  const isAllowed = ALLOWED_ENDPOINTS.some(allowed =>
    normalizedEndpoint === allowed || normalizedEndpoint.startsWith(allowed + '/')
  );

  if (!isAllowed) {
    return NextResponse.json(
      { error: 'Endpoint not allowed', source: 'proxy' },
      { status: 403 }
    );
  }

  // Security: Prevent path traversal
  if (normalizedEndpoint.includes('..') || normalizedEndpoint.includes('\\')) {
    return NextResponse.json(
      { error: 'Invalid endpoint', source: 'proxy' },
      { status: 400 }
    );
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

    const backendUrl = `${BACKEND_URL}/${normalizedEndpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Forwarded-For': request.headers.get('x-forwarded-for') || 'unknown',
      'X-Request-ID': crypto.randomUUID(),
    };

    // Forward authorization header if present
    const authHeader = request.headers.get('authorization');
    if (authHeader) {
      headers['Authorization'] = authHeader;
    }

    const fetchOptions: RequestInit = {
      method: request.method,
      headers,
      signal: controller.signal,
    };

    // Forward request body for POST/PUT/PATCH
    if (['POST', 'PUT', 'PATCH'].includes(request.method)) {
      try {
        const body = await request.json();
        fetchOptions.body = JSON.stringify(body);
      } catch {
        // No valid JSON body — proceed without
      }
    }

    const backendResponse = await fetch(backendUrl, fetchOptions);
    clearTimeout(timeoutId);

    const data = await backendResponse.json();

    return NextResponse.json(
      { ...data, source: 'python_backend' },
      {
        status: backendResponse.status,
        headers: {
          'X-Proxy-Version': 'v35.0',
          'X-Request-ID': headers['X-Request-ID'],
          'Cache-Control': 'no-store',
        },
      }
    );
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    const isTimeout = errorMessage.includes('abort') || errorMessage.includes('timeout');

    return NextResponse.json(
      {
        error: isTimeout ? 'Backend timeout' : 'Backend unreachable',
        source: 'proxy',
        details: process.env.NODE_ENV === 'development' ? errorMessage : undefined,
      },
      { status: isTimeout ? 504 : 503 }
    );
  }
}

export async function GET(request: NextRequest) {
  return proxyRequest(request);
}

export async function POST(request: NextRequest) {
  return proxyRequest(request);
}

export async function PUT(request: NextRequest) {
  return proxyRequest(request);
}

export async function PATCH(request: NextRequest) {
  return proxyRequest(request);
}
