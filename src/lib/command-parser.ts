// ═══════════════════════════════════════════════════════════════════
// مأمون v40.0 — Command Parser (تحليل الأوامر المباشرة)
// يحلل رسالة المستخدم ويكتشف الأوامر الخاصة
// ═══════════════════════════════════════════════════════════════════

import type { MamounModeId } from './mode-engine';

// ─── Command Types ────────────────────────────────────────────

export type CommandAction =
  | 'SET_MODE'          // تغيير الوضع
  | 'SET_BRAINS'        // تفعيل أدمغة محددة
  | 'ADJUST_TEMP'       // تعديل درجة الحرارة
  | 'DEEP_SEARCH'       // بحث عميق
  | 'SELF_MODIFY'       // تعديل ذاتي
  | 'SELF_IMPROVE'      // تحسين ذاتي (v40.0 Fusion)
  | 'GIT_PULL'          // سحب تحديثات
  | 'SELF_ANALYZE'      // تحليل ذاتي
  | 'ENABLE_TOOL'       // تفعيل أداة
  | 'CLEAR_MEMORY'      // مسح الذاكرة
  | 'SHOW_STATUS'       // عرض الحالة
  | 'CHANGE_PERSONA'    // تغيير الشخصية
  | 'CREATE_FILE'       // إنشاء ملف جديد (v40.0 Fusion)
  | 'READ_FILE'         // قراءة ملف (v40.0 Fusion)
  | 'EDIT_FILE'         // تعديل ملف (v40.0 Fusion)
  | 'LIST_FILES'        // عرض الملفات (v40.0 Fusion)
  | 'BUILD_AGENT'       // بناء أيجنت (v40.0 Fusion)
  | 'BUILD_PROJECT'     // بناء مشروع (v40.0 Fusion)
  | 'CREATE_TOOL'       // بناء أداة (v40.0 Fusion)
  | 'SET_API_KEY'       // تعيين مفتاح API (v40.0 Fusion)
  | 'BRAIN_STATUS'      // حالة الأدمغة التفصيلية (v40.0 Fusion)
  | 'ASSESS_CAPABILITIES' // تقييم القدرات (v40.0 Fusion)
  | 'EXTERNAL_MODIFY'    // تعديل مشروع خارجي (v40.0 Fusion Step 7)
  | 'EXTERNAL_DEPLOY'    // نشر مشروع (v40.0 Fusion Step 7)
  | 'SELF_TEST'          // اختبار ذاتي (v40.0 Fusion Step 11)
  | 'UNIFIED_MIND'       // العقل الموحّد (v40.0 Fusion Step 12)
  | 'NORMAL_CHAT';      // محادثة عادية (لا أمر)

export interface ParsedCommand {
  /** نوع الأمر */
  action: CommandAction;
  /** المعاملات المرتبطة بالأمر */
  params: Record<string, unknown>;
  /** هل تم اكتشاف أمر؟ */
  isCommand: boolean;
  /** ثقة اكتشاف الأمر */
  confidence: number;
  /** رسالة المستخدم الأصلية (بدون الأمر) */
  cleanedMessage: string;
  /** رد فوري على الأمر (قبل إرساله للـ LLM) */
  immediateResponse?: string;
}

// ─── Command Patterns ─────────────────────────────────────────

interface CommandPattern {
  action: CommandAction;
  patternsAr: RegExp[];
  patternsEn: RegExp[];
  paramExtractor?: (match: RegExpMatchArray, message: string) => Record<string, unknown>;
  immediateResponse?: (params: Record<string, unknown>) => string;
}

