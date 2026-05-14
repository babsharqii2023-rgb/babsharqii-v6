import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/agi/plan');
export const POST = createProxyHandler('/agi/plan');
