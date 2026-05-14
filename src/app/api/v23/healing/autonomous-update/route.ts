import { createProxyHandler } from '@/lib/backend-proxy';
export const POST = createProxyHandler('/v23/healing/autonomous-update');
