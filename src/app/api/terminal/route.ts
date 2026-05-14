import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/terminal/status');
export const POST = createProxyHandler('/terminal/execute');
