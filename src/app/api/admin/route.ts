import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/db-status');
export const POST = createProxyHandler('/backup/create');
