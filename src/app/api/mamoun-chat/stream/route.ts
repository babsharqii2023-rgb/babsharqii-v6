import { NextRequest } from 'next/server';
import ZAI from 'z-ai-web-dev-sdk';
import { chatGovernor } from '@/lib/chat-governor';
import { BRAIN_PERSONAS } from '@/lib/brains';
import { calculateFallbackConfidence } from '@/lib/chat-confidence';
import type { ChatMessage } from '@/lib/store';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

const MODEL_MAP: Record<string, string> = {
  'glm-5.1': 'glm-5.1',
  'glm-4-plus': 'glm-4-plus',
  'glm-4': 'glm-4',
  'gemini-3.1-pro': 'gemini-3.1-pro',
  'deepseek-chat': 'deepseek-chat',
  'deepseek-reasoner': 'deepseek-reasoner',
};

async function* parseOpenAIStream(readableStream: ReadableStream<Uint8Array>): AsyncGenerator<string> {
  const reader = readableStream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n');
      buffer = parts.pop() || '';
      for (const part of parts) {
        const trimmed = part.trim();
        if (trimmed.startsWith('data: ')) {
          const data = trimmed.slice(6).trim();
          if (data === '[DONE]') return;
          try {
            const parsed = JSON.parse(data);
            const content = parsed?.choices?.[0]?.delta?.content;
            if (content) yield content;
          } catch { /* skip */ }
        }
      }
    }
    if (buffer.trim().startsWith('data: ')) {
      const data = buffer.trim().slice(6).trim();
      if (data !== '[DONE]') {
        try {
          const parsed = JSON.parse(data);
          const content = parsed?.choices?.[0]?.delta?.content;
          if (content) yield content;
        } catch { /* skip */ }
      }
    }
  } finally { reader.releaseLock(); }
}

