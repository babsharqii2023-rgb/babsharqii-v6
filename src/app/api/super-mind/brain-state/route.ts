import { NextResponse } from 'next/server';
const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/brains`, { signal: AbortSignal.timeout(10000) });
    if (res.ok) return NextResponse.json(await res.json());
  } catch {}
  return NextResponse.json({
    brains: [
      { id: 'neural', name: 'العصبي', status: 'idle', confidence: 0.5, model: 'glm-5.1', weight: 0.25, _isOffline: true },
      { id: 'causal', name: 'السببي', status: 'idle', confidence: 0.5, model: 'deepseek-reasoner', weight: 0.22, _isOffline: true },
      { id: 'symbolic', name: 'الرمزي', status: 'idle', confidence: 0.5, model: 'glm-4-plus', weight: 0.18, _isOffline: true },
      { id: 'bayesian', name: 'البيزي', status: 'idle', confidence: 0.5, model: 'gemini-2.0-flash', weight: 0.17, _isOffline: true },
      { id: 'world_model', name: 'العالمي', status: 'idle', confidence: 0.5, model: 'deepseek-chat', weight: 0.18, _isOffline: true },
    ],
    _isOffline: true,
  });
}
