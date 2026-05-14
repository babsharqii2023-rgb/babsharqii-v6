import { createProxyHandler, getAuthHeaders } from '@/lib/backend-proxy';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ flagName: string }> }
) {
  const { flagName } = await params;
  const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';
  const url = `${BACKEND_URL}/api/v2/feature-flags/${flagName}`;
  
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(15000),
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 });
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ flagName: string }> }
) {
  const { flagName } = await params;
  const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';
  const url = `${BACKEND_URL}/api/v2/feature-flags/${flagName}`;
  
  try {
    const body = await request.json();
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders(request) },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(15000),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 });
  }
}
