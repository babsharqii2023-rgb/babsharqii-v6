import { createProxyHandler } from '@/lib/backend-proxy';
export const POST = createProxyHandler('/skill-discovery/discover');
