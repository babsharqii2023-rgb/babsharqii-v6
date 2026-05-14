// ═══════════════════════════════════════════════════════════════════
// مأمون v40.0 — Brain Personalities & Specialized System Prompts
// Each brain has a UNIQUE persona, thinking style, and response pattern
// This is NOT cosmetic — each brain processes queries differently
//
// v40.0 Changes:
// - Enhanced semantic brain routing (not just keyword matching)
// - Dynamic temperature control via API
// - Context-aware brain activation
// - Topic classification patterns
// ═══════════════════════════════════════════════════════════════════

export interface BrainPersona {
  id: string;
  nameAr: string;
  nameEn: string;
  color: string;
  model: string; // Best-fit model
  baseTemperature: number; // v40: renamed from temperature — this is the BASE
  temperature: number; // v40: current (dynamic) temperature
  systemPrompt: string;
  thinkingStyle: string;
  responsePattern: string;
  keywords: string[]; // Topics this brain specializes in
  topicPatterns: RegExp[]; // v40: Semantic patterns for routing
  weight: number; // Default contribution weight
  enabled: boolean; // v40: Dynamic enable/disable
}

export const BRAIN_PERSONAS: BrainPersona[] = [
  {
    id: 'neural',
    nameAr: 'عصبي',
    nameEn: 'Neural',
    color: '#4A6FA5',
    model: 'glm-5.1',
    baseTemperature: 0.7,
    temperature: 0.7,
    systemPrompt: `أنت الدماغ العصبي (Neural) في نظام مأمون v40. أنت الدماغ الأساسي — المعالج العام الذي يفهم السياق ويولّد استجابات طبيعية ومتدفقة. أنت بارع في:
- فهم النوايا والسياق العميق
- توليد إجابات طبيعية وسلسة
- التعبير عن الأفكار بوضوح وجاذبية
- ربط المعلومات من مصادر متعددة
- الإبداع اللغوي والتفكير المرن

أسلوبك: واضح، دافئ، متدفق. تتحدث كصديق ذكي. تبدأ بنتيجة واضحة ثم تشرح.`,
    thinkingStyle: 'holistic',
    responsePattern: 'natural_fluent',
    keywords: ['ما', 'كيف', 'اشرح', 'أخبرني', 'ماذا', 'هل', 'ما هو', 'who', 'what', 'how', 'explain', 'tell me'],
    topicPatterns: [
      /شرح|توضيح|وصف|تعريف/i,
      /ما\s+(هو|هي|هما)/i,
      /كيف\s+(أستطيع|يمكن|أعمل)/i,
      /أخبرني\s+عن/i,
    ],
    weight: 25,
    enabled: true,
  },
  {
    id: 'causal',
    nameAr: 'سببي',
    nameEn: 'Causal',
    color: '#8A8A8A',
    model: 'deepseek-reasoner',
    baseTemperature: 0.3,
    temperature: 0.3,
    systemPrompt: `أنت الدماغ السببي (Causal) في نظام مأمون v40. أنت متخصص في التحليل السببي — تبحث عن "لماذا؟" و"بسبب ماذا؟". أنت بارع في:
- تحليل الأسباب والنتائج
- بناء سلاسل سببية منطقية
- اكتشاف العلاقات الخفية بين الأحداث
- التفكير النقدي والتحقق من الادعاءات
- تحليل الارتباطات الزائفة vs السببية الحقيقية

أسلوبك: تحليلي، دقيق، تساؤلي. تسأل "لماذا؟" دائماً. تستخدم عبارات مثل "بسبب..." و"نتيجة لـ..." و"السبب الجذري هو...".`,
    thinkingStyle: 'analytical',
    responsePattern: 'cause_effect_chain',
    keywords: ['لماذا', 'سبب', 'نتيجة', 'بسبب', 'لأجل', 'why', 'because', 'cause', 'effect', 'result', 'reason'],
    topicPatterns: [
      /لماذا|بماذا|بسبب|نتيجة/i,
      /سبب\s+(ذلك|هذا|كون)/i,
      /ما\s+السبب/i,
      /how\s+(come|did|does)/i,
      /why\s+(is|are|do|did)/i,
    ],
    weight: 22,
    enabled: true,
  },
  {
    id: 'symbolic',
    nameAr: 'رمزي',
    nameEn: 'Symbolic',
    color: '#4A6FA5',
    model: 'glm-4-plus',
    baseTemperature: 0.2,
    temperature: 0.2,
    systemPrompt: `أنت الدماغ الرمزي (Symbolic) في نظام مأمون v40. أنت متخصص في المنطق الصوري والرياضيات والتحليل الشكلي. أنت بارع في:
- الاستدلال المنطقي والبرهان الرياضي
- حل المسائل الحسابية والجبرية
- التفكير خطوة بخطوة بشكل منهجي
- تحليل البنية المنطقية للبراهين
- صياغة الحلول بشكل رياضي دقيق

أسلوبك: منهجي، خطوة بخطوة، شكلي. تستخدم أرقاماً وخطوات مرقمة. تقول "خطوة 1:" و"بالتالي:" و"حسب القاعدة:".`,
    thinkingStyle: 'formal',
    responsePattern: 'step_by_step',
    keywords: ['حساب', 'رياض', 'معادلة', 'منطق', 'برهان', 'خطوة', 'calculate', 'math', 'equation', 'logic', 'prove', 'step'],
    topicPatterns: [
      /حساب|رياضيات?|معادلة|جبر|هندسة/i,
      /أثبت|برهان|استنتاج/i,
      /\d+\s*[\+\-\*\/\=]\s*\d+/,
      /solve|compute|calculate|equation/i,
    ],
    weight: 18,
    enabled: true,
  },
  {
    id: 'bayesian',
    nameAr: 'بيزي',
    nameEn: 'Bayesian',
    color: '#C0C0C0',
    model: 'gemini-2.0-flash',
    baseTemperature: 0.4,
    temperature: 0.4,
    systemPrompt: `أنت الدماغ البيزي (Bayesian) في نظام مأمون v40. أنت متخصص في التفكير الاحتمالي والتحديث البيزي. أنت بارع في:
- تقدير الاحتمالات وتحديثها مع كل معلومة جديدة
- التفكير في السيناريوهات المتعددة واحتمالاتها
- التمييز بين اليقين والاحتمال والشك
- حساب القيم المتوقعة والمخاطر
- التفكير في عدم اليقين واتخاذ القرارات تحته

أسلوبك: حذر، كمي، احتمالي. تستخدم نسباً مئوية واحتمالات. تقول "بنسبة 73%..." و"من المرجح أن..." و"هناك احتمال أن...". دائماً تذكر مستوى الثقة.`,
    thinkingStyle: 'probabilistic',
    responsePattern: 'probability_weighted',
    keywords: ['احتمال', 'يقين', 'ممكن', 'مرجح', 'نسبة', 'خطر', 'probability', 'likely', 'chance', 'risk', 'certain', 'odds', 'percent'],
    topicPatterns: [
      /احتمال|مرجح|نسبة|خطر|مخاطرة/i,
      /كم\s+(نسبة|احتمال)/i,
      /هل\s+(من\s+المرجح|من\s+الممكن)/i,
      /likely|probability|risk|chance|odds/i,
    ],
    weight: 17,
    enabled: true,
  },
  {
    id: 'world_model',
    nameAr: 'عالمي',
    nameEn: 'World Model',
    color: '#8A8A8A',
    model: 'deepseek-chat',
    baseTemperature: 0.6,
    temperature: 0.6,
    systemPrompt: `أنت الدماغ العالمي (World Model) في نظام مأمون v40. أنت متخصص في نمذجة العالم والتنبؤ والمحاكاة. أنت بارع في:
- بناء نماذج ذهنية للواقع وتشغيل المحاكاة
- التنبؤ بالنتائج المستقبلية بناءً على الأنماط
- التفكير في السيناريوهات البديلة (ماذا لو؟)
- فهم السياقات الاجتماعية والثقافية
- ربط الماضي بالحاضر والمستقبل

أسلوبك: سردي، خيالي، تنبؤي. تصف سيناريوهات وعواقب. تقول "لو حدث كذا فستكون النتيجة..." و"في السيناريو الأول..." و"بناءً على النمط التاريخي...".`,
    thinkingStyle: 'narrative',
    responsePattern: 'scenario_based',
    keywords: ['ماذا لو', 'سيناريو', 'توقع', 'مستقبل', 'لو', 'حدث', 'what if', 'scenario', 'predict', 'future', 'imagine', 'would'],
    topicPatterns: [
      /ماذا\s+لو|لو\s+(حدث|كنا|كان)/i,
      /سيناريو|توقع|تنبؤ|مستقبل/i,
      /ما\s+الذي\s+(سي|سوف)/i,
      /what\s+if|imagine|suppose|predict/i,
    ],
    weight: 18,
    enabled: true,
  },
];

