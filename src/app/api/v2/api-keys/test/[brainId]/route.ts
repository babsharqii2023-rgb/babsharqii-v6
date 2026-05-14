import { NextRequest, NextResponse } from 'next/server';
import { execSync } from 'child_process';
import { BRAIN_KEY_MAP, maskKey } from '@/lib/key-manager';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

function readKeyStore() {
  const path = join(process.cwd(), '.keys.json');
  if (!existsSync(path)) return { keys: {} };
  try { return JSON.parse(readFileSync(path, 'utf-8')); } catch { return { keys: {} }; }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ brainId: string }> }
) {
  const { brainId } = await params;

  if (!BRAIN_KEY_MAP[brainId]) {
    return NextResponse.json({ brain_id: brainId, status: 'unknown', message: 'دماغ غير معروف' }, { status: 404 });
  }

  const envVar = BRAIN_KEY_MAP[brainId];
  const store = readKeyStore();
  const key = store.keys[brainId] || process.env[envVar] || '';

  if (!key) {
    return NextResponse.json({ brain_id: brainId, status: 'missing_key', message: 'لا يوجد مفتاح — أدخل المفتاح أولاً ثم اضغط حفظ' });
  }

  try {
    let testCmd = '';

    if (envVar === 'GLM_API_KEY') {
      testCmd = `curl -s -o /dev/null -w "%{http_code}" -X POST https://open.bigmodel.cn/api/paas/v4/chat/completions -H "Authorization: Bearer ${key}" -H "Content-Type: application/json" -d '{"model":"glm-4-flash","messages":[{"role":"user","content":"test"}],"max_tokens":1}' --max-time 15 2>/dev/null`;
    } else if (envVar === 'DEEPSEEK_API_KEY') {
      testCmd = `curl -s -o /dev/null -w "%{http_code}" -X POST https://api.deepseek.com/chat/completions -H "Authorization: Bearer ${key}" -H "Content-Type: application/json" -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"test"}],"max_tokens":1}' --max-time 15 2>/dev/null`;
    } else if (envVar === 'GEMINI_API_KEY') {
      const proxy = process.env.GEMINI_PROXY_URL || store.gemini_proxy_url || '';
      if (proxy) {
        testCmd = `curl -s -o /dev/null -w "%{http_code}" -X POST ${proxy}/v1/chat/completions -H "Authorization: Bearer ${key}" -H "Content-Type: application/json" -d '{"model":"gemini-2.0-flash","messages":[{"role":"user","content":"test"}],"max_tokens":1}' --max-time 15 2>/dev/null`;
      } else {
        testCmd = `curl -s -o /dev/null -w "%{http_code}" "https://generativelanguage.googleapis.com/v1beta/models?key=${key}" --max-time 10 2>/dev/null`;
      }
    }

    if (!testCmd) {
      return NextResponse.json({ brain_id: brainId, status: 'unknown', message: 'مزود غير معروف' });
    }

    const httpCode = parseInt(execSync(testCmd, { encoding: 'utf-8', timeout: 20000 }).trim());

    if (httpCode === 200 || httpCode === 201) {
      return NextResponse.json({ brain_id: brainId, status: 'valid', message: '✅ المفتاح صالح ويعمل', key_masked: maskKey(key) });
    } else if (httpCode === 401 || httpCode === 403) {
      return NextResponse.json({ brain_id: brainId, status: 'invalid', message: '❌ المفتاح غير صالح — تحقق من صحته' });
    } else {
      return NextResponse.json({ brain_id: brainId, status: 'error', message: `⚠️ استجابة غير متوقعة: HTTP ${httpCode}` });
    }
  } catch {
    return NextResponse.json({ brain_id: brainId, status: 'error', message: '⚠️ خطأ في الاتصال — تحقق من الإنترنت' });
  }
}
