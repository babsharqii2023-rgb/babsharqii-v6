// ═══════════════════════════════════════════════════════════════════
// مأمون v40.0 — Real Confidence Calculation Engine
// حساب الثقة من مصادر متعددة وليس من طول الرد
// ═══════════════════════════════════════════════════════════════════

export interface ConfidenceInput {
  /** رد النموذج */
  responseText: string;
  /** هل جاء من مداولة حقيقية (5 أدمغة) أم دماغ واحد؟ */
  isRealDeliberation: boolean;
  /** مستوى إجماع الأدمغة (0-1) */
  consensusLevel?: number;
  /** هل كشف تناقض بين الأدمغة؟ */
  conflictDetected?: boolean;
  /** درجة التقاطع الحرج (0-1) */
  cjs?: number;
  /** عدد الفولباكات (0 = نجح من أول مرة) */
  fallbackCount: number;
  /** زمن الاستجابة بالميلي ثانية */
  latencyMs: number;
  /** عدد التوكنات المستخدمة */
  tokensUsed?: number;
  /** درجة حرارة النموذج المستخدم */
  temperature: number;
}

export interface ConfidenceResult {
  /** درجة الثقة الإجمالية (0-1) */
  confidence: number;
  /** مستوى الثقة بالعربية */
  levelAr: string;
  /** مستوى الثقة بالإنجليزية */
  levelEn: string;
  /** تفصيل العوامل */
  breakdown: {
    deliberationFactor: number;
    consensusFactor: number;
    fallbackFactor: number;
    responseQualityFactor: number;
    latencyFactor: number;
  };
  /** هل يجب إظهار تحذير للمستخدم؟ */
  showWarning: boolean;
  /** رسالة التحذير */
  warningMessage?: string;
}

/**
 * حساب الثقة الحقيقي من مصادر متعددة
 * يحل محل calculateConfidence الوهمي
 */
