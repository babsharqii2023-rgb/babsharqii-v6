import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/agi/uncertainty');
export const POST = createProxyHandler('/agi/uncertainty');
