'use client';

import { useState, useEffect, useCallback } from 'react';

const BACKEND = process.env.NEXT_PUBLIC_MAMOUN_BACKEND_URL || 'http://localhost:8000';

// Map of data keys to Next.js API proxy routes (avoid CORS issues)
// Routes without a Next.js proxy call the backend directly
const API_ROUTES = {
  health: `${BACKEND}/health`,
  brains: '/api/brains',
  workspace: '/api/kernel/workspace',
  capabilities: '/api/capabilities-proxy/status',
  projects: '/api/kernel/workspace',
  updateStatus: '/api/update/status',
  metrics: `${BACKEND}/metrics`,
  approvalPending: `${BACKEND}/api/admin/agent/manifest`,
  evolution: '/api/evolution/current',
  v23Status: '/api/v23/status',
  v24Status: '/api/v24/status',
  v25Status: '/api/v25/status',
  livingVitals: `${BACKEND}/api/living/vitals`,
  livingEmotions: `${BACKEND}/api/living/emotions`,
  livingBonding: `${BACKEND}/api/living/bonding`,
  livingStatus: `${BACKEND}/api/living/status`,
};

export interface BrainData {
  id: string;
  name: string;
  model: string;
  status: string;
  confidence: number;
  weight: number;
  active: boolean;
}

export interface VitalSigns {
  energy: number;
  mood: number;
  arousal: number;
  attachment: number;
  curiosity: number;
  stress: number;
}

export interface BondingInfo {
  level: string;
  score: number;
  phase: string;
}

export interface UpdateInfo {
  git_state: {
    branch: string;
    commit: string;
    short_commit: string;
    last_message: string;
    dirty: boolean;
  };
  is_updating: boolean;
  last_check: string | null;
  updates_available: boolean;
  rollback_available: boolean;
  recent_updates: Array<Record<string, unknown>>;
}

async function safeFetch<T>(url: string, fallback: T): Promise<T> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);
    const res = await fetch(url, { signal: controller.signal });
    clearTimeout(timeout);
    if (!res.ok) return fallback;
    return await res.json();
  } catch {
    return fallback;
  }
}

const BRAIN_NAMES: Record<string, string> = {
  neural: 'العصبي',
  causal: 'السببي',
  symbolic: 'الرمزي',
  bayesian: 'الاحتمالي',
  world_model: 'نموذج العالم',
};

const BRAIN_WEIGHTS: Record<string, number> = {
  neural: 0.25, causal: 0.22, symbolic: 0.18, bayesian: 0.17, world_model: 0.18,
};

export interface JarvisData {
  connected: boolean;
  loading: boolean;
  health: Record<string, unknown> | null;
  brains: BrainData[];
  workspace: Record<string, unknown> | null;
  capabilities: Record<string, unknown> | null;
  projects: Array<Record<string, unknown>>;
  updateInfo: UpdateInfo | null;
  metrics: Record<string, unknown> | null;
  approvalPending: Array<Record<string, unknown>>;
  evolution: Record<string, unknown> | null;
  v23Status: Record<string, unknown> | null;
  v24Status: Record<string, unknown> | null;
  v25Status: Record<string, unknown> | null;
  // v22.0: Living Systems
  vitalSigns: VitalSigns | null;
  bonding: BondingInfo | null;
  emotions: Record<string, unknown> | null;
  livingStatus: Record<string, unknown> | null;
  refresh: () => void;
  lastUpdate: Date | null;
}

const DEFAULT_VITALS: VitalSigns = {
  energy: 0.78, mood: 0.65, arousal: 0.42, attachment: 0.55, curiosity: 0.88, stress: 0.22,
};

