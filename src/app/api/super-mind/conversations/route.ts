// ═══════════════════════════════════════════════════════════════════
// SuperMind Conversations Search BFF Route
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';
const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get('q');

  try {
    const res = await fetch(`${BACKEND_URL}/api/supermind/conversations?q=${encodeURIComponent(query || '')}`, {
      signal: AbortSignal.timeout(8000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({ ...data, source: 'backend' });
    }
  } catch { /* unavailable */ }

  return NextResponse.json({
    conversations: [],
    total: 0,
    query: query || '',
    source: 'local',
    message: 'البحث في المحادثات يتطلب اتصالاً بالخادم الخلفي',
  });
}
