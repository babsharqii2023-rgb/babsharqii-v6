import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/capabilities/terminal/status');
export const POST = createProxyHandler('/capabilities/terminal/execute');