export function useJarvisData(pollInterval = 8000): JarvisData {
  const [data, setData] = useState<JarvisData>({
    connected: false, loading: true, health: null, brains: [],
    workspace: null, capabilities: null, projects: [], updateInfo: null, metrics: null,
    approvalPending: [], evolution: null, v23Status: null, v24Status: null, v25Status: null,
    vitalSigns: null, bonding: null, emotions: null, livingStatus: null,
    refresh: () => {}, lastUpdate: null,
  });

  const fetchAll = useCallback(async () => {
    try {
      const [health, kernelBrains, workspace, capabilities, projects, updateInfo,
        metrics, approvalPending, evolution, v23Status, v24Status, v25Status,
        livingVitals, livingEmotions, livingBonding, livingStatus,
      ] = await Promise.allSettled([
        safeFetch(API_ROUTES.health, null),
        safeFetch(API_ROUTES.brains, { brains: {} }),
        safeFetch(API_ROUTES.workspace, null),
        safeFetch(API_ROUTES.capabilities, null),
        safeFetch(API_ROUTES.projects, null),
        safeFetch(API_ROUTES.updateStatus, null),
        safeFetch(API_ROUTES.metrics, null),
        safeFetch(API_ROUTES.approvalPending, { pending: [] }),
        safeFetch(API_ROUTES.evolution, null),
        safeFetch(API_ROUTES.v23Status, null),
        safeFetch(API_ROUTES.v24Status, null),
        safeFetch(API_ROUTES.v25Status, null),
        // Living Systems
        safeFetch(API_ROUTES.livingVitals, null),
        safeFetch(API_ROUTES.livingEmotions, null),
        safeFetch(API_ROUTES.livingBonding, null),
        safeFetch(API_ROUTES.livingStatus, null),
      ]);

      const brainsData = kernelBrains.status === 'fulfilled' ? kernelBrains.value : { brains: {} };
      const brains: BrainData[] = [];
      if (brainsData && typeof brainsData === 'object') {
        const b = brainsData as Record<string, unknown>;
        if (b.brains && typeof b.brains === 'object') {
          for (const [id, info] of Object.entries(b.brains as Record<string, unknown>)) {
            const brain = info as Record<string, unknown>;
            brains.push({
              id, name: BRAIN_NAMES[id] || id,
              model: String(brain.model || '?'),
              status: String(brain.status || 'offline'),
              confidence: Number(brain.confidence || 0),
              weight: BRAIN_WEIGHTS[id] || 0.1,
              active: brain.status === 'active',
            });
          }
        }
      }

      let projectsList: Array<Record<string, unknown>> = [];
      const pd = projects.status === 'fulfilled' ? projects.value : null;
      if (pd && typeof pd === 'object') {
        const pArr = (pd as Record<string, unknown>).projects;
        if (Array.isArray(pArr)) projectsList = pArr;
      }

      let pendingList: Array<Record<string, unknown>> = [];
      const ap = approvalPending.status === 'fulfilled' ? approvalPending.value : null;
      if (ap && typeof ap === 'object') {
        const apArr = (ap as Record<string, unknown>).pending;
        if (Array.isArray(apArr)) pendingList = apArr;
      }

      // Parse vital signs from backend
      let vitalSigns: VitalSigns | null = null;
      if (livingVitals.status === 'fulfilled' && livingVitals.value) {
        const v = livingVitals.value as Record<string, unknown>;
        vitalSigns = {
          energy: Number(v.energy ?? DEFAULT_VITALS.energy),
          mood: Number(v.mood ?? DEFAULT_VITALS.mood),
          arousal: Number(v.arousal ?? DEFAULT_VITALS.arousal),
          attachment: Number(v.attachment ?? DEFAULT_VITALS.attachment),
          curiosity: Number(v.curiosity ?? DEFAULT_VITALS.curiosity),
          stress: Number(v.stress ?? DEFAULT_VITALS.stress),
        };
      }

      // Parse bonding
      let bonding: BondingInfo | null = null;
      if (livingBonding.status === 'fulfilled' && livingBonding.value) {
        const bd = livingBonding.value as Record<string, unknown>;
        bonding = {
          level: String(bd.level || bd.phase || 'stranger'),
          score: Number(bd.score ?? bd.bond_strength ?? 42),
          phase: String(bd.phase || bd.level || 'stranger'),
        };
      }

      setData(prev => ({
        ...prev,
        connected: health.status === 'fulfilled' && health.value !== null,
        loading: false,
        health: health.status === 'fulfilled' ? health.value : null,
        brains,
        workspace: workspace.status === 'fulfilled' ? workspace.value : null,
        capabilities: capabilities.status === 'fulfilled' ? capabilities.value : null,
        projects: projectsList,
        updateInfo: updateInfo.status === 'fulfilled' ? updateInfo.value as unknown as UpdateInfo : null,
        metrics: metrics.status === 'fulfilled' ? metrics.value : null,
        approvalPending: pendingList,
        evolution: evolution.status === 'fulfilled' ? evolution.value : null,
        v23Status: v23Status.status === 'fulfilled' ? v23Status.value : null,
        v24Status: v24Status.status === 'fulfilled' ? v24Status.value : null,
        v25Status: v25Status.status === 'fulfilled' ? v25Status.value : null,
        vitalSigns,
        bonding,
        emotions: livingEmotions.status === 'fulfilled' ? livingEmotions.value : null,
        livingStatus: livingStatus.status === 'fulfilled' ? livingStatus.value : null,
        lastUpdate: new Date(),
      }));
    } catch {
      setData(prev => ({ ...prev, connected: false, loading: false }));
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, pollInterval);
    return () => clearInterval(interval);
  }, [fetchAll, pollInterval]);

  return { ...data, refresh: fetchAll };
}
