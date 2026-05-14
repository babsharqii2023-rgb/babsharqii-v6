/**
 * BABSHARQII v40.0 — Brains API Route
 * مسار API للأدمغة — مع تحويل بنية البيانات وإضافة Auth
 * 
 * الباكند قد يعيد brains كـ dict {neural: {...}, causal: {...}} أو كـ array [{...}]
 * الفرونتند يتوقع دائماً: { brains: [{id, name, nameAr, confidence, status, ...}] }
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

const FALLBACK_BRAINS = [
  { id: 'neural', name: 'Neural', nameAr: 'العصبي', type: 'deep_learning', enabled: true, status: 'active', confidence: 92, weight: 0.25, model: 'glm-5.1' },
  { id: 'causal', name: 'Causal', nameAr: 'السببي', type: 'causal_reasoning', enabled: true, status: 'active', confidence: 87, weight: 0.22, model: 'deepseek-reasoner' },
  { id: 'symbolic', name: 'Symbolic', nameAr: 'الرمزي', type: 'symbolic_logic', enabled: true, status: 'idle', confidence: 79, weight: 0.18, model: 'glm-4-plus' },
  { id: 'bayesian', name: 'Bayesian', nameAr: 'الاحتمالي', type: 'probabilistic', enabled: true, status: 'active', confidence: 85, weight: 0.17, model: 'gemini-2.0-flash' },
  { id: 'world_model', name: 'World Model', nameAr: 'نموذج العالم', type: 'world_modeling', enabled: true, status: 'idle', confidence: 81, weight: 0.18, model: 'deepseek-chat' },
];

function normalizeBrains(raw: Record<string, unknown>) {
  let brainsArray: Record<string, unknown>[] = [];

  if (raw.brains) {
    if (Array.isArray(raw.brains)) {
      brainsArray = raw.brains as Record<string, unknown>[];
    } else if (typeof raw.brains === 'object') {
      // تحويل dict إلى array
      brainsArray = Object.values(raw.brains as Record<string, Record<string, unknown>>);
    }
  }

  // تطبيع كل دماغ
  const normalized = brainsArray.map((b: Record<string, unknown>) => ({
    id: b.id || b.brain_id || '',
    name: b.name || b.id || '',
    nameAr: b.nameAr || b.name_ar || b.name || '',
    type: b.type || 'unknown',
    enabled: b.enabled !== false,
    status: b.status || (b.active ? 'active' : 'idle'),
    confidence: typeof b.confidence === 'number' ? Math.round(b.confidence > 1 ? b.confidence : b.confidence * 100) : 75,
    weight: typeof b.weight === 'number' ? b.weight : 0.2,
    model: b.model || b.llm_model || '',
    temperature: b.temperature || 0.7,
  }));

  return { brains: normalized, total: normalized.length };
}

function getAuthHeaders(request: NextRequest): Record<string, string> {
  const headers: Record<string, string> = {};
  const authHeader = request.headers.get('authorization');
  if (authHeader) {
    headers['Authorization'] = authHeader;
  } else {
    const cookie = request.cookies.get('mamoun_auth_token')?.value
      || request.cookies.get('babsharqii_session')?.value;
    if (cookie) headers['Authorization'] = `Bearer ${cookie}`;
  }
  return headers;
}

export async function GET() {
  try {
    // جرب /api/brains أولاً (يعيد array)
    let res = await fetch(`${BACKEND_URL}/api/brains`, {
      signal: AbortSignal.timeout(5000),
    });
    
    if (res.ok) {
      const data = await res.json();
      // /api/brains يعيد { brains: [...] } مباشرة
      if (data.brains && Array.isArray(data.brains)) {
        return NextResponse.json(normalizeBrains(data), {
          headers: { 'X-Data-Source': 'backend' },
        });
      }
    }

    // Fallback: /api/kernel/brains (يعيد dict)
    res = await fetch(`${BACKEND_URL}/api/kernel/brains`, {
      signal: AbortSignal.timeout(5000),
    });
    
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(normalizeBrains(data), {
        headers: { 'X-Data-Source': 'backend' },
      });
    }
  } catch {
    // Backend unavailable
  }

  return NextResponse.json(
    { brains: FALLBACK_BRAINS, total: 5, fallback: true },
    { headers: { 'X-Data-Source': 'fallback' } }
  );
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, brainId } = body;

    if (!brainId || !action) {
      return NextResponse.json(
        { error: 'يرجى تحديد الإجراء ومعرّف الدماغ' },
        { status: 400 }
      );
    }

    const actionPath = action === 'activate' ? 'activate' : 'deactivate';
    const authHeaders = getAuthHeaders(request);
    
    const res = await fetch(`${BACKEND_URL}/api/kernel/brains/${brainId}/${actionPath}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders },
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      return NextResponse.json(await res.json());
    }
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 });
  } catch {
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 });
  }
}