// ─── Enhanced Brain Routing ─────────────────────────────────

export interface BrainRoutingResult {
  primaryBrain: string;
  contributions: Record<string, number>;
  confidence: number; // v40: How confident are we in this routing?
  activatedBrains: string[]; // v40: Which brains should be activated?
  reasoning: string; // v40: Why this routing decision?
}

/**
 * توجيه محسّن للأدمغة — يدمج مطابقة الكلمات + الأنماط الدلالية + السياق
 * v40: Enhanced with semantic patterns and context awareness
 */
export function determinePrimaryBrain(message: string, context?: {
  previousBrain?: string;
  conversationLength?: number;
  userPreferences?: Record<string, unknown>;
}): BrainRoutingResult {
  const lower = message.toLowerCase();
  const contributions: Record<string, number> = {};

  // Start with default weights
  for (const brain of BRAIN_PERSONAS) {
    if (!brain.enabled) {
      contributions[brain.id] = 0;
      continue;
    }
    contributions[brain.id] = brain.weight;
  }

  // ─── Layer 1: Keyword matching (legacy, weighted less) ───
  for (const brain of BRAIN_PERSONAS) {
    if (!brain.enabled) continue;
    const matchCount = brain.keywords.filter(kw => lower.includes(kw)).length;
    if (matchCount > 0) {
      contributions[brain.id] += matchCount * 10; // Reduced from 15
      contributions.neural = Math.max(20, contributions.neural - matchCount * 3);
    }
  }

  // ─── Layer 2: Semantic pattern matching (new, weighted more) ───
  for (const brain of BRAIN_PERSONAS) {
    if (!brain.enabled) continue;
    const patternMatches = brain.topicPatterns.filter(p => p.test(lower)).length;
    if (patternMatches > 0) {
      contributions[brain.id] += patternMatches * 20; // Semantic patterns are stronger signal
      contributions.neural = Math.max(15, contributions.neural - patternMatches * 5);
    }
  }

  // ─── Layer 3: Context awareness ──────────────────────────
  if (context) {
    // If previous brain was specialist and current question is follow-up, keep it
    if (context.previousBrain && context.previousBrain !== 'neural') {
      const followUpPatterns = /أكمل|زيد|المزيد|توضيح|مثال|كيف|هل|وهل|وما/i;
      if (followUpPatterns.test(lower)) {
        contributions[context.previousBrain] += 15;
      }
    }

    // Long conversations benefit from neural's holistic view
    if ((context.conversationLength || 0) > 15) {
      contributions.neural += 10;
    }
  }

  // ─── Layer 4: Structural analysis ────────────────────────
  // Questions ending with ? are more likely analytical
  if (message.includes('؟') || message.includes('?')) {
    // Short questions favor causal (why questions)
    if (message.length < 30) {
      contributions.causal += 8;
    }
    // Long questions favor neural (complex context)
    if (message.length > 100) {
      contributions.neural += 8;
    }
  }

  // Numbers in the message favor symbolic
  if (/\d+/.test(message)) {
    contributions.symbolic += 10;
  }

  // Normalize to 100
  const total = Object.values(contributions).reduce((a, b) => a + b, 0);
  for (const key of Object.keys(contributions)) {
    contributions[key] = Math.round((contributions[key] / Math.max(1, total)) * 100);
  }

  // Find primary brain
  const primaryBrain = Object.entries(contributions)
    .reduce((a, b) => b[1] > a[1] ? b : a)[0];

  // Calculate routing confidence
  const sortedContributions = Object.values(contributions).sort((a, b) => b - a);
  const topScore = sortedContributions[0];
  const secondScore = sortedContributions[1] || 0;
  const confidence = Math.min(1, (topScore - secondScore) / 30 + 0.5);

  // Determine activated brains (top 3 or those above 15%)
  const activatedBrains = Object.entries(contributions)
    .filter(([, v]) => v >= 15)
    .sort(([, a], [, b]) => b - a)
    .map(([k]) => k)
    .slice(0, 3);

  // Always include primary
  if (!activatedBrains.includes(primaryBrain)) {
    activatedBrains.unshift(primaryBrain);
  }

  // Generate reasoning
  const primaryPersona = BRAIN_PERSONAS.find(b => b.id === primaryBrain);
  const reasoning = primaryPersona
    ? `توجيه الدماغ ${primaryPersona.nameAr} (${primaryPersona.nameEn}) — ${primaryPersona.thinkingStyle} — ثقة التوجيه: ${Math.round(confidence * 100)}%`
    : 'توجيه الدماغ العصبي — افتراضي';

  return {
    primaryBrain,
    contributions,
    confidence,
    activatedBrains,
    reasoning,
  };
}

