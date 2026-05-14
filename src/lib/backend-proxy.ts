/**
 * BABSHARQII v31.2 — Universal Backend Proxy Utility
 * أداة البروكسي الشاملة — توصيل كل مسارات الفرونتند بالباكند
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

/**
 * Extract auth headers from a NextRequest — checks Authorization header first, then cookies.
 * يمكن استخدامها في أي route.ts تحتاج تمرير Auth
 */
export function getAuthHeaders(request: NextRequest): Record<string, string> {
  const headers: Record<string, string> = {};
  const authHeader = request.headers.get('authorization');
  if (authHeader) {
    headers['Authorization'] = authHeader;
  } else {
    const cookie = request.cookies.get('mamoun_auth_token')?.value
      || request.cookies.get('babsharqii_session')?.value;
    if (cookie) headers['Authorization'] = `Bearer ${cookie}`;
  }
  return headers;
}

/**
 * Create a proxy handler that forwards requests to the FastAPI backend.
 * Works for GET, POST, PUT, DELETE, PATCH.
 */
export function createProxyHandler(apiPath: string) {
  return async function proxyHandler(request: NextRequest) {
    const url = `${BACKEND_URL}/api${apiPath}`;
    const method = request.method;

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };

      // Forward auth header if present
      const authHeader = request.headers.get('authorization');
      if (authHeader) {
        headers['Authorization'] = authHeader;
      } else {
        // If no Authorization header in request, check for session cookies
        const sessionCookie = request.cookies.get('babsharqii_session')?.value
          || request.cookies.get('mamoun_auth_token')?.value;
        if (sessionCookie) {
          headers['Authorization'] = `Bearer ${sessionCookie}`;
        }
      }

      const fetchOptions: RequestInit = {
        method,
        headers,
        signal: AbortSignal.timeout(15000),
      };

      // Forward body for non-GET requests
      if (method !== 'GET' && method !== 'HEAD') {
        try {
          const body = await request.json();
          fetchOptions.body = JSON.stringify(body);
        } catch {
          // No body — that's fine
        }
      }

      const res = await fetch(url, fetchOptions);

      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data, {
          headers: { 'X-Data-Source': 'backend', 'X-Backend-Online': 'true' },
        });
      }

      return NextResponse.json(
        { error: 'Backend returned error', status: res.status, fallback: true },
        { status: res.status, headers: { 'X-Data-Source': 'fallback', 'X-Backend-Online': 'true' } }
      );
    } catch (error) {
      return NextResponse.json(
        { error: 'Backend unavailable', fallback: true },
        { status: 503, headers: { 'X-Data-Source': 'fallback', 'X-Backend-Online': 'false', 'Retry-After': '5' } }
      );
    }
  };
}

/**
 * Create a multi-method proxy with both GET and POST handlers.
 */
export function createProxyRoute(apiPath: string) {
  const handler = createProxyHandler(apiPath);
  return { GET: handler, POST: handler, PUT: handler, DELETE: handler, PATCH: handler };
}

/**
 * Specific proxy for streaming endpoints (SSE).
 */
export function createStreamProxy(apiPath: string) {
  return async function streamProxy(request: NextRequest) {
    const url = `${BACKEND_URL}/api${apiPath}`;
    try {
      const body = await request.json();
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(60000),
      });

      if (res.ok && res.body) {
        const stream = new ReadableStream({
          async start(controller) {
            const reader = res.body!.getReader();
            const decoder = new TextDecoder();
            const encoder = new TextEncoder();
            try {
              while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                controller.enqueue(encoder.encode(decoder.decode(value, { stream: true })));
              }
            } catch { /* stream ended */ }
            finally { controller.close(); }
          },
        });
        return new Response(stream, {
          headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' },
        });
      }
      return NextResponse.json({ error: 'Stream unavailable' }, { status: 503 });
    } catch {
      return NextResponse.json({ error: 'Backend unavailable' }, { status: 503 });
    }
  };
}
