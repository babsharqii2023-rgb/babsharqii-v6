// ═══════════════════════════════════════════════════════════════════
// SuperMind Router — مُوَجِّه العقل الخارق v63
// Two-stage intent detection: Keyword pre-filter + LLM-assisted classification
// Determines: API endpoint, screen component, animation, sound
// Supports 17+ intents with compound request handling
// ═══════════════════════════════════════════════════════════════════

export type SuperMindIntent =
  | 'projects.list'
  | 'projects.monitor'
  | 'projects.promote'
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
  | 'capabilities.list'
  | 'code.generate'
  | 'project.scaffold'
  | 'evolution.status'
  | 'health.dashboard'
  | 'default';

export interface SuperMindRoute {
  intent: SuperMindIntent;
  screenComponent: string;
  apiEndpoint: string;
  httpMethod: 'GET' | 'POST';
  animation: string;
  soundEvent: string;
  activatedBrains: string[];
  confidence: number;
  confidenceThreshold: number;
  requiresConfirmation: boolean;
  autonomyLevel: 0 | 1 | 2 | 3;
  compoundWith?: SuperMindIntent[];
  labelAr: string;
  labelEn: string;
  icon: string;
}

// ─── Intent Detection Rules ────────────────────────────────────

interface IntentRule {
  intent: SuperMindIntent;
  screenComponent: string;
  apiEndpoint: string;
  httpMethod: 'GET' | 'POST';
  animation: string;
  soundEvent: string;
  activatedBrains: string[];
  confidenceThreshold: number;
  requiresConfirmation: boolean;
  autonomyLevel: 0 | 1 | 2 | 3;
  compoundWith?: SuperMindIntent[];
  labelAr: string;
  labelEn: string;
  icon: string;
  patterns: RegExp[];
  keywords: string[];
  priority: number;
}

