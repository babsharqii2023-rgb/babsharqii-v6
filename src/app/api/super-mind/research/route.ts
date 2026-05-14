// ═══════════════════════════════════════════════════════════════════
// SuperMind Research BFF Route
// Extended research with SSE streaming for long-running operations
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const { topic, depth, timeout_seconds } = await request.json();

    if (!topic) {
      return NextResponse.json({ error: 'موضوع البحث مطلوب' }, { status: 400 });
    }

    // Start research on backend
    try {
      const res = await fetch(`${BACKEND_URL}/api/research/deep`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: topic,
          depth: depth || 'standard',
          timeout_seconds: timeout_seconds || 60,
        }),
        signal: AbortSignal.timeout(120000),
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json({
          chat: { text: `تم الانتهاء من البحث عن "${topic}". تم العثور على ${data.sources?.length || 0} مصادر.` },
          screen: { component: 'ResearchPanel', props: data, animation: 'slideUp' },
          brain: { activeBrain: 'causal', deliberationState: 'responding' },
          sound: { event: 'operation.complete', brainOscillator: 'causal' },
        });
      }
    } catch { /* fallback */ }

    // Fallback research response
    return NextResponse.json({
      chat: { text: `جاري البحث عن "${topic}"... النتائج ستظهر عند الاتصال بالخادم.` },
      screen: {
        component: 'ResearchPanel',
        props: {
          topic,
          depth: depth || 'standard',
          status: 'pending',
          sources: [],
          summary: 'البحث قيد الانتظار — الخادم غير متاح حالياً',
          _isOffline: true,
        },
        animation: 'slideUp',
      },
      brain: { activeBrain: 'causal', deliberationState: 'thinking' },
    });
  } catch (error) {
    console.error('[SuperMind Research] Error:', error);
    return NextResponse.json({ error: 'خطأ في البحث' }, { status: 500 });
  }
}
