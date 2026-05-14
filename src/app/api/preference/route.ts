import { createProxyHandler } from '@/lib/backend-proxy';
export const GET = createProxyHandler('/preference/status');
export const POST = createProxyHandler('/preference/feedback');
