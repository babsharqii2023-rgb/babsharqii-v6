import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/backup/list');
export const POST = createProxyHandler('/backup/restore');
