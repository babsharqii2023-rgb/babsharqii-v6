import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/fluid-reasoner/stats');
export const POST = createProxyHandler('/fluid-reasoner/think');
