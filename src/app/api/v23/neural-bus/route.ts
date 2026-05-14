import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/v23/neural-bus');
export const POST = createProxyHandler('/v23/neural-bus');
