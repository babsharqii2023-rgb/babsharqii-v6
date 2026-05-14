import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v25/status`, { signal: AbortSignal.timeout(5000) });
    if (res.ok) return NextResponse.json(await res.json());
  } catch {}
  return NextResponse.json({ neural_network: true, knowledge_transfer: true, long_term_planning: true, causal_model: true, source: 'fallback' });
}
