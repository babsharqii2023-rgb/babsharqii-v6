import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders } from '@/lib/backend-proxy';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const resp = await fetch(`${BACKEND_URL}/api/capabilities`, {
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (resp.ok) {
      const data = await resp.json();
      return NextResponse.json({ source: 'python_backend', ...data });
    }
  } catch {
    // Backend unreachable
  }
  return NextResponse.json({
    source: 'frontend_fallback',
    capabilities: [
      { id: 'laptop-control', name: 'Laptop Control', status: 'active' },
      { id: 'terminal', name: 'Terminal', status: 'active' },
      { id: 'code', name: 'Professional Coding', status: 'active' },
      { id: 'deep-research', name: 'Deep Research', status: 'active' },
      { id: 'project-building', name: 'Project Building', status: 'active' },
      { id: 'instagram', name: 'Instagram Analysis', status: 'idle' },
      { id: 'blender', name: 'Blender Control', status: 'standby' },
      { id: 'browser', name: 'Agent Browser', status: 'active' },
      { id: 'sandbox', name: 'Testing Sandbox', status: 'active' },
      { id: 'trading', name: 'Trading Room', status: 'idle' },
    ],
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const resp = await fetch(`${BACKEND_URL}/api/capabilities`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders(request) },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10000),
    });
    if (resp.ok) {
      return NextResponse.json(await resp.json());
    }
  } catch {
    // Backend unreachable
  }
  return NextResponse.json({ source: 'frontend_fallback', success: false, error: 'Backend unavailable' });
}
