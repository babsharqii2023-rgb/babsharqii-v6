import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const resp = await fetch(`${BACKEND_URL}/api/mamoun/instincts`, {
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (resp.ok) {
      const data = await resp.json();
      return NextResponse.json({ source: 'python_backend', ...data });
    }
  } catch {
    // Backend unreachable
  }
  return NextResponse.json({
    source: 'frontend_fallback',
    instincts: [
      { id: 'survival', name: 'Survival', level: 30, active: false },
      { id: 'curiosity', name: 'Curiosity', level: 65, active: true },
      { id: 'consistency', name: 'Consistency', level: 50, active: false },
      { id: 'efficiency', name: 'Efficiency', level: 45, active: false },
    ],
  });
}
