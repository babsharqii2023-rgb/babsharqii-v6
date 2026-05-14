import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/living/status');
export const POST = createProxyHandler('/living/event');
