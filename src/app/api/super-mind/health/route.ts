// ═══════════════════════════════════════════════════════════════════
// SuperMind Health Dashboard BFF Route
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const res = await fetch(`${BACKEND_URL}/api/health-monitor`, {
      signal: AbortSignal.timeout(8000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({ ...data, source: 'backend' });
    }
  } catch { /* unavailable */ }

  const health: Record<string, any> = {
    timestamp: new Date().toISOString(),
    overall: 'degraded',
    components: {} as Record<string, any>,
  };

  const checks = [
    { name: 'api', url: `${BACKEND_URL}/health` },
    { name: 'brains', url: `${BACKEND_URL}/api/brains` },
    { name: 'kernel', url: `${BACKEND_URL}/api/kernel/status` },
    { name: 'living', url: `${BACKEND_URL}/api/living/vitals` },
  ];

  for (const check of checks) {
    try {
      const res = await fetch(check.url, { signal: AbortSignal.timeout(5000) });
      health.components[check.name] = { status: res.ok ? 'healthy' : 'unhealthy', statusCode: res.status };
    } catch {
      health.components[check.name] = { status: 'unreachable' };
    }
  }

  const allHealthy = Object.values(health.components).every((c: any) => c.status === 'healthy');
  health.overall = allHealthy ? 'healthy' : 'degraded';

  return NextResponse.json(health);
}
