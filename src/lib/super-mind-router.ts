// ═══════════════════════════════════════════════════════════════════
// SuperMind Router — مُوَجِّه العقل الخارق
// Smart intent detection from user messages
// Determines: API endpoint, screen component, animation, sound
// ═══════════════════════════════════════════════════════════════════

export type SuperMindIntent =
  | 'projects.list'
  | 'projects.monitor'
  | 'site.stats'
  | 'research.deep'
  | 'research.extended'
  | 'tool.create'
  | 'agent.build'
  | 'deploy'
  | 'healing'
  | 'self.modify'
  | 'workflow'
  | 'terminal'
  | 'brain.state'
  | 'vitals'
  | 'conversations.search'
  | 'update.pull'
  | 'default';

export interface SuperMindRoute {
  intent: SuperMindIntent;
  screenComponent: string;
  apiEndpoint: string;
  animation: string;
  soundEvent: string;
  activatedBrains: string[];
  confidence: number;
  labelAr: string;
  labelEn: string;
  icon: string;
}

// ─── Intent Detection Rules ────────────────────────────────────

interface IntentRule {
  intent: SuperMindIntent;
  screenComponent: string;
  apiEndpoint: string;
  animation: string;
  soundEvent: string;
  activatedBrains: string[];
  labelAr: string;
  labelEn: string;
  icon: string;
  patterns: RegExp[];
  keywords: string[];
  priority: number; // higher = checked first
}

