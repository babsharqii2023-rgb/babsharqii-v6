import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/kernel/workspace`, {
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) return NextResponse.json(await res.json());
  } catch {}

  return NextResponse.json({
    current: { winning_brain: 'neural', confidence: 0.7 },
    source: 'fallback',
  });
}