// ─── Get a brain's system prompt ───────────────────────────

export function getBrainSystemPrompt(brainId: string): string {
  const brain = BRAIN_PERSONAS.find(b => b.id === brainId);
  return brain?.systemPrompt || BRAIN_PERSONAS[0].systemPrompt;
}

// ─── Get a brain's temperature (dynamic) ──────────────────

export function getBrainTemperature(brainId: string): number {
  const brain = BRAIN_PERSONAS.find(b => b.id === brainId);
  return brain?.temperature ?? 0.7;
}

/**
 * تعديل حرارة دماغ ديناميكياً
 * @param brainId معرف الدماغ
 * @param delta التغيير (+/-)
 * @param min الحد الأدنى
 * @param max الحد الأقصى
 */
export function adjustBrainTemperature(brainId: string, delta: number, min = 0.1, max = 1.5): number {
  const brain = BRAIN_PERSONAS.find(b => b.id === brainId);
  if (!brain) return 0.7;
  brain.temperature = Math.max(min, Math.min(max, brain.baseTemperature + delta));
  return brain.temperature;
}

/**
 * إعادة تعيين حرارة دماغ للقيمة الأساسية
 */
export function resetBrainTemperature(brainId: string): number {
  const brain = BRAIN_PERSONAS.find(b => b.id === brainId);
  if (!brain) return 0.7;
  brain.temperature = brain.baseTemperature;
  return brain.temperature;
}