const INTENT_RULES: IntentRule[] = [
  {
    intent: 'projects.list',
    screenComponent: 'ProjectsTracker',
    apiEndpoint: '/api/super-mind/chat',
    animation: 'slideRight',
    soundEvent: 'intent.detected',
    activatedBrains: ['neural', 'symbolic', 'world_model'],
    labelAr: 'المشاريع',
    labelEn: 'Projects',
    icon: '📁',
    patterns: [
      /مشروع|مشاريع|بروجكت/i,
      /project|projects/i,
      /بناء|تطوير|طور/i,
      /ماذا تبنى|ماذا تعمل/i,
    ],
    keywords: ['مشروع', 'مشاريع', 'بناء', 'تطوير', 'project', 'projects', 'build'],
    priority: 80,
  },
  {
    intent: 'site.stats',
    screenComponent: 'SiteStatsPanel',
    apiEndpoint: '/api/super-mind/chat',
    animation: 'fadeIn',
    soundEvent: 'intent.detected',
    activatedBrains: ['causal', 'bayesian', 'world_model'],
    labelAr: 'إحصائيات الموقع',
    labelEn: 'Site Stats',
    icon: '📊',
    patterns: [
      /إحصائ|احصائ|إحصاء|احصاء|stats|statistics/i,
      /زيارات|زوار|traffic|visitors/i,
      /موقع|site|website/i,
      /أداء|performance|analytics/i,
    ],
    keywords: ['إحصائيات', 'زيارات', 'موقع', 'أداء', 'stats', 'analytics', 'traffic'],
    priority: 75,
  },
  {
    intent: 'research.deep',
    screenComponent: 'ResearchPanel',
    apiEndpoint: '/api/super-mind/chat',
    animation: 'expandDown',
    soundEvent: 'intent.detected',
    activatedBrains: ['neural', 'causal', 'world_model'],
    labelAr: 'البحث العميق',
    labelEn: 'Deep Research',
    icon: '🔍',
    patterns: [
      /بحث|ابحث|research|search/i,
      /استكشف|explore|investigate/i,
      /دراس|study|analyze|حلل/i,
    ],
    keywords: ['بحث', 'ابحث', 'استكشف', 'حلل', 'research', 'search', 'explore'],
    priority: 70,
  },
  {
    intent: 'tool.create',
    screenComponent: 'ToolCreatorPanel',
    apiEndpoint: '/api/super-mind/chat',
    animation: 'slideUp',
    soundEvent: 'intent.detected',
    activatedBrains: ['symbolic', 'neural', 'bayesian'],
    labelAr: 'إنشاء أداة',
    labelEn: 'Tool Creator',
    icon: '🔧',
    patterns: [
      /أنشئ أداة|أداة جديدة|create tool|make tool/i,
      /أداة|tool|utility/i,
      /بناء أداة|build tool/i,
    ],
    keywords: ['أداة', 'أدوات', 'tool', 'tools', 'أنشئ أداة'],
    priority: 65,
  },
  {
    intent: 'agent.build',
    screenComponent: 'AgentBuilderPanel',
    apiEndpoint: '/api/super-mind/chat',
    animation: 'slideUp',
    soundEvent: 'intent.detected',
    activatedBrains: ['neural', 'causal', 'symbolic'],
    labelAr: 'بناء وكيل',
    labelEn: 'Agent Builder',
    icon: '🤖',
    patterns: [
      /وكيل|agent|bots?/i,
      /بناء وكيل|build agent|create agent/i,
      /سرب|swarm/i,
    ],
    keywords: ['وكيل', 'وكلاء', 'agent', 'bots', 'سرب'],
    priority: 65,
  },
  {
    intent: 'deploy',
    screenComponent: 'DeployPanel',
    apiEndpoint: '/api/super-mind/chat',
    animation: 'zoomIn',
    soundEvent: 'intent.detected',
    activatedBrains: ['neural', 'causal', 'bayesian'],
    labelAr: 'النشر',
    labelEn: 'Deploy',
    icon: '🚀',
    patterns: [
      /نشر|deploy|launch|إطلاق/i,
      /رفع|upload|publish/i,
      /إنتاج|production/i,
    ],
    keywords: ['نشر', 'deploy', 'إطلاق', 'رفع', 'launch'],
    priority: 70,
  },
  {
    intent: 'healing',
    screenComponent: 'HealingPanel',
    apiEndpoint: '/api/super-mind/chat',
    animation: 'pulseIn',
    soundEvent: 'brain.activate',
    activatedBrains: ['causal', 'bayesian', 'neural'],
    labelAr: 'الإصلاح الذاتي',
    labelEn: 'Self-Healing',
    icon: '💚',
    patterns: [
      /أصلح|إصلاح|heal|fix|repair/i,
      /مشكلة|خربان|broken|error|خطأ/i,
      /صيانة|maintenance/i,
    ],
    keywords: ['أصلح', 'إصلاح', 'مشكلة', 'خطأ', 'heal', 'fix', 'repair'],
    priority: 75,
  },
  {
    intent: 'self.modify',
    screenComponent: 'SelfModifyPanel',
    apiEndpoint: '/api/super-mind/kernel',
    animation: 'pulseIn',
    soundEvent: 'brain.activate',
    activatedBrains: ['neural', 'symbolic', 'world_model'],
    labelAr: 'التعديل الذاتي',
    labelEn: 'Self-Modify',
    icon: '🧬',
    patterns: [
      /عدّل نفس|تعديل ذاتي|self.modif|self.modify/i,
      /طوّر نفسك|تطور ذاتي|self.improv/i,
      /غيّر كودك|غيّر نفسك/i,
    ],
    keywords: ['عدّل نفسك', 'طوّر نفسك', 'self-modify', 'self-improve'],
    priority: 80,
  },
  {
    intent: 'workflow',
    screenComponent: 'WorkflowDesigner',
    apiEndpoint: '/api/super-mind/chat',
    animation: 'slideRight',
    soundEvent: 'intent.detected',
    activatedBrains: ['symbolic', 'neural', 'causal'],
    labelAr: 'سير العمل',
    labelEn: 'Workflow',
    icon: '⚡',
    patterns: [
      /سير عمل|workflow|automation/i,
      /أتمت|automate|pipeline/i,
    ],
    keywords: ['سير عمل', 'أتمتة', 'workflow', 'automate'],
    priority: 60,
  },
  {
    intent: 'terminal',
    screenComponent: 'TerminalPanel',
    apiEndpoint: '/api/super-mind/chat',
    animation: 'slideUp',
    soundEvent: 'intent.detected',
    activatedBrains: ['symbolic', 'neural'],
    labelAr: 'الطرفية',
    labelEn: 'Terminal',
    icon: '💻',
    patterns: [
      /طرفية|terminal|cmd|أمر|تشغيل/i,
      /نفّذ|execute|run command/i,
      /كونسول|console|shell/i,
    ],
    keywords: ['طرفية', 'terminal', 'أمر', 'نفّذ', 'command'],
    priority: 70,
  },
  {
    intent: 'brain.state',
    screenComponent: 'BrainStateOverlay',
    apiEndpoint: '/api/super-mind/brain-state',
    animation: 'fadeIn',
    soundEvent: 'brain.activate',
    activatedBrains: ['neural', 'causal', 'symbolic', 'bayesian', 'world_model'],
    labelAr: 'حالة الأدمغة',
    labelEn: 'Brain State',
    icon: '🧠',
    patterns: [
      /دماغ|أدمغة|brain/i,
      /حالة الدماغ|brain state/i,
      /وعي|إدراك|consciousness/i,
    ],
    keywords: ['دماغ', 'أدمغة', 'وعي', 'brain', 'consciousness'],
    priority: 75,
  },
  {
    intent: 'projects.monitor',
    screenComponent: 'ProjectsTracker',
    apiEndpoint: '/api/super-mind/projects',
    animation: 'fadeIn',
    soundEvent: 'intent.detected',
    activatedBrains: ['neural', 'causal'],
    labelAr: 'مراقبة المشروع',
    labelEn: 'Project Monitor',
    icon: '📡',
    patterns: [
      /راقب|حالة المشروع|monitor project/i,
      /halat|status project/i,
      /تقدم المشروع|project progress/i,
    ],
    keywords: ['راقب', 'حالة المشروع', 'monitor', 'status', 'تقدم'],
    priority: 72,
  },
  {
    intent: 'research.extended',
    screenComponent: 'ResearchPanel',
    apiEndpoint: '/api/super-mind/research',
    animation: 'expandDown',
    soundEvent: 'brain.activate',
    activatedBrains: ['neural', 'causal', 'world_model', 'bayesian'],
    labelAr: 'البحث الممتد',
    labelEn: 'Extended Research',
    icon: '🔬',
    patterns: [
      /بحث ممتد|extended research/i,
      /بحث طويل|taheel|deep analysis/i,
      /تحليل معمق|thorough research/i,
    ],
    keywords: ['بحث ممتد', 'extended research', 'بحث طويل', 'تحليل معمق'],
    priority: 68,
  },
  {
    intent: 'vitals',
    screenComponent: 'SiteStatsPanel',
    apiEndpoint: '/api/super-mind/vitals',
    animation: 'fadeIn',
    soundEvent: 'brain.activate',
    activatedBrains: ['causal', 'bayesian'],
    labelAr: 'الحيوية',
    labelEn: 'Vitals',
    icon: '❤️',
    patterns: [
      /حيوية|صحة|vitals|health|sihha/i,
      /نبض|heartbeat|pulse/i,
      /مؤشرات|indicators|metrics/i,
    ],
    keywords: ['حيوية', 'صحة', 'vitals', 'health', 'نبض', 'مؤشرات'],
    priority: 73,
  },
  {
    intent: 'conversations.search',
    screenComponent: 'ProjectsTracker',
    apiEndpoint: '/api/super-mind/chat',
    animation: 'fadeIn',
    soundEvent: 'intent.detected',
    activatedBrains: ['neural', 'bayesian'],
    labelAr: 'البحث في المحادثات',
    labelEn: 'Search Conversations',
    icon: '💬',
    patterns: [
      /محادثات سابقة|previous conversations/i,
      /ابحث في المحادثات|search conversations/i,
    ],
    keywords: ['محادثات', 'conversations', 'سجل'],
    priority: 55,
  },
  {
    intent: 'update.pull',
    screenComponent: 'UpdatePanel',
    apiEndpoint: '/api/super-mind/update',
    animation: 'pulseIn',
    soundEvent: 'brain.activate',
    activatedBrains: ['neural', 'causal', 'symbolic'],
    labelAr: 'تحديث ذاتي',
    labelEn: 'Self Update',
    icon: '🔄',
    patterns: [
      /تحديث|update|سحب التحديثات|pull updates/i,
      /جيت هب|github|git/i,
      /حدث نفسك|self.update|auto.update/i,
      /اسحب التحديثات|pull changes/i,
    ],
    keywords: ['تحديث', 'سحب', 'github', 'git', 'update', 'pull', 'حدث نفسك'],
    priority: 85,
  },
];

