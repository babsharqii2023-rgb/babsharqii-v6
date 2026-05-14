import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/awareness/state');
