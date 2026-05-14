import { NextResponse } from 'next/server';

// Capability Router API — Tries real backend first, falls back to simulated data
const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

// Fallback routing statistics
const fallbackStats: Record<string, { count: number; avgConfidence: number; system1: number; system2: number }> = {
  programming: { count: 47, avgConfidence: 0.89, system1: 35, system2: 12 },
  content: { count: 32, avgConfidence: 0.82, system1: 28, system2: 4 },
  business: { count: 25, avgConfidence: 0.75, system1: 10, system2: 15 },
  site_control: { count: 18, avgConfidence: 0.85, system1: 14, system2: 4 },
  tools: { count: 12, avgConfidence: 0.91, system1: 10, system2: 2 },
  self_reflection: { count: 8, avgConfidence: 0.95, system1: 8, system2: 0 },
  general: { count: 5, avgConfidence: 0.40, system1: 0, system2: 5 },
};

export async function GET() {
  // Try real backend first
  try {
    const res = await fetch(`${BACKEND_URL}/api/kernel/capabilities`, {
      signal: AbortSignal.timeout(3000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch {
    // Backend not available — use fallback
  }

  // Fallback: simulated data
  const totalRouted = Object.values(fallbackStats).reduce((a, b) => a + b.count, 0);
  const totalS1 = Object.values(fallbackStats).reduce((a, b) => a + b.system1, 0);
  const totalS2 = Object.values(fallbackStats).reduce((a, b) => a + b.system2, 0);

  return NextResponse.json({
    stats: fallbackStats,
    summary: {
      totalRouted,
      totalSystem1: totalS1,
      totalSystem2: totalS2,
      domainCount: Object.keys(fallbackStats).length,
      lastUpdated: Date.now(),
    },
    source: 'fallback',
  });
}
