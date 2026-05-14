import { createProxyHandler } from '@/lib/backend-proxy';
export const POST = createProxyHandler('/capabilities/instagram/analyze');
