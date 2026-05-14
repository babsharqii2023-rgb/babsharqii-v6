// ═══════════════════════════════════════════════════════════════════
// مأمون v40.0 — Sleep Cycle API (Real Backend Proxy + Auth)
// Proxies to FastAPI backend at /api/sleep/*
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

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
    const res = await fetch(`${BACKEND}/api/sleep/status`, {
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({
        phase: data.phase || 'awake',
        isSleeping: data.isSleeping || false,
        cyclesCompleted: data.cyclesCompleted || 0,
        dreamsGenerated: data.dreamsGenerated || 0,
        knowledgeCompressed: data.knowledgeCompressed || 0,
        lastSleepTime: data.currentCycleStart || null,
        currentSleepDuration: data.isSleeping && data.currentCycleStart
          ? Date.now() / 1000 - data.currentCycleStart
          : null,
        dreamLog: data.dreamLog || [],
        phaseDescriptions: {
          awake: 'مستيقظ — جميع الأدمغة نشطة وجاهزة للعمل',
          nrem: 'نوم عميق — ضغط المعرفة وإعادة تنظيم الذكريات',
          rem: 'نوم حالم — محاكاة السيناريوهات واكتشاف أنماط جديدة',
          recalibration: 'إعادة معايرة — تحسين أوزان الأدمغة وتحديث النماذج',
        },
      });
    }
    throw new Error(`Backend returned ${res.status}`);
  } catch {
    // Fallback: awake state
    return NextResponse.json({
      phase: 'awake',
      isSleeping: false,
      cyclesCompleted: 0,
      dreamsGenerated: 0,
      knowledgeCompressed: 0,
      dreamLog: [],
      phaseDescriptions: {
        awake: 'مستيقظ — جميع الأدمغة نشطة وجاهزة للعمل',
        nrem: 'نوم عميق — ضغط المعرفة وإعادة تنظيم الذكريات',
        rem: 'نوم حالم — محاكاة السيناريوهات واكتشاف أنماط جديدة',
        recalibration: 'إعادة معايرة — تحسين أوزان الأدمغة وتحديث النماذج',
      },
      fallback: true,
    });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action } = body;

    const endpointMap: Record<string, string> = {
      start: '/api/sleep/start',
      wake: '/api/sleep/wake',
      advance_phase: '/api/sleep/advance',
    };

    const endpoint = endpointMap[action];
    if (!endpoint) {
      return NextResponse.json(
        { error: 'إجراء غير معروف. الإجراءات المتاحة: start, wake, advance_phase' },
        { status: 400 }
      );
    }

    const authHeaders = getAuthHeaders(request);

    const res = await fetch(`${BACKEND}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders },
      body: JSON.stringify({ force: false }),
      signal: AbortSignal.timeout(5000),
    });

    if (res.ok) {
      return NextResponse.json(await res.json());
    }
    throw new Error(`Backend returned ${res.status}`);
  } catch {
    return NextResponse.json({ error: 'فشل في تحديث حالة النوم', fallback: true }, { status: 500 });
  }
}
