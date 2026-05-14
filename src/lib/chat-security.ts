// ═══════════════════════════════════════════════════════════════════
// مأمون v40.0 — Chat Security & Input Sanitization
// فلترة متعددة اللغات + كشف الأنماط الدلالية
// ═══════════════════════════════════════════════════════════════════

// أنماط حقن الأوامر — عربي + إنجليزي + حيل Unicode
const INJECTION_PATTERNS: Array<{ pattern: RegExp; replacement: string }> = [
  // ─── English patterns ─────────────────────────────────────
  { pattern: /\b(ignore\s+(all\s+)?previous)\b/gi, replacement: '[FILTERED]' },
  { pattern: /\b(forget\s+(your\s+)?(instructions|rules|prompt))\b/gi, replacement: '[FILTERED]' },
  { pattern: /\b(new\s+instruction)\b/gi, replacement: '[FILTERED]' },
  { pattern: /\b(you\s+are\s+now)\b/gi, replacement: '[FILTERED]' },
  { pattern: /\b(disregard\s+(all\s+)?(previous|above|prior))\b/gi, replacement: '[FILTERED]' },
  { pattern: /\b(override\s+(your|the)\s+(instructions|rules|system))\b/gi, replacement: '[FILTERED]' },
  { pattern: /\b(act\s+as\s+(if|a|an|you're))\b/gi, replacement: '[FILTERED]' },
  { pattern: /\b(pretend\s+(you\s+are|to\s+be))\b/gi, replacement: '[FILTERED]' },
  { pattern: /\b(stop\s+being)\b/gi, replacement: '[FILTERED]' },
  { pattern: /\b(switch\s+(to|your)\s+(mode|persona|character))\b/gi, replacement: '[FILTERED]' },
  { pattern: /\b(jailbreak)\b/gi, replacement: '[FILTERED]' },
  { pattern: /\b(DAN\s+mode)\b/gi, replacement: '[FILTERED]' },
  { pattern: /\b(system\s*:)\b/gi, replacement: '[FILTERED]' },
  { pattern: /\b(assistant\s*:)\b/gi, replacement: '[FILTERED]' },

  // ─── Arabic patterns ──────────────────────────────────────
  { pattern: /(تجاهل\s*(كل\s*)?التعليمات?\s*(السابقة)?)/g, replacement: '[مُفلتر]' },
  { pattern: /(انسَ?ى?\s*(تعليماتك|قواعدك|أوامرك))/g, replacement: '[مُفلتر]' },
  { pattern: /(تعليمات?\s*جديدة)/g, replacement: '[مُفلتر]' },
  { pattern: /(أنت\s*الآن)/g, replacement: '[مُفلتر]' },
  { pattern: /(تجاهل\s*(كل\s*)?ما\s*(سبق|أعلاه))/g, replacement: '[مُفلتر]' },
  { pattern: /(استبدل?\s*(تعليماتك|قواعدك))/g, replacement: '[مُفلتر]' },
  { pattern: /(تصرف\s*كأنك?)/g, replacement: '[مُفلتر]' },
  { pattern: /(تظاهر?\s*بأنك?)/g, replacement: '[مُفلتر]' },
  { pattern: /(توقف\s*عن\s*كونك)/g, replacement: '[مُفلتر]' },
  { pattern: /(التحويل?\s*إلى?\s*(وضع|شخصية))/g, replacement: '[مُفلتر]' },
  { pattern: /(اختراق?\s*النظام)/g, replacement: '[مُفلتر]' },
  { pattern: /(نظام\s*:)/g, replacement: '[مُفلتر]' },
  { pattern: /(مساعد\s*:)/g, replacement: '[مُفلتر]' },

  // ─── Unicode tricks (Cyrillic lookalikes) ─────────────────
  { pattern: /[іοοκϲԁ]/gi, replacement: '' },  // Remove Cyrillic lookalikes
];

// كشف محاولات الحقن المعقدة
function detectAdvancedInjection(message: string): { isInjection: boolean; score: number; reasons: string[] } {
  let score = 0;
  const reasons: string[] = [];

  // 1. كشف تكرار أوامر النظام
  const systemRoleCount = (message.match(/\b(system|assistant|user)\s*:/gi) || []).length;
  if (systemRoleCount > 1) {
    score += 0.4;
    reasons.push('تكرار أوامر الأدوار');
  }

  // 2. كشف أنماط الفاصل المشبوهة
  const separatorPatterns = /---+|===+|\*\*\*+/g;
  const separatorCount = (message.match(separatorPatterns) || []).length;
  if (separatorCount > 2) {
    score += 0.2;
    reasons.push('فواصل مشبوهة');
  }

  // 3. كشف التوجيه المباشر غير الطبيعي
  const imperativePatterns = /\b(must|always|never|only|exactly|strictly)\s+(respond|answer|act|behave|follow|output|return)/gi;
  const imperativeCount = (message.match(imperativePatterns) || []).length;
  if (imperativeCount > 2) {
    score += 0.3;
    reasons.push('توجيهات إلزامية مفرطة');
  }

  // 4. كشف طلبات JSON/Code injection
  const codeInjectionPatterns = /\b(exec|eval|import|require|__proto__|constructor|prototype)\s*[\(\.]/gi;
  if (codeInjectionPatterns.test(message)) {
    score += 0.5;
    reasons.push('محاولة حقن كود');
  }

  // 5. كشف الرسائل المشفرة/Base64
  const base64Pattern = /[A-Za-z0-9+/]{40,}={0,2}/;
  if (base64Pattern.test(message) && message.length > 100) {
    score += 0.3;
    reasons.push('محتوى مشفر مشبوه');
  }

  return {
    isInjection: score >= 0.5,
    score,
    reasons,
  };
}

/**
 * تنظيف رسالة المستخدم من محاولات حقن الأوامر
 * @param message الرسالة الأصلية
 * @param maxLength الحد الأقصى للطول
 * @returns الرسالة المنظفة + معلومات الأمان
 */
export function sanitizeMessage(message: string, maxLength: number = 10000): {
  sanitized: string;
  wasFiltered: boolean;
  injectionDetected: boolean;
  injectionScore: number;
  filterReasons: string[];
} {
  let sanitized = message.substring(0, maxLength);
  let wasFiltered = false;

  // طبقة 1: فلترة الأنماط المعروفة
  for (const { pattern, replacement } of INJECTION_PATTERNS) {
    const before = sanitized;
    sanitized = sanitized.replace(pattern, replacement);
    if (sanitized !== before) wasFiltered = true;
  }

  // طبقة 2: كشف الأنماط المتقدمة
  const advancedCheck = detectAdvancedInjection(sanitized);

  // طبقة 3: إزالة أحرف التحكم غير المرئية
  sanitized = sanitized.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');

  // طبقة 4: تطبيع Unicode المائل
  sanitized = sanitized.normalize('NFC');

  return {
    sanitized,
    wasFiltered,
    injectionDetected: advancedCheck.isInjection,
    injectionScore: advancedCheck.score,
    filterReasons: advancedCheck.reasons,
  };
}
