import { NextRequest, NextResponse } from 'next/server';
import { callBackendJSON, isBackendAvailable } from '@/lib/backend';

// In-memory settings state (fallback when Python backend is unavailable)
const settingsState = {
  apiKeys: {
    glm: '',
    deepseek: '',
    gemini: '',
    wolfram: '',
  },
  defaultModel: 'glm-4-plus',
  language: 'ar' as 'ar' | 'en',
  timezone: 'Asia/Riyadh',
  availableModels: [
    { id: 'glm-4-plus', name: 'GLM-4 Plus', provider: 'glm' },
    { id: 'glm-4-flash', name: 'GLM-4 Flash', provider: 'glm' },
    { id: 'deepseek-chat', name: 'DeepSeek Chat', provider: 'deepseek' },
    { id: 'deepseek-reasoner', name: 'DeepSeek Reasoner', provider: 'deepseek' },
    { id: 'gemini-pro', name: 'Gemini Pro', provider: 'gemini' },
  ],
  availableTimezones: [
    'Asia/Riyadh',
    'Asia/Dubai',
    'Asia/Baghdad',
    'Asia/Cairo',
    'Africa/Casablanca',
    'Asia/Beirut',
    'Asia/Kuwait',
    'Asia/Muscat',
    'Africa/Tunis',
    'Africa/Algiers',
  ],
};

/**
 * Mask an API key for display
 * Shows first 4 and last 4 characters, masks the rest
 */
function maskApiKey(key: string): string {
  if (!key || key.length < 12) {
    return key ? '••••••••' : '';
  }
  // VULN-010 Fix: Show only first 3 chars + last 2 chars (not 4+4)
  return `${key.substring(0, 3)}${'•'.repeat(key.length - 5)}${key.substring(key.length - 2)}`;
}

/**
 * Build a masked-keys response from raw keys object
 */
function buildMaskedKeys(apiKeys: Record<string, string>) {
  return {
    glm: maskApiKey(apiKeys.glm || ''),
    deepseek: maskApiKey(apiKeys.deepseek || ''),
    gemini: maskApiKey(apiKeys.gemini || ''),
    wolfram: maskApiKey(apiKeys.wolfram || ''),
  };
}

/**
 * Build a keys-configured boolean map from raw keys
 */
function buildKeysConfigured(apiKeys: Record<string, string>) {
  return {
    glm: (apiKeys.glm || '').length > 0,
    deepseek: (apiKeys.deepseek || '').length > 0,
    gemini: (apiKeys.gemini || '').length > 0,
    wolfram: (apiKeys.wolfram || '').length > 0,
  };
}

export async function GET() {
  try {
    // Try fetching masked API keys from Python backend first
    let apiKeys: Record<string, string> = settingsState.apiKeys;
    let source = 'local';

    const backendUp = await isBackendAvailable();
    if (backendUp) {
      const backendData = await callBackendJSON<Record<string, unknown>>('/api/api-keys');
      if (backendData && typeof backendData === 'object') {
        // Backend returns masked keys — use them for display
        const masked = backendData.masked_keys || backendData.api_keys || backendData;
        if (masked && typeof masked === 'object') {
          // If backend already returns masked keys, use them directly
          apiKeys = masked as Record<string, string>;
          source = 'python_backend';
        }
      }
    }

    // If backend didn't provide keys, use local fallback
    const maskedKeys = source === 'python_backend'
      ? apiKeys
      : buildMaskedKeys(settingsState.apiKeys);

    const keysConfigured = source === 'python_backend'
      ? buildKeysConfigured(apiKeys)
      : buildKeysConfigured(settingsState.apiKeys);

    return NextResponse.json({
      apiKeys: maskedKeys,
      apiKeysConfigured: keysConfigured,
      defaultModel: settingsState.defaultModel,
      language: settingsState.language,
      timezone: settingsState.timezone,
      availableModels: settingsState.availableModels,
      availableTimezones: settingsState.availableTimezones,
      source,
    });
  } catch (error: any) {
    console.error('Settings GET Error:', error);
    return NextResponse.json(
      { error: 'فشل في جلب الإعدادات' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { apiKeys, defaultModel, language, timezone } = body;

    const updates: string[] = [];
    let apiKeysProxied = false;

    // Forward API keys to Python backend if available
    if (apiKeys && typeof apiKeys === 'object') {
      // Filter out masked keys (containing •) — only send real keys
      const realKeys: Record<string, string> = {};
      for (const [provider, key] of Object.entries(apiKeys)) {
        if (typeof key === 'string' && !key.includes('•') && provider in settingsState.apiKeys) {
          realKeys[provider] = key;
        }
      }

      if (Object.keys(realKeys).length > 0) {
        const backendUp = await isBackendAvailable();
        if (backendUp) {
          // Forward to Python backend
          const result = await callBackendJSON<{ success?: boolean }>('/api/api-keys', {
            method: 'PUT',
            body: JSON.stringify({ keys: realKeys }),
          });
          if (result) {
            apiKeysProxied = true;
            updates.push('مفاتيح API (خلفية)');
          }
        }

        // Also store locally as fallback (so settings still work without backend)
        for (const [provider, key] of Object.entries(realKeys)) {
          if (provider in settingsState.apiKeys) {
            (settingsState.apiKeys as Record<string, string>)[provider] = key;
            if (!apiKeysProxied) {
              updates.push(`مفتاح ${provider}`);
            }
          }
        }
      }
    }

    // Update default model
    if (defaultModel && typeof defaultModel === 'string') {
      const modelExists = settingsState.availableModels.some((m) => m.id === defaultModel);
      if (modelExists) {
        settingsState.defaultModel = defaultModel;
        updates.push('النموذج الافتراضي');
      }
    }

    // Update language
    if (language && (language === 'ar' || language === 'en')) {
      settingsState.language = language;
      updates.push('اللغة');
    }

    // Update timezone
    if (timezone && typeof timezone === 'string') {
      const tzExists = settingsState.availableTimezones.includes(timezone);
      if (tzExists) {
        settingsState.timezone = timezone;
        updates.push('المنطقة الزمنية');
      }
    }

    return NextResponse.json({
      success: true,
      message: updates.length > 0
        ? `تم تحديث: ${updates.join('، ')}`
        : 'لم يتم تحديث أي إعدادات',
      settings: {
        defaultModel: settingsState.defaultModel,
        language: settingsState.language,
        timezone: settingsState.timezone,
        apiKeysConfigured: buildKeysConfigured(settingsState.apiKeys),
        apiKeysProxied,
      },
    });
  } catch (error: any) {
    console.error('Settings POST Error:', error);
    return NextResponse.json(
      { error: 'فشل في حفظ الإعدادات' },
      { status: 500 }
    );
  }
}
