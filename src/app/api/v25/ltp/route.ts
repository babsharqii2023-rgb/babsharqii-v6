import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/v25/ltp');
export const POST = createProxyHandler('/v25/ltp');
