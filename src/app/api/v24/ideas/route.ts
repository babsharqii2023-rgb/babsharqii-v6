import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/v24/ideas');
export const POST = createProxyHandler('/v24/ideas');
