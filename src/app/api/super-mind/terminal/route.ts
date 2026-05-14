// ═══════════════════════════════════════════════════════════════════
// SuperMind Terminal BFF Route
// Proxies terminal commands to the backend
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const { command, args, working_dir } = await request.json();

    if (!command) {
      return NextResponse.json({ error: 'الأمر مطلوب' }, { status: 400 });
    }

    // Try backend terminal endpoint
    try {
      const res = await fetch(`${BACKEND_URL}/api/terminal/npm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command, args: args || [], working_dir: working_dir || '.' }),
        signal: AbortSignal.timeout(30000),
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json({
          chat: { text: `تم تنفيذ: ${command}` },
          screen: {
            component: 'TerminalPanel',
            props: {
              output: data.output || data.stdout || '',
              exitCode: data.exit_code ?? 0,
              command,
              workingDir: working_dir || '~',
            },
            animation: 'slideUp',
          },
          brain: { activeBrain: 'symbolic', deliberationState: 'responding' },
        });
      }
    } catch { /* fallback */ }

    // Try generic terminal endpoint
    try {
      const res = await fetch(`${BACKEND_URL}/api/terminal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command }),
        signal: AbortSignal.timeout(30000),
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json({
          chat: { text: `تم تنفيذ: ${command}` },
          screen: {
            component: 'TerminalPanel',
            props: {
              output: data.output || '',
              exitCode: data.exit_code ?? 0,
              command,
            },
            animation: 'slideUp',
          },
          brain: { activeBrain: 'symbolic', deliberationState: 'responding' },
        });
      }
    } catch { /* fallback */ }

    // Offline response
    return NextResponse.json({
      chat: { text: `الأمر "${command}" في وضع الانتظار — الخادم غير متاح` },
      screen: {
        component: 'TerminalPanel',
        props: {
          output: `$ ${command}\n# الخادم غير متاح — سيتم التنفيذ عند الاتصال`,
          exitCode: -1,
          command,
          _isOffline: true,
        },
        animation: 'slideUp',
      },
      brain: { activeBrain: 'symbolic', deliberationState: 'idle' },
    });
  } catch (error) {
    console.error('[SuperMind Terminal] Error:', error);
    return NextResponse.json({ error: 'خطأ في الطرفية' }, { status: 500 });
  }
}