function sseResponse(stream: ReadableStream): Response {
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { message, model, history = [] } = body;

    if (!message || typeof message !== 'string') {
      const errorStream = new ReadableStream({
        start(controller) {
          const encoder = new TextEncoder();
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'error', message: 'الرسالة مطلوبة' })}\n\n`));
          controller.close();
        },
      });
      return sseResponse(errorStream);
    }

    // ═══ ChatGovernor: التحليل المركزي ═══════════════════════
    const decision = chatGovernor.analyze(message, history);

    // ─── حقن مكتشف ────────────────────────────────────────
    if (decision.injectionScore >= 0.5) {
      const errorStream = new ReadableStream({
        start(controller) {
          const encoder = new TextEncoder();
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'error', message: 'تم اكتشاف محاولة حقن أوامر.', brain: 'safety' })}\n\n`));
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'done', brain: 'safety', confidence: 0.1 })}\n\n`));
          controller.close();
        },
      });
      return sseResponse(errorStream);
    }

    // ─── أوامر التحكم المباشر ──────────────────────────────
    if (decision.action === 'mode_change' && decision.parsedCommand.immediateResponse) {
      const cmdStream = new ReadableStream({
        start(controller) {
          const encoder = new TextEncoder();
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'token', content: decision.parsedCommand.immediateResponse, brain: 'governor', mode: decision.currentMode.id })}\n\n`));
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'done', brain: 'governor', confidence: 1.0, current_mode: decision.currentMode })}\n\n`));
          controller.close();
        },
      });
      return sseResponse(cmdStream);
    }

    const primaryBrain = decision.routing.primaryBrain;
    const brainPersona = BRAIN_PERSONAS.find(b => b.id === primaryBrain) || BRAIN_PERSONAS[0];
    const startTime = Date.now();
    const fullSystemPrompt = chatGovernor.buildFullSystemPrompt(decision);
    const selectedModel = MODEL_MAP[model] || brainPersona.model || 'glm-4-plus';

    // Context from governor
    const contextMessages = decision.smartContext.messages.map(m => ({
      role: (m.role === 'user' ? 'user' : 'assistant') as 'user' | 'assistant',
      content: m.content.substring(0, 4000),
    }));

    const messages = [
      { role: 'system' as const, content: fullSystemPrompt },
      ...contextMessages,
      { role: 'user' as const, content: decision.sanitizedMessage },
    ];

    // ─── 1. Try FastAPI backend SSE ───────────────────────
    try {
      const backendResponse = await fetch(`${BACKEND_URL}/api/kernel/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
        body: JSON.stringify({
          message: decision.sanitizedMessage, history, model: model || 'auto', stream: true,
          mode: decision.currentMode.id, active_brains: decision.activatedBrains,
        }),
        signal: AbortSignal.timeout(60000),
      });
      if (backendResponse.ok && backendResponse.body) {
        const proxiedStream = new ReadableStream({
          async start(controller) {
            const reader = backendResponse.body!.getReader();
            const decoder = new TextDecoder();
            const encoder = new TextEncoder();
            try {
              while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                controller.enqueue(encoder.encode(decoder.decode(value, { stream: true })));
              }
            } catch { /* stream ended */ }
            finally { controller.close(); }
          },
        });
        return sseResponse(proxiedStream);
      }
    } catch { /* Backend unavailable */ }

    // ─── 2. Stream from z-ai SDK ─────────────────────────
    try {
      const zai = await ZAI.create();
      const streamResult = await zai.chat.completions.create({
        model: selectedModel, messages, stream: true,
        temperature: decision.suggestedTemperature,
      });

      const readableStream = streamResult as ReadableStream<Uint8Array>;
      const tokenGenerator = parseOpenAIStream(readableStream);

      let closed = false;
      const sseStream = new ReadableStream({
        async start(controller) {
          const encoder = new TextEncoder();
          let fullContent = '';

          const safeEnqueue = (data: Uint8Array) => {
            if (!closed) { try { controller.enqueue(data); } catch { closed = true; } }
          };
          const safeClose = () => {
            if (!closed) { try { controller.close(); } catch { /* */ } closed = true; }
          };

          try {
            for await (const token of tokenGenerator) {
              if (closed) break;
              fullContent += token;
              safeEnqueue(encoder.encode(`data: ${JSON.stringify({
                type: 'token', content: token, brain: primaryBrain,
                mode: decision.currentMode.id,
              })}\n\n`));
            }
            const confidence = calculateFallbackConfidence(fullContent, 1, Date.now() - startTime, decision.suggestedTemperature);
            const latency = Date.now() - startTime;
            safeEnqueue(encoder.encode(`data: ${JSON.stringify({
              type: 'done', brain: primaryBrain, confidence, latency,
              brainContributions: decision.routing.contributions,
              brainPersona: { nameAr: brainPersona.nameAr, nameEn: brainPersona.nameEn, thinkingStyle: brainPersona.thinkingStyle },
              is_real_deliberation: false,
              current_mode: decision.currentMode,
              feedforward_suggestions: chatGovernor.generateFeedforward(decision, fullContent),
            })}\n\n`));
          } catch {
            safeEnqueue(encoder.encode(`data: ${JSON.stringify({ type: 'error', message: 'Stream interrupted', brain: primaryBrain })}\n\n`));
          } finally { safeClose(); }
        },
        cancel() { closed = true; },
      });

      return sseResponse(sseStream);
    } catch (sdkStreamError) {
      console.error('[Mamoun Stream] z-ai streaming failed:', sdkStreamError);
    }

    // ─── 3. Fallback: non-streaming wrapped as SSE ────────
    try {
      const zai2 = await ZAI.create();
      const selectedModel2 = MODEL_MAP[model] || brainPersona.model || 'glm-4-plus';

      const response = await zai2.chat.completions.create({
        model: selectedModel2, messages, stream: false,
        temperature: decision.suggestedTemperature,
      });

      let assistantContent = response?.choices?.[0]?.message?.content || (typeof response === 'string' ? response : 'عذراً، لم أتمكن من معالجة طلبك.');
      const confidence = calculateFallbackConfidence(assistantContent, 2, Date.now() - startTime, decision.suggestedTemperature);
      const latency = Date.now() - startTime;

      const sseStream = new ReadableStream({
        start(controller) {
          const encoder = new TextEncoder();
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'token', content: assistantContent, brain: primaryBrain, mode: decision.currentMode.id })}\n\n`));
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({
            type: 'done', brain: primaryBrain, confidence, latency,
            brainContributions: decision.routing.contributions,
            brainPersona: { nameAr: brainPersona.nameAr, nameEn: brainPersona.nameEn },
            is_real_deliberation: false,
            current_mode: decision.currentMode,
          })}\n\n`));
          controller.close();
        },
      });

      return sseResponse(sseStream);
    } catch (finalError) {
      console.error('[Mamoun Stream] All methods failed:', finalError);
      const errorStream = new ReadableStream({
        start(controller) {
          const encoder = new TextEncoder();
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'error', message: 'فشل الاتصال. يرجى المحاولة لاحقاً.', brain: primaryBrain })}\n\n`));
          controller.close();
        },
      });
      return sseResponse(errorStream);
    }
  } catch (error: unknown) {
    const errMsg = error instanceof Error ? error.message : 'Unknown error';
    console.error('[Mamoun Stream] Handler error:', errMsg);
    const errorStream = new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder();
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'error', message: 'حدث خطأ داخلي' })}\n\n`));
        controller.close();
      },
    });
    return sseResponse(errorStream);
  }
}
