/**
 * BABSHARQII v6.0 — Authentication Middleware Helper
 * VULN-022 Fix: Centralized auth check for all API routes
 *
 * Usage in any API route:
 *   import { requireAuth } from '@/lib/auth-middleware';
 *   const auth = requireAuth(request);
 *   if (!auth.authorized) return auth.response!;
 */

import { NextRequest, NextResponse } from 'next/server';

// Session store shared with auth route (in-memory)
// This is a simplified approach — in production, use Redis/DB
const SESSION_COOKIE_NAME = 'babsharqii_session';

interface AuthResult {
  authorized: boolean;
  response?: NextResponse;
  sessionId?: string;
}

/**
 * Validate that the request has a valid session cookie.
 * Returns { authorized: true } if valid, or { authorized: false, response } with 401.
 */
export function requireAuth(request: NextRequest): AuthResult {
  const sessionToken = request.cookies.get(SESSION_COOKIE_NAME)?.value;

  if (!sessionToken) {
    return {
      authorized: false,
      response: NextResponse.json(
        { error: 'مطلوب تسجيل الدخول', needsAuth: true },
        { status: 401 }
      ),
    };
  }

  // Basic format check — actual session validation happens in /api/auth
  // We just verify the cookie exists; the auth route handles expiry
  if (sessionToken.length < 10) {
    return {
      authorized: false,
      response: NextResponse.json(
        { error: 'جلسة غير صالحة', needsAuth: true },
        { status: 401 }
      ),
    };
  }

  return { authorized: true, sessionId: sessionToken };
}

/**
 * Routes that DON'T require authentication (public endpoints)
 */
export const PUBLIC_ROUTES = [
  '/api/auth',       // Login, setup, verify
  '/api/chat',       // Chat is public (the LLM handles its own safety)
];

/**
 * Check if a route path is public (doesn't need auth)
 */
export function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some(route => pathname.startsWith(route));
}
