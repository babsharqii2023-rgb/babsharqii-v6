import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/privacy/status');
export const POST = createProxyHandler('/privacy/scan');
