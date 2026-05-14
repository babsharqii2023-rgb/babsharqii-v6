/**
 * BABSHARQII v40.0 — Swarm Status API Route
 * مسار API لحالة السرب
 * Backend endpoint: GET /api/swarm/status
 */

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/swarm/status`, {
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
  return NextResponse.json(
    { agents: [], active: 0, fallback: true },
    { headers: { 'X-Data-Source': 'fallback' } }
  );
}