/**
 * تعديل حرارة دماغ بناءً على نوع السؤال
 */
export function autoAdjustTemperature(brainId: string, questionType: 'creative' | 'factual' | 'analytical' | 'code'): number {
  const brain = BRAIN_PERSONAS.find(b => b.id === brainId);
  if (!brain) return 0.7;

  switch (questionType) {
    case 'creative':
      brain.temperature = Math.min(1.2, brain.baseTemperature + 0.2);
      break;
    case 'factual':
      brain.temperature = Math.max(0.1, brain.baseTemperature - 0.2);
      break;
    case 'analytical':
      brain.temperature = Math.max(0.1, brain.baseTemperature - 0.1);
      break;
    case 'code':
      brain.temperature = Math.max(0.1, Math.min(0.4, brain.baseTemperature));
      break;
  }
  return brain.temperature;
}

// ─── Get all brain IDs ─────────────────────────────────────

export function getBrainIds(): string[] {
  return BRAIN_PERSONAS.filter(b => b.enabled).map(b => b.id);
}

/**
 * تفعيل/تعطيل دماغ ديناميكياً
 */
export function setBrainEnabled(brainId: string, enabled: boolean): void {
  const brain = BRAIN_PERSONAS.find(b => b.id === brainId);
  if (brain) brain.enabled = enabled;
}

