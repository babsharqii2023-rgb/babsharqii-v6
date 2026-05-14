import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/v23/healing');
export const POST = createProxyHandler('/v23/healing');
