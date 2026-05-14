// ═══════════════════════════════════════════════════════════════════
// SuperMind Update BFF Route
// Handles system self-update via GitHub pull
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    // Step 1: Check for updates
    let checkData: Record<string, unknown> = {};
    try {
      const checkRes = await fetch(`${BACKEND_URL}/api/update/check`, {
        signal: AbortSignal.timeout(15000),
      });
      if (checkRes.ok) checkData = await checkRes.json();
    } catch { /* skip check */ }

    // Step 2: Pull updates
    try {
      const pullRes = await fetch(`${BACKEND_URL}/api/update/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(120000),
      });
      if (pullRes.ok) {
        const data = await pullRes.json();
        return NextResponse.json({
          chat: {
            text: data.status === 'up_to_date'
              ? 'النظام محدث بالفعل — لا توجد تحديثات جديدة.'
              : `تم التحديث بنجاح! Commit: ${data.new_commit || 'unknown'}`,
          },
          screen: {
            component: 'UpdatePanel',
            props: {
              status: data.status,
              newCommit: data.new_commit,
              elapsedSeconds: data.elapsed_seconds,
              hadLocalChanges: data.had_local_changes,
              conflictsResolved: data.conflicts_resolved,
            },
            animation: 'pulseIn',
          },
          brain: { activeBrain: 'neural', deliberationState: 'responding' },
          sound: { event: 'operation.complete' },
        });
      }
    } catch { /* fallback */ }

    return NextResponse.json({
      chat: { text: 'فشل الاتصال بخادم التحديثات' },
      screen: {
        component: 'UpdatePanel',
        props: { status: 'offline', _isOffline: true },
        animation: 'pulseIn',
      },
      brain: { activeBrain: 'neural', deliberationState: 'idle' },
      sound: { event: 'operation.error' },
    });
  } catch (error) {
    console.error('[SuperMind Update] Error:', error);
    return NextResponse.json({ error: 'خطأ في التحديث' }, { status: 500 });
  }
}

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/update/status`, {
      signal: AbortSignal.timeout(10000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch { /* fallback */ }

  return NextResponse.json({
    is_updating: false,
    current_commit: 'unknown',
    _isOffline: true,
  });
}
