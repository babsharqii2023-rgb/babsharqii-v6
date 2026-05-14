/**
 * BABSHARQII v20.0 — Autonomy API Route
 * مسار API للاستقلالية — تصنيف العمليات + الموافقة التلقائية
 * Proxies to FastAPI backend at /kernel/v20/autonomy
 */

import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders } from '@/lib/backend-proxy';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';
const KERNEL_API = `${BACKEND_URL}/api/kernel`;

async function fetchFromBackend(path: string, fallback: unknown, options?: RequestInit) {
  try {
    const res = await fetch(`${KERNEL_API}${path}`, {
      ...options,
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) return await res.json();
    return fallback;
  } catch {
    return fallback;
  }
}

const defaultAutonomyStatus = {
  autonomy: {
    autonomy_level: 0,
    total_decisions: 0,
    auto_approved_count: 0,
    human_approved_count: 0,
    auto_approval_rate: 0,
  },
  status: { initialized: false },
  recent_decisions: [],
};

export async function GET() {
  try {
    const data = await fetchFromBackend('/autonomy/status', defaultAutonomyStatus);
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to get autonomy status' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const action = body.action || 'classify';

    if (action === 'classify') {
      const data = await fetchFromBackend('/autonomy/classify', {
        level: 'moderate', auto_approve: false, confidence: 0.5,
      }, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders(request) },
        body: JSON.stringify({
          operation_type: body.operation_type || 'unknown',
          target: body.target || '',
          scope: body.scope || 'single_file',
          reversibility: body.reversibility || 'easy',
        }),
      });
      return NextResponse.json(data);
    }

    if (action === 'should-approve') {
      const data = await fetchFromBackend('/autonomy/should-approve', {
        auto_approve: false, confidence: 0.5,
      }, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders(request) },
        body: JSON.stringify({
          operation_type: body.operation_type || 'unknown',
          target: body.target || '',
          scope: body.scope || 'single_file',
          reversibility: body.reversibility || 'easy',
        }),
      });
      return NextResponse.json(data);
    }

    if (action === 'record-decision') {
      const data = await fetchFromBackend('/autonomy/record-decision', {
        status: 'recorded',
      }, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders(request) },
        body: JSON.stringify({
          operation_id: body.operation_id || '',
          approved: body.approved ?? true,
          reason: body.reason || '',
        }),
      });
      return NextResponse.json(data);
    }

    return NextResponse.json({ error: 'Unknown action' }, { status: 400 });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to process autonomy request' }, { status: 500 });
  }
}
