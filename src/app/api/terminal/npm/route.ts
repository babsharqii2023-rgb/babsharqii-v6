import { createProxyHandler } from '@/lib/backend-proxy';
export const POST = createProxyHandler('/terminal/npm/build');
