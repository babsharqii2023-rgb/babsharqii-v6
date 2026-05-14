import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/continual-learning/stats');
export const POST = createProxyHandler('/continual-learning/learn');
