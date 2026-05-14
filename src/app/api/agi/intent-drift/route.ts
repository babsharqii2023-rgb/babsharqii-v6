import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/intent-drift/report');
export const POST = createProxyHandler('/intent-drift/track');
