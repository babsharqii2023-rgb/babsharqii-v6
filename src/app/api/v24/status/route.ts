import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v24/status`, { signal: AbortSignal.timeout(5000) });
    if (res.ok) return NextResponse.json(await res.json());
  } catch {}
  return NextResponse.json({
    self_modifier: { enabled: true }, inner_monologue: { enabled: true },
    behavioral_memory: { enabled: true }, world_monitor: { enabled: true },
    idea_generator: { enabled: true }, source: 'fallback',
  });
}
