import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders } from '@/lib/backend-proxy';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${BACKEND_URL}/api/update/improve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders(req) },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(120000), // 2 min timeout for improvement pipeline
    });
    if (res.ok) return NextResponse.json(await res.json());
    const err = await res.text();
    return NextResponse.json({ error: 'Backend error', detail: err }, { status: res.status });
  } catch (e: any) {
    return NextResponse.json({ error: 'Backend unavailable', detail: e.message }, { status: 503 });
  }
}
