import { createProxyRoute } from '@/lib/backend-proxy';
export const { GET, POST } = createProxyRoute('/v2/command');
