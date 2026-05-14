import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    // Forward auth headers
    const authHeader = request.headers.get('authorization');
    if (authHeader) {
      headers['Authorization'] = authHeader;
    } else {
      const sessionCookie = request.cookies.get('mamoun_auth_token')?.value
        || request.cookies.get('babsharqii_session')?.value;
      if (sessionCookie) {
        headers['Authorization'] = `Bearer ${sessionCookie}`;
      }
    }

    const res = await fetch(`${BACKEND_URL}/api/update/pull`, {
      method: 'POST',
      headers,
      signal: AbortSignal.timeout(30000),
    });
    if (res.ok) return NextResponse.json(await res.json());
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 });
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 });
  }
}
