// ═══════════════════════════════════════════════════════════════════
// SuperMind Evolution Status BFF Route
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';
const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const res = await fetch(`${BACKEND_URL}/api/evolution/current`, {
      signal: AbortSignal.timeout(8000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({ ...data, source: 'backend' });
    }
  } catch { /* unavailable */ }

  return NextResponse.json({
    status: 'idle',
    currentCycle: null,
    lastCycle: { completedAt: new Date().toISOString(), improvements: 0, status: 'completed' },
    totalCycles: 0,
    totalImprovements: 0,
    source: 'local',
  });
}
