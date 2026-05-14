// ═══════════════════════════════════════════════════════════════════
// مأمون v22.0 — Temporal Awareness API (Real Backend Proxy)
// Proxies to FastAPI backend at /api/temporal/*
// ═══════════════════════════════════════════════════════════════════

import { NextResponse } from 'next/server';

const BACKEND = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const [statusRes, timelineRes] = await Promise.allSettled([
      fetch(`${BACKEND}/api/temporal/status`, { signal: AbortSignal.timeout(5000) }),
      fetch(`${BACKEND}/api/temporal/timeline?limit=20`, { signal: AbortSignal.timeout(5000) }),
    ]);

    const status = statusRes.status === 'fulfilled' && statusRes.value.ok
      ? await statusRes.value.json()
      : null;
    const timeline = timelineRes.status === 'fulfilled' && timelineRes.value.ok
      ? await timelineRes.value.json()
      : null;

    if (status || timeline) {
      return NextResponse.json({
        timeline: timeline?.events || [],
        weekly_patterns: status?.weekly_patterns || [],
        absence_status: status?.absence || { absent: false, days: 0, message: '', severity: 'low' },
        proactive_suggestions: status?.proactive_suggestions || [],
        status_info: status?.status || {},
      });
    }

    throw new Error('Backend unavailable');
  } catch {
    // Fallback: minimal temporal data
    return NextResponse.json({
      timeline: [],
      weekly_patterns: [],
      absence_status: { absent: false, days: 0, message: '', severity: 'low' },
      proactive_suggestions: [],
      fallback: true,
    });
  }
}
