// ═══════════════════════════════════════════════════════════════════
// SuperMind Structure BFF Route
// Returns project structure tree from backend
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;

  try {
    const res = await fetch(`${BACKEND_URL}/api/external/structure/${encodeURIComponent(name)}`, {
      signal: AbortSignal.timeout(10000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({
        chat: { text: `هيكل المشروع: ${name}` },
        screen: {
          component: 'ProjectsTracker',
          props: { structure: data, projectName: name },
          animation: 'slideRight',
        },
        brain: { activeBrain: 'symbolic', deliberationState: 'responding' },
      });
    }
  } catch { /* fallback */ }

  return NextResponse.json({
    chat: { text: `هيكل المشروع "${name}" غير متاح حالياً` },
    screen: {
      component: 'ProjectsTracker',
      props: { projectName: name, _isOffline: true },
      animation: 'slideRight',
    },
    brain: { activeBrain: 'symbolic', deliberationState: 'idle' },
  });
}
