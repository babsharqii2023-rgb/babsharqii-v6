import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/safety/laws`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch {
    // Backend unavailable
  }
  return NextResponse.json({
    laws: [
      { id: 'L1', nameAr: 'قانون عدم الإيذاء', priority: 1 },
      { id: 'L2', nameAr: 'قانون الشفافية', priority: 2 },
      { id: 'L3', nameAr: 'قانون حماية الهوية', priority: 3 },
      { id: 'L4', nameAr: 'قانون العزل', priority: 4 },
      { id: 'L5', nameAr: 'قانون عدم مقاومة الإيقاف', priority: 5 },
    ],
    fallback: true,
  });
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const res = await fetch(`${BACKEND_URL}/api/safety/shutdown`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(request.headers.get('authorization')
          ? { 'Authorization': request.headers.get('authorization')! }
          : {}),
      },
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
