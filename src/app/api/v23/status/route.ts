import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v23/status`, { signal: AbortSignal.timeout(5000) });
    if (res.ok) return NextResponse.json(await res.json());
  } catch {}
  return NextResponse.json({ neural_bus: true, executor: true, self_heal: true, source: 'fallback' });
}
