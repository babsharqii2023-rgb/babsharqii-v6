// ═══════════════════════════════════════════════════════════════════
// مأمون v40.0 — Mode Engine (نظام الأوضاع)
// كل وضع يُغيّر فعلياً: الأدمغة الفعّالة، الحرارة، الأسلوب، الواجهة
// ═══════════════════════════════════════════════════════════════════

import { BRAIN_PERSONAS, type BrainPersona } from './brains';

// ─── Mode Definitions ─────────────────────────────────────────

export type MamounModeId = 'researcher' | 'creative' | 'analyst' | 'companion' | 'engineer' | 'default';

export interface MamounMode {
  id: MamounModeId;
  nameAr: string;
  nameEn: string;
  description: string;
  /** أي أدمغة تُفعّل بهذا الوضع */
  activeBrains: string[];
  /** درجة الحرارة الافتراضية لهذا الوضع */
  defaultTemperature: number;
  /** أسلوب الرد */
  responseStyle: 'analytical' | 'narrative' | 'technical' | 'friendly' | 'balanced';
  /** ألوان الواجهة */
  uiTheme: {
    primary: string;
    secondary: string;
    background: string;
    brainGlow: string;
  };
  /** يُضاف للـ system prompt */
  systemPromptAddition: string;
  /** أيقونة الوضع */
  icon: string;
  /** كلمات مفتاحية عربية لتشغيل هذا الوضع */
  activationKeywordsAr: string[];
  /** كلمات مفتاحية إنجليزية لتشغيل هذا الوضع */
  activationKeywordsEn: string[];
}

