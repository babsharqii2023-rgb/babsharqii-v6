/**
 * BABSHARQII v40.0 — Living Heartbeat API Route
 * مسار API لنبض القلب — مع تحويل بنية البيانات
 * 
 * الباكند يعيد: { cycle, dominant_emotion, vitals, energy_level, last_interaction_hours_ago }
 * الفرونتند يتوقع: { bpm: 72, rhythm: "steady", last_beat: "..." }
 */

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

const HEARTBEAT_FALLBACK = {
  bpm: 72,
  rhythm: 'steady',
  last_beat: new Date().toISOString(),
  fallback: true,
};

function normalizeHeartbeat(raw: Record<string, unknown>) {
  // الباكند لا يعيد bpm مباشرة — نحسبه من البيانات المتاحة
  const cycle = (raw.cycle as number) || 0;
  const energyLevel = (raw.energy_level as string) || 'normal';
  
  // حساب BPM تقريبي بناءً على مستوى الطاقة
  let bpm = 72;
  if (energyLevel === 'high') bpm = 85 + Math.floor(Math.random() * 10);
  else if (energyLevel === 'elevated') bpm = 75 + Math.floor(Math.random() * 8);
  else if (energyLevel === 'low') bpm = 60 + Math.floor(Math.random() * 8);
  else if (energyLevel === 'critical') bpm = 50 + Math.floor(Math.random() * 10);
  else bpm = 68 + Math.floor(Math.random() * 12);

  // إذا كان الباكند يعيد bpm فعلياً
  if (typeof raw.bpm === 'number') bpm = raw.bpm;
  if (typeof raw.heartbeat_bpm === 'number') bpm = raw.heartbeat_bpm;

  // حساب الإيقاع
  let rhythm = 'steady';
  const vitals = raw.vitals as Record<string, unknown> | undefined;
  if (vitals && typeof vitals.stress === 'object') {
    const stress = (vitals.stress as Record<string, unknown>)?.value;
    if (typeof stress === 'number' && stress > 60) rhythm = 'elevated';
    else if (typeof stress === 'number' && stress > 80) rhythm = 'racing';
  }

  return {
    bpm,
    rhythm,
    last_beat: raw.last_beat || new Date().toISOString(),
    // بيانات إضافية من الباكند
    cycle,
    dominant_emotion: raw.dominant_emotion,
    energy_level: energyLevel,
  };
}

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/living/heartbeat`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      const normalized = normalizeHeartbeat(data);
      return NextResponse.json(normalized, {
        headers: { 'X-Data-Source': 'backend' },
      });
    }
  } catch {
    // Backend unavailable
  }

  return NextResponse.json(HEARTBEAT_FALLBACK, {
    headers: { 'X-Data-Source': 'fallback', 'X-Backend-Online': 'false' },
  });
}
