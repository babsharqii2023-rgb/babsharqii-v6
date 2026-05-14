import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/agi/status');
export const POST = createProxyHandler('/agi/status');
