// =============================================================================
// مأمون v18 — API Client with SSE Streaming
// Connects to FastAPI backend at localhost:8000
// Falls back gracefully when backend is unavailable
// =============================================================================

const API_BASE = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export interface HealthResponse {
  status: string;
  organism: string;
  version: string;
  brains: Record<string, { status: string; confidence: number }>;
  kernel_running: boolean;
  workspace_winner: string;
}

export interface BrainStatusResponse {
  brains: Array<{
    id: string;
    name: string;
    status: string;
    confidence: number;
    latency: number;
    model: string;
  }>;
  active_count: number;
  consensus_level: number;
}

export interface ChatRequest {
  message: string;
  history?: Array<{ role: string; content: string }>;
  model?: string;
  context?: Record<string, unknown>;
}

export interface ChatResponse {
  content: string;
  brain: string;
  confidence: number;
  latency: number;
  brain_responses?: Record<string, { response: string; confidence: number; stance: string }>;
  consensus_level?: number;
  cjs?: number;
  conflict_detected?: boolean;
  needs_approval?: boolean;
  query_type?: string;
  source: string;
}

/**
 * GET request to the FastAPI backend
 */
export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) throw new Error(`API Error: ${res.status}`);
  return res.json();
}

/**
 * POST request to the FastAPI backend
 */
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(60000),
  });
  if (!res.ok) throw new Error(`API Error: ${res.status}`);
  return res.json();
}

/**
 * SSE streaming fetch — connects to backend streaming endpoint
 * Returns the raw Response for consumer to read the stream
 */
export async function sseFetch(path: string, body: unknown): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(120000),
  });
  if (!res.ok) throw new Error(`SSE Error: ${res.status}`);
  return res;
}

/**
 * Parse SSE stream from a Response object
 * Yields parsed event data objects
 * Handles both standard SSE format and edge cases
 */
export async function* parseSSEStream(response: Response): AsyncGenerator<{ event?: string; data: string }> {
  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Split by newlines to process SSE lines
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent: string | undefined;
      let currentData = '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          currentData += line.slice(6);
        } else if (line.startsWith('data:')) {
          // Handle "data:" without space
          currentData += line.slice(5);
        } else if (line === '') {
          // Empty line = end of event
          if (currentData) {
            yield { event: currentEvent, data: currentData.trim() };
            currentEvent = undefined;
            currentData = '';
          }
        }
      }
    }

    // Yield any remaining data in buffer
    if (buffer.trim()) {
      const trimmed = buffer.trim();
      if (trimmed.startsWith('data: ')) {
        yield { data: trimmed.slice(6).trim() };
      } else if (trimmed.startsWith('data:')) {
        yield { data: trimmed.slice(5).trim() };
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Check if the backend is available
 */
export async function checkBackendHealth(): Promise<HealthResponse | null> {
  try {
    return await apiGet<HealthResponse>('/health');
  } catch {
    return null;
  }
}

/**
 * Send a chat message via the Next.js proxy (avoids CORS issues)
 * Non-streaming mode — returns JSON
 */
export async function sendChatViaProxy(request: ChatRequest): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error(`Chat proxy error: ${res.status}`);
  return res.json();
}

/**
 * Send a chat message via SSE through the Next.js proxy
 * Returns the raw Response for streaming
 */
export async function sendChatSSEViaProxy(request: ChatRequest): Promise<Response> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify({ ...request, stream: true }),
  });
  if (!res.ok) throw new Error(`Chat SSE proxy error: ${res.status}`);
  return res;
}

/**
 * Send a chat message via the dedicated SSE streaming endpoint
 * This endpoint ALWAYS streams, even when falling back to non-streaming LLM calls
 * Returns the raw Response for streaming
 */
export async function sendChatDedicatedSSE(request: ChatRequest): Promise<Response> {
  const res = await fetch('/api/mamoun-chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify({ ...request, stream: true }),
  });
  // Check if response is actually SSE
  const contentType = res.headers.get('content-type') || '';
  if (!contentType.includes('text/event-stream') && !contentType.includes('text/plain')) {
    // Server returned JSON instead of SSE — this shouldn't happen from the dedicated endpoint
    // but handle it gracefully by creating a synthetic SSE response
    const data = await res.json().catch(() => ({ error: 'Unknown error' }));
    const syntheticBody = new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder();
        if (data.error) {
          const errorEvent = `data: ${JSON.stringify({ type: 'error', message: data.error })}\n\n`;
          controller.enqueue(encoder.encode(errorEvent));
        } else if (data.content) {
          const tokenEvent = `data: ${JSON.stringify({ type: 'token', content: data.content, brain: data.brain || 'neural' })}\n\n`;
          controller.enqueue(encoder.encode(tokenEvent));
          const doneEvent = `data: ${JSON.stringify({ type: 'done', brain: data.brain || 'neural', confidence: data.confidence || 0.85, latency: data.latency || 0 })}\n\n`;
          controller.enqueue(encoder.encode(doneEvent));
        }
        controller.close();
      },
    });
    return new Response(syntheticBody, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  }
  return res;
}
