// ═══════════════════════════════════════════════════════════════════
// UIDirective — نظام واجهة المستخدم التوليدي
// Generative UI Component Grammar for SuperMind
// Maps intents to structured UI directives with atomic components
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
 * This is the core of the Generative UI system — the BFF returns
 * structured UI instructions instead of just data.
 */
export function generateUIDirective(intent: string, data: Record<string, any>): UIDirective {
  switch (intent) {
    case 'projects.list':
      return {
        component: 'ProjectsTracker',
        layout: 'grid',
        sections: [
          { type: 'MetricCard', props: { title: 'إجمالي المشاريع', value: (data.projects as unknown[])?.length || data.total || 0, icon: 'folder', color: '#0d7bb5' }, span: 3 },
          { type: 'MetricCard', props: { title: 'نشطة', value: data.active || 0, icon: 'play', color: '#4CAF50' }, span: 3 },
          { type: 'MetricCard', props: { title: 'مكتملة', value: data.completed || 0, icon: 'check', color: '#2196F3' }, span: 3 },
          { type: 'MetricCard', props: { title: 'متوقفة', value: data.paused || 0, icon: 'pause', color: '#FF9800' }, span: 3 },
          { type: 'DataTable', props: { data: data.projects || [], columns: ['name', 'status', 'progress', 'brain'] }, span: 12, actions: [
            { trigger: 'click', intentId: 'projects.list', label: 'عرض المشروع' }
          ]},
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
        layout: 'single',
        sections: [
          { type: 'MetricCard', props: { title: 'المصادر', value: (data.sources as unknown[])?.length || 0, icon: 'search', color: '#0d7bb5' }, span: 4 },
          { type: 'MetricCard', props: { title: 'العمق', value: data.depth || 'standard', icon: 'layers', color: '#0a9b8a' }, span: 4 },
          { type: 'MetricCard', props: { title: 'الحالة', value: data.status === 'completed' ? 'مكتمل' : 'قيد التنفيذ', icon: 'status', color: data.status === 'completed' ? '#4CAF50' : '#FF9800' }, span: 4 },
          { type: 'CodeBlock', props: { title: 'ملخص البحث', content: data.summary || 'لا يوجد ملخص متاح', language: 'markdown' }, span: 12 },
        ],
      };

    case 'tool.create':
      return {
        component: 'ToolCreatorPanel',
        layout: 'split',
        sections: [
          { type: 'MetricCard', props: { title: 'حالة الإنشاء', value: data.status || 'جاهز', icon: 'tool', color: '#0d7bb5' }, span: 6 },
          { type: 'CodeBlock', props: { title: 'الكود المُنشأ', content: data.code || '// سيظهر الكود هنا بعد الإنشاء', language: 'python' }, span: 12, actions: [
            { trigger: 'click', intentId: 'tool.create', label: 'تنفيذ' }
          ]},
        ],
      };

    case 'agent.build':
      return {
        component: 'AgentBuilderPanel',
        layout: 'split',
        sections: [
          { type: 'MetricCard', props: { title: 'حالة البناء', value: data.status || 'جاهز', icon: 'bot', color: '#0a9b8a' }, span: 6 },
          { type: 'CodeBlock', props: { title: 'منطق الوكيل', content: data.agent_logic || '// سيظهر المنطق هنا بعد البناء', language: 'python' }, span: 12 },
        ],
      };

    case 'deploy':
      return {
        component: 'DeployPanel',
        layout: 'single',
        sections: [
          { type: 'MetricCard', props: { title: 'حالة النشر', value: data.status || 'جاهز', icon: 'rocket', color: '#0d7bb5' }, span: 4 },
          { type: 'MetricCard', props: { title: 'البيئة', value: data.environment || 'production', icon: 'server', color: '#0a9b8a' }, span: 4 },
          { type: 'MetricCard', props: { title: 'الإصدار', value: data.version || 'v62', icon: 'tag', color: '#448aff' }, span: 4 },
          { type: 'ProgressBar', props: { label: 'تقدم النشر', value: data.progress || 0, color: '#0d7bb5' }, span: 12 },
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
          { type: 'DataTable', props: { data: data.healing_log || [], columns: ['time', 'action', 'result'] }, span: 12 },
        ],
      };

    case 'self.modify':
      return {
        component: 'DefaultScreen',
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
        component: 'DefaultScreen',
        layout: 'grid',
        sections: (data.brains as Array<Record<string, unknown>> || []).map((brain, i) => ({
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

    case 'update.pull':
      return {
        component: 'DefaultScreen',
        layout: 'single',
        sections: [
          { type: 'MetricCard', props: { title: 'حالة التحديث', value: data.status || 'جاري التحديث...', icon: 'download', color: '#0d7bb5' }, span: 6 },
          { type: 'MetricCard', props: { title: 'الإصدار الجديد', value: data.new_version || '—', icon: 'tag', color: '#0a9b8a' }, span: 6 },
          { type: 'ProgressBar', props: { label: 'تقدم التحديث', value: data.progress || 0, color: '#0d7bb5' }, span: 12 },
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