const INTENT_RULES: IntentRule[] = [
  {
    intent: 'projects.list',
    screenComponent: 'ProjectsTracker',
    apiEndpoint: '/api/super-mind/projects',
    httpMethod: 'GET',
    animation: 'slideRight',
    soundEvent: 'intent.detected',
    activatedBrains: ['neural', 'symbolic', 'world_model'],
    confidenceThreshold: 0.5,
    requiresConfirmation: false,
    autonomyLevel: 2,
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
    intent: 'projects.monitor',
    screenComponent: 'ProjectsTracker',
    apiEndpoint: '/api/super-mind/projects',
    httpMethod: 'GET',
    animation: 'fadeIn',
    soundEvent: 'intent.detected',
    activatedBrains: ['neural', 'causal'],
    confidenceThreshold: 0.5,
    requiresConfirmation: false,
    autonomyLevel: 2,
    labelAr: 'مراقبة المشروع',
    labelEn: 'Project Monitor',
    icon: '📡',
    patterns: [
      /راقب|حالة المشروع|monitor project/i,
      /تقدم المشروع|project progress/i,
    ],
    keywords: ['راقب', 'حالة المشروع', 'monitor', 'status', 'تقدم'],
    priority: 72,
  },
  {
    intent: 'projects.promote',
    screenComponent: 'ProjectsTracker',
    apiEndpoint: '/api/super-mind/projects/promote',
    httpMethod: 'POST',
    animation: 'slideUp',
    soundEvent: 'brain.activate',
    activatedBrains: ['neural', 'causal', 'world_model'],
    confidenceThreshold: 0.7,
    requiresConfirmation: true,
    autonomyLevel: 1,
    compoundWith: ['projects.list'],
    labelAr: 'ترقية مشروع',
    labelEn: 'Promote Project',
    icon: '⬆️',
    patterns: [
      /ابدأ المشروع|ابدأ عمل|promote project/i,
      /نشّط المشروع|activate project/i,
      /حوّل المقترح|convert proposal/i,
    ],
    keywords: ['ابدأ المشروع', 'نشّط', 'promote', 'activate'],
    priority: 78,
  },
  {
    intent: 'site.stats',
    screenComponent: 'SiteStatsPanel',
    apiEndpoint: '/api/super-mind/stats',
    httpMethod: 'GET',
    animation: 'fadeIn',
    soundEvent: 'intent.detected',
    activatedBrains: ['causal', 'bayesian', 'world_model'],
    confidenceThreshold: 0.4,
    requiresConfirmation: false,
    autonomyLevel: 2,
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
    apiEndpoint: '/api/super-mind/research',
    httpMethod: 'POST',
    animation: 'expandDown',
    soundEvent: 'intent.detected',
    activatedBrains: ['neural', 'causal', 'world_model'],
    confidenceThreshold: 0.5,
    requiresConfirmation: true,
    autonomyLevel: 1,
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
    intent: 'research.extended',
    screenComponent: 'ResearchPanel',
    apiEndpoint: '/api/super-mind/research/extended',
    httpMethod: 'POST',
    animation: 'expandDown',
    soundEvent: 'brain.activate',
    activatedBrains: ['neural', 'causal', 'world_model', 'bayesian'],
    confidenceThreshold: 0.6,
    requiresConfirmation: true,
    autonomyLevel: 1,
    compoundWith: ['research.deep'],
    labelAr: 'البحث الممتد',
    labelEn: 'Extended Research',
    icon: '🔬',
    patterns: [
      /بحث ممتد|extended research/i,
      /بحث طويل|deep analysis/i,
      /تحليل معمق|thorough research/i,
    ],
    keywords: ['بحث ممتد', 'extended research', 'بحث طويل', 'تحليل معمق'],
    priority: 68,
  },
  {
    intent: 'tool.create',
    screenComponent: 'ToolCreatorPanel',
    apiEndpoint: '/api/super-mind/tools',
    httpMethod: 'POST',
    animation: 'slideUp',
    soundEvent: 'intent.detected',
    activatedBrains: ['symbolic', 'neural', 'bayesian'],
    confidenceThreshold: 0.6,
    requiresConfirmation: true,
    autonomyLevel: 1,
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
    apiEndpoint: '/api/super-mind/agents',
    httpMethod: 'POST',
    animation: 'slideUp',
    soundEvent: 'intent.detected',
    activatedBrains: ['neural', 'causal', 'symbolic'],
    confidenceThreshold: 0.6,
    requiresConfirmation: true,
    autonomyLevel: 1,
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
    apiEndpoint: '/api/super-mind/deploy',
    httpMethod: 'POST',
    animation: 'zoomIn',
    soundEvent: 'brain.activate',
    activatedBrains: ['neural', 'causal', 'bayesian'],
    confidenceThreshold: 0.7,
    requiresConfirmation: true,
    autonomyLevel: 0,
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
    apiEndpoint: '/api/super-mind/healing',
    httpMethod: 'POST',
    animation: 'pulseIn',
    soundEvent: 'brain.activate',
    activatedBrains: ['causal', 'bayesian', 'neural'],
    confidenceThreshold: 0.4,
    requiresConfirmation: false,
    autonomyLevel: 2,
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
    httpMethod: 'POST',
    animation: 'pulseIn',
    soundEvent: 'brain.activate',
    activatedBrains: ['neural', 'symbolic', 'world_model'],
    confidenceThreshold: 0.8,
    requiresConfirmation: true,
    autonomyLevel: 0,
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
    httpMethod: 'POST',
    animation: 'slideRight',
    soundEvent: 'intent.detected',
    activatedBrains: ['symbolic', 'neural', 'causal'],
    confidenceThreshold: 0.5,
    requiresConfirmation: false,
    autonomyLevel: 2,
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
    apiEndpoint: '/api/super-mind/terminal',
    httpMethod: 'POST',
    animation: 'slideUp',
    soundEvent: 'intent.detected',
    activatedBrains: ['symbolic', 'neural'],
    confidenceThreshold: 0.4,
    requiresConfirmation: false,
    autonomyLevel: 2,
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
    httpMethod: 'GET',
    animation: 'fadeIn',
    soundEvent: 'brain.activate',
    activatedBrains: ['neural', 'causal', 'symbolic', 'bayesian', 'world_model'],
    confidenceThreshold: 0.3,
    requiresConfirmation: false,
    autonomyLevel: 2,
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
    intent: 'vitals',
    screenComponent: 'SiteStatsPanel',
    apiEndpoint: '/api/super-mind/vitals',
    httpMethod: 'GET',
    animation: 'fadeIn',
    soundEvent: 'brain.activate',
    activatedBrains: ['causal', 'bayesian'],
    confidenceThreshold: 0.4,
    requiresConfirmation: false,
    autonomyLevel: 2,
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
    apiEndpoint: '/api/super-mind/conversations',
    httpMethod: 'GET',
    animation: 'fadeIn',
    soundEvent: 'intent.detected',
    activatedBrains: ['neural', 'bayesian'],
    confidenceThreshold: 0.5,
    requiresConfirmation: false,
    autonomyLevel: 2,
    labelAr: 'البحث في المحادثات',
    labelEn: 'Search Conversations',
    icon: '💬',
    patterns: [
      /محادثات سابقة|previous conversations/i,
      /ابحث في المحادثات|search conversations/i,
      /سجل المحادثات|chat history/i,
    ],
    keywords: ['محادثات', 'conversations', 'سجل', 'history'],
    priority: 55,
  },
  {
    intent: 'update.pull',
    screenComponent: 'UpdatePanel',
    apiEndpoint: '/api/super-mind/update',
    httpMethod: 'POST',
    animation: 'pulseIn',
    soundEvent: 'brain.activate',
    activatedBrains: ['neural', 'causal', 'symbolic'],
    confidenceThreshold: 0.7,
    requiresConfirmation: true,
    autonomyLevel: 0,
    labelAr: 'تحديث ذاتي',
    labelEn: 'Self Update',
    icon: '🔄',
    patterns: [
      /تحديث|update|سحب التحديثات|pull updates/i,
      /جيت هب|github|git/i,
      /حدث نفسك|self.update|auto.update/i,
    ],
    keywords: ['تحديث', 'سحب', 'github', 'git', 'update', 'pull'],
    priority: 85,
  },
  {
    intent: 'capabilities.list',
    screenComponent: 'DefaultScreen',
    apiEndpoint: '/api/super-mind/capabilities',
    httpMethod: 'GET',
    animation: 'fadeIn',
    soundEvent: 'intent.detected',
    activatedBrains: ['neural', 'symbolic'],
    confidenceThreshold: 0.4,
    requiresConfirmation: false,
    autonomyLevel: 2,
    labelAr: 'القدرات',
    labelEn: 'Capabilities',
    icon: '🎯',
    patterns: [
      /قدرات|capabilities|what can you/i,
      /ماذا تستطيع|ما قدراتك/i,
      /مهارات|skills/i,
    ],
    keywords: ['قدرات', 'مهارات', 'capabilities', 'skills'],
    priority: 50,
  },
  {
    intent: 'code.generate',
    screenComponent: 'DefaultScreen',
    apiEndpoint: '/api/super-mind/code-generate',
    httpMethod: 'POST',
    animation: 'slideUp',
    soundEvent: 'intent.detected',
    activatedBrains: ['symbolic', 'neural', 'causal'],
    confidenceThreshold: 0.6,
    requiresConfirmation: true,
    autonomyLevel: 1,
    labelAr: 'توليد كود',
    labelEn: 'Code Generation',
    icon: '⌨️',
    patterns: [
      /اكتب كود|generate code|code gen/i,
      /برمج|program|script/i,
      /أنشئ دالة|create function/i,
    ],
    keywords: ['كود', 'برمجة', 'code', 'generate', 'program'],
    priority: 67,
  },
  {
    intent: 'project.scaffold',
    screenComponent: 'DefaultScreen',
    apiEndpoint: '/api/super-mind/scaffold',
    httpMethod: 'POST',
    animation: 'slideUp',
    soundEvent: 'brain.activate',
    activatedBrains: ['neural', 'symbolic', 'world_model', 'causal'],
    confidenceThreshold: 0.7,
    requiresConfirmation: true,
    autonomyLevel: 0,
    compoundWith: ['projects.list'],
    labelAr: 'بناء مشروع جديد',
    labelEn: 'Scaffold Project',
    icon: '🏗️',
    patterns: [
      /أنشئ مشروع|create project|scaffold/i,
      /مشروع جديد من الصفر|new project from scratch/i,
    ],
    keywords: ['أنشئ مشروع', 'scaffold', 'مشروع جديد'],
    priority: 82,
  },
  {
    intent: 'evolution.status',
    screenComponent: 'DefaultScreen',
    apiEndpoint: '/api/super-mind/evolution',
    httpMethod: 'GET',
    animation: 'fadeIn',
    soundEvent: 'intent.detected',
    activatedBrains: ['neural', 'causal'],
    confidenceThreshold: 0.5,
    requiresConfirmation: false,
    autonomyLevel: 2,
    labelAr: 'حالة التطور',
    labelEn: 'Evolution Status',
    icon: '📈',
    patterns: [
      /تطور|evolution|evolve/i,
      /تحسن ذاتي|self improvement/i,
      /دورة التطور|evolution cycle/i,
    ],
    keywords: ['تطور', 'evolution', 'تحسن', 'improvement'],
    priority: 58,
  },
  {
    intent: 'health.dashboard',
    screenComponent: 'DefaultScreen',
    apiEndpoint: '/api/super-mind/health',
    httpMethod: 'GET',
    animation: 'fadeIn',
    soundEvent: 'brain.activate',
    activatedBrains: ['causal', 'bayesian', 'neural'],
    confidenceThreshold: 0.5,
    requiresConfirmation: false,
    autonomyLevel: 2,
    labelAr: 'لوحة الصحة',
    labelEn: 'Health Dashboard',
    icon: '🏥',
    patterns: [
      /لوحة الصحة|health dashboard|system health/i,
      /تقرير الصحة|health report/i,
      /مراقبة صحية|health monitoring/i,
    ],
    keywords: ['صحة', 'health', 'dashboard', 'مراقبة'],
    priority: 56,
  },
];

