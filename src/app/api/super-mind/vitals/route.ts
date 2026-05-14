// ═══════════════════════════════════════════════════════════════════
// SuperMind Vitals BFF Route
// Aggregates system health, consciousness state, and living vitals
// ═══════════════════════════════════════════════════════════════════

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  const [vitalsRes, consciousnessRes, healthRes] = await Promise.allSettled([
    fetch(`${BACKEND_URL}/api/living/vitals`, { signal: AbortSignal.timeout(8000) }),
    fetch(`${BACKEND_URL}/api/consciousness/state`, { signal: AbortSignal.timeout(8000) }),
    fetch(`${BACKEND_URL}/api/health-monitor`, { signal: AbortSignal.timeout(8000) }),
  ]);

  const vitals = vitalsRes.status === 'fulfilled' && vitalsRes.value.ok
    ? await vitalsRes.value.json().catch(() => null)
    : null;
  const consciousness = consciousnessRes.status === 'fulfilled' && consciousnessRes.value.ok
    ? await consciousnessRes.value.json().catch(() => null)
    : null;
  const health = healthRes.status === 'fulfilled' && healthRes.value.ok
    ? await healthRes.value.json().catch(() => null)
    : null;

  const isOffline = !vitals && !consciousness && !health;

  return NextResponse.json({
    chat: {
      text: isOffline
        ? 'الخادم غير متصل — بيانات تقريبية'
        : 'تم جلب بيانات الصحة والحيوية بنجاح',
    },
    screen: {
      component: 'SiteStatsPanel',
      props: {
        vitals: vitals || {
          vitality: 75, energy: 85, coherence: 0.82,
          _isOffline: true,
        },
        consciousness: consciousness || {
          level: 0.7, coherence: 0.65, self_awareness: 0.65,
          metacognition: 0.72, state: 'aware',
          _isOffline: true,
        },
        health: health || {
          overall_health: 85, alerts: [],
          _isOffline: true,
        },
        _isOffline: isOffline,
      },
      animation: 'fadeIn',
    },
    brain: {
      activeBrain: 'causal',
      deliberationState: 'responding',
    },
    sound: { event: 'operation.complete' },
  });
}
