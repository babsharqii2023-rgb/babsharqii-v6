// =============================================================================
// Next.js Middleware — Security headers, rate limiting, and request validation
// =============================================================================
import { NextRequest, NextResponse } from 'next/server';

// Simple in-memory rate limiter
const rateLimitMap = new Map<string, { count: number; resetTime: number }>();
const RATE_LIMIT_WINDOW = 60_000; // 1 minute
const RATE_LIMIT_MAX = 100; // requests per window

function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  const entry = rateLimitMap.get(ip);

  if (!entry || now > entry.resetTime) {
    rateLimitMap.set(ip, { count: 1, resetTime: now + RATE_LIMIT_WINDOW });
    return true;
  }

  entry.count++;
  return entry.count <= RATE_LIMIT_MAX;
}

// Clean up old entries periodically
if (typeof setInterval !== 'undefined') {
  setInterval(() => {
    const now = Date.now();
    for (const [key, entry] of rateLimitMap.entries()) {
      if (now > entry.resetTime) {
        rateLimitMap.delete(key);
      }
    }
  }, RATE_LIMIT_WINDOW);
}

export function middleware(request: NextRequest) {
  const response = NextResponse.next();

  // ── Security Headers ──────────────────────────────────────────────
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set(
    'Content-Security-Policy',
    "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https://z-cdn.chatglm.cn; connect-src 'self' http://localhost:* https:; frame-ancestors 'none';"
  );
  response.headers.set(
    'Strict-Transport-Security',
    'max-age=31536000; includeSubDomains'
  );
  response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');

  // ── Rate Limiting for API Routes ──────────────────────────────────
  if (request.nextUrl.pathname.startsWith('/api/')) {
    const clientIp =
      request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
      request.headers.get('x-real-ip') ||
      'unknown';

    if (!checkRateLimit(clientIp)) {
      return NextResponse.json(
        { error: 'Rate limit exceeded', retryAfter: RATE_LIMIT_WINDOW / 1000 },
        {
          status: 429,
          headers: {
            'Retry-After': String(RATE_LIMIT_WINDOW / 1000),
            'X-RateLimit-Limit': String(RATE_LIMIT_MAX),
          },
        }
      );
    }

    response.headers.set('X-RateLimit-Limit', String(RATE_LIMIT_MAX));
    response.headers.set(
      'X-RateLimit-Remaining',
      String(RATE_LIMIT_MAX - (rateLimitMap.get(clientIp)?.count || 0))
    );
  }

  // ── Block suspicious request patterns ─────────────────────────────
  const url = request.nextUrl.pathname;
  if (url.includes('..') || url.includes('\\') || url.includes('//')) {
    return NextResponse.json({ error: 'Invalid URL' }, { status: 400 });
  }

  return response;
}

export const config = {
  matcher: [
    '/api/:path*',
    '/((?!_next/static|_next/image|favicon.ico|robots.txt|logo.svg).*)',
  ],
};