export function calculateRealConfidence(input: ConfidenceInput): ConfidenceResult {
  // ─── 1. عامل المداولة ────────────────────────────────────
  // مداولة حقيقية = ثقة أعلى، دماغ واحد = ثقة أقل
  const deliberationFactor = input.isRealDeliberation ? 1.0 : 0.6;

  // ─── 2. عامل الإجماع ─────────────────────────────────────
  // إجماع عالي = ثقة أعلى، تناقض = ثقة أقل
  let consensusFactor = 0.7; // افتراضي إذا لا بيانات
  if (input.consensusLevel !== undefined) {
    consensusFactor = input.consensusLevel;
  }
  if (input.conflictDetected) {
    consensusFactor *= 0.7; // خفض 30% عند التناقض
  }

  // ─── 3. عامل الفولباك ────────────────────────────────────
  // نجح من أول مرة = أفضل، كل فولباك يخفض الثقة
  const fallbackFactor = Math.max(0.3, 1.0 - (input.fallbackCount * 0.2));

  // ─── 4. عامل جودة الرد ───────────────────────────────────
  let responseQualityFactor = 0.7;
  const text = input.responseText;

  // طول مناسب
  if (text.length > 50 && text.length < 5000) {
    responseQualityFactor += 0.1;
  } else if (text.length < 30) {
    responseQualityFactor -= 0.2;
  }

  // يحتوي تفاصيل وأدلة
  const evidencePatterns = /[\d٪%]+|وفقاً|بناءً على|تشير|أظهرت|أثبتت|حسب|طبقاً ل/g;
  const evidenceCount = (text.match(evidencePatterns) || []).length;
  if (evidenceCount > 0) responseQualityFactor += Math.min(0.15, evidenceCount * 0.03);

  // يحتوي تحفظات (ليس بالضرورة سيء لكن يخفض الثقة)
  const hedgingPatterns = /ربما|قد يكون|من المحتمل|يمكن أن|يُحتمل|لست متأكداً|لست واثقاً/g;
  const hedgingCount = (text.match(hedgingPatterns) || []).length;
  if (hedgingCount > 2) responseQualityFactor -= 0.1;

  // اعتذار = انخفاض حاد
  if (text.includes('عذراً') || text.includes('آسف') || text.includes('لم أتمكن')) {
    responseQualityFactor -= 0.2;
  }

  responseQualityFactor = Math.max(0.2, Math.min(1.0, responseQualityFactor));

  // ─── 5. عامل السرعة ──────────────────────────────────────
  // رد سريع = أفضل (لكن السرعة الزائدة قد تعني بساطة)
  let latencyFactor = 0.8;
  if (input.latencyMs > 0 && input.latencyMs < 30000) {
    latencyFactor = 0.9; // رد سريع ومعقول
  } else if (input.latencyMs >= 30000) {
    latencyFactor = 0.6; // رد بطيء = قد يكون غير مستقر
  }

  // ─── حساب الموزون ────────────────────────────────────────
  const weights = {
    deliberation: 0.25,
    consensus: 0.25,
    fallback: 0.20,
    responseQuality: 0.20,
    latency: 0.10,
  };

  const confidence = (
    deliberationFactor * weights.deliberation +
    consensusFactor * weights.consensus +
    fallbackFactor * weights.fallback +
    responseQualityFactor * weights.responseQuality +
    latencyFactor * weights.latency
  );

  const clampedConfidence = Math.max(0.1, Math.min(1.0, confidence));

  // ─── تحديد المستوى ────────────────────────────────────────
  let levelAr: string;
  let levelEn: string;
  if (clampedConfidence >= 0.9) { levelAr = 'عالي جداً'; levelEn = 'Very High'; }
  else if (clampedConfidence >= 0.75) { levelAr = 'عالي'; levelEn = 'High'; }
  else if (clampedConfidence >= 0.55) { levelAr = 'متوسط'; levelEn = 'Medium'; }
  else if (clampedConfidence >= 0.35) { levelAr = 'منخفض'; levelEn = 'Low'; }
  else { levelAr = 'منخفض جداً'; levelEn = 'Very Low'; }

  // ─── تحذيرات ──────────────────────────────────────────────
  const showWarning = clampedConfidence < 0.5;
  let warningMessage: string | undefined;
  if (input.fallbackCount > 0) {
    warningMessage = 'تم استخدام مسار بديل — قد تكون دقة الرد أقل من المعتاد';
  } else if (input.conflictDetected) {
    warningMessage = 'الأدمغة غير متفقة تماماً — قد لا يكون الرد أمثلياً';
  } else if (!input.isRealDeliberation) {
    warningMessage = 'لم تتم مداولة كاملة — رد من دماغ واحد فقط';
  } else if (clampedConfidence < 0.35) {
    warningMessage = 'انخفاض ملحوظ في الثقة — يُنصح بالتحقق من المعلومات';
  }

  return {
    confidence: Math.round(clampedConfidence * 100) / 100,
    levelAr,
    levelEn,
    breakdown: {
      deliberationFactor: Math.round(deliberationFactor * 100) / 100,
      consensusFactor: Math.round(consensusFactor * 100) / 100,
      fallbackFactor: Math.round(fallbackFactor * 100) / 100,
      responseQualityFactor: Math.round(responseQualityFactor * 100) / 100,
      latencyFactor: Math.round(latencyFactor * 100) / 100,
    },
    showWarning,
    warningMessage,
  };
}

/**
 * حساب ثقة سريع للـ fallback (دماغ واحد فقط)
 * يحل محل الدالة الوهمية القديمة
 */
export function calculateFallbackConfidence(
  responseText: string,
  fallbackCount: number = 1,
  latencyMs: number = 0,
  temperature: number = 0.7,
): number {
  const result = calculateRealConfidence({
    responseText,
    isRealDeliberation: false,
    fallbackCount,
    latencyMs,
    temperature,
  });
  return result.confidence;
}
