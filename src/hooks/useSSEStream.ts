// ═══════════════════════════════════════════════════════════════════
// useSSEStream — Enhanced SSE Streaming Hook
// Supports reconnection, event typing, and brain deliberation events
// ═══════════════════════════════════════════════════════════════════

'use client';

import { useState, useCallback, useRef } from 'react';
import { parseSSEStream, sendChatDedicatedSSE, sendChatSSEViaProxy } from '@/lib/api';

// ─── SSE Event Types ───────────────────────────────────────────

export interface SSEBrainEvent {
  type: 'brain.thinking' | 'brain.response' | 'brain.consensus' | 'brain.complete';
  brainId?: string;
  brainName?: string;
  content?: string;
  confidence?: number;
  stance?: string;
  consensusLevel?: number;
  winner?: string;
  [key: string]: unknown;
}

export interface SSEStreamState {
  isStreaming: boolean;
  error: string | null;
  streamedContent: string;
  metadata: Record<string, unknown> | null;
  brainEvents: SSEBrainEvent[];
  activeBrains: string[];
}

interface UseSSEStreamReturn extends SSEStreamState {
  send: (message: string, history?: Array<{ role: string; content: string }>) => Promise<string | null>;
  sendToSuperMind: (message: string, intent?: string, history?: Array<{ role: string; content: string }>) => Promise<string | null>;
  reset: () => void;
}

export function useSSEStream(): UseSSEStreamReturn {
  const [state, setState] = useState<SSEStreamState>({
    isStreaming: false,
    error: null,
    streamedContent: '',
    metadata: null,
    brainEvents: [],
    activeBrains: [],
  });
  const abortRef = useRef<AbortController | null>(null);

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

        // Token/Content events
        if (parsed.type === 'token' || parsed.type === 'content') {
          const chunk = parsed.content || parsed.token || '';
          fullContent += chunk;
          setState(prev => ({
            ...prev,
            streamedContent: fullContent,
          }));
        }
        // Brain-specific events
        else if (parsed.type === 'brain.thinking' || parsed.type === 'brain.response' ||
                 parsed.type === 'brain.consensus' || parsed.type === 'brain.complete') {
          setState(prev => ({
            ...prev,
            brainEvents: [...prev.brainEvents, parsed as SSEBrainEvent],
            activeBrains: parsed.brainId
              ? prev.activeBrains.includes(parsed.brainId)
                ? prev.activeBrains
                : [...prev.activeBrains, parsed.brainId]
              : prev.activeBrains,
          }));
        }
        // Metadata events
        else if (parsed.type === 'metadata') {
          meta = parsed;
          setState(prev => ({ ...prev, metadata: meta }));
        }
        // Done event
        else if (parsed.type === 'done') {
          meta = parsed;
          setState(prev => ({
            ...prev,
            metadata: meta,
            isStreaming: false,
          }));
        }
        // Error event
        else if (parsed.type === 'error') {
          setState(prev => ({
            ...prev,
            error: parsed.message || 'Stream error',
            isStreaming: false,
          }));
          throw new Error(parsed.message || 'Stream error');
        }
        // Fallback: raw content
        else if (parsed.content && !parsed.type) {
          fullContent += parsed.content;
          setState(prev => ({ ...prev, streamedContent: fullContent }));
        }
      } catch (parseError) {
        if (parseError instanceof SyntaxError) {
          if (event.data && event.data !== '[DONE]') {
            fullContent += event.data;
            setState(prev => ({ ...prev, streamedContent: fullContent }));
          } else if (event.data === '[DONE]') {
            setState(prev => ({ ...prev, isStreaming: false }));
          }
        } else {
          throw parseError;
        }
      }
    }

    return { content: fullContent, meta };
  }, []);

  // ─── Regular Send ──────────────────────────────────────────

  const send = useCallback(async (
    message: string,
    history?: Array<{ role: string; content: string }>
  ): Promise<string | null> => {
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({
      isStreaming: true,
      error: null,
      streamedContent: '',
      metadata: null,
      brainEvents: [],
      activeBrains: [],
    });

    try {
      // 1. Dedicated SSE endpoint
      try {
        const response = await sendChatDedicatedSSE({ message, history });
        const result = await processSSEResponse(response, controller);
        setState(prev => ({ ...prev, isStreaming: false }));
        return result.content;
      } catch {
        console.warn('[SSE] Dedicated endpoint failed, trying fallback');
        setState(prev => ({ ...prev, streamedContent: '', isStreaming: true }));
      }

      // 2. /api/chat SSE
      try {
        const response = await sendChatSSEViaProxy({ message, history });
        const result = await processSSEResponse(response, controller);
        setState(prev => ({ ...prev, isStreaming: false }));
        return result.content;
      } catch {
        console.warn('[SSE] /api/chat SSE failed, trying regular POST');
        setState(prev => ({ ...prev, streamedContent: '', isStreaming: true }));
      }

      // 3. Regular POST fallback
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, history }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const content = data.content || data.response || '';
        setState({
          isStreaming: false,
          error: null,
          streamedContent: content,
          metadata: { brain: data.brain || 'neural', confidence: data.confidence || 0.85 },
          brainEvents: [],
          activeBrains: [],
        });
        return content;
      } catch (postError) {
        if (controller.signal.aborted) return null;
        setState(prev => ({
          ...prev,
          isStreaming: false,
          error: postError instanceof Error ? postError.message : 'فشل الاتصال',
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

  // ─── SuperMind Send ────────────────────────────────────────

  const sendToSuperMind = useCallback(async (
    message: string,
    intent?: string,
    history?: Array<{ role: string; content: string }>
  ): Promise<string | null> => {
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({
      isStreaming: true,
      error: null,
      streamedContent: '',
      metadata: null,
      brainEvents: [],
      activeBrains: [],
    });

    try {
      const res = await fetch('/api/super-mind/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, intent, history }),
      });

      if (!res.ok) {
        // Fallback to regular chat
        return send(message, history);
      }

      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('text/event-stream')) {
        const result = await processSSEResponse(res, controller);
        setState(prev => ({ ...prev, isStreaming: false }));
        return result.content;
      }

      // JSON response
      const data = await res.json();
      const content = data.content || data.response || '';
      setState({
        isStreaming: false,
        error: null,
        streamedContent: content,
        metadata: data,
        brainEvents: data.brain_events || [],
        activeBrains: data.activated_brains || [],
      });
      return content;
    } catch {
      // Fallback to regular chat
      return send(message, history);
    }
  }, [send, processSSEResponse]);

  const reset = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();
    setState({
      isStreaming: false,
      error: null,
      streamedContent: '',
      metadata: null,
      brainEvents: [],
      activeBrains: [],
    });
  }, []);

  return { ...state, send, sendToSuperMind, reset };
}
