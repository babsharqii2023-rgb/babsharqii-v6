import { NextResponse } from 'next/server';
const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const [vitalsRes, kernelRes] = await Promise.allSettled([
      fetch(`${BACKEND_URL}/api/living/vitals`, { signal: AbortSignal.timeout(8000) }),
      fetch(`${BACKEND_URL}/api/kernel/status`, { signal: AbortSignal.timeout(8000) }),
    ]);
    const vitals = vitalsRes.status === 'fulfilled' && vitalsRes.value.ok ? await vitalsRes.value.json() : {};
    const kernel = kernelRes.status === 'fulfilled' && kernelRes.value.ok ? await kernelRes.value.json() : {};
    return NextResponse.json({ ...vitals, ...kernel });
  } catch {}
  return NextResponse.json({ vitality: 0, _isOffline: true });
}
