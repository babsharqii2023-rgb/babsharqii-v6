import { createProxyRoute } from '@/lib/backend-proxy';
export const { GET } = createProxyRoute('/v2/events/connection-status');