// ─── Default Route ─────────────────────────────────────────────

const DEFAULT_ROUTE: SuperMindRoute = {
  intent: 'default',
  screenComponent: '',
  apiEndpoint: '/api/super-mind/chat',
  httpMethod: 'POST',
  animation: 'fadeIn',
  soundEvent: 'message.receive',
  activatedBrains: ['neural'],
  confidence: 0.5,
  confidenceThreshold: 0.0,
  requiresConfirmation: false,
  autonomyLevel: 2,
  labelAr: 'محادثة عامة',
  labelEn: 'General Chat',
  icon: '💬',
};

// ─── LLM-Assisted Intent Classification ────────────────────────

/**
 * Second-stage LLM classification for ambiguous messages.
 * Sends the message to the backend ChatGovernor for deeper analysis.
 * Falls back to keyword matching if LLM is unavailable.
 */
async function classifyWithLLM(message: string, context: string[]): Promise<SuperMindIntent | null> {
  try {
    const response = await fetch('/api/super-mind/intent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        context: context.slice(-5),
        availableIntents: INTENT_RULES.map(r => ({
          id: r.intent,
          labelAr: r.labelAr,
          labelEn: r.labelEn,
          keywords: r.keywords,
        })),
      }),
    });

    if (!response.ok) return null;

    const data = await response.json();
    const classifiedIntent = data?.intent as SuperMindIntent;

    // Verify the intent exists in our rules
    if (classifiedIntent && INTENT_RULES.some(r => r.intent === classifiedIntent)) {
      return classifiedIntent;
    }
    return null;
  } catch {
    // LLM unavailable — return null to fall back to keyword matching
    return null;
  }
}

