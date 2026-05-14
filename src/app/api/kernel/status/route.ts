/**
 * BABSHARQII v42.0 — Kernel Status API Route
 * مسار API لحالة النواة — مع استرجاع بيانات احتياطية
 * Primary: GET /api/kernel/status (requires auth on backend)
 * Fallback: GET /api/awareness/state (no auth required)
 */

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

const KERNEL_STATUS_FALLBACK = {
  kernel_status: 'running',
  uptime: 86400,
  active_processes: 5,
  current_task: 'مراقبة النظام',
  fallback: true,
};

export async function GET() {
  // Try kernel/status first (may require auth → 401)
  try {
    const res = await fetch(`${BACKEND_URL}/api/kernel/status`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data, {
        headers: { 'X-Data-Source': 'backend', 'X-Backend-Online': 'true' },
      });
    }
    // 401 or other error — try awareness/state as fallback
  } catch {
    // Backend might be down entirely
  }

  // Fallback 1: Try awareness/state (no auth required)
  try {
    const res = await fetch(`${BACKEND_URL}/api/awareness/state`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      // Map awareness/state to kernel/status format
      return NextResponse.json(
        {
          kernel_status: 'running',
          uptime: data.uptime ?? 0,
          active_processes: data.active_processes ?? 1,
          current_task: data.current_task ?? 'مراقبة النظام',
          vitality: data.vitality,
          llm_connectivity: data.llm_connectivity,
          fallback: true,
          source: 'awareness/state',
        },
        { headers: { 'X-Data-Source': 'backend-fallback', 'X-Backend-Online': 'true' } }
      );
    }
  } catch {
    // awareness/state also unavailable
  }

  // Fallback 2: Static data
  return NextResponse.json(KERNEL_STATUS_FALLBACK, {
    headers: { 'X-Data-Source': 'fallback', 'X-Backend-Online': 'false' },
  });
}
