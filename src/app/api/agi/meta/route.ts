import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/agi/meta');
export const POST = createProxyHandler('/agi/meta');
