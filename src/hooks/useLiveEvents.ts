// ═══════════════════════════════════════════════════════════════════
// مأمون v18 — useLiveEvents Hook
// Polls the /api/events endpoint for real-time system updates
// Brain status, notifications, task updates, etc.
// ═══════════════════════════════════════════════════════════════════

'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

export interface LiveEvent {
  id: string;
  type: string;
  source: string;
  data: Record<string, any>;
  timestamp: number;
}

interface UseLiveEventsOptions {
  pollInterval?: number; // ms, default 5000
  enabled?: boolean;
}

export function useLiveEvents(options: UseLiveEventsOptions = {}) {
  const { pollInterval = 5000, enabled = true } = options;
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const lastEventIdRef = useRef<string>('0');
  const abortRef = useRef<AbortController | null>(null);

  const poll = useCallback(async () => {
    if (!enabled) return;

    try {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch(`/api/events?lastEventId=${lastEventIdRef.current}`, {
        signal: controller.signal,
      });

      if (!res.ok) return;

      const text = await res.text();
      const newEvents: LiveEvent[] = [];

      // Parse SSE text format
      for (const line of text.split('\n')) {
        if (line.startsWith('data: ')) {
          try {
            const parsed = JSON.parse(line.slice(6));
            if (parsed.type === 'heartbeat') {
              setIsConnected(true);
              continue;
            }
            if (parsed.id) {
              newEvents.push(parsed as LiveEvent);
              lastEventIdRef.current = parsed.id;
            }
          } catch { /* skip invalid JSON */ }
        }
      }

      if (newEvents.length > 0) {
        setEvents(prev => [...prev.slice(-50), ...newEvents]);
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setIsConnected(false);
      }
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;

    // Initial poll
    poll();

    const interval = setInterval(poll, pollInterval);
    return () => {
      clearInterval(interval);
      abortRef.current?.abort();
    };
  }, [poll, pollInterval, enabled]);

  const pushEvent = useCallback(async (type: string, source: string, data: Record<string, any>) => {
    try {
      await fetch('/api/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, source, data }),
      });
    } catch { /* silent */ }
  }, []);

  return { events, isConnected, pushEvent };
}
