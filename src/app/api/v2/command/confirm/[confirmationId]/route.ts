import { createProxyHandler, getAuthHeaders } from '@/lib/backend-proxy';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ confirmationId: string }> }
) {
  const { confirmationId } = await params;
  const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';
  const url = `${BACKEND_URL}/api/v2/command/confirm/${confirmationId}`;
  
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
