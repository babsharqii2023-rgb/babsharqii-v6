// ═══════════════════════════════════════════════════════════════════
// مأمون v22.0 — Predictions API (Real Backend Proxy)
// Proxies to FastAPI backend at /api/predictions/*
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders } from '@/lib/backend-proxy';

const BACKEND = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/api/predictions/status`, {
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({
        predictions: data.recent_predictions || [],
        accuracy: data.status?.overall_accuracy || 0,
        total: data.status?.total_predictions || 0,
        pending: data.status?.active_predictions || 0,
        correct: data.status?.correct_predictions || 0,
        wrong: data.status?.total_verified - data.status?.correct_predictions || 0,
      });
    }
    throw new Error(`Backend returned ${res.status}`);
  } catch {
    // Fallback: empty predictions
    return NextResponse.json({
      predictions: [],
      accuracy: 0,
      total: 0,
      pending: 0,
      correct: 0,
      wrong: 0,
      fallback: true,
    });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await fetch(`${BACKEND}/api/predictions/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders(request) },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      return NextResponse.json(await res.json());
    }
    throw new Error(`Backend returned ${res.status}`);
  } catch {
    return NextResponse.json({ error: 'Failed to create prediction', fallback: true }, { status: 500 });
  }
}
