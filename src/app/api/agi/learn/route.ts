import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/agi/learn');
export const POST = createProxyHandler('/agi/learn');
