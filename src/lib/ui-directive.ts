// ═══════════════════════════════════════════════════════════════════
// UIDirective — نظام واجهة المستخدم التوليدي v63
// Generative UI Component Grammar for SuperMind
// Full mapping for all 22+ intents with atomic component composition
// ═══════════════════════════════════════════════════════════════════

export interface UIAction {
  trigger: 'click' | 'expand' | 'confirm';
  intentId: string;
  payload?: Record<string, unknown>;
  label?: string;
}

export interface UISection {
  type: string;  // Atomic component type
  props: Record<string, unknown>;
  span?: number;  // Grid span (1-12)
  order?: number;
  animation?: { preset: string; delay?: number };
  actions?: UIAction[];
}

export interface UIDirective {
  component: string;  // ScreenRegistry key
  layout: 'single' | 'split' | 'grid';
  sections: UISection[];
}

/**
 * Generate a UI directive from an intent and data.
 * Complete mapping for all 22+ intents in the SuperMindRouter.
 */
export function generateUIDirective(intent: string, data: Record<string, any>): UIDirective {
  switch (intent) {
    case 'projects.list':
      return {
        component: 'ProjectsTracker',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'إجمالي المشاريع', value: (data.projects as unknown[])?.length || data.total || 0, icon: 'folder', color: '#0d7bb5' }, span: 3 },
          { type: 'MetricCard', props: { title: 'نشطة', value: data.stats?.working || data.active || 0, icon: 'play', color: '#4CAF50' }, span: 3 },
          { type: 'MetricCard', props: { title: 'مقترحة', value: data.stats?.proposed || data.proposed || 0, icon: 'lightbulb', color: '#FF9800' }, span: 3 },
          { type: 'MetricCard', props: { title: 'مكتملة', value: data.stats?.done || data.completed || 0, icon: 'check', color: '#2196F3' }, span: 3 },
          { type: 'DataTable', props: { data: data.projects || [], columns: ['nameAr', 'status', 'progress', 'leadingBrain', 'priority'] }, span: 12, actions: [
            { trigger: 'click', intentId: 'projects.monitor', label: 'مراقبة' },
            { trigger: 'click', intentId: 'projects.promote', label: 'ترقية' },
          ]},
        ],
      };

    case 'projects.monitor':
      return {
        component: 'ProjectsTracker',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'إجمالي المشاريع', value: (data.projects as unknown[])?.length || 0, icon: 'folder', color: '#0d7bb5' }, span: 3 },
          { type: 'MetricCard', props: { title: 'قيد التفكير', value: data.stats?.thinking || 0, icon: 'brain', color: '#9C27B0' }, span: 3 },
          { type: 'MetricCard', props: { title: 'قيد العمل', value: data.stats?.working || 0, icon: 'hammer', color: '#4CAF50' }, span: 3 },
          { type: 'MetricCard', props: { title: 'مكتملة', value: data.stats?.done || 0, icon: 'check-circle', color: '#2196F3' }, span: 3 },
          { type: 'ProgressBar', props: { label: 'تقدم المشاريع الإجمالي', value: data.overallProgress || 45, color: '#0d7bb5' }, span: 12 },
          { type: 'DataTable', props: { data: data.projects || [], columns: ['nameAr', 'status', 'progress', 'leadingBrain', 'priority', 'category'] }, span: 12 },
        ],
      };

    case 'projects.promote':
      return {
        component: 'ProjectsTracker',
        layout: 'split',
        sections: [
          { type: 'StatusBadge', props: { status: data.status || 'proposed', size: 'lg' }, span: 6 },
          { type: 'MetricCard', props: { title: 'التقدم', value: `${data.progress || 0}%`, icon: 'chart', color: '#0d7bb5' }, span: 6 },
          { type: 'ActionButtons', props: { buttons: [
            { label: 'تأكيد الترقية', intentId: 'projects.promote', variant: 'approve' as const },
            { label: 'رفض', intentId: 'projects.list', variant: 'reject' as const },
          ] }, span: 12 },
        ],
      };

    case 'site.stats':
      return {
        component: 'SiteStatsPanel',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'الحيوية', value: `${Math.round((Number(data.vitality) || 0) * 100)}%`, icon: 'heart', color: Number(data.vitality) > 0.7 ? '#4CAF50' : '#FF9800' }, span: 3 },
          { type: 'MetricCard', props: { title: 'اتصال LLM', value: data.llm_connectivity ? 'متصل' : 'منفصل', icon: 'wifi', color: data.llm_connectivity ? '#4CAF50' : '#EF4444' }, span: 3 },
          { type: 'MetricCard', props: { title: 'معدل الأخطاء', value: `${Math.round((Number(data.error_rate) || 0) * 100)}%`, icon: 'alert', color: Number(data.error_rate) < 0.1 ? '#4CAF50' : '#EF4444' }, span: 3 },
          { type: 'MetricCard', props: { title: 'وقت التشغيل', value: data.uptime ? `${Math.round(Number(data.uptime) / 3600)}س` : '—', icon: 'clock', color: '#0d7bb5' }, span: 3 },
          { type: 'ProgressBar', props: { label: 'صحة النظام', value: Math.round((Number(data.vitality) || 0) * 100), color: Number(data.vitality) > 0.7 ? '#4CAF50' : '#FF9800' }, span: 12 },
        ],
      };

    case 'research.deep':
      return {
        component: 'ResearchPanel',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'المصادر', value: (data.sources as unknown[])?.length || 0, icon: 'search', color: '#0d7bb5' }, span: 4 },
          { type: 'MetricCard', props: { title: 'العمق', value: data.depth || 'standard', icon: 'layers', color: '#0a9b8a' }, span: 4 },
          { type: 'MetricCard', props: { title: 'الحالة', value: data.status === 'completed' ? 'مكتمل' : 'قيد التنفيذ', icon: 'status', color: data.status === 'completed' ? '#4CAF50' : '#FF9800' }, span: 4 },
          { type: 'ProgressBar', props: { label: 'تقدم البحث', value: data.progress || 0, color: '#0d7bb5' }, span: 12 },
          { type: 'CodeBlock', props: { title: 'ملخص البحث', content: data.summary || data.findings?.join('\n') || 'لا يوجد ملخص متاح', language: 'markdown' }, span: 12 },
        ],
      };

    case 'research.extended':
      return {
        component: 'ResearchPanel',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'المدة المقدرة', value: `${data.estimatedMinutes || 120} دقيقة`, icon: 'timer', color: '#9C27B0' }, span: 3 },
          { type: 'MetricCard', props: { title: 'المصادر المكتشفة', value: (data.sources as unknown[])?.length || 0, icon: 'globe', color: '#0d7bb5' }, span: 3 },
          { type: 'MetricCard', props: { title: 'النتائج', value: (data.findings as unknown[])?.length || 0, icon: 'insight', color: '#0a9b8a' }, span: 3 },
          { type: 'MetricCard', props: { title: 'التوصيات', value: (data.recommendations as unknown[])?.length || 0, icon: 'star', color: '#FF9800' }, span: 3 },
          { type: 'ProgressBar', props: { label: 'مراحل البحث', value: data.progress || 0, color: '#9C27B0' }, span: 12 },
          { type: 'DataTable', props: { data: data.sources || [], columns: ['title', 'relevance', 'url'] }, span: 12 },
        ],
      };

    case 'tool.create':
      return {
        component: 'ToolCreatorPanel',
        layout: 'split',
        sections: [
          { type: 'MetricCard', props: { title: 'حالة الإنشاء', value: data.status || 'جاهز', icon: 'tool', color: '#0d7bb5' }, span: 6 },
          { type: 'StatusBadge', props: { status: data.status || 'ready', size: 'md' }, span: 6 },
          { type: 'CodeBlock', props: { title: 'الكود المُنشأ', content: data.code || '// سيظهر الكود هنا بعد الإنشاء', language: 'python' }, span: 12, actions: [
            { trigger: 'click', intentId: 'tool.create', label: 'تنفيذ' },
            { trigger: 'confirm', intentId: 'tool.create', label: 'تأكيد الإنشاء' },
          ]},
        ],
      };

    case 'agent.build':
      return {
        component: 'AgentBuilderPanel',
        layout: 'split',
        sections: [
          { type: 'MetricCard', props: { title: 'حالة البناء', value: data.status || 'جاهز', icon: 'bot', color: '#0a9b8a' }, span: 6 },
          { type: 'MetricCard', props: { title: 'الأدمغة المخصصة', value: (data.assignedBrains as unknown[])?.length || 1, icon: 'brain', color: '#9C27B0' }, span: 6 },
          { type: 'CodeBlock', props: { title: 'منطق الوكيل', content: data.agent_logic || '// سيظهر المنطق هنا بعد البناء', language: 'python' }, span: 12 },
          { type: 'ActionButtons', props: { buttons: [
            { label: 'تأكيد البناء', intentId: 'agent.build', variant: 'approve' as const },
            { label: 'رفض', intentId: 'agent.build', variant: 'reject' as const },
          ] }, span: 12 },
        ],
      };

    case 'deploy':
      return {
        component: 'DeployPanel',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'حالة النشر', value: data.status || 'جاهز', icon: 'rocket', color: '#0d7bb5' }, span: 4 },
          { type: 'MetricCard', props: { title: 'البيئة', value: data.environment || 'production', icon: 'server', color: '#0a9b8a' }, span: 4 },
          { type: 'MetricCard', props: { title: 'الإصدار', value: data.version || 'v63', icon: 'tag', color: '#448aff' }, span: 4 },
          { type: 'ProgressBar', props: { label: 'تقدم النشر', value: data.progress || 0, color: '#0d7bb5' }, span: 12 },
          { type: 'ActionButtons', props: { buttons: [
            { label: 'تأكيد النشر', intentId: 'deploy', variant: 'approve' as const },
            { label: 'إلغاء', intentId: 'deploy', variant: 'reject' as const },
          ] }, span: 12 },
        ],
      };

    case 'healing':
      return {
        component: 'HealingPanel',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'عمليات الإصلاح', value: data.healing_count || 0, icon: 'heal', color: '#4CAF50' }, span: 4 },
          { type: 'MetricCard', props: { title: 'الحالة', value: data.status || 'نشط', icon: 'shield', color: '#4CAF50' }, span: 4 },
          { type: 'MetricCard', props: { title: 'آخر إصلاح', value: data.last_healing || 'لا يوجد', icon: 'clock', color: '#0d7bb5' }, span: 4 },
          { type: 'ProgressBar', props: { label: 'صحة النظام', value: data.system_health || 85, color: '#4CAF50' }, span: 12 },
          { type: 'DataTable', props: { data: data.healing_log || [], columns: ['time', 'action', 'result'] }, span: 12 },
        ],
      };

    case 'self.modify':
      return {
        component: 'SelfModifyPanel',
        layout: 'split',
        sections: [
          { type: 'MetricCard', props: { title: 'مستوى المخاطر', value: 'عالي', icon: 'warning', color: '#EF4444' }, span: 6 },
          { type: 'StatusBadge', props: { status: data.status || 'proposed', size: 'lg' }, span: 6 },
          { type: 'CodeBlock', props: { title: 'التعديل المقترح', content: data.proposed_change || '// التعديل المقترح', language: 'python' }, span: 12 },
          { type: 'ActionButtons', props: { buttons: [
            { label: 'تأكيد التنفيذ', intentId: 'self.modify', variant: 'approve' as const },
            { label: 'رفض', intentId: 'self.modify', variant: 'reject' as const },
            { label: 'تعديل', intentId: 'self.modify', variant: 'modify' as const },
          ] }, span: 12 },
        ],
      };

    case 'terminal':
      return {
        component: 'TerminalPanel',
        layout: 'single',
        sections: [
          { type: 'CodeBlock', props: { title: 'الطرفية', content: data.output || '$ _', language: 'bash' }, span: 12 },
        ],
      };

    case 'brain.state':
      return {
        component: 'BrainStateOverlay',
        layout: 'grid',
        sections: (data.brains as Array<Record<string, unknown>> || [
          { id: 'neural', name: 'عصبي', confidence: 0.85, status: 'active', model: 'glm-5.1' },
          { id: 'causal', name: 'سببي', confidence: 0.80, status: 'active', model: 'deepseek-reasoner' },
          { id: 'symbolic', name: 'رمزي', confidence: 0.75, status: 'active', model: 'glm-4-plus' },
          { id: 'bayesian', name: 'بيزي', confidence: 0.78, status: 'active', model: 'gemini-2.0-flash' },
          { id: 'world_model', name: 'عالمي', confidence: 0.72, status: 'active', model: 'deepseek-chat' },
        ]).map((brain, i) => ({
          type: 'MetricCard',
          props: {
            title: brain.name || brain.id,
            value: `${Math.round((brain.confidence as number || 0) * 100)}%`,
            subtitle: brain.model || '',
            icon: 'brain',
            color: brain.status === 'active' ? '#4CAF50' : brain.status === 'error' ? '#EF4444' : '#FF9800',
          },
          span: 4,
          order: i,
        })),
      };

    case 'vitals':
      return {
        component: 'SiteStatsPanel',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'الطاقة', value: `${Math.round((Number(data.energy) || 0.8) * 100)}%`, icon: 'battery', color: Number(data.energy) > 0.5 ? '#4CAF50' : '#EF4444' }, span: 3 },
          { type: 'MetricCard', props: { title: 'الضغط', value: `${Math.round((Number(data.stress) || 0.3) * 100)}%`, icon: 'gauge', color: Number(data.stress) < 0.5 ? '#4CAF50' : '#EF4444' }, span: 3 },
          { type: 'MetricCard', props: { title: 'السعادة', value: `${Math.round((Number(data.happiness) || 0.7) * 100)}%`, icon: 'smile', color: '#FF9800' }, span: 3 },
          { type: 'MetricCard', props: { title: 'الارتباط', value: `${Math.round((Number(data.bond_strength) || 0.6) * 100)}%`, icon: 'heart', color: '#E91E63' }, span: 3 },
          { type: 'ProgressBar', props: { label: 'الحيوية العامة', value: Math.round((Number(data.vitality) || 0.75) * 100), color: '#4CAF50' }, span: 12 },
        ],
      };

    case 'update.pull':
      return {
        component: 'UpdatePanel',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'حالة التحديث', value: data.status || 'جاري التحديث...', icon: 'download', color: '#0d7bb5' }, span: 6 },
          { type: 'MetricCard', props: { title: 'الإصدار الجديد', value: data.new_version || '—', icon: 'tag', color: '#0a9b8a' }, span: 6 },
          { type: 'ProgressBar', props: { label: 'تقدم التحديث', value: data.progress || 0, color: '#0d7bb5' }, span: 12 },
          { type: 'ActionButtons', props: { buttons: [
            { label: 'تأكيد التحديث', intentId: 'update.pull', variant: 'approve' as const },
            { label: 'إلغاء', intentId: 'update.pull', variant: 'reject' as const },
          ] }, span: 12 },
        ],
      };

    case 'conversations.search':
      return {
        component: 'ProjectsTracker',
        layout: 'single',
        sections: [
          { type: 'SearchBar', props: { placeholder: 'ابحث في المحادثات السابقة...' }, span: 12 },
          { type: 'DataTable', props: { data: data.conversations || [], columns: ['title', 'date', 'brain', 'summary'] }, span: 12 },
        ],
      };

    case 'capabilities.list':
      return {
        component: 'DefaultScreen',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'القدرات المتاحة', value: (data.capabilities as unknown[])?.length || 10, icon: 'star', color: '#0d7bb5' }, span: 12 },
          ...(data.capabilities || []).map((cap: any, i: number) => ({
            type: 'MetricCard',
            props: { title: cap.name || cap.id, value: cap.status === 'active' ? 'نشط' : 'غير نشط', subtitle: cap.brain || '', icon: cap.icon || 'gear', color: cap.status === 'active' ? '#4CAF50' : '#9E9E9E' },
            span: 4,
            order: i + 1,
          })),
        ],
      };

    case 'code.generate':
      return {
        component: 'DefaultScreen',
        layout: 'split',
        sections: [
          { type: 'MetricCard', props: { title: 'لغة البرمجة', value: data.language || 'python', icon: 'code', color: '#0d7bb5' }, span: 6 },
          { type: 'StatusBadge', props: { status: data.status || 'generated', size: 'md' }, span: 6 },
          { type: 'CodeBlock', props: { title: 'الكود المُولد', content: data.code || '// الكود سيظهر هنا', language: data.language || 'python' }, span: 12, actions: [
            { trigger: 'click', intentId: 'code.generate', label: 'نسخ' },
            { trigger: 'click', intentId: 'terminal', label: 'تنفيذ' },
          ]},
        ],
      };

    case 'project.scaffold':
      return {
        component: 'DefaultScreen',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'اسم المشروع', value: data.projectName || 'مشروع جديد', icon: 'project', color: '#0d7bb5' }, span: 6 },
          { type: 'MetricCard', props: { title: 'القالب', value: data.template || 'default', icon: 'layout', color: '#0a9b8a' }, span: 6 },
          { type: 'ProgressBar', props: { label: 'تقدم الإنشاء', value: data.progress || 0, color: '#0d7bb5' }, span: 12 },
          { type: 'DataTable', props: { data: data.files || [], columns: ['path', 'status', 'size'] }, span: 12 },
        ],
      };

    case 'evolution.status':
      return {
        component: 'DefaultScreen',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'حالة التطور', value: data.status || 'خامل', icon: 'evolve', color: '#9C27B0' }, span: 4 },
          { type: 'MetricCard', props: { title: 'الدورات الكلية', value: data.totalCycles || 0, icon: 'cycle', color: '#0d7bb5' }, span: 4 },
          { type: 'MetricCard', props: { title: 'التحسينات', value: data.totalImprovements || 0, icon: 'up', color: '#4CAF50' }, span: 4 },
        ],
      };

    case 'health.dashboard':
      return {
        component: 'DefaultScreen',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'الصحة العامة', value: data.overall || 'degraded', icon: 'health', color: data.overall === 'healthy' ? '#4CAF50' : '#FF9800' }, span: 12 },
          ...Object.entries(data.components || {}).map(([name, info]: [string, any], i) => ({
            type: 'MetricCard',
            props: { title: name, value: info.status, icon: 'component', color: info.status === 'healthy' ? '#4CAF50' : '#EF4444' },
            span: 3,
            order: i + 1,
          })),
        ],
      };

    case 'workflow':
      return {
        component: 'WorkflowDesigner',
        layout: 'single',
        sections: [
          { type: 'MetricCard', props: { title: 'سير العمل', value: data.status || 'جاهز', icon: 'workflow', color: '#0d7bb5' }, span: 12 },
        ],
      };

    default:
      return {
        component: 'DefaultScreen',
        layout: 'single',
        sections: [
          { type: 'MetricCard', props: { title: 'حالة النظام', value: 'نشط', icon: 'info', color: '#0d7bb5' } },
        ],
      };
  }
}
