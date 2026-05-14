/**
 * BABSHARQII v41.0 — API Key Test Route
 * اختبار حقيقي لمفاتيح API — يتصل فعلياً بالمزود
 */
import { NextRequest, NextResponse } from 'next/server';

interface ProviderTest {
  minLength: number;
  message: string;
  testUrl: string;
  testMethod: string;
  buildHeaders: (key: string) => Record<string, string>;
  buildBody?: () => string;
  validateResponse: (data: any, status: number) => boolean;
}

const PROVIDER_TESTS: Record<string, ProviderTest> = {
  glm: {
    minLength: 20,
    message: 'مفتاح GLM',
    testUrl: 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    testMethod: 'POST',
    buildHeaders: (key) => ({
      'Authorization': `Bearer ${key}`,
      'Content-Type': 'application/json',
    }),
    buildBody: () => JSON.stringify({
      model: 'glm-4-flash',
      messages: [{ role: 'user', content: 'test' }],
      max_tokens: 1,
    }),
    validateResponse: (data, status) => status === 200 || (status === 400 && data?.error?.message !== 'Invalid API key'),
  },
  deepseek: {
    minLength: 20,
    message: 'مفتاح DeepSeek',
    testUrl: 'https://api.deepseek.com/v1/chat/completions',
    testMethod: 'POST',
    buildHeaders: (key) => ({
      'Authorization': `Bearer ${key}`,
      'Content-Type': 'application/json',
    }),
    buildBody: () => JSON.stringify({
      model: 'deepseek-chat',
      messages: [{ role: 'user', content: 'test' }],
      max_tokens: 1,
    }),
    validateResponse: (data, status) => status === 200 || (status === 400 && data?.error?.message !== 'Invalid API key'),
  },
  gemini: {
    minLength: 20,
    message: 'مفتاح Gemini',
    testUrl: 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent',
    testMethod: 'POST',
    buildHeaders: () => ({ 'Content-Type': 'application/json' }),
    buildBody: () => JSON.stringify({ contents: [{ parts: [{ text: 'test' }] }] }),
    validateResponse: (data, status) => status === 200,
  },
};

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { provider, key } = body;

    if (!provider || !key) {
      return NextResponse.json(
        { success: false, message: 'مطلوب: المزود والمفتاح' },
        { status: 400 }
      );
    }

    const testConfig = PROVIDER_TESTS[provider];
    if (!testConfig) {
      return NextResponse.json(
        { success: false, message: `مزود غير معروف: ${provider}` },
        { status: 400 }
      );
    }

    // Basic format validation
    if (key.length < testConfig.minLength) {
      return NextResponse.json({
        success: false,
        message: `${testConfig.message} قصير جداً — يتطلب ${testConfig.minLength} حرف على الأقل`,
      });
    }

    // Real API connection test
    try {
      const fetchOptions: RequestInit = {
        method: testConfig.testMethod,
        headers: testConfig.buildHeaders(key),
        signal: AbortSignal.timeout(10000),
      };

      // Add query param for Gemini (key in URL)
      let testUrl = testConfig.testUrl;
      if (provider === 'gemini') {
        testUrl = `${testUrl}?key=${key}`;
      }

      if (testConfig.buildBody) {
        fetchOptions.body = testConfig.buildBody();
      }

      const res = await fetch(testUrl, fetchOptions);
      const data = await res.json().catch(() => ({}));

      if (testConfig.validateResponse(data, res.status)) {
        return NextResponse.json({
          success: true,
          message: `تم التحقق من ${testConfig.message} بنجاح — الاتصال يعمل`,
          status_code: res.status,
        });
      }

      // Key is invalid or API returned error
      const errorMsg = data?.error?.message || data?.message || `خطأ من المزود (HTTP ${res.status})`;
      return NextResponse.json({
        success: false,
        message: `${testConfig.message} غير صالح — ${errorMsg}`,
        status_code: res.status,
      });
    } catch (fetchError: any) {
      // Network error — key might still be valid but provider unreachable
      const isTimeout = fetchError?.name === 'TimeoutError';
      return NextResponse.json({
        success: false,
        message: isTimeout
          ? `${testConfig.message} — انتهت مهلة الاتصال بالمزود`
          : `${testConfig.message} — لا يمكن الوصول للمزود حالياً`,
        network_error: true,
      });
    }
  } catch (error) {
    console.error('Key Test Error:', error);
    return NextResponse.json(
      { success: false, message: 'فشل في اختبار المفتاح' },
      { status: 500 }
    );
  }
}
