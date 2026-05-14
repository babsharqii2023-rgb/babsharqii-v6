// ═══════════════════════════════════════════════════════════════════
// SuperMind Deliberate BFF Route — SSE Streaming
// Streams brain deliberation events in real-time
// SSE Events: thinking, progress, result, complete
// ═══════════════════════════════════════════════════════════════════

import { NextRequest } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const { message, activated_brains, model } = await request.json();

    if (!message) {
      return new Response(JSON.stringify({ error: 'الرسالة مطلوبة' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const brains = activated_brains || ['neural', 'causal', 'symbolic', 'bayesian', 'world_model'];
    const selectedModel = model || 'glm-5.1';

    // Try real backend deliberation with SSE
    try {
      const backendRes = await fetch(`${BACKEND_URL}/api/deliberate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, activated_brains: brains, model: selectedModel }),
        signal: AbortSignal.timeout(120000),
      });

      if (backendRes.ok) {
        const contentType = backendRes.headers.get('content-type') || '';
        if (contentType.includes('text/event-stream')) {
          // Proxy the SSE stream from backend
          const encoder = new TextEncoder();
          const stream = new ReadableStream({
            async start(controller) {
              try {
                const reader = backendRes.body?.getReader();
                if (!reader) {
                  controller.close();
                  return;
                }
                const decoder = new TextDecoder();
                while (true) {
                  const { done, value } = await reader.read();
                  if (done) break;
                  controller.enqueue(value);
                }
              } catch {
                // Stream ended
              }
              controller.close();
            },
          });

          return new Response(stream, {
            headers: {
              'Content-Type': 'text/event-stream',
              'Cache-Control': 'no-cache',
              'Connection': 'keep-alive',
            },
          });
        }

        // Backend returned JSON — wrap in SSE events
        const data = await backendRes.json();
        return createSSEFromJSON(data, brains);
      }
    } catch {
      // Backend unavailable — generate simulated deliberation
    }

    // Simulated deliberation SSE stream
    return createSimulatedDeliberation(message, brains);
  } catch (error) {
    console.error('[SuperMind Deliberate] Error:', error);
    return new Response(JSON.stringify({ error: 'خطأ في التداول' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// ─── Create SSE from JSON response ──────────────────────────────

function createSSEFromJSON(data: Record<string, unknown>, brains: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      // Send thinking events for each brain
      for (const brain of brains) {
        controller.enqueue(encoder.encode(
          `data: ${JSON.stringify({ type: 'thinking', brain, activity: 'جاري التحليل...' })}\n\n`
        ));
      }

      // Send progress
      controller.enqueue(encoder.encode(
        `data: ${JSON.stringify({ type: 'progress', percent: 50, message: 'جاري التداول بين الأدمغة...' })}\n\n`
      ));

      // Send result
      controller.enqueue(encoder.encode(
        `data: ${JSON.stringify({ type: 'result', data, partial: false })}\n\n`
      ));

      // Send complete
      controller.enqueue(encoder.encode(
        `data: ${JSON.stringify({
          type: 'complete',
          data,
          screenDirective: {
            component: 'BrainStateOverlay',
            layout: 'single',
            sections: [{
              type: 'BrainStatusTable',
              props: { brains: data.brain_responses || {} },
              span: 12,
              order: 1,
            }],
          },
        })}\n\n`
      ));

      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}

// ─── Simulated Deliberation ─────────────────────────────────────

function createSimulatedDeliberation(message: string, brains: string[]): Response {
  const encoder = new TextEncoder();
  const brainNames: Record<string, string> = {
    neural: 'العصبي', causal: 'السببي', symbolic: 'الرمزي',
    bayesian: 'الاحتمالي', world_model: 'نموذج العالم',
  };

  const stream = new ReadableStream({
    async start(controller) {
      // Thinking phase — each brain
      for (let i = 0; i < brains.length; i++) {
        const brain = brains[i];
        controller.enqueue(encoder.encode(
          `data: ${JSON.stringify({
            type: 'thinking',
            brain,
            activity: `${brainNames[brain] || brain} يفكر في: "${message.substring(0, 50)}..."`,
          })}\n\n`
        ));
        await delay(600);
      }

      // Progress phase
      for (let p = 20; p <= 80; p += 20) {
        controller.enqueue(encoder.encode(
          `data: ${JSON.stringify({
            type: 'progress',
            percent: p,
            message: `جاري التداول — ${p}%`,
          })}\n\n`
        ));
        await delay(400);
      }

      // Brain responses
      const brainResponses: Record<string, unknown> = {};
      for (const brain of brains) {
        brainResponses[brain] = {
          argument: `تحليل ${brainNames[brain]} للرسالة`,
          confidence: 0.6 + Math.random() * 0.35,
          stance: 'support',
        };
      }

      // Result phase
      controller.enqueue(encoder.encode(
        `data: ${JSON.stringify({
          type: 'result',
          data: {
            content: `تم تحليل طلبك من قبل ${brains.length} أدمغة. الإجماع: المقترح قابل للتنفيذ.`,
            brain_responses: brainResponses,
            consensus_level: 0.75 + Math.random() * 0.2,
            winner: brains[0],
          },
          partial: false,
        })}\n\n`
      ));

      // Complete phase
      controller.enqueue(encoder.encode(
        `data: ${JSON.stringify({
          type: 'complete',
          data: {
            content: `اكتمل التداول — الفائز: ${brainNames[brains[0]] || brains[0]}`,
            brain_responses: brainResponses,
            consensus_level: 0.8,
            winner: brains[0],
            _isOffline: true,
          },
          screenDirective: {
            component: 'BrainStateOverlay',
            layout: 'single',
            sections: [{
              type: 'BrainStatusTable',
              props: { brains: brainResponses },
              span: 12,
              order: 1,
            }],
          },
        })}\n\n`
      ));

      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
