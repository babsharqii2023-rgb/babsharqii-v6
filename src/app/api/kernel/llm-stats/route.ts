import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/kernel/llm-stats');
