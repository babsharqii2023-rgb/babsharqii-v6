// ═══════════════════════════════════════════════════════════════════
// SuperMind Project Scaffold BFF Route
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';
const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { projectName, description, template = 'default', options } = body;

  if (!projectName) {
    return NextResponse.json({ error: 'اسم المشروع مطلوب' }, { status: 400 });
  }

  try {
    const res = await fetch(`${BACKEND_URL}/api/supermind/scaffold`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_name: projectName, description, template, options }),
      signal: AbortSignal.timeout(60000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({ ...data, source: 'backend' });
    }
  } catch { /* unavailable */ }

  return NextResponse.json({
    status: 'pending',
    projectName,
    description: description || '',
    template,
    files: [],
    source: 'offline',
    message: 'الخادم الخلفي غير متاح — سيتم إنشاء المشروع عند توفر الاتصال',
  });
}
