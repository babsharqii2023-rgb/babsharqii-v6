import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/agi/world');
export const POST = createProxyHandler('/agi/world');