// ─── Route Function ────────────────────────────────────────────

/**
 * تحليل رسالة المستخدم لتحديد النية والمسار المناسب
 * Stage 1: Fast keyword/pattern pre-filter
 * Stage 2: LLM-assisted classification for ambiguous messages
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

  // If confidence is below threshold, mark for LLM-assisted classification
  const needsLLMClassification = confidence < rule.confidenceThreshold;

  return {
    intent: rule.intent,
    screenComponent: rule.screenComponent,
    apiEndpoint: rule.apiEndpoint,
    httpMethod: rule.httpMethod,
    animation: rule.animation,
    soundEvent: rule.soundEvent,
    activatedBrains: rule.activatedBrains,
    confidence,
    confidenceThreshold: rule.confidenceThreshold,
    requiresConfirmation: rule.requiresConfirmation,
    autonomyLevel: rule.autonomyLevel,
    compoundWith: rule.compoundWith,
    labelAr: rule.labelAr,
    labelEn: rule.labelEn,
    icon: rule.icon,
  };
}

/**
 * Async version that uses LLM for ambiguous messages
 */
export async function routeIntentAsync(
  message: string,
  conversationHistory: string[] = []
): Promise<SuperMindRoute> {
  const keywordResult = routeIntent(message);

  // If keyword confidence is high enough, return immediately
  if (keywordResult.confidence >= keywordResult.confidenceThreshold) {
    return keywordResult;
  }

  // Stage 2: Try LLM-assisted classification
  const llmIntent = await classifyWithLLM(message, conversationHistory);

  if (llmIntent) {
    const rule = INTENT_RULES.find(r => r.intent === llmIntent);
    if (rule) {
      return {
        intent: rule.intent,
        screenComponent: rule.screenComponent,
        apiEndpoint: rule.apiEndpoint,
        httpMethod: rule.httpMethod,
        animation: rule.animation,
        soundEvent: rule.soundEvent,
        activatedBrains: rule.activatedBrains,
        confidence: 0.85, // LLM classification gets high confidence
        confidenceThreshold: rule.confidenceThreshold,
        requiresConfirmation: rule.requiresConfirmation,
        autonomyLevel: rule.autonomyLevel,
        compoundWith: rule.compoundWith,
        labelAr: rule.labelAr,
        labelEn: rule.labelEn,
        icon: rule.icon,
      };
    }
  }

  return keywordResult;
}

