/**
 * BABSHARQII v40.0 — Living Emotions API Route
 * مسار API للمشاعر الحية — مع تحويل بنية البيانات
 * 
 * الباكند يعيد: { spectrum: { joy: 0.45, excitement: 0.38, ... }, dominant: "curiosity_eager" }
 * الفرونتند يتوقع: { emotions: { joy: 0.6, sadness: 0.1, ... }, dominant: "focus" }
 */

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

const EMOTIONS_FALLBACK = {
  emotions: {
    joy: 0.6,
    sadness: 0.1,
    anger: 0.05,
    fear: 0.08,
    surprise: 0.3,
    trust: 0.7,
  },
  dominant: 'joy',
  valence: 'positive',
  intensity: 0.7,
  current: 'focused',
  timestamp: new Date().toISOString(),
  fallback: true,
};

// تحويل مفاتيح المشاعر من الباكند إلى الفرونتند
const EMOTION_KEY_MAP: Record<string, string> = {
  'joy': 'joy',
  'excitement': 'joy',
  'contentment': 'trust',
  'curiosity_eager': 'surprise',
  'love': 'trust',
  'anxiety': 'fear',
  'frustration': 'anger',
  'sadness': 'sadness',
  'boredom': 'sadness',
  'calm': 'trust',
  'curiosity': 'surprise',
  'focus': 'trust',
  'satisfaction': 'joy',
  'alertness': 'fear',
  'empathy': 'trust',
  'determination': 'trust',
  'interest': 'surprise',
  'surprise': 'surprise',
  'anger': 'anger',
  'fear': 'fear',
};

function normalizeEmotions(raw: Record<string, unknown>) {
  // الباكند قد يعيد spectrum أو emotions
  const rawEmotions = (raw.spectrum || raw.emotions || {}) as Record<string, number>;
  
  // دمج المشاعر المتشابهة
  const merged: Record<string, number> = { joy: 0, sadness: 0, anger: 0, fear: 0, surprise: 0, trust: 0 };
  
  for (const [key, val] of Object.entries(rawEmotions)) {
    const mappedKey = EMOTION_KEY_MAP[key] || 'surprise'; // default
    if (typeof val === 'number') {
      // أخذ القيمة الأعلى إذا كان هناك تكرار
      merged[mappedKey] = Math.max(merged[mappedKey] || 0, val);
    }
  }
  
  // التأكد من أن كل المشاعر لها قيمة
  if (merged.joy === 0 && merged.sadness === 0 && merged.trust === 0) {
    // إذا كلها صفر، ربما البيانات بتنسيق مختلف — حاول القراءة المباشرة
    for (const key of Object.keys(rawEmotions)) {
      if (['joy', 'sadness', 'anger', 'fear', 'surprise', 'trust'].includes(key)) {
        merged[key] = rawEmotions[key];
      }
    }
  }

  // تحديد المشاعرة السائدة
  const dominant = (raw.dominant as string) || 'joy';
  const dominantMapped = EMOTION_KEY_MAP[dominant] || dominant;

  return {
    emotions: merged,
    dominant: dominantMapped,
    valence: (raw.valence as string) || (merged.joy > merged.sadness ? 'positive' : 'negative'),
    intensity: (raw.intensity as number) || 0.7,
    current: dominantMapped,
  };
}

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/living/emotions`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      const normalized = normalizeEmotions(data);
      return NextResponse.json(normalized, {
        headers: { 'X-Data-Source': 'backend' },
      });
    }
  } catch {
    // Backend unavailable
  }

  return NextResponse.json(EMOTIONS_FALLBACK, {
    headers: { 'X-Data-Source': 'fallback', 'X-Backend-Online': 'false' },
  });
}
