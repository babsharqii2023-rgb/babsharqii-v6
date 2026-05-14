import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/agi/memory');
export const POST = createProxyHandler('/agi/memory');
