import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/v24/self-modify');
export const POST = createProxyHandler('/v24/self-modify');
