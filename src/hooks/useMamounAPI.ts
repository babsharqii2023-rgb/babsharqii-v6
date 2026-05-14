'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { checkBackendHealth, apiGet, type HealthResponse, type BrainStatusResponse } from '@/lib/api';
import { useAppStore } from '@/lib/store';

// ─── useHealth ────────────────────────────────────────────────
// Polls /health every 10s, updates store with brain status

interface HealthState {
  health: HealthResponse | null;
  isBackendOnline: boolean;
  lastCheck: number | null;
  error: string | null;
}

export function useHealth(pollInterval: number = 10000) {
  const [state, setState] = useState<HealthState>({
    health: null,
    isBackendOnline: false,
    lastCheck: null,
    error: null,
  });
  const setSystemHealth = useAppStore(s => s.setSystemHealth);
  const updateBrainStatus = useAppStore(s => s.updateBrainStatus);
  const updateBrainConfidence = useAppStore(s => s.updateBrainConfidence);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      const health = await checkBackendHealth();
      const isOnline = health !== null && health.status === 'ok';

      setState({
        health,
        isBackendOnline: isOnline,
        lastCheck: Date.now(),
        error: null,
      });

      // Update store with health data
      if (health) {
        const brainCount = Object.keys(health.brains || {}).length;
        const overallHealth = isOnline ? (brainCount > 0 ? 85 + Math.random() * 15 : 60) : 20;
        setSystemHealth(Math.round(overallHealth));

        // Update individual brain statuses from health data
        if (health.brains) {
          for (const [brainId, brainInfo] of Object.entries(health.brains)) {
            const status = (brainInfo as { status: string; confidence: number }).status === 'active' ? 'active' as const :
                          (brainInfo as { status: string; confidence: number }).status === 'idle' ? 'idle' as const : 'sleeping' as const;
            updateBrainStatus(brainId, status);
            updateBrainConfidence(brainId, (brainInfo as { status: string; confidence: number }).confidence);
          }
        }
      }
    } catch (err) {
      setState(prev => ({
        ...prev,
        isBackendOnline: false,
        error: err instanceof Error ? err.message : 'Connection failed',
      }));
      setSystemHealth(20);
    }
  }, [setSystemHealth, updateBrainStatus, updateBrainConfidence]);

  useEffect(() => {
    checkHealth();
    intervalRef.current = setInterval(checkHealth, pollInterval);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [checkHealth, pollInterval]);

  return state;
}

// ─── useBrainStatus ───────────────────────────────────────────
// Gets detailed brain status from /api/brains/status

interface BrainStatusState {
  data: BrainStatusResponse | null;
  loading: boolean;
  error: string | null;
}

export function useBrainStatus() {
  const [state, setState] = useState<BrainStatusState>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchStatus = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true }));
      const data = await apiGet<BrainStatusResponse>('/api/brains/status');
      setState({ data, loading: false, error: null });
    } catch (err) {
      setState({
        data: null,
        loading: false,
        error: err instanceof Error ? err.message : 'Failed to fetch brain status',
      });
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const doFetch = async () => {
      try {
        const data = await apiGet<BrainStatusResponse>('/api/brains/status');
        if (!cancelled) {
          setState({ data, loading: false, error: null });
        }
      } catch (err) {
        if (!cancelled) {
          setState({
            data: null,
            loading: false,
            error: err instanceof Error ? err.message : 'Failed to fetch brain status',
          });
        }
      }
    };
    doFetch();
    return () => { cancelled = true; };
  }, [fetchStatus]);

  return { ...state, refetch: fetchStatus };
}

// ─── useSystemMetrics ─────────────────────────────────────────
// Derived metrics from store + health data

interface SystemMetrics {
  healthPercent: number;
  activeBrains: number;
  totalBrains: number;
  avgConfidence: number;
  avgLatency: number;
  isOnline: boolean;
}

export function useSystemMetrics(): SystemMetrics {
  const brains = useAppStore(s => s.brains);
  const systemHealth = useAppStore(s => s.systemHealth);

  const activeBrains = brains.filter(b => b.status === 'active').length;
  const totalBrains = brains.length;
  const avgConfidence = totalBrains > 0
    ? brains.reduce((sum, b) => sum + b.confidence, 0) / totalBrains
    : 0;
  const avgLatency = totalBrains > 0
    ? brains.reduce((sum, b) => sum + b.latency, 0) / totalBrains
    : 0;

  return {
    healthPercent: systemHealth,
    activeBrains,
    totalBrains,
    avgConfidence: Math.round(avgConfidence * 100),
    avgLatency: Math.round(avgLatency),
    isOnline: systemHealth > 50,
  };
}
