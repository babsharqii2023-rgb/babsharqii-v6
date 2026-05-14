import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = 'http://localhost:8000/api';

async function proxyRequest(request: NextRequest, method: string) {
  try {
    const pathSegments = request.nextUrl.pathname
      .replace('/api/mamoun/', '')
      .replace('/api/mamoun', '');
    
    const searchParams = request.nextUrl.searchParams.toString();
    const url = `${BACKEND_URL}/${pathSegments}${searchParams ? `?${searchParams}` : ''}`;

    const headers: HeadersInit = {};
    request.headers.forEach((value, key) => {
      if (!['host', 'connection', 'content-length'].includes(key.toLowerCase())) {
        headers[key] = value;
      }
    });

    const fetchOptions: RequestInit = {
      method,
      headers,
      signal: AbortSignal.timeout(30000),
    };

    if (method !== 'GET' && method !== 'HEAD') {
      const body = await request.text();
      if (body) {
        fetchOptions.body = body;
      }
    }

    const response = await fetch(url, fetchOptions);

    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      if (!['transfer-encoding', 'connection'].includes(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    });

    const data = await response.arrayBuffer();
    return new NextResponse(data, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Proxy error';
    const isTimeout = message.includes('timeout') || message.includes('abort');
    return NextResponse.json(
      { error: isTimeout ? 'Backend timeout' : 'Backend unavailable', details: message },
      { status: isTimeout ? 504 : 502 }
    );
  }
}

export async function GET(request: NextRequest) {
  return proxyRequest(request, 'GET');
}

export async function POST(request: NextRequest) {
  return proxyRequest(request, 'POST');
}

export async function PUT(request: NextRequest) {
  return proxyRequest(request, 'PUT');
}

export async function PATCH(request: NextRequest) {
  return proxyRequest(request, 'PATCH');
}

export async function DELETE(request: NextRequest) {
  return proxyRequest(request, 'DELETE');
}
