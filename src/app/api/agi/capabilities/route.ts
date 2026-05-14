import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/agi/capabilities');
export const POST = createProxyHandler('/agi/capabilities');
