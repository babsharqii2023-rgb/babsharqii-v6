import { NextResponse } from 'next/server';
import { execSync } from 'child_process';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import { BRAIN_KEY_MAP, BRAIN_NAMES, EXTRA_KEYS, type KeyStore } from '@/lib/key-manager';

const PROJECT_ROOT = process.cwd();
const FRONTEND_ENV_PATH = join(PROJECT_ROOT, '.env.local');
const BACKEND_ENV_PATH = join(PROJECT_ROOT, 'backend', '.env');
const KEYS_JSON_PATH = join(PROJECT_ROOT, '.keys.json');

function readEnvFile(path: string): Record<string, string> {
  const result: Record<string, string> = {};
  if (!existsSync(path)) return result;
  try {
    const content = readFileSync(path, 'utf-8');
    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const eqIndex = trimmed.indexOf('=');
      if (eqIndex > 0) {
        result[trimmed.slice(0, eqIndex).trim()] = trimmed.slice(eqIndex + 1).trim();
      }
    }
  } catch { /* */ }
  return result;
}

function writeEnvFile(path: string, updates: Record<string, string>, managedKeys: string[]) {
  const existing = readEnvFile(path);
  const merged = { ...existing, ...updates };
  for (const key of managedKeys) { if (!merged[key]) delete merged[key]; }
  const lines = [`# BABSHARQII v41.0 — Auto-generated`, `# Updated: ${new Date().toISOString()}`, ``];
  for (const [key, value] of Object.entries(merged)) { lines.push(`${key}=${value}`); }
  try {
    const dir = join(path, '..');
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    writeFileSync(path, lines.join('\n') + '\n', 'utf-8');
  } catch { /* */ }
}

export async function POST() {
  const store: KeyStore = existsSync(KEYS_JSON_PATH)
    ? JSON.parse(readFileSync(KEYS_JSON_PATH, 'utf-8'))
    : { keys: {}, updatedAt: new Date().toISOString() };

  const allEnvKeys = [...new Set([...Object.values(BRAIN_KEY_MAP), ...EXTRA_KEYS])];
  const envUpdates: Record<string, string> = {};
  const distributed: string[] = [];

  for (const [brainId, apiKey] of Object.entries(store.keys)) {
    if (!apiKey || apiKey === '(محفوظ)' || apiKey.includes('•')) continue;
    const envVar = BRAIN_KEY_MAP[brainId];
    if (envVar) envUpdates[envVar] = apiKey;
  }
  if (store.gemini_proxy_url && store.gemini_proxy_url !== '(محفوظ)') envUpdates['GEMINI_PROXY_URL'] = store.gemini_proxy_url;
  if (store.github_token && store.github_token !== '(محفوظ)') envUpdates['MAMOUN_GITHUB_TOKEN'] = store.github_token;
  if (store.admin_password && store.admin_password !== '(محفوظ)') envUpdates['MAMOUN_ADMIN_PASSWORD'] = store.admin_password;

  distributed.push('.keys.json');
  const fe: Record<string, string> = { ...envUpdates };
  for (const [k, v] of Object.entries(envUpdates)) { fe[`NEXT_PUBLIC_${k}`] = v; }
  writeEnvFile(FRONTEND_ENV_PATH, fe, [...allEnvKeys, ...allEnvKeys.map(k => `NEXT_PUBLIC_${k}`)]);
  distributed.push('.env.local');
  writeEnvFile(BACKEND_ENV_PATH, envUpdates, allEnvKeys);
  distributed.push('backend/.env');
  for (const [k, v] of Object.entries(envUpdates)) { process.env[k] = v; process.env[`NEXT_PUBLIC_${k}`] = v; }
  distributed.push('process.env');

  let backendReloaded = false;
  try {
    const backendUrl = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';
    const result = execSync(`curl -s -X POST ${backendUrl}/api/v2/api-keys/reload --max-time 5 2>/dev/null || echo '{"success":false}'`, { encoding: 'utf-8', timeout: 8000 });
    backendReloaded = !!JSON.parse(result.trim()).success;
  } catch { /* */ }

  let active = 0;
  const activeBrains: string[] = [];
  for (const [brainId, key] of Object.entries(store.keys)) {
    if (key) { active++; activeBrains.push(brainId); }
  }

  const brainNamesStr = activeBrains.map(id => BRAIN_NAMES[id] || id).join('، ');

  return NextResponse.json({
    success: true,
    active_brains: active,
    distributed_to: distributed,
    backend_reloaded: backendReloaded,
    message: `✅ تم إعادة تحميل وتوزيع المفاتيح — ${active}/5 أدمغة نشطة: ${brainNamesStr || 'لا توجد مفاتيح'}`,
  });
}
