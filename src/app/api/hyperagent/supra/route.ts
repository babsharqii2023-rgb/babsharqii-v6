import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/hyperagent/supra/status');
export const POST = createProxyHandler('/hyperagent/supra/evaluate');
