'use client';

import { useState, useCallback, useRef } from 'react';
import { parseSSEStream, sendChatDedicatedSSE, sendChatSSEViaProxy } from '@/lib/api';

// ─── SSE Stream Hook ──────────────────────────────────────────
// Connects to the SSE streaming chat endpoint
// Fallback chain: dedicated SSE endpoint → /api/chat SSE → regular POST
// CRITICAL FIX: streamedContent now properly accumulates from SSE chunks
// CRITICAL FIX: properly handles z-ai SDK returning ReadableStream (not async iterable)

interface SSEStreamState {
  isStreaming: boolean;
  error: string | null;
  streamedContent: string;
  metadata: Record<string, unknown> | null;
}

interface UseSSEStreamReturn extends SSEStreamState {
  send: (message: string, history?: Array<{ role: string; content: string }>) => Promise<string | null>;
  reset: () => void;
}

export function useSSEStream(): UseSSEStreamReturn {
  const [state, setState] = useState<SSEStreamState>({
    isStreaming: false,
    error: null,
    streamedContent: '',
    metadata: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  /**
   * Process an SSE Response and accumulate tokens
   * Returns the full content string, or null on error
   */
  const processSSEResponse = useCallback(async (
    response: Response,
    controller: AbortController
  ): Promise<{ content: string; meta: Record<string, unknown> | null }> => {
    let fullContent = '';
    let meta: Record<string, unknown> | null = null;

    for await (const event of parseSSEStream(response)) {
      if (controller.signal.aborted) break;

      try {
        const parsed = JSON.parse(event.data);

        if (parsed.type === 'token' || parsed.type === 'content') {
          const chunk = parsed.content || parsed.token || '';
          fullContent += chunk;
          setState(prev => ({
            ...prev,
            streamedContent: fullContent,
          }));
        } else if (parsed.type === 'metadata') {
          meta = parsed;
          setState(prev => ({
            ...prev,
            metadata: meta,
          }));
        } else if (parsed.type === 'done') {
          meta = parsed;
          setState(prev => ({
            ...prev,
            metadata: meta,
            isStreaming: false,
          }));
        } else if (parsed.type === 'error') {
          setState(prev => ({
            ...prev,
            error: parsed.message || 'Stream error',
            isStreaming: false,
          }));
          throw new Error(parsed.message || 'Stream error');
        } else if (parsed.content && !parsed.type) {
          // Some backends just send content directly
          fullContent += parsed.content;
          setState(prev => ({
            ...prev,
            streamedContent: fullContent,
          }));
        }
      } catch (parseError) {
        // If data isn't JSON, treat as raw text token
        if (parseError instanceof SyntaxError) {
          if (event.data && event.data !== '[DONE]') {
            fullContent += event.data;
            setState(prev => ({
              ...prev,
              streamedContent: fullContent,
            }));
          } else if (event.data === '[DONE]') {
            setState(prev => ({
              ...prev,
              isStreaming: false,
            }));
          }
        } else {
          // Re-throw non-parse errors (like our own error type throws)
          throw parseError;
        }
      }
    }

    return { content: fullContent, meta };
  }, []);

  const send = useCallback(async (
    message: string,
    history?: Array<{ role: string; content: string }>
  ): Promise<string | null> => {
    // Cancel any existing stream
    if (abortRef.current) {
      abortRef.current.abort();
    }

    const controller = new AbortController();
    abortRef.current = controller;

    // Reset state for new stream
    setState({
      isStreaming: true,
      error: null,
      streamedContent: '',
      metadata: null,
    });

    try {
      // ─── 1. Try dedicated SSE endpoint first (always streams) ───
      try {
        const response = await sendChatDedicatedSSE({ message, history });
        const result = await processSSEResponse(response, controller);

        // Mark stream complete if not already done
        setState(prev => ({
          ...prev,
          isStreaming: false,
        }));

        return result.content;
      } catch (dedicatedSSEError) {
        console.warn('[SSE] Dedicated endpoint failed, trying /api/chat SSE:', dedicatedSSEError);
        // Reset streaming state for retry
        setState(prev => ({
          ...prev,
          streamedContent: '',
          isStreaming: true,
        }));
      }

      // ─── 2. Try /api/chat with stream:true ───
      try {
        const response = await sendChatSSEViaProxy({ message, history });
        const result = await processSSEResponse(response, controller);

        setState(prev => ({
          ...prev,
          isStreaming: false,
        }));

        return result.content;
      } catch (chatSSEError) {
        console.warn('[SSE] /api/chat SSE failed, trying regular POST:', chatSSEError);
        setState(prev => ({
          ...prev,
          streamedContent: '',
          isStreaming: true,
        }));
      }

      // ─── 3. Fallback: regular POST (no streaming) ───
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, history }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();

        // Wrap the JSON response as if it were a streamed response
        const content = data.content || data.response || '';
        const meta: Record<string, unknown> = {
          brain: data.brain || 'neural',
          confidence: data.confidence || 0.85,
          latency: data.latency || 0,
          source: data.source || 'fallback',
        };

        setState({
          isStreaming: false,
          error: null,
          streamedContent: content,
          metadata: meta,
        });

        return content;
      } catch (postError) {
        console.error('[SSE] All methods failed:', postError);
        if (controller.signal.aborted) return null;

        setState(prev => ({
          ...prev,
          isStreaming: false,
          error: postError instanceof Error ? postError.message : 'فشل الاتصال بجميع الخدمات',
        }));
        return null;
      }
    } catch (err) {
      if (controller.signal.aborted) return null;
      setState(prev => ({
        ...prev,
        isStreaming: false,
        error: err instanceof Error ? err.message : 'Connection failed',
      }));
      return null;
    }
  }, [processSSEResponse]);

  const reset = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    setState({
      isStreaming: false,
      error: null,
      streamedContent: '',
      metadata: null,
    });
  }, []);

  return { ...state, send, reset };
}
