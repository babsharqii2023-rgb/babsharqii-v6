import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders } from '@/lib/backend-proxy';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const res = await fetch(`${BACKEND_URL}/api/update/rollback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders(request) },
      signal: AbortSignal.timeout(30000),
    });
    if (res.ok) return NextResponse.json(await res.json());
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 });
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 });
  }
}