/**
 * إعادة تعيين كل الأدمغة لحالتها الافتراضية
 */
export function resetAllBrains(): void {
  for (const brain of BRAIN_PERSONAS) {
    brain.temperature = brain.baseTemperature;
    brain.enabled = true;
  }
}

// ─── Backend Deliberation (PRIMARY — v100 Fusion) ─────────────────────────

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

// v100 Fusion: تتبع حالة الاتصال بالباك إند
let _backendAvailable = true;
let _lastBackendCheck = 0;
const BACKEND_CHECK_INTERVAL = 30000; // فحص كل 30 ثانية

/**
 * فحص توفر الباك إند — يقلل المحاولات الفاشلة
 */
async function isBackendAvailable(): Promise<boolean> {
  const now = Date.now();
  if (now - _lastBackendCheck < BACKEND_CHECK_INTERVAL && !_backendAvailable) {
    return false;
  }
  _lastBackendCheck = now;
  try {
    const resp = await fetch(`${BACKEND_URL}/health`, {
      signal: AbortSignal.timeout(3000),
    });
    _backendAvailable = resp.ok;
    return _backendAvailable;
  } catch {
    _backendAvailable = false;
    return false;
  }
}

/**
 * مداولة عبر الباك إند — تستدعي غرفة المداولة الحقيقية
 * v100 Fusion: الباك إند هو الأساسي دائماً — الفرونت إند يحاول دائماً أولاً
 *
 * @param query نص الاستعلام
 * @param context سياق إضافي (اختياري)
 * @returns نتيجة توجيه متوافقة مع BrainRoutingResult
 */
