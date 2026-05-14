/**
 * BABSHARQII v20.0 — Full Project Build API Route
 * بناء مشروع كامل مع الموافقة التلقائية
 * Proxies to FastAPI backend at /kernel/v20/build-full-project
 */

import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders } from '@/lib/backend-proxy';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';
const KERNEL_V20 = `${BACKEND_URL}/api/kernel`;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    try {
      const res = await fetch(`${KERNEL_V20}/build-project`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders(request) },
        body: JSON.stringify({
          description: body.description || body.idea || '',
          project_type: body.project_type || 'web',
          language: body.language || 'auto',
          auto_approve: body.auto_approve ?? true,
        }),
        signal: AbortSignal.timeout(30000),
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend unavailable
    }

    return NextResponse.json({
      status: 'backend_unavailable',
      message: 'الخادم غير متاح — حاول لاحقاً',
    });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to build project' }, { status: 500 });
  }
}
