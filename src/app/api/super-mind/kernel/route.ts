// ═══════════════════════════════════════════════════════════════════
// SuperMind Kernel BFF Route
// Handles kernel status and self-modification proposals
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const [kernelRes, workspaceRes, toolsRes] = await Promise.allSettled([
      fetch(`${BACKEND_URL}/api/kernel/status`, { signal: AbortSignal.timeout(8000) }),
      fetch(`${BACKEND_URL}/api/kernel/workspace`, { signal: AbortSignal.timeout(8000) }),
      fetch(`${BACKEND_URL}/api/kernel/tools`, { signal: AbortSignal.timeout(8000) }),
    ]);

    const kernel = kernelRes.status === 'fulfilled' && kernelRes.value.ok
      ? await kernelRes.value.json().catch(() => null) : null;
    const workspace = workspaceRes.status === 'fulfilled' && workspaceRes.value.ok
      ? await workspaceRes.value.json().catch(() => null) : null;
    const tools = toolsRes.status === 'fulfilled' && toolsRes.value.ok
      ? await toolsRes.value.json().catch(() => null) : null;

    return NextResponse.json({
      chat: { text: 'حالة النواة الحالية' },
      screen: {
        component: 'SiteStatsPanel',
        props: {
          kernel: kernel || { kernel_status: 'unknown', uptime: 0, active_processes: 0, _isOffline: true },
          workspace: workspace || { workspace: 'default', active_projects: 0, _isOffline: true },
          tools: tools || { tools: [], total: 0, _isOffline: true },
        },
        animation: 'fadeIn',
      },
      brain: { activeBrain: 'neural', deliberationState: 'responding' },
    });
  } catch {
    return NextResponse.json({
      chat: { text: 'الخادم غير متاح' },
      screen: {
        component: 'SiteStatsPanel',
        props: { kernel: { kernel_status: 'offline', _isOffline: true } },
        animation: 'fadeIn',
      },
      brain: { activeBrain: 'neural', deliberationState: 'idle' },
    });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, modification } = body;

    // Self-modify proposal
    if (action === 'self_modify' || action === 'propose') {
      try {
        const res = await fetch(`${BACKEND_URL}/api/kernel/self-modify/propose`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(modification || body),
          signal: AbortSignal.timeout(30000),
        });
        if (res.ok) {
          const data = await res.json();
          return NextResponse.json({
            chat: { text: 'تم تقديم اقتراح التعديل الذاتي' },
            screen: {
              component: 'SelfModifyPanel',
              props: data,
              animation: 'pulseIn',
            },
            brain: { activeBrain: 'neural', deliberationState: 'responding' },
            sound: { event: 'confirm.request' },
          });
        }
      } catch { /* fallback */ }

      return NextResponse.json({
        chat: { text: 'التعديل الذاتي في وضع الانتظار — الخادم غير متاح' },
        screen: {
          component: 'SelfModifyPanel',
          props: { modification, status: 'pending', _isOffline: true },
          animation: 'pulseIn',
        },
        brain: { activeBrain: 'neural', deliberationState: 'idle' },
      });
    }

    return NextResponse.json({ error: 'إجراء غير معروف' }, { status: 400 });
  } catch (error) {
    console.error('[SuperMind Kernel] Error:', error);
    return NextResponse.json({ error: 'خطأ في النواة' }, { status: 500 });
  }
}
