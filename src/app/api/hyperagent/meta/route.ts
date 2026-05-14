import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/hyperagent/meta/status');
