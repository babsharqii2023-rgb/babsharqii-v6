// ═══════════════════════════════════════════════════════════════════
// SuperMind Intent Classification Route
// Classifies user messages into intents using SuperMindRouter
// Falls back to LLM-assisted classification for ambiguous messages
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';
import { routeIntent, type SuperMindRoute } from '@/lib/super-mind-router';

export async function POST(request: NextRequest) {
  try {
    const { message, context } = await request.json();

    if (!message) {
      return NextResponse.json({ error: 'الرسالة مطلوبة' }, { status: 400 });
    }

    // Use SuperMindRouter for keyword-based classification
    const route: SuperMindRoute = routeIntent(message);

    // If confidence is low, try LLM-assisted classification via backend
    if (route.confidence < 0.6) {
      try {
        const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';
        const llmResponse = await fetch(`${BACKEND_URL}/api/supermind/classify-intent`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, context }),
          signal: AbortSignal.timeout(10000),
        });
        if (llmResponse.ok) {
          const llmResult = await llmResponse.json();
          if (llmResult.confidence > route.confidence) {
            return NextResponse.json({
              ...llmResult,
              classification_method: 'llm-assisted',
            });
          }
        }
      } catch {
        // Backend unavailable, use keyword result
      }
    }

    return NextResponse.json({
      intent: route.intent,
      screenComponent: route.screenComponent,
      apiEndpoint: route.apiEndpoint,
      animation: route.animation,
      soundEvent: route.soundEvent,
      activatedBrains: route.activatedBrains,
      confidence: route.confidence,
      labelAr: route.labelAr,
      labelEn: route.labelEn,
      classification_method: 'keyword',
    });
  } catch (error) {
    console.error('[SuperMind Intent] Error:', error);
    return NextResponse.json({ error: 'خطأ في تصنيف النية' }, { status: 500 });
  }
}
