import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/v25/cwm');
export const POST = createProxyHandler('/v25/cwm');
