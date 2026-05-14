// ═══════════════════════════════════════════════════════════════════
// BABSHARQII v41.0 — Unified Key Manager (shared between routes)
// ═══════════════════════════════════════════════════════════════════

export const BRAIN_KEY_MAP: Record<string, string> = {
  neural: 'GLM_API_KEY',
  causal: 'DEEPSEEK_API_KEY',
  symbolic: 'GLM_API_KEY',
  bayesian: 'GEMINI_API_KEY',
  worldmodel: 'DEEPSEEK_API_KEY',
};

export const BRAIN_NAMES: Record<string, string> = {
  neural: 'العصبي (GLM-5.1)',
  causal: 'السببي (DeepSeek-Reasoner)',
  symbolic: 'الرمزي (GLM-4-Plus)',
  bayesian: 'الاحتمالي (Gemini-2.0-Flash)',
  worldmodel: 'نموذج العالم (DeepSeek-Chat)',
};

export const EXTRA_KEYS = ['GEMINI_PROXY_URL', 'MAMOUN_GITHUB_TOKEN', 'MAMOUN_ADMIN_PASSWORD'];

export interface KeyStore {
  keys: Record<string, string>;
  gemini_proxy_url?: string;
  github_token?: string;
  admin_password?: string;
  updatedAt: string;
}

export function maskKey(key: string): string {
  if (!key) return '';
  if (key.length <= 8) return '•••';
  return `${key.slice(0, 4)}•••${key.slice(-4)}`;
}
