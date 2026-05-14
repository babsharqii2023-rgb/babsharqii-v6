// ═══════════════════════════════════════════════════════════════════
// SuperMind Chat API Route
// Routes messages through the SuperMind system
// Falls back to mamoun-chat if backend is unavailable
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { message, model, intent, activated_brains, context } = body;

    if (!message) {
      return NextResponse.json(
        { error: 'الرسالة مطلوبة' },
        { status: 400 }
      );
    }

    // Try to forward to backend SuperMind endpoint
    try {
      const backendResponse = await fetch(`${BACKEND_URL}/api/supermind/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          model: model || 'glm-5.1',
          intent: intent || 'default',
          activated_brains: activated_brains || ['neural'],
          context: context || {},
        }),
        signal: AbortSignal.timeout(45000),
      });

      if (backendResponse.ok) {
        const data = await backendResponse.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend unavailable, fall through to chat endpoint
    }

    // Fallback: Try the mamoun-chat backend endpoint
    try {
      const chatResponse = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          model: model || 'glm-5.1',
          context: context || {},
        }),
        signal: AbortSignal.timeout(30000),
      });

      if (chatResponse.ok) {
        const data = await chatResponse.json();
        // Wrap in SuperMind format
        return NextResponse.json({
          content: data.content || data.response || '',
          brain: data.brain || data.winning_brain || 'neural',
          confidence: data.confidence || 0.85,
          brain_responses: data.brain_responses || {},
          consensus_level: data.consensus_level || 0.7,
          winning_brain: data.winning_brain || data.brain || 'neural',
          query_type: intent || data.query_type || 'general',
          source: 'supermind-fallback',
          activated_brains: activated_brains || ['neural'],
        });
      }
    } catch {
      // Backend completely unavailable
    }

    // Final fallback: Try the local /api/mamoun-chat
    try {
      const localResponse = await fetch(new URL('/api/mamoun-chat', request.url), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, model: model || 'glm-5.1', context: context || {} }),
      });

      if (localResponse.ok) {
        const data = await localResponse.json();
        return NextResponse.json({
          content: data.content || 'لا يمكنني معالجة طلبك حالياً.',
          brain: data.brain || 'neural',
          confidence: data.confidence || 0.7,
          source: 'local-fallback',
          activated_brains: activated_brains || ['neural'],
        });
      }
    } catch {
      // All fallbacks failed
    }

    return NextResponse.json({
      content: 'عذراً، جميع خدمات المعالجة غير متاحة حالياً. يرجى المحاولة لاحقاً.',
      brain: 'neural',
      confidence: 0.1,
      source: 'offline',
      activated_brains: ['neural'],
    });

  } catch (error) {
    console.error('[SuperMind Chat] Error:', error);
    return NextResponse.json(
      { error: 'حدث خطأ داخلي في معالجة الرسالة' },
      { status: 500 }
    );
  }
}