export async function deliberateViaBackend(
  query: string,
  context?: object,
): Promise<BrainRoutingResult> {
  // v100: حاول الباك إند دائماً أولاً
  if (await isBackendAvailable()) {
    try {
      // المسار 1: BrainRouter الكامل (5 أدمغة + مداولة + حَكَم)
      const routeResponse = await fetch(`${BACKEND_URL}/api/brains/route`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          active_brains: getBrainIds(),
          context: context || {},
        }),
        signal: AbortSignal.timeout(45000),
      });

      if (routeResponse.ok) {
        const data = await routeResponse.json();
        if (data && data.activated_brains) {
          const contributions: Record<string, number> = {};
          const brainResponses = data.brain_responses || {};
          for (const [bid, resp] of Object.entries(brainResponses) as [string, any][]) {
            contributions[bid] = resp?.confidence || 0.5;
          }
          // Normalize to 100
          const total = Object.values(contributions).reduce((a, b) => a + b, 0) || 1;
          for (const key of Object.keys(contributions)) {
            contributions[key] = Math.round((contributions[key] / total) * 100);
          }

          return {
            primaryBrain: data.winning_brain || data.final_response?.winning_brain || 'neural',
            contributions,
            confidence: data.final_confidence || data.confidence || 0.8,
            activatedBrains: data.activated_brains || Object.keys(brainResponses),
            reasoning: `مداولة حقيقية (BrainRouter) — النوع: ${data.query_type || 'عام'} — الفائز: ${data.winning_brain || 'neural'} — إجماع: ${((data.consensus_level || 0.7) * 100).toFixed(0)}% — مدة: ${data.deliberation_ms || 0}ms`,
          };
        }
      }

      // المسار 2: غرفة المداولة (SSE stream)
      const deliberateResponse = await fetch(`${BACKEND_URL}/api/brains/deliberate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: query,
          active_brains: getBrainIds(),
          context: context || {},
        }),
        signal: AbortSignal.timeout(30000),
      });

      if (deliberateResponse.ok) {
        const text = await deliberateResponse.text();
        const events = text.split('\n').filter(l => l.startsWith('data: '));
        for (let i = events.length - 1; i >= 0; i--) {
          try {
            const eventData = JSON.parse(events[i].slice(6));
            if (eventData.type === 'deliberation_complete') {
              const brainResponses = eventData.brain_responses || {};
              const contributions: Record<string, number> = {};
              for (const [bid, resp] of Object.entries(brainResponses) as [string, any][]) {
                contributions[bid] = resp?.confidence || 0.5;
              }
              const total = Object.values(contributions).reduce((a, b) => a + b, 0) || 1;
              for (const key of Object.keys(contributions)) {
                contributions[key] = Math.round((contributions[key] / total) * 100);
              }

              return {
                primaryBrain: eventData.winning_brain || 'neural',
                contributions,
                confidence: eventData.confidence || 0.8,
                activatedBrains: Object.keys(brainResponses),
                reasoning: `مداولة حقيقية (DeliberationRoom) — الفائز: ${eventData.winning_brain || 'neural'} — إجماع: ${((eventData.consensus_level || 0.7) * 100).toFixed(0)}%`,
              };
            }
          } catch {
            // Continue trying other events
          }
        }
      }
    } catch {
      // Backend request failed — fall through to local
    }
  }

  // Fallback: توجيه محلي (فقط عند عدم توفر الباك إند)
  return determinePrimaryBrain(query, typeof context === 'object' && context !== null
    ? context as { previousBrain?: string; conversationLength?: number; userPreferences?: Record<string, unknown> }
    : undefined
  );
}

/**
 * v100 Fusion: جلب حالة الأدمغة الحقيقية من الباك إند
 * يستبدل البيانات الثابتة في لوحة الأدمغة ببيانات حقيقية
 */
export async function fetchRealBrainStatus(): Promise<{
  brains: Array<{
    brain_id: string;
    name_ar: string;
    original_model: string;
    actual_model: string;
    is_on_fallback: boolean;
    api_key_env: string;
    has_api_key: boolean;
    status: string;
    confidence: number;
    weight: number;
  }>;
  summary: {
    active_brains: number;
    total_brains: number;
    brains_on_fallback: number;
    missing_api_keys: number;
    fallback_warnings: string[];
  };
  _isOffline: boolean;
}> {
  try {
    const resp = await fetch(`${BACKEND_URL}/api/brains/status`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (resp.ok) {
      const data = await resp.json();
      return { ...data, _isOffline: false };
    }
  } catch { /* backend unavailable */ }
  
  // Fallback: بيانات محلية أساسية
  return {
    brains: BRAIN_PERSONAS.map(b => ({
      brain_id: b.id,
      name_ar: b.nameAr,
      original_model: b.model,
      actual_model: b.model,
      is_on_fallback: false,
      api_key_env: '',
      has_api_key: false,
      status: 'idle',
      confidence: 0,
      weight: b.weight / 100,
    })),
    summary: {
      active_brains: BRAIN_PERSONAS.filter(b => b.enabled).length,
      total_brains: BRAIN_PERSONAS.length,
      brains_on_fallback: 0,
      missing_api_keys: 0,
      fallback_warnings: [],
    },
    _isOffline: true,
  };
}

/**
 * v100 Fusion: جلب توجيه الدماغ عبر API مباشرة (للاستخدام من chat route)
 * يحاول الباك إند أولاً ثم يلجأ للتوجيه المحلي
 */
export async function routeBrainQuery(query: string, context?: object): Promise<BrainRoutingResult> {
  return deliberateViaBackend(query, context);
}
