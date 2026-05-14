import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/hyperagent/status');
export const POST = createProxyHandler('/hyperagent/cycle');