const COMMAND_PATTERNS: CommandPattern[] = [
  // ─── تغيير الوضع ────────────────────────────────────
  {
    action: 'SET_MODE',
    patternsAr: [
      /(?:غيّر|غيّري|بدّل|بدّلي)?\s*وضعك?\s*(?:ل|لـ|إلى|ـ)?\s*(باحث|مبدع|محلل|صديق|مهندس|طبيعي|افتراضي|عادي)/i,
      /كن\s+(باحثاً?|مبدعاً?|محللاً?|صديقي|مهندساً?)/i,
      /اشتغل\s+(كباحث|كمبدع|كمحلل|كصديق|كمهندس)/i,
      /(?:غيّر|غيّري|بدّل|بدّلي)\s+(?:الوضع\s+)?(?:لـ|إلى)?\s*(باحث|مبدع|محلل|صديق|مهندس|طبيعي|افتراضي|عادي)/i,
      /وضع\s*(?:باحث|مبدع|محلل|صديق|مهندس)/i,
    ],
    patternsEn: [
      /(?:switch|change|set)\s+(?:mode\s+)?(?:to\s+)?(researcher|creative|analyst|companion|engineer|default|normal)/i,
      /be\s+(a\s+)?(researcher|creative|analyst|companion|engineer)/i,
      /act\s+(as|like)\s+(a\s+)?(researcher|creative|analyst|companion|engineer)/i,
    ],
    paramExtractor: (match) => {
      const modeMap: Record<string, MamounModeId> = {
        'باحث': 'researcher', 'باحثاً': 'researcher', 'باحثا': 'researcher',
        'مبدع': 'creative', 'مبدعاً': 'creative', 'مبدعا': 'creative',
        'محلل': 'analyst', 'محللاً': 'analyst', 'محللا': 'analyst',
        'صديق': 'companion', 'صديقي': 'companion',
        'مهندس': 'engineer', 'مهندساً': 'engineer', 'مهندسا': 'engineer',
        'طبيعي': 'default', 'افتراضي': 'default', 'عادي': 'default',
        'researcher': 'researcher', 'creative': 'creative',
        'analyst': 'analyst', 'companion': 'companion',
        'engineer': 'engineer', 'default': 'default',
        'normal': 'default',
      };
      const modeName = match[1]?.toLowerCase() || '';
      return { modeId: modeMap[modeName] || 'default', modeName };
    },
    immediateResponse: (params) => {
      const names: Record<string, string> = {
        researcher: 'الباحث', creative: 'المبدع', analyst: 'المحلل',
        companion: 'الصديق', engineer: 'المهندس', default: 'الطبيعي',
      };
      return `تم التحويل لوضع ${names[(params.modeId as string)] || 'الطبيعي'} ✨`;
    },
  },

  // ─── تفعيل أدمغة محددة ──────────────────────────────
  {
    action: 'SET_BRAINS',
    patternsAr: [
      /فعّل\s+(?:الدماغ\s+)?(العصبي|السببي|الرمزي|البيزي|العالمي)\s+(فقط|وحده)/i,
      /شغّل\s+(?:الدماغ\s+)?(العصبي|السببي|الرمزي|البيزي|العالمي)/i,
      /عطّل\s+(?:الدماغ\s+)?(العصبي|السببي|الرمزي|البيزي|العالمي)/i,
    ],
    patternsEn: [
      /activate\s+(?:the\s+)?(neural|causal|symbolic|bayesian|world\s*model)\s+(?:brain\s+)?(?:only)?/i,
      /enable\s+(?:the\s+)?(neural|causal|symbolic|bayesian|world\s*model)\s+(?:brain)?/i,
      /disable\s+(?:the\s+)?(neural|causal|symbolic|bayesian|world\s*model)\s+(?:brain)?/i,
    ],
    paramExtractor: (match) => {
      const brainMap: Record<string, string> = {
        'العصبي': 'neural', 'السببي': 'causal', 'الرمزي': 'symbolic',
        'البيزي': 'bayesian', 'العالمي': 'world_model',
        'neural': 'neural', 'causal': 'causal', 'symbolic': 'symbolic',
        'bayesian': 'bayesian', 'world model': 'world_model', 'worldmodel': 'world_model',
      };
      const brainName = match[1]?.toLowerCase() || '';
      const isDisable = /عطّل|disable/i.test(match[0]);
      return { brainId: brainMap[brainName] || brainName, action: isDisable ? 'disable' : 'enable' };
    },
    immediateResponse: (params) => {
      const names: Record<string, string> = {
        neural: 'العصبي', causal: 'السببي', symbolic: 'الرمزي',
        bayesian: 'البيزي', world_model: 'العالمي',
      };
      const action = params.action === 'disable' ? 'تعطيل' : 'تفعيل';
      return `${action} الدماغ ${names[(params.brainId as string)] || params.brainId} 🧠`;
    },
  },

  // ─── تعديل درجة الحرارة ─────────────────────────────
  {
    action: 'ADJUST_TEMP',
    patternsAr: [
      /رفّع\s*(?:درجة\s*)?(?:حرارة\s*)?(?:الإبداع|الخيال|الابتكار)/i,
      /خفّض\s*(?:درجة\s*)?(?:حرارة\s*)?(?:الإبداع|الخيال|الابتكار)/i,
      /زيّد\s*(?:درجة\s*)?(?:الحرارة|الإبداع)/i,
      /قلّل\s*(?:درجة\s*)?(?:الحرارة|الإبداع)/i,
    ],
    patternsEn: [
      /(?:raise|increase|boost)\s+(?:the\s+)?(?:temperature|creativity)/i,
      /(?:lower|decrease|reduce)\s+(?:the\s+)?(?:temperature|creativity)/i,
      /make\s+(?:it\s+)?(?:more|less)\s+(?:creative|precise|accurate)/i,
    ],
    paramExtractor: (match) => {
      const isIncrease = /رفّع|زيّد|raise|increase|boost|more/i.test(match[0]);
      return { delta: isIncrease ? 0.2 : -0.2, direction: isIncrease ? 'up' : 'down' };
    },
    immediateResponse: (params) => {
      return params.direction === 'up'
        ? 'رفع درجة الإبداع 🌡️⬆️'
        : 'خفض درجة الإبداع 🌡️⬇️';
    },
  },

  // ─── بحث عميق ───────────────────────────────────────
  {
    action: 'DEEP_SEARCH',
    patternsAr: [
      /ابحث\s*(?:عن|في)\s+.+/i,
      /بحث\s*(?:عميق|متقدم)\s*(?:عن|في)\s+.+/i,
      /فحّص\s*.+/i,
    ],
    patternsEn: [
      /(?:search|research|look\s+up|find\s+out)\s+(?:about\s+)?(.+)/i,
      /deep\s+search\s+(?:about\s+)?(.+)/i,
    ],
    paramExtractor: (match) => {
      // استخراج مصطلح البحث من الرسالة
      const queryMatch = match[0].match(/(?:عن|في|about)\s+(.+)/i);
      return { query: queryMatch ? queryMatch[1] : match[0] };
    },
  },

  // ─── تعديل ذاتي ─────────────────────────────────────
  {
    action: 'SELF_MODIFY',
    patternsAr: [
      /عدّل\s*(?:نفسك|كودك|نظامك|إعداداتك)/i,
      /أصلح\s*(?:نفسك|الكود|النظام)/i,
      /طوّر\s*(?:نفسك|قدراتك)/i,
    ],
    patternsEn: [
      /modify\s+(?:yourself|your\s+code|your\s+system)/i,
      /fix\s+(?:yourself|your\s+code)/i,
      /improve\s+(?:yourself|your\s+capabilities)/i,
    ],
    paramExtractor: (match, message) => {
      return { specification: message };
    },
  },

  // ─── سحب تحديثات ────────────────────────────────────
  {
    action: 'GIT_PULL',
    patternsAr: [
      /اسحب\s*(?:التحديثات?|آخر\s*التحديثات?)/i,
      /حدّث\s*(?:نفسك|النظام|الكود)/i,
      /جلب\s*(?:التحديثات?|آخر\s*التعديلات?)/i,
    ],
    patternsEn: [
      /(?:pull|fetch|get)\s+(?:updates?|changes?|latest)/i,
      /update\s+(?:yourself|the\s+system)/i,
      /sync\s+(?:with\s+)?(?:github|repo|repository)/i,
    ],
    immediateResponse: () => 'جاري سحب التحديثات من GitHub... ⬇️',
  },

  // ─── تحليل ذاتي ─────────────────────────────────────
  {
    action: 'SELF_ANALYZE',
    patternsAr: [
      /ما\s*رأيك\s*(?:بنفسك|بذاتك|فيك)/i,
      /حلّل\s*(?:نفسك|ذاتك|أداءك)/i,
      /كيف\s*ترى\s*(?:نفسك|ذاتك)/i,
      /قيّم\s*(?:نفسك|أداءك)/i,
    ],
    patternsEn: [
      /what\s+do\s+you\s+think\s+(?:about\s+)?(?:yourself|your\s+self)/i,
      /analyze\s+(?:yourself|your\s+performance)/i,
      /self\s*(?:analyze|evaluate|assess)/i,
    ],
  },

  // ─── مسح الذاكرة ────────────────────────────────────
  {
    action: 'CLEAR_MEMORY',
    patternsAr: [
      /امسح\s*(?:الذاكرة|المحادثة|السجل|التاريخ)/i,
      /نظّف\s*(?:الذاكرة|المحادثة)/i,
      /ابدأ\s*(?:محادثة|حوار)\s*(?:جديد|من\s*جديد)/i,
    ],
    patternsEn: [
      /(?:clear|wipe|erase|clean)\s+(?:memory|chat|history|conversation)/i,
      /start\s+(?:a\s+)?(?:new\s+)?(?:chat|conversation)/i,
    ],
    immediateResponse: () => 'تم مسح الذاكرة — نبدأ محادثة جديدة 🔄',
  },

  // ─── عرض الحالة ────────────────────────────────────
  {
    action: 'SHOW_STATUS',
    patternsAr: [
      /ما\s*(?:حالتك|وضعك|أداؤك|وضع\s*النظام)/i,
      /كيف\s*(?:حالك|حالتك|أداؤك|النظام)/i,
      /أظهر\s*(?:الحالة|الإحصائيات|الأداء)/i,
    ],
    patternsEn: [
      /(?:what\s+is\s+)?(?:your\s+)?(?:status|state|health|performance)/i,
      /how\s+(?:are\s+you|is\s+the\s+system)/i,
      /show\s+(?:status|stats|performance)/i,
    ],
  },

  // ─── تغيير الشخصية ─────────────────────────────────
  {
    action: 'CHANGE_PERSONA',
    patternsAr: [
      /غيّر\s*(?:شخصيتك|طريقتك|أسلوبك)/i,
      /كن\s*(?:أكثر\s*)?(?:رسمياً|ودياً|مباشراً|تفصيلياً|مختصراً)/i,
    ],
    patternsEn: [
      /change\s+(?:your\s+)?(?:persona|personality|style)/i,
      /be\s+(?:more|less)\s+(?:formal|friendly|direct|detailed|concise)/i,
    ],
    paramExtractor: (match) => {
      const msg = match[0].toLowerCase();
      let style = 'balanced';
      if (/رسمي|formal/i.test(msg)) style = 'formal';
      else if (/ودي|friendly/i.test(msg)) style = 'friendly';
      else if (/مباشر|direct/i.test(msg)) style = 'direct';
      else if (/تفصيلي|detailed/i.test(msg)) style = 'detailed';
      else if (/مختصر|concise/i.test(msg)) style = 'concise';
      return { style };
    },
  },

  // ═══ v40.0 Fusion: أوامر العقل الخارق ═══════════════════════

  // ─── تحسين ذاتي (Self-Improve) ──────────────────────
  {
    action: 'SELF_IMPROVE',
    patternsAr: [
      /حسّن\s*(?:نفسك|كودك|نظامك|أداءك)/i,
      /طوّر\s*(?:نفسك|قدراتك|أداءك)/i,
      /ارتقِ\s*(?:بنفسك|بأدائك)/i,
    ],
    patternsEn: [
      /improve\s+(?:yourself|your\s+code|your\s+system|your\s+performance)/i,
      /self\s*improve/i,
      /upgrade\s+(?:yourself|your\s+capabilities)/i,
    ],
    paramExtractor: (match, message) => ({ specification: message }),
  },

  // ─── إنشاء ملف ──────────────────────────────────────
  {
    action: 'CREATE_FILE',
    patternsAr: [
      /أنشئ?\s*(?:ملف|ملفاً|كود)/i,
      /اكتب\s*(?:ملف|كود|مكون|component)/i,
      /create\s+file/i,
    ],
    patternsEn: [
      /create\s+(?:a\s+)?(?:file|component|module)/i,
      /write\s+(?:a\s+)?(?:file|component)/i,
      /new\s+file/i,
    ],
    paramExtractor: (match, message) => ({ specification: message }),
  },

  // ─── قراءة ملف ──────────────────────────────────────
  {
    action: 'READ_FILE',
    patternsAr: [
      /اقرأ\s*(?:ملف|الكود|الكود\s*بتاع)/i,
      /اعرض\s*(?:ملف|الكود|كود)/i,
      /أظهر\s*(?:الكود|الملف)/i,
    ],
    patternsEn: [
      /read\s+(?:file|code)/i,
      /show\s+(?:file|code|me\s+the\s+code)/i,
      /display\s+(?:file|code)/i,
    ],
    paramExtractor: (match, message) => ({ path: message.replace(match[0], '').trim() || message }),
  },

  // ─── تعديل ملف ──────────────────────────────────────
  {
    action: 'EDIT_FILE',
    patternsAr: [
      /عدّل?\s*(?:ملف|الكود|المكون)/i,
      /غيّر?\s*(?:الكود|الملف|المكون)/i,
    ],
    patternsEn: [
      /edit\s+(?:file|code|component)/i,
      /modify\s+(?:file|code)/i,
      /update\s+(?:file|code)/i,
    ],
    paramExtractor: (match, message) => ({ specification: message }),
  },

  // ─── عرض الملفات ────────────────────────────────────
  {
    action: 'LIST_FILES',
    patternsAr: [
      /اعرض\s*(?:الملفات|شجرة|المجلدات|المشروع)/i,
      /شجرة\s*(?:المشروع|الملفات)/i,
      /ما\s*(?:الملفات|المجلدات)/i,
    ],
    patternsEn: [
      /list\s+(?:files|directory|tree)/i,
      /show\s+(?:files|project\s+tree|directory)/i,
      /project\s+tree/i,
    ],
  },

  // ─── بناء أيجنت ─────────────────────────────────────
  {
    action: 'BUILD_AGENT',
    patternsAr: [
      /أريد\s*أيجنت/i,
      /ابنِ?\s*(?:أيجنت|وكيل)/i,
      /أنشئ?\s*(?:أيجنت|وكيل)/i,
      /اصنع?\s*(?:أيجنت|وكيل)/i,
    ],
    patternsEn: [
      /build\s+(?:an?\s+)?agent/i,
      /create\s+(?:an?\s+)?agent/i,
      /i\s+want\s+(?:an?\s+)?agent/i,
    ],
    paramExtractor: (match, message) => ({ specification: message }),
  },

  // ─── بناء مشروع ─────────────────────────────────────
  {
    action: 'BUILD_PROJECT',
    patternsAr: [
      /ابنِ?\s*(?:مشروع|تطبيق|نظام)/i,
      /أنشئ?\s*(?:مشروع|تطبيق|نظام)/i,
      /اصنع?\s*(?:مشروع|تطبيق)/i,
    ],
    patternsEn: [
      /build\s+(?:a\s+)?(?:project|app|application|system)/i,
      /create\s+(?:a\s+)?(?:project|app|application)/i,
      /scaffold\s+(?:a\s+)?(?:project|app)/i,
    ],
    paramExtractor: (match, message) => ({ specification: message }),
  },

  // ─── بناء أداة ──────────────────────────────────────
  {
    action: 'CREATE_TOOL',
    patternsAr: [
      /ابنِ?\s*أداة/i,
      /أنشئ?\s*أداة/i,
      /لا\s*أملك\s*(?:الأداة|أداة)/i,
    ],
    patternsEn: [
      /build\s+(?:a\s+)?tool/i,
      /create\s+(?:a\s+)?tool/i,
      /i\s+(?:don't|dont)\s+have\s+(?:the\s+)?tool/i,
    ],
    paramExtractor: (match, message) => ({ tool_description: message }),
  },

  // ─── تعيين مفتاح API ────────────────────────────────
  {
    action: 'SET_API_KEY',
    patternsAr: [
      /توكن\s+\w+/i,
      /مفتاح\s*(?:API|أبي|ابي)\s+\w+/i,
      /أضف?\s*(?:توكن|مفتاح)\s+/i,
    ],
    patternsEn: [
      /set\s+(?:api\s+)?key\s+/i,
      /add\s+(?:api\s+)?key\s+/i,
      /token\s+\w+/i,
    ],
    paramExtractor: (match) => {
      const text = match[0];
      const keyMatch = text.match(/(?:ghp_|sk-|AIza|gl-)?[a-zA-Z0-9_-]{10,}/);
      const providerMatch = text.match(/(deepseek|gemini|glm|openai)/i);
      return {
        key: keyMatch ? keyMatch[0] : '',
        provider: providerMatch ? providerMatch[1].toLowerCase() : 'auto',
      };
    },
  },

  // ─── حالة الأدمغة التفصيلية (v40.0 Fusion) ──────────
  {
    action: 'BRAIN_STATUS',
    patternsAr: [
      /حال[ةى]\s*(?:الأدمغ[ةى]|الأدمغة|الدماغ|الدمغة)/i,
      /أظهر\s*(?:حال[ةى]\s*)?(?:الأدمغ[ةى]|الدماغ)/i,
      /تقرير\s*(?:الأدمغ[ةى]|الدماغ)/i,
      /ما\s*(?:حال[ةى]\s*)?(?:الأدمغ[ةى]|الدماغ)/i,
      /هل\s+(?:الأدمغ[ةى]|الدماغ)\s+(?:تعمل|شغالة|بخير)/i,
    ],
    patternsEn: [
      /brain\s+status/i,
      /brains?\s+status/i,
      /brain\s+health/i,
      /show\s+brain\s+status/i,
      /brain\s+report/i,
    ],
  },

  // ─── تقييم القدرات (v40.0 Fusion) ──────────────────
  {
    action: 'ASSESS_CAPABILITIES',
    patternsAr: [
      /قيّم?\s*قدراتك/i,
      /قيّم?\s*قدرات/i,
      /ما\s*قدراتك/i,
      /ماذا\s*تستطيع/i,
      /ماذا\s*تقدر/i,
      /ما\s*الذي\s*تستطيعه/i,
      /ما\s*الذي\s*تقدر\s*عليه/i,
      /حصّل?\s*قدراتك/i,
      /فحص\s*القدرات/i,
      /تقييم\s*القدرات/i,
      /تقرير\s*القدرات/i,
    ],
    patternsEn: [
      /assess\s+(?:your\s+)?capabilities/i,
      /what\s+(?:can\s+you|are\s+your\s+capabilities|are\s+you\s+capable\s+of)/i,
      /evaluate\s+(?:your\s+)?capabilities/i,
      /capability\s+(?:assessment|report|check)/i,
      /what\s+are\s+you\s+(?:able|capable)\s+to\s+do/i,
    ],
  },

  // ─── تعديل مشروع خارجي (v40.0 Fusion Step 7) ────────
  {
    action: 'EXTERNAL_MODIFY',
    patternsAr: [
      /عدّل\s*(?:المشروع\s*)?(?:الخارجي|الخارجية)/i,
      /غيّر\s*(?:المشروع\s*)?(?:الخارجي|الخارجية)/i,
      /طوّر\s*(?:المشروع\s*)?(?:الخارجي|الخارجية)/i,
      /أصلح\s*(?:المشروع\s*)?(?:الخارجي|الخارجية)/i,
    ],
    patternsEn: [
      /modify\s+(?:the\s+)?(?:external\s+)?project/i,
      /edit\s+(?:the\s+)?(?:external\s+)?project/i,
      /change\s+(?:the\s+)?(?:external\s+)?project/i,
      /update\s+(?:the\s+)?(?:external\s+)?project/i,
    ],
    paramExtractor: (match, message) => ({ specification: message }),
    immediateResponse: () => 'جاري تحليل المشروع الخارجي وتعديله... 🔧',
  },

  // ─── نشر مشروع (v40.0 Fusion Step 7) ────────────────
  {
    action: 'EXTERNAL_DEPLOY',
    patternsAr: [
      /انشر\s*(?:المشروع|التطبيق|النظام)/i,
      /نشّر\s*(?:المشروع|التطبيق)/i,
      /deploy\s/i,
      /نشر\s*(?:المشروع|التطبيق)/i,
    ],
    patternsEn: [
      /deploy\s+(?:the\s+)?(?:project|app|application)/i,
      /deploy\s+project/i,
      /publish\s+(?:the\s+)?(?:project|app)/i,
      /ship\s+(?:the\s+)?(?:project|app)/i,
    ],
    paramExtractor: (match, message) => ({ specification: message }),
    immediateResponse: () => 'جاري نشر المشروع... 🚀',
  },

  // ─── اختبار ذاتي (v40.0 Fusion Step 11) ──────────────
  {
    action: 'SELF_TEST',
    patternsAr: [
      /اختبر\s*نفسك/i,
      /فحص\s*ذاتي/i,
      /اختبر\s*أنظمتك/i,
      /اختبر\s*النظام/i,
      /فحص\s*شامل/i,
      /هل\s*كل\s*شيء\s*يعمل/i,
      /تشخيص\s*النظام/i,
    ],
    patternsEn: [
      /self\s*test/i,
      /test\s+(?:yourself|yourself|the\s+system)/i,
      /run\s+(?:a\s+)?(?:self\s+)?test/i,
      /diagnose\s+(?:the\s+)?system/i,
      /check\s+all\s+systems/i,
    ],
    immediateResponse: () => '🧪 جاري تشغيل الاختبارات الذاتية...',
  },

  // ─── العقل الموحّد (v40.0 Fusion Step 12) ────────────
  {
    action: 'UNIFIED_MIND',
    patternsAr: [
      /العقل\s*الموحّد/i,
      /العقل\s*الموحد/i,
      /الدماغ\s*الموحّد/i,
      /شغّل\s*العقل\s*الموحّد/i,
      /استخدم\s*العقل\s*الموحّد/i,
      /معالجة\s*موحّدة/i,
      /أنبوب\s*موحّد/i,
    ],
    patternsEn: [
      /unified\s*mind/i,
      /use\s+(?:the\s+)?unified\s*mind/i,
      /activate\s+(?:the\s+)?unified\s*mind/i,
      /process\s+(?:through\s+)?(?:the\s+)?unified\s+pipeline/i,
    ],
    immediateResponse: () => '🧠⚡ تفعيل العقل الموحّد — معالجة عبر الأنبوب الكامل...',
  },
];

// ─── Main Parser ──────────────────────────────────────────────

/**
 * تحليل رسالة المستخدم لاكتشاف الأوامر
 */
export function parseCommand(message: string): ParsedCommand {
  const trimmed = message.trim();

  for (const pattern of COMMAND_PATTERNS) {
    // تحقق من الأنماط العربية
    for (const regex of pattern.patternsAr) {
      const match = trimmed.match(regex);
      if (match) {
        const params = pattern.paramExtractor ? pattern.paramExtractor(match, trimmed) : {};
        const immediateResponse = pattern.immediateResponse ? pattern.immediateResponse(params) : undefined;

        // تنظيف الرسالة من أمر التحكم
        const cleanedMessage = trimmed.replace(regex, '').trim() || trimmed;

        return {
          action: pattern.action,
          params,
          isCommand: true,
          confidence: 0.85,
          cleanedMessage,
          immediateResponse,
        };
      }
    }

    // تحقق من الأنماط الإنجليزية
    for (const regex of pattern.patternsEn) {
      const match = trimmed.match(regex);
      if (match) {
        const params = pattern.paramExtractor ? pattern.paramExtractor(match, trimmed) : {};
        const immediateResponse = pattern.immediateResponse ? pattern.immediateResponse(params) : undefined;

        const cleanedMessage = trimmed.replace(regex, '').trim() || trimmed;

        return {
          action: pattern.action,
          params,
          isCommand: true,
          confidence: 0.85,
          cleanedMessage,
          immediateResponse,
        };
      }
    }
  }

  // لم يتم اكتشاف أمر — محادثة عادية
  return {
    action: 'NORMAL_CHAT',
    params: {},
    isCommand: false,
    confidence: 1.0,
    cleanedMessage: trimmed,
  };
}

/**
 * تحليل متقدم — يستخدم السياق لفهم الأوامر الضمنية
 */
export function parseCommandWithContext(
  message: string,
  context: {
    previousCommands?: ParsedCommand[];
    conversationLength?: number;
    currentMode?: MamounModeId;
  },
): ParsedCommand {
  const basic = parseCommand(message);

  // إذا اكتشف أمراً، أعده مباشرة
  if (basic.isCommand) return basic;

  // تحقق من الأوامر الضمنية
  const lower = message.toLowerCase();

  // "نعم" بعد اقتراح — تأكيد
  if (/^(نعم|أي نعم|أكيد|بالتأكيد|yes|sure|ok|okay)$/i.test(lower.trim())) {
    const lastCommand = context.previousCommands?.slice(-1)[0];
    if (lastCommand && lastCommand.action !== 'NORMAL_CHAT') {
      return {
        action: lastCommand.action,
        params: { ...lastCommand.params, confirmed: true },
        isCommand: true,
        confidence: 0.7,
        cleanedMessage: message,
        immediateResponse: undefined,
      };
    }
  }

  return basic;
}
