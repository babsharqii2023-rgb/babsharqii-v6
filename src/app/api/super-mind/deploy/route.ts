import { NextRequest, NextResponse } from 'next/server';
const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await fetch(`${BACKEND_URL}/api/external/deploy`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body), signal: AbortSignal.timeout(120000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({
        chat: { text: 'تم النشر بنجاح' },
        screen: { component: 'DeployPanel', props: data, animation: 'expandDown' },
        brain: { activeBrain: 'world_model', deliberationState: 'responding' },
        sound: { event: 'operation.complete' },
      });
    }
  } catch {}
  return NextResponse.json({
    chat: { text: 'النشر قيد الانتظار — الخادم غير متاح' },
    screen: { component: 'DeployPanel', props: { _isOffline: true }, animation: 'expandDown' },
    brain: { activeBrain: 'world_model', deliberationState: 'idle' },
  });
}
