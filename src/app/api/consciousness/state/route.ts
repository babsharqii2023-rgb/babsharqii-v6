/**
 * BABSHARQII v42.0 — Consciousness State API Route
 * مسار API لحالة الوعي
 * Backend endpoint: GET /api/consciousness/state
 */

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

const STATE_FALLBACK = {
  level: 0.7,
  self_awareness: 0.65,
  metacognition: 0.72,
  coherence: 0.68,
  state: 'aware',
  stage: 'perceive',
  current_phase: 'perceive',
  overall_accuracy: 0.7,
  cycle_count: 0,
  timestamp: new Date().toISOString(),
  fallback: true,
};

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/consciousness/state`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data, {
        headers: { 'X-Data-Source': 'backend' },
      });
    }
  } catch {
    // Backend unavailable
  }
  return NextResponse.json(STATE_FALLBACK, {
    headers: { 'X-Data-Source': 'fallback' },
  });
}
