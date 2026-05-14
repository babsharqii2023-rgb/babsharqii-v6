import { NextRequest, NextResponse } from 'next/server';
import { writeFile, readFile } from 'fs/promises';
import { join } from 'path';

// ═══ Correct env variable names matching backend/.env ═══
const PROVIDER_ENV_MAP: Record<string, string> = {
  glm: 'GLM_API_KEY',
  deepseek: 'DEEPSEEK_API_KEY',
  gemini: 'GEMINI_API_KEY',
};

// Also update the GEMINI_API_URL when Gemini key changes
function buildGeminiUrl(key: string): string {
  return `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${key}`;
}

/**
 * GET /api/api-keys
 * Returns current API key status (masked) from backend/.env
 */
export async function GET() {
  try {
    const envPath = join(process.cwd(), '..', 'backend', '.env');
    let envContent = '';
    try {
      envContent = await readFile(envPath, 'utf-8');
    } catch {
      // No .env file yet
    }

    const keys: Array<{ provider: string; masked?: string; configured: boolean }> = [];
    const configured: Record<string, boolean> = {};

    for (const [provider, envKey] of Object.entries(PROVIDER_ENV_MAP)) {
      const regex = new RegExp(`^${envKey}=(.*)$`, 'm');
      const match = regex.exec(envContent);
      const rawValue = match ? match[1].replace(/^["']|["']$/g, '').trim() : '';
      const isConfigured = rawValue.length > 0 && !rawValue.startsWith('your_') && !rawValue.startsWith('xxx');

      const masked = rawValue.length > 8
        ? `${rawValue.substring(0, 4)}${'•'.repeat(Math.min(rawValue.length - 6, 12))}${rawValue.substring(rawValue.length - 2)}`
        : rawValue ? '••••' : undefined;

      keys.push({ provider, masked: isConfigured ? masked : undefined, configured: isConfigured });
      configured[provider] = isConfigured;
    }

    return NextResponse.json({ keys, configured });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

/**
 * POST /api/api-keys
 * Saves an API key to backend/.env — propagates to the entire system
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { provider, key } = body as { provider: string; key: string };

    if (!provider) {
      return NextResponse.json({ error: 'مطلوب: المزود' }, { status: 400 });
    }

    const envKey = PROVIDER_ENV_MAP[provider];
    if (!envKey) {
      return NextResponse.json({ error: `مزود غير معروف: ${provider}` }, { status: 400 });
    }

    const envPath = join(process.cwd(), '..', 'backend', '.env');

    // Read existing .env
    let envContent = '';
    try {
      envContent = await readFile(envPath, 'utf-8');
    } catch {
      envContent = '';
    }

    if (!key || key.trim() === '') {
      // Remove the key (set to empty)
      const regex = new RegExp(`^${envKey}=.*$`, 'm');
      if (regex.test(envContent)) {
        envContent = envContent.replace(regex, `${envKey}=`);
      } else {
        envContent += `\n${envKey}=`;
      }
    } else {
      // Set the key
      const escapedValue = key.includes(' ') || key.includes('"') ? `"${key.replace(/"/g, '\\"')}"` : key;
      const regex = new RegExp(`^${envKey}=.*$`, 'm');
      if (regex.test(envContent)) {
        envContent = envContent.replace(regex, `${envKey}=${escapedValue}`);
      } else {
        envContent += `\n${envKey}=${escapedValue}`;
      }

      // Auto-update GEMINI_API_URL when Gemini key is set
      if (provider === 'gemini') {
        const urlRegex = /^GEMINI_API_URL=.*$/m;
        const newUrl = `GEMINI_API_URL=${buildGeminiUrl(key)}`;
        if (urlRegex.test(envContent)) {
          envContent = envContent.replace(urlRegex, newUrl);
        } else {
          envContent += `\n${newUrl}`;
        }
      }
    }

    await writeFile(envPath, envContent, 'utf-8');

    return NextResponse.json({
      success: true,
      message: key ? `تم حفظ مفتاح ${provider.toUpperCase()} وتطبيقه على كامل النظام` : `تم حذف مفتاح ${provider.toUpperCase()}`,
    });
  } catch (error: any) {
    console.error('API Keys save error:', error);
    return NextResponse.json(
      { error: `فشل في حفظ المفتاح: ${error.message}` },
      { status: 500 }
    );
  }
}
