import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/agi/causal');
export const POST = createProxyHandler('/agi/causal');
