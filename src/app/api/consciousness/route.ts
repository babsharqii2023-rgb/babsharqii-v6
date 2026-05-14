/**
 * BABSHARQII v42.0 — Consciousness API Route
 * مسار API للوعي — إدراك→توقع→مفاجأة→تعلم→فعل
 * Backend endpoint: GET/POST /api/consciousness (dashboard_bridge)
 */

import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders } from '@/lib/backend-proxy';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

const CONSCIOUSNESS_FALLBACK = {
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
    const res = await fetch(`${BACKEND_URL}/api/consciousness`, {
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
    // Backend unavailable — return fallback
  }
  return NextResponse.json(CONSCIOUSNESS_FALLBACK, {
    headers: { 'X-Data-Source': 'fallback' },
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await fetch(`${BACKEND_URL}/api/consciousness`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', ...getAuthHeaders(request) },
      body: JSON.stringify(body),
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
  return NextResponse.json(
    { error: 'Backend unavailable', ...CONSCIOUSNESS_FALLBACK },
    { status: 503, headers: { 'X-Data-Source': 'fallback' } }
  );
}
