/**
 * BABSHARQII v40.0 — Project Registration API Route
 * مسار API لتسجيل مشاريع جديدة
 * Backend endpoint: POST /api/project-mgmt/registry/register
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    // Forward auth header if present
    const authHeader = request.headers.get('authorization');
    if (authHeader) {
      headers['Authorization'] = authHeader;
    } else {
      const sessionCookie = request.cookies.get('babsharqii_session')?.value;
      if (sessionCookie) {
        headers['Authorization'] = `Bearer ${sessionCookie}`;
      }
    }

    const res = await fetch(`${BACKEND_URL}/api/project-mgmt/registry/register`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10000),
    });

    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data, {
        headers: { 'X-Data-Source': 'backend' },
      });
    }

    return NextResponse.json(
      { error: 'Backend returned error', status: res.status },
      { status: res.status, headers: { 'X-Data-Source': 'backend' } }
    );
  } catch {
    return NextResponse.json(
      { error: 'Backend unavailable', fallback: true },
      { status: 503 }
    );
  }
}
