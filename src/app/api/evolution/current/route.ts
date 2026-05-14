import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/evolution/current`, {
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) return NextResponse.json(await res.json());
  } catch {}

  return NextResponse.json({
    version: 'v29.0',
    genome_version: '29.0',
    generation: 1,
    source: 'fallback',
  });
}
