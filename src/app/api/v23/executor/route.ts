import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/v23/executor');
export const POST = createProxyHandler('/v23/executor');
