import { createProxyHandler } from '@/lib/backend-proxy';
export const POST = createProxyHandler('/capabilities/blender/control');
