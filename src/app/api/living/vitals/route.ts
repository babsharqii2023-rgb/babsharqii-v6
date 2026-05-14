/**
 * BABSHARQII v40.0 — Living Vitals API Route
 * مسار API للمؤشرات الحيوية — مع تحويل بنية البيانات
 * 
 * الباكند يعيد: { energy: {value, percent, trend}, mood: {value, percent, trend}, ... }
 * الفرونتند يتوقع: { vitality: 75, energy: 85, curiosity: 68, coherence: 82, mood: 75, stress: 23 }
 */

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

const VITALS_FALLBACK = {
  vitality: 78,
  energy: 85,
  curiosity: 68,
  coherence: 82,
  mood: 75,
  stress: 23,
  heartbeat_bpm: 72,
  timestamp: new Date().toISOString(),
  fallback: true,
};

function normalizeVitals(raw: Record<string, unknown>) {
  // الباكند يعيد بنية nested: { energy: { value, percent, trend }, ... }
  const getVal = (key: string, altKey?: string): number => {
    const v = raw[key] ?? (altKey ? raw[altKey] : undefined);
    if (v === undefined || v === null) return 0;
    if (typeof v === 'number') return v;
    if (typeof v === 'object' && v !== null) {
      const obj = v as Record<string, unknown>;
      // استخدم percent أو value
      if (typeof obj.percent === 'number') return Math.round(obj.percent);
      if (typeof obj.value === 'number') return Math.round(Math.abs(obj.value) > 1 ? obj.value : obj.value * 100);
    }
    return 0;
  };

  return {
    vitality: getVal('vitality') || Math.round((getVal('energy') + getVal('mood') + getVal('curiosity')) / 3),
    energy: getVal('energy'),
    curiosity: getVal('curiosity'),
    coherence: getVal('coherence') || getVal('attachment', 'arousal') || 82,
    mood: getVal('mood'),
    stress: getVal('stress'),
    heartbeat_bpm: typeof raw.heartbeat_bpm === 'number' ? raw.heartbeat_bpm : 72,
  };
}

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/living/vitals`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      const normalized = normalizeVitals(data);
      return NextResponse.json(normalized, {
        headers: { 'X-Data-Source': 'backend' },
      });
    }
  } catch {
    // Backend unavailable
  }

  return NextResponse.json(VITALS_FALLBACK, {
    headers: { 'X-Data-Source': 'fallback', 'X-Backend-Online': 'false' },
  });
}
