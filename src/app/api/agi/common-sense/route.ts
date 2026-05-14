import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/common-sense/rules');
export const POST = createProxyHandler('/common-sense/filter');
