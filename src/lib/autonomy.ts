// ═══════════════════════════════════════════════════════════════════
// Autonomy System — نظام الاستقلالية
// Human-ON-the-Loop: 4 autonomy levels for different operations
// Level 0: Full Approval Required (destructive/irreversible)
// Level 1: Notify Before Execution (significant but reversible)
// Level 2: Execute and Report (routine operations)
// Level 3: Autonomous (background operations)
// ═══════════════════════════════════════════════════════════════════

export type AutonomyLevel = 0 | 1 | 2 | 3;

export interface AutonomyConfig {
  operationType: string;
  level: AutonomyLevel;
  confirmTimeoutMs: number;  // For Level 1: auto-proceed after timeout
  requiresConfirmation: boolean;
  riskLabel: string;
  riskColor: string;
}

export const AUTONOMY_RULES: Record<string, AutonomyConfig> = {
  'self.modify': {
    operationType: 'self.modify',
    level: 0,
    confirmTimeoutMs: 0,
    requiresConfirmation: true,
    riskLabel: 'حرج — تعديل ذاتي',
    riskColor: '#EF4444',
  },
  'deploy': {
    operationType: 'deploy',
    level: 0,
    confirmTimeoutMs: 0,
    requiresConfirmation: true,
    riskLabel: 'حرج — نشر إنتاجي',
    riskColor: '#EF4444',
  },
  'update.pull': {
    operationType: 'update.pull',
    level: 0,
    confirmTimeoutMs: 0,
    requiresConfirmation: true,
    riskLabel: 'حرج — تحديث النظام',
    riskColor: '#EF4444',
  },
  'tool.create': {
    operationType: 'tool.create',
    level: 1,
    confirmTimeoutMs: 30000,
    requiresConfirmation: true,
    riskLabel: 'متوسط — إنشاء أداة',
    riskColor: '#FF9800',
  },
  'agent.build': {
    operationType: 'agent.build',
    level: 1,
    confirmTimeoutMs: 30000,
    requiresConfirmation: true,
    riskLabel: 'متوسط — بناء وكيل',
    riskColor: '#FF9800',
  },
  'research.deep': {
    operationType: 'research.deep',
    level: 1,
    confirmTimeoutMs: 30000,
    requiresConfirmation: true,
    riskLabel: 'متوسط — بحث عميق',
    riskColor: '#FF9800',
  },
  'projects.list': {
    operationType: 'projects.list',
    level: 2,
    confirmTimeoutMs: 0,
    requiresConfirmation: false,
    riskLabel: 'منخفض — قراءة',
    riskColor: '#4CAF50',
  },
  'site.stats': {
    operationType: 'site.stats',
    level: 2,
    confirmTimeoutMs: 0,
    requiresConfirmation: false,
    riskLabel: 'منخفض — قراءة',
    riskColor: '#4CAF50',
  },
  'healing': {
    operationType: 'healing',
    level: 2,
    confirmTimeoutMs: 0,
    requiresConfirmation: false,
    riskLabel: 'منخفض — إصلاح ذاتي',
    riskColor: '#4CAF50',
  },
  'brain.state': {
    operationType: 'brain.state',
    level: 2,
    confirmTimeoutMs: 0,
    requiresConfirmation: false,
    riskLabel: 'منخفض — قراءة',
    riskColor: '#4CAF50',
  },
  'projects.monitor': {
    operationType: 'projects.monitor',
    level: 2,
    confirmTimeoutMs: 0,
    requiresConfirmation: false,
    riskLabel: 'منخفض — قراءة',
    riskColor: '#4CAF50',
  },
  'research.extended': {
    operationType: 'research.extended',
    level: 1,
    confirmTimeoutMs: 30000,
    requiresConfirmation: true,
    riskLabel: 'متوسط — بحث ممتد',
    riskColor: '#FF9800',
  },
  'vitals': {
    operationType: 'vitals',
    level: 2,
    confirmTimeoutMs: 0,
    requiresConfirmation: false,
    riskLabel: 'منخفض — قراءة',
    riskColor: '#4CAF50',
  },
  'terminal': {
    operationType: 'terminal',
    level: 2,
    confirmTimeoutMs: 0,
    requiresConfirmation: false,
    riskLabel: 'منخفض — طرفية',
    riskColor: '#4CAF50',
  },
  'default': {
    operationType: 'default',
    level: 2,
    confirmTimeoutMs: 0,
    requiresConfirmation: false,
    riskLabel: 'منخفض — عام',
    riskColor: '#4CAF50',
  },
};

export function getAutonomyConfig(intentId: string): AutonomyConfig {
  return AUTONOMY_RULES[intentId] || AUTONOMY_RULES['default'];
}

export function requiresConfirmation(intentId: string): boolean {
  return getAutonomyConfig(intentId).requiresConfirmation;
}

export function getAutonomyLevel(intentId: string): AutonomyLevel {
  return getAutonomyConfig(intentId).level;
}
