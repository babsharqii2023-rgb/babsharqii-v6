import { NextRequest, NextResponse } from 'next/server';
const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await fetch(`${BACKEND_URL}/api/evolution/create-tool`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body), signal: AbortSignal.timeout(60000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({
        chat: { text: `تم إنشاء الأداة "${body.name || ''}" بنجاح` },
        screen: { component: 'ToolCreatorPanel', props: data, animation: 'zoomIn' },
        brain: { activeBrain: 'symbolic', deliberationState: 'responding' },
        sound: { event: 'operation.complete' },
      });
    }
  } catch {}
  return NextResponse.json({
    chat: { text: 'إنشاء الأداة قيد الانتظار' },
    screen: { component: 'ToolCreatorPanel', props: { _isOffline: true }, animation: 'zoomIn' },
    brain: { activeBrain: 'symbolic', deliberationState: 'idle' },
  });
}
