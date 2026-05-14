import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/a2ui/status');
export const POST = createProxyHandler('/a2ui/generate/section');
