import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/capabilities/browser/navigate');
export const POST = createProxyHandler('/capabilities/browser/action');
