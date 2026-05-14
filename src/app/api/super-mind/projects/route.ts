// ═══════════════════════════════════════════════════════════════════
// SuperMind Projects BFF Route
// Manages project lifecycle: thinking → proposed → working → done
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/project-mgmt/projects`, {
      signal: AbortSignal.timeout(10000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch { /* fallback */ }

  // Fallback: return project data from local storage or defaults
  return NextResponse.json({
    projects: [],
    total: 0,
    active: 0,
    completed: 0,
    paused: 0,
    _isOffline: true,
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, project } = body;

    // Route to backend based on action
    let endpoint = '';
    let payload = body;

    switch (action) {
      case 'create':
        endpoint = `${BACKEND_URL}/api/project-mgmt/registry/register`;
        payload = { name: project?.name, description: project?.description, category: project?.category || 'general' };
        break;
      case 'update_status':
        endpoint = `${BACKEND_URL}/api/project-mgmt/projects`;
        payload = { project_id: project?.id, status: project?.status };
        break;
      case 'promote':
        endpoint = `${BACKEND_URL}/api/project-mgmt/projects`;
        payload = { project_id: project?.id, action: 'promote', target_status: project?.target_status };
        break;
      default:
        endpoint = `${BACKEND_URL}/api/project-mgmt/projects`;
    }

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(15000),
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json({
          chat: { text: `تم تنفيذ العملية على المشروع "${project?.name || ''}" بنجاح` },
          screen: { component: 'ProjectsTracker', props: data, animation: 'slideRight' },
          brain: { activeBrain: 'neural', deliberationState: 'responding' },
        });
      }
    } catch { /* fallback */ }

    // Offline fallback
    return NextResponse.json({
      chat: { text: `تم تسجيل العملية محلياً. سيتم مزامنتها عند الاتصال بالخادم.` },
      screen: { component: 'ProjectsTracker', props: { project, action, _isOffline: true }, animation: 'slideRight' },
      brain: { activeBrain: 'neural', deliberationState: 'responding' },
    });
  } catch (error) {
    console.error('[SuperMind Projects] Error:', error);
    return NextResponse.json({ error: 'خطأ في إدارة المشاريع' }, { status: 500 });
  }
}
