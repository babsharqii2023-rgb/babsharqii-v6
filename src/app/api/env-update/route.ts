import { NextRequest, NextResponse } from 'next/server';
import { writeFile, readFile } from 'fs/promises';
import { join } from 'path';

/**
 * POST /api/env-update
 * Writes API keys directly to backend/.env file
 * Called from the Settings page
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { envVars } = body as { envVars: Record<string, string> };

    if (!envVars || typeof envVars !== 'object' || Object.keys(envVars).length === 0) {
      return NextResponse.json({ error: 'لا توجد متغيرات للتحديث' }, { status: 400 });
    }

    const envPath = join(process.cwd(), '..', 'backend', '.env');

    // Read existing .env
    let envContent = '';
    try {
      envContent = await readFile(envPath, 'utf-8');
    } catch {
      envContent = '';
    }

    // Update each variable
    const updatedKeys: string[] = [];
    for (const [key, value] of Object.entries(envVars)) {
      if (!value || typeof value !== 'string') continue;

      const escapedValue = value.includes(' ') || value.includes('"') ? `"${value.replace(/"/g, '\\"')}"` : value;

      const regex = new RegExp(`^${key}=.*$`, 'm');
      if (regex.test(envContent)) {
        envContent = envContent.replace(regex, `${key}=${escapedValue}`);
        updatedKeys.push(key);
      } else {
        envContent += `\n${key}=${escapedValue}`;
        updatedKeys.push(key);
      }
    }

    // Write back
    await writeFile(envPath, envContent, 'utf-8');

    return NextResponse.json({
      success: true,
      message: `تم تحديث ${updatedKeys.length} مفتاح في ملف .env`,
      updatedKeys,
    });
  } catch (error: any) {
    console.error('Env update error:', error);
    return NextResponse.json(
      { error: `فشل في تحديث ملف .env: ${error.message}` },
      { status: 500 }
    );
  }
}

/**
 * GET /api/env-update
 * Returns the current .env keys status (masked)
 */
export async function GET() {
  try {
    const envPath = join(process.cwd(), '..', 'backend', '.env');
    let envContent = '';
    try {
      envContent = await readFile(envPath, 'utf-8');
    } catch {
      return NextResponse.json({ error: 'ملف .env غير موجود' }, { status: 404 });
    }

    const keyPattern = /^(MAMOUN_GITHUB_TOKEN|MAMOUN_LLM_API_KEY|DEEPSEEK_API_KEY|GEMINI_API_KEY|WOLFRAM_API_KEY|OPENAI_API_KEY|MAMOUN_GITHUB_REPO|MAMOUN_GITHUB_BRANCH|MAMOUN_AUTO_UPDATE_INTERVAL)=(.*)$/gm;
    const keyStatus: Record<string, { configured: boolean; masked: string }> = {};
    let match;

    while ((match = keyPattern.exec(envContent)) !== null) {
      const keyName = match[1];
      const keyValue = match[2].replace(/^["']|["']$/g, '');
      keyStatus[keyName] = {
        configured: keyValue.length > 0 && !keyValue.startsWith('your_') && !keyValue.startsWith('xxx'),
        masked: keyValue.length > 8
          ? `${keyValue.substring(0, 3)}${'•'.repeat(keyValue.length - 5)}${keyValue.substring(keyValue.length - 2)}`
          : keyValue ? '••••' : '',
      };
    }

    return NextResponse.json({ keyStatus });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
