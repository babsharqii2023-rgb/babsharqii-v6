import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/terminal/git/status');
export const POST = createProxyHandler('/terminal/git/push');
