// ═══════════════════════════════════════════════════════════════════
// مأمون v22.0 — System Events (Real Backend Proxy)
// Proxies to FastAPI backend at /api/events/*
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders } from '@/lib/backend-proxy';

const BACKEND = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const limit = url.searchParams.get('limit') || '50';
    const eventType = url.searchParams.get('event_type') || '';
    const severity = url.searchParams.get('severity') || '';

    let backendUrl = `${BACKEND}/api/events/recent?limit=${limit}`;
    if (eventType) backendUrl += `&event_type=${eventType}`;
    if (severity) backendUrl += `&severity=${severity}`;

    const res = await fetch(backendUrl, { signal: AbortSignal.timeout(5000) });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
    throw new Error(`Backend returned ${res.status}`);
  } catch {
    // Fallback: minimal response
    return NextResponse.json({
      events: [],
      count: 0,
      total: 0,
      fallback: true,
    });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await fetch(`${BACKEND}/api/events/emit`, {
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
    return NextResponse.json({ error: 'Failed to emit event', fallback: true }, { status: 500 });
  }
}
