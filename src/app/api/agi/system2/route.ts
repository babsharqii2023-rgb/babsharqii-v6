import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/system2/stats');
export const POST = createProxyHandler('/system2/reason');
