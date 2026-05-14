import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/update/check`, {
      signal: AbortSignal.timeout(15000),
    });
    if (res.ok) return NextResponse.json(await res.json());
    return NextResponse.json({ error: 'Backend unavailable', fallback: true }, { status: 503 });
  } catch {
    return NextResponse.json({ error: 'Backend unavailable', fallback: true }, { status: 503 });
  }
}
