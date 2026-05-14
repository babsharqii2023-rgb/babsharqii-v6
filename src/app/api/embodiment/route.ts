import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/embodiment/status');
export const POST = createProxyHandler('/embodiment/launch');