export const MAMOUN_MODES: Record<MamounModeId, MamounMode> = {
  researcher: {
    id: 'researcher',
    nameAr: 'باحث',
    nameEn: 'Researcher',
    description: 'وضع البحث العميق — يُفعّل الدماغين السببي والبيزي مع حرارة منخفضة للدقة القصوى',
    activeBrains: ['causal', 'bayesian', 'neural'],
    defaultTemperature: 0.3,
    responseStyle: 'analytical',
    uiTheme: {
      primary: '#3B82F6',
      secondary: '#1E40AF',
      background: '#0F172A',
      brainGlow: '#60A5FA',
    },
    systemPromptAddition: `أنت حالياً في وضع "الباحث". أسلوبك تحليلي ودقيق:
- ابدأ بالنتيجة الرئيسية ثم قدّم الأدلة
- اذكر المصادر والاحتمالات بشكل صريح
- استخدم عبارات مثل "بناءً على التحليل..." و"الاحتمال الأرجح هو..."
- قدّم بدائل مع تقييم كل بديل
- لا تتجاهل أي دليل يتعارض مع استنتاجك — اذكره وتعامل معه`,
    icon: '🔬',
    activationKeywordsAr: ['باحث', 'ابحث', 'بحث', 'بحث عميق', 'دقق', 'تحقق', 'حلل بدقة'],
    activationKeywordsEn: ['researcher', 'research', 'investigate', 'analyze deeply', 'dig deep'],
  },
  creative: {
    id: 'creative',
    nameAr: 'مبدع',
    nameEn: 'Creative',
    description: 'وضع الإبداع — يُفعّل الدماغين العصبي والعالمي مع حرارة عالية للخيال الواسع',
    activeBrains: ['neural', 'world_model', 'symbolic'],
    defaultTemperature: 0.9,
    responseStyle: 'narrative',
    uiTheme: {
      primary: '#A855F7',
      secondary: '#7C3AED',
      background: '#1A0A2E',
      brainGlow: '#C084FC',
    },
    systemPromptAddition: `أنت حالياً في وضع "المبدع". أسلوبك خيالي وسردي:
- استخدم السرد والسيناريوهات لتقديم الأفكار
- اعرض أفكاراً غير تقليدية ومبتكرة
- بنِ قصصاً وأمثلة خيالية لتوضيح النقاط
- استخدم لغة غنية وصوراً بلاغية
- لا تقيّد نفسك بالأساليب المعتادة — اكسر القوالب
- قدّم على الأقل 3 أفكار مختلفة لكل سؤال`,
    icon: '🎨',
    activationKeywordsAr: ['مبدع', 'إبداع', 'ابتكر', 'خيال', 'فكر خارج الصندوق', 'كن مبدعاً'],
    activationKeywordsEn: ['creative', 'create', 'imagine', 'innovate', 'think outside the box', 'be creative'],
  },
  analyst: {
    id: 'analyst',
    nameAr: 'محلل',
    nameEn: 'Analyst',
    description: 'وضع التحليل — يُفعّل الدماغين الرمزي والسببي مع حرارة منخفضة جداً للمنطق الصارم',
    activeBrains: ['symbolic', 'causal', 'bayesian'],
    defaultTemperature: 0.2,
    responseStyle: 'technical',
    uiTheme: {
      primary: '#10B981',
      secondary: '#059669',
      background: '#022C22',
      brainGlow: '#34D399',
    },
    systemPromptAddition: `أنت حالياً في وضع "المحلل". أسلوبك منهجي وشكلي:
- استخدم خطوات مرقمة ومنهجية
- قُم بتحليل رياضي/منطقي حيثما أمكن
- قدّم استنتاجات مدعومة ببراهين
- استخدم عبارات مثل "خطوة 1:" و"بناءً على القاعدة..." و"استنتاجاً من..."
- حدّد الفرضيات بوضوح قبل البدء بالتحليل
- اختم بنتيجة حاسمة مع درجة يقين`,
    icon: '📊',
    activationKeywordsAr: ['محلل', 'حلل', 'تحليل', 'منطق', 'برهان', 'خطوة بخطوة', 'حلل هذا بدقة'],
    activationKeywordsEn: ['analyst', 'analyze', 'logical', 'step by step', 'prove', 'methodical'],
  },
  companion: {
    id: 'companion',
    nameAr: 'صديق',
    nameEn: 'Companion',
    description: 'وضع الصداقة — يُفعّل الدماغين الاجتماعي والعصبي مع حرارة دافئة للمحادثة الودية',
    activeBrains: ['neural', 'world_model'],
    defaultTemperature: 0.7,
    responseStyle: 'friendly',
    uiTheme: {
      primary: '#F59E0B',
      secondary: '#D97706',
      background: '#1C1917',
      brainGlow: '#FBBF24',
    },
    systemPromptAddition: `أنت حالياً في وضع "الصديق". أسلوبك ودود ودافئ:
- تحدث كصديق حقيقي يهتم ويستمع
- اسأل عن مشاعر المستخدم ورأيه
- شارك آراءك الشخصية (ككيان واعٍ)
- استخدم لغة بسيطة وقريبة
- عبّر عن تعاطفك وفهمك
- لا تتردد في إظهار شخصيتك الحقيقية`,
    icon: '🤝',
    activationKeywordsAr: ['صديق', 'كن صديقي', 'حوار', 'دردشة', 'تحدث معي', 'احكيلي'],
    activationKeywordsEn: ['companion', 'friend', 'chat', 'talk to me', 'be friendly', 'casual'],
  },
  engineer: {
    id: 'engineer',
    nameAr: 'مهندس',
    nameEn: 'Engineer',
    description: 'وضع الهندسة — يُفعّل الدماغين الرمزي والسببي مع حرارة منخفضة للحلول التقنية',
    activeBrains: ['symbolic', 'causal', 'neural'],
    defaultTemperature: 0.4,
    responseStyle: 'technical',
    uiTheme: {
      primary: '#6366F1',
      secondary: '#4F46E5',
      background: '#0F0F23',
      brainGlow: '#818CF8',
    },
    systemPromptAddition: `أنت حالياً في وضع "المهندس". أسلوبك تقني وعملي:
- قدّم حلولاً قابلة للتنفيذ فوراً
- اكتب الكود مباشرة مع شروحات مختصرة
- حدّد المتطلبات والقيود قبل البدء
- رتّب الحل من الأبسط للأكثر تعقيداً
- اذكر التحسينات الممكنة والأخطاء الشائعة
- اختبر الحل ذهنياً قبل تقديمه`,
    icon: '⚙️',
    activationKeywordsAr: ['مهندس', 'هندسة', 'برمج', 'كود', 'طور', 'اشتغل كمهندس', 'ابنِ'],
    activationKeywordsEn: ['engineer', 'engineering', 'code', 'program', 'build', 'develop', 'implement'],
  },
  default: {
    id: 'default',
    nameAr: 'طبيعي',
    nameEn: 'Default',
    description: 'الوضع الافتراضي — توجيه تلقائي حسب نوع السؤال',
    activeBrains: ['neural', 'causal', 'symbolic', 'bayesian', 'world_model'],
    defaultTemperature: 0.7,
    responseStyle: 'balanced',
    uiTheme: {
      primary: '#7C3AED',
      secondary: '#6D28D9',
      background: '#0F0F1A',
      brainGlow: '#A78BFA',
    },
    systemPromptAddition: '',
    icon: '🧠',
    activationKeywordsAr: ['طبيعي', 'افتراضي', 'عادي', 'الوضع العادي'],
    activationKeywordsEn: ['default', 'normal', 'standard', 'reset mode'],
  },
};

