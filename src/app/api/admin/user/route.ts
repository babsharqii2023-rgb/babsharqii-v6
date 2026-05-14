import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/user/data-summary');