/**
 * Detect compound requests (e.g., "Show me project stats AND start research")
 */
export function detectCompoundIntents(message: string): SuperMindRoute[] {
  const routes: SuperMindRoute[] = [];
  const lower = message.toLowerCase();

  // Split by conjunctions
  const conjunctions = [' و ', ' وايضاً ', ' وأيضاً ', ' and ', ' also ', ' plus ', ' ثم ', ' ثم '];
  let parts = [message];

  for (const conj of conjunctions) {
    const newParts: string[] = [];
    for (const part of parts) {
      const split = part.split(conj);
      newParts.push(...split);
    }
    parts = newParts;
  }

  if (parts.length > 1) {
    for (const part of parts) {
      const trimmed = part.trim();
      if (trimmed.length > 3) {
        const route = routeIntent(trimmed);
        if (route.intent !== 'default') {
          routes.push(route);
        }
      }
    }
  }

  return routes.length > 1 ? routes : [];
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
    httpMethod: rule.httpMethod,
    animation: rule.animation,
    soundEvent: rule.soundEvent,
    activatedBrains: rule.activatedBrains,
    confidence: 1,
    confidenceThreshold: rule.confidenceThreshold,
    requiresConfirmation: rule.requiresConfirmation,
    autonomyLevel: rule.autonomyLevel,
    compoundWith: rule.compoundWith,
    labelAr: rule.labelAr,
    labelEn: rule.labelEn,
    icon: rule.icon,
  };
}

/**
 * الحصول على جميع قواعد التوجيه (للعرض في UI)
 */
export function getIntentCatalog(): IntentRule[] {
  return [...INTENT_RULES];
}
