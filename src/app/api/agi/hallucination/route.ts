import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/hallucination/stats');
export const POST = createProxyHandler('/hallucination/detect');
