import { NextRequest, NextResponse } from 'next/server';
const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v23/healing`, { signal: AbortSignal.timeout(10000) });
    if (res.ok) return NextResponse.json(await res.json());
  } catch {}
  return NextResponse.json({ status: 'unknown', healing_count: 0, _isOffline: true });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await fetch(`${BACKEND_URL}/api/v23/healing`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body), signal: AbortSignal.timeout(30000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({
        chat: { text: 'تم تنفيذ الإصلاح الذاتي بنجاح' },
        screen: { component: 'HealingPanel', props: data, animation: 'pulseIn' },
        brain: { activeBrain: 'neural', deliberationState: 'responding' },
      });
    }
  } catch {}
  return NextResponse.json({
    chat: { text: 'الإصلاح الذاتي قيد الانتظار — الخادم غير متاح' },
    screen: { component: 'HealingPanel', props: { _isOffline: true }, animation: 'pulseIn' },
    brain: { activeBrain: 'neural', deliberationState: 'idle' },
  });
}
