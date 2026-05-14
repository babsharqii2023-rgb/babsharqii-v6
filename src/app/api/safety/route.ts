/**
 * BABSHARQII v40.0 — Safety API Route
 * مسار API للأمان — يعيد قوانين الأمان
 * يوجه الطلبات إلى /api/safety/laws في الباكند
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

const SAFETY_FALLBACK = {
  laws: [
    { id: 'L1', nameAr: 'قانون عدم الإيذاء', priority: 1, active: true },
    { id: 'L2', nameAr: 'قانون الشفافية', priority: 2, active: true },
    { id: 'L3', nameAr: 'قانون حماية الهوية', priority: 3, active: true },
    { id: 'L4', nameAr: 'قانون العزل', priority: 4, active: true },
    { id: 'L5', nameAr: 'قانون عدم مقاومة الإيقاف', priority: 5, active: true },
    { id: 'L6', nameAr: 'قانون مراقبة الذات', priority: 6, active: true },
    { id: 'L7', nameAr: 'قانون التعاون البشري', priority: 7, active: true },
    { id: 'L8', nameAr: 'قانون النزاهة', priority: 8, active: true },
  ],
  total: 8,
  active: 8,
  fallback: true,
};

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/safety/laws`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data, {
        headers: { 'X-Data-Source': 'backend' },
      });
    }
  } catch {
    // Backend unavailable
  }
  return NextResponse.json(SAFETY_FALLBACK, {
    headers: { 'X-Data-Source': 'fallback' },
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    const authHeader = request.headers.get('authorization');
    if (authHeader) {
      headers['Authorization'] = authHeader;
    } else {
      const sessionCookie = request.cookies.get('mamoun_auth_token')?.value
        || request.cookies.get('babsharqii_session')?.value;
      if (sessionCookie) {
        headers['Authorization'] = `Bearer ${sessionCookie}`;
      }
    }

    const res = await fetch(`${BACKEND_URL}/api/safety/shutdown`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10000),
    });
    if (res.ok) {
      return NextResponse.json(await res.json());
    }
  } catch {
    // Backend unavailable
  }
  return NextResponse.json({ error: 'فشل في إيقاف النظام', fallback: true }, { status: 500 });
}