// ─── Default Route ─────────────────────────────────────────────

const DEFAULT_ROUTE: SuperMindRoute = {
  intent: 'default',
  screenComponent: '',
  apiEndpoint: '/api/super-mind/chat',
  animation: 'fadeIn',
  soundEvent: 'message.receive',
  activatedBrains: ['neural'],
  confidence: 0.5,
  labelAr: 'محادثة عامة',
  labelEn: 'General Chat',
  icon: '💬',
};

// ─── Route Function ────────────────────────────────────────────

/**
 * تحليل رسالة المستخدم لتحديد النية والمسار المناسب
 * Analyzes user message to determine intent and appropriate route
 */
export function routeIntent(message: string): SuperMindRoute {
  if (!message || message.trim().length === 0) {
    return DEFAULT_ROUTE;
  }

  const lower = message.toLowerCase().trim();
  let bestMatch: { rule: IntentRule; score: number } | null = null;

  for (const rule of INTENT_RULES) {
    let score = 0;

    // Pattern matching (strongest signal)
    for (const pattern of rule.patterns) {
      if (pattern.test(lower)) {
        score += 30;
      }
    }

    // Keyword matching
    for (const keyword of rule.keywords) {
      if (lower.includes(keyword.toLowerCase())) {
        score += 15;
      }
    }

    // Add priority bonus
    score += rule.priority / 10;

    if (!bestMatch || score > bestMatch.score) {
      bestMatch = { rule, score };
    }
  }

  if (!bestMatch || bestMatch.score < 5) {
    return DEFAULT_ROUTE;
  }

  const { rule } = bestMatch;
  const confidence = Math.min(1, bestMatch.score / 100);

  return {
    intent: rule.intent,
    screenComponent: rule.screenComponent,
    apiEndpoint: rule.apiEndpoint,
    animation: rule.animation,
    soundEvent: rule.soundEvent,
    activatedBrains: rule.activatedBrains,
    confidence,
    labelAr: rule.labelAr,
    labelEn: rule.labelEn,
    icon: rule.icon,
  };
}

/**
 * الحصول على قائمة بجميع النوايا المتاحة
 */
export function getAllIntents(): SuperMindIntent[] {
  return INTENT_RULES.map(r => r.intent).concat('default');
}

/**
 * الحصول على مسار بنية معينة
 */
export function getRouteForIntent(intent: SuperMindIntent): SuperMindRoute {
  if (intent === 'default') return DEFAULT_ROUTE;
  const rule = INTENT_RULES.find(r => r.intent === intent);
  if (!rule) return DEFAULT_ROUTE;
  return {
    intent: rule.intent,
    screenComponent: rule.screenComponent,
    apiEndpoint: rule.apiEndpoint,
    animation: rule.animation,
    soundEvent: rule.soundEvent,
    activatedBrains: rule.activatedBrains,
    confidence: 1,
    labelAr: rule.labelAr,
    labelEn: rule.labelEn,
    icon: rule.icon,
  };
}
