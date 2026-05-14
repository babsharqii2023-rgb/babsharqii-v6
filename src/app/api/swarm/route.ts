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

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action, ...rest } = body;

    const endpointMap: Record<string, string> = {
      form: '/api/swarm/form',
      complete: '/api/swarm/complete',
    };

    const endpoint = endpointMap[action] || '/api/swarm/form';
    const res = await fetch(`${BACKEND_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(request.headers.get('authorization')
          ? { 'Authorization': request.headers.get('authorization')! }
          : {}),
      },
      body: JSON.stringify(rest),
      signal: AbortSignal.timeout(10000),
    });

    if (res.ok) {
      return NextResponse.json(await res.json());
    }
    throw new Error(`Backend returned ${res.status}`);
  } catch {
    return NextResponse.json({ error: 'فشل في عملية السرب', fallback: true }, { status: 500 });
  }
}
