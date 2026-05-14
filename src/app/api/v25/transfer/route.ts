import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/v25/transfer');
export const POST = createProxyHandler('/v25/transfer');
