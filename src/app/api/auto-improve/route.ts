/**
 * BABSHARQII v20.0 — Auto Improve Safe API Route
 * تحسين تلقائي آمن — تعليقات + توثيق + اختبارات
 * Proxies to FastAPI backend at /kernel/v20/auto-improve-safe
 */

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';
const KERNEL_API = `${BACKEND_URL}/api/kernel`;

export async function POST() {
  try {
    try {
      const res = await fetch(`${KERNEL_API}/self-modify/auto-improve`, {
        method: 'POST',
        signal: AbortSignal.timeout(10000),
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
    return NextResponse.json({ error: 'Failed to auto-improve' }, { status: 500 });
  }
}
