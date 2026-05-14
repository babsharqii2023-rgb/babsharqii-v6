import { createProxyHandler } from '@/lib/backend-proxy';
export const POST = createProxyHandler('/terminal/approvals/{approval_id}/approve');