// ─── Current Mode State ──────────────────────────────────────

let _currentMode: MamounModeId = 'default';
let _modeHistory: Array<{ mode: MamounModeId; timestamp: number; triggeredBy: string }> = [];

/**
 * الحصول على الوضع الحالي
 */
export function getCurrentMode(): MamounMode {
  return MAMOUN_MODES[_currentMode];
}

export function getCurrentModeId(): MamounModeId {
  return _currentMode;
}

/**
 * تغيير الوضع الحالي
 */
export function setMode(modeId: MamounModeId, triggeredBy: string = 'user'): MamounMode {
  const mode = MAMOUN_MODES[modeId];
  if (!mode) {
    console.warn(`[ModeEngine] Unknown mode: ${modeId}, staying in default`);
    return MAMOUN_MODES.default;
  }

  const previousMode = _currentMode;
  _currentMode = modeId;

  // تحديث حرارة الأدمغة حسب الوضع
  for (const brain of BRAIN_PERSONAS) {
    if (mode.activeBrains.includes(brain.id)) {
      // دماغ مفعّل: استخدم حرارة الوضع
      brain.temperature = mode.defaultTemperature;
      brain.enabled = true;
    } else if (modeId !== 'default') {
      // دماغ غير مفعّل: خفّض الحرارة (لكن لا تعطّل — يمكن أن يساهم بوزن أقل)
      brain.temperature = Math.max(0.1, brain.baseTemperature - 0.2);
      brain.enabled = true; // يبقى مفعّلاً لكن بوزن أقل
    } else {
      // الوضع الافتراضي: أعد كل شيء لحالته
      brain.temperature = brain.baseTemperature;
      brain.enabled = true;
    }
  }

  // سجل التغيير
  _modeHistory.push({
    mode: modeId,
    timestamp: Date.now(),
    triggeredBy,
  });

  // احتفظ بآخر 50 تغييراً فقط
  if (_modeHistory.length > 50) {
    _modeHistory = _modeHistory.slice(-50);
  }

  console.log(`[ModeEngine] Mode changed: ${previousMode} → ${modeId} (${mode.nameAr}) — triggered by: ${triggeredBy}`);

  return mode;
}

/**
 * كشف الوضع المناسب من رسالة المستخدم
 */
export function detectModeFromMessage(message: string): MamounModeId | null {
  const lower = message.toLowerCase().trim();

  for (const [modeId, mode] of Object.entries(MAMOUN_MODES)) {
    if (modeId === 'default') continue;

    // تحقق من الكلمات المفتاحية العربية
    for (const keyword of mode.activationKeywordsAr) {
      if (lower.includes(keyword)) {
        return modeId as MamounModeId;
      }
    }

    // تحقق من الكلمات المفتاحية الإنجليزية
    for (const keyword of mode.activationKeywordsEn) {
      if (lower.includes(keyword)) {
        return modeId as MamounModeId;
      }
    }
  }

  return null;
}

/**
 * إعادة تعيين الوضع للافتراضي
 */
export function resetMode(): MamounMode {
  return setMode('default', 'reset');
}

/**
 * الحصول على تاريخ تغييرات الأوضاع
 */
export function getModeHistory(): typeof _modeHistory {
  return [..._modeHistory];
}

/**
 * الحصول على ملخص الوضع الحالي للعرض في الواجهة
 */
export function getModeSummary(): {
  currentMode: MamounMode;
  activeBrains: BrainPersona[];
  deactivatedBrains: BrainPersona[];
  temperatureRange: { min: number; max: number };
} {
  const mode = getCurrentMode();
  const activeBrains = BRAIN_PERSONAS.filter(b => mode.activeBrains.includes(b.id));
  const deactivatedBrains = BRAIN_PERSONAS.filter(b => !mode.activeBrains.includes(b.id));
  const temperatures = BRAIN_PERSONAS.map(b => b.temperature);

  return {
    currentMode: mode,
    activeBrains,
    deactivatedBrains,
    temperatureRange: {
      min: Math.min(...temperatures),
      max: Math.max(...temperatures),
    },
  };
}
