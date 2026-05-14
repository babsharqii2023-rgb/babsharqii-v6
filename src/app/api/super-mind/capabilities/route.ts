// ═══════════════════════════════════════════════════════════════════
// SuperMind Capabilities BFF Route
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const res = await fetch(`${BACKEND_URL}/api/capabilities`, {
      signal: AbortSignal.timeout(8000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({ ...data, source: 'backend' });
    }
  } catch { /* unavailable */ }

  // Fallback: Known capabilities
  return NextResponse.json({
    capabilities: [
      { id: 'code_generation', name: 'توليد الكود', nameEn: 'Code Generation', status: 'active', brain: 'symbolic' },
      { id: 'project_scaffold', name: 'بناء المشاريع', nameEn: 'Project Scaffold', status: 'active', brain: 'neural' },
      { id: 'web_search', name: 'البحث في الويب', nameEn: 'Web Search', status: 'active', brain: 'world_model' },
      { id: 'self_healing', name: 'الإصلاح الذاتي', nameEn: 'Self-Healing', status: 'active', brain: 'causal' },
      { id: 'agent_building', name: 'بناء الوكلاء', nameEn: 'Agent Building', status: 'active', brain: 'neural' },
      { id: 'tool_creation', name: 'إنشاء الأدوات', nameEn: 'Tool Creation', status: 'active', brain: 'symbolic' },
      { id: 'deployment', name: 'النشر', nameEn: 'Deployment', status: 'active', brain: 'causal' },
      { id: 'research', name: 'البحث العميق', nameEn: 'Research', status: 'active', brain: 'world_model' },
      { id: 'terminal', name: 'الطرفية', nameEn: 'Terminal', status: 'active', brain: 'symbolic' },
      { id: 'evolution', name: 'التطور الذاتي', nameEn: 'Self-Evolution', status: 'active', brain: 'neural' },
    ],
    total: 10,
    source: 'local',
  });
}
