// ═══════════════════════════════════════════════════════════════════
// SuperMind Code Generation BFF Route
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';
const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { prompt, language = 'python', filePath } = body;

  if (!prompt) {
    return NextResponse.json({ error: 'مطلوب وصف الكود' }, { status: 400 });
  }

  try {
    const res = await fetch(`${BACKEND_URL}/api/supermind/code-generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, language, file_path: filePath }),
      signal: AbortSignal.timeout(60000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({ ...data, source: 'backend' });
    }
  } catch { /* unavailable */ }

  // Try the code_generation_engine endpoint
  try {
    const res = await fetch(`${BACKEND_URL}/api/supermind/code`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, language }),
      signal: AbortSignal.timeout(60000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({ ...data, source: 'backend-alt' });
    }
  } catch { /* unavailable */ }

  return NextResponse.json({
    code: `# تم إنشاء هذا الكود بناءً على طلبك\n# "${prompt}"\n\n# ملاحظة: الخادم الخلفي غير متاح حالياً\n# يرجى التأكد من تشغيل الخادم للحصول على نتائج حقيقية\npass`,
    language,
    source: 'offline',
    message: 'الخادم الخلفي غير متاح — الكود المعروض هو بديل محلي',
  });
}
