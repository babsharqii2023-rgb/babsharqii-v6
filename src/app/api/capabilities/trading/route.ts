import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/capabilities/trading/overview');
export const POST = createProxyHandler('/capabilities/trading/action');
