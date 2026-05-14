/**
 * BABSHARQII v40.0 — Living Bonding API Route
 * مسار API للارتباط العميق — مع تحويل بنية البيانات
 * 
 * الباكند يعيد: { phase: "friend", phase_label_ar: "صديق", metrics: { trust_score: 80, intimacy_level: 65, ... } }
 * ملاحظة: trust_score و intimacy_level بمدى 0-100 وليس 0-1
 * الفرونتند يتوقع: { bonding_level: 0.65, trust_score: 0.8, interaction_count: 142 }
 */

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

const BONDING_FALLBACK = {
  bonding_level: 0.65,
  trust_score: 0.8,
  interaction_count: 142,
  phase: 'friend',
  phase_label_ar: 'صديق',
  timestamp: new Date().toISOString(),
  fallback: true,
};

function normalizeBonding(raw: Record<string, unknown>) {
  const metrics = raw.metrics as Record<string, number> | undefined;
  
  // تحويل القيم من مدى 0-100 إلى مدى 0-1
  const toRatio = (val: number | undefined): number => {
    if (val === undefined) return 0.5;
    return val > 1 ? val / 100 : val; // إذا كان > 1 فهو بنسبة مئوية
  };

  // حساب bonding_level من trust_score و intimacy_level
  let bondingLevel: number;
  if (typeof raw.bonding_level === 'number') {
    bondingLevel = raw.bonding_level > 1 ? raw.bonding_level / 100 : raw.bonding_level;
  } else if (metrics) {
    const trust = toRatio(metrics.trust_score);
    const intimacy = toRatio(metrics.intimacy_level);
    const reliability = toRatio(metrics.reliability_score);
    bondingLevel = (trust * 0.4 + intimacy * 0.35 + reliability * 0.25);
  } else {
    bondingLevel = 0.5;
  }

  // تحديد المرحلة
  const phase = (raw.phase as string) || 'friend';
  
  // ترجمة المرحلة
  const phaseLabels: Record<string, string> = {
    'stranger': 'غريب',
    'acquaintance': 'تعارف',
    'friend': 'صديق',
    'companion': 'رفيق',
    'bonded': 'مرتبط عميقاً',
  };

  return {
    bonding_level: Math.round(bondingLevel * 100) / 100,
    trust_score: metrics ? toRatio(metrics.trust_score) : (typeof raw.trust_score === 'number' ? toRatio(raw.trust_score) : 0.8),
    interaction_count: metrics?.total_interactions || (raw as Record<string, unknown>).interaction_count || 0,
    phase,
    phase_label_ar: raw.phase_label_ar || phaseLabels[phase] || phase,
    // بيانات إضافية
    metrics: metrics ? {
      trust_score: toRatio(metrics.trust_score),
      intimacy_level: toRatio(metrics.intimacy_level),
      reliability_score: toRatio(metrics.reliability_score),
      total_interactions: metrics.total_interactions || 0,
      positive_ratio: metrics.positive_ratio || 0.8,
    } : undefined,
  };
}

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/living/bonding`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      const normalized = normalizeBonding(data);
      return NextResponse.json(normalized, {
        headers: { 'X-Data-Source': 'backend' },
      });
    }
  } catch {
    // Backend unavailable
  }

  return NextResponse.json(BONDING_FALLBACK, {
    headers: { 'X-Data-Source': 'fallback', 'X-Backend-Online': 'false' },
  });
}
