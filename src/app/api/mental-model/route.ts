/**
 * BABSHARQII v19.0 — Mental Model API Route
 * مسار API للنموذج العقلي
 * Backend endpoint: POST /api/agi/theory-of-mind/model, POST /api/agi/theory-of-mind/predict
 */

import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders } from '@/lib/backend-proxy';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    // Use /api/agi/theory-of-mind/model with default agent_id to get status
    const res = await fetch(`${BACKEND_URL}/api/agi/theory-of-mind/model`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: 'user' }),
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
    return NextResponse.json({ error: 'Backend unavailable', fallback: true }, { status: 503 });
  } catch (error) {
    return NextResponse.json({ error: 'Backend unavailable', fallback: true }, { status: 503 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    // Use /api/agi/theory-of-mind/predict to update/predict actions
    const res = await fetch(`${BACKEND_URL}/api/agi/theory-of-mind/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders(request) },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 });
  } catch (error) {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 });
  }
}
