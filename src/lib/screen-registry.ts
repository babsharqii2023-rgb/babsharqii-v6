// ═══════════════════════════════════════════════════════════════════
// ScreenRegistry — سجل الشاشات الديناميكية v63
// Full mapping for all 22+ intents with dynamic loading
// ═══════════════════════════════════════════════════════════════════

import type { ComponentType } from 'react';

export interface ScreenDefinition {
  id: string;
  component: string;
  labelAr: string;
  labelEn: string;
  icon: string;
  description: string;
  animation: string;
  transitionDuration: number;
}

export const SCREEN_REGISTRY: Record<string, ScreenDefinition> = {
  ProjectsTracker: {
    id: 'ProjectsTracker',
    component: 'ProjectsTracker',
    labelAr: 'متتبع المشاريع',
    labelEn: 'Projects Tracker',
    icon: '📁',
    description: 'عرض وإدارة المشاريع بنظام كانبان مع دورة حياة كاملة',
    animation: 'slideRight',
    transitionDuration: 800,
  },
  SiteStatsPanel: {
    id: 'SiteStatsPanel',
    component: 'SiteStatsPanel',
    labelAr: 'إحصائيات الموقع',
    labelEn: 'Site Statistics',
    icon: '📊',
    description: 'لوحة إحصائيات الموقع والمقاييس',
    animation: 'fadeIn',
    transitionDuration: 600,
  },
  ResearchPanel: {
    id: 'ResearchPanel',
    component: 'ResearchPanel',
    labelAr: 'البحث العميق',
    labelEn: 'Deep Research',
    icon: '🔍',
    description: 'لوحة البحث العميق والممتد مع التحديثات المباشرة عبر SSE',
    animation: 'expandDown',
    transitionDuration: 700,
  },
  TerminalPanel: {
    id: 'TerminalPanel',
    component: 'TerminalPanel',
    labelAr: 'الطرفية',
    labelEn: 'Terminal',
    icon: '💻',
    description: 'محاكي طرفية مع إدخال/إخراج الأوامر',
    animation: 'slideUp',
    transitionDuration: 500,
  },
  HealingPanel: {
    id: 'HealingPanel',
    component: 'HealingPanel',
    labelAr: 'الإصلاح الذاتي',
    labelEn: 'Self-Healing',
    icon: '💚',
    description: 'تشخيصات الإصلاح الذاتي مع سجل العمليات',
    animation: 'pulseIn',
    transitionDuration: 600,
  },
  ToolCreatorPanel: {
    id: 'ToolCreatorPanel',
    component: 'ToolCreatorPanel',
    labelAr: 'منشئ الأدوات',
    labelEn: 'Tool Creator',
    icon: '🔧',
    description: 'معالج إنشاء الأدوات مع معاينة الكود',
    animation: 'slideUp',
    transitionDuration: 700,
  },
  AgentBuilderPanel: {
    id: 'AgentBuilderPanel',
    component: 'AgentBuilderPanel',
    labelAr: 'بناء الوكلاء',
    labelEn: 'Agent Builder',
    icon: '🤖',
    description: 'منشئ الوكلاء الأذكياء مع اختيار الأدمغة',
    animation: 'slideUp',
    transitionDuration: 700,
  },
  DeployPanel: {
    id: 'DeployPanel',
    component: 'DeployPanel',
    labelAr: 'لوحة النشر',
    labelEn: 'Deploy Panel',
    icon: '🚀',
    description: 'لوحة النشر والتحكم بالإصدارات',
    animation: 'zoomIn',
    transitionDuration: 800,
  },
  DefaultScreen: {
    id: 'DefaultScreen',
    component: 'DefaultScreen',
    labelAr: 'شاشة توليدية',
    labelEn: 'Generative Screen',
    icon: '📋',
    description: 'شاشة توليدية تعرض مكونات ذرية بناءً على UIDirective',
    animation: 'fadeIn',
    transitionDuration: 500,
  },
  SelfModifyPanel: {
    id: 'SelfModifyPanel',
    component: 'SelfModifyPanel',
    labelAr: 'التعديل الذاتي',
    labelEn: 'Self-Modify',
    icon: '🧬',
    description: 'اقتراحات التعديل الذاتي مع عرض التغييرات وتأكيد',
    animation: 'pulseIn',
    transitionDuration: 800,
  },
  WorkflowDesigner: {
    id: 'WorkflowDesigner',
    component: 'WorkflowDesigner',
    labelAr: 'مصمم سير العمل',
    labelEn: 'Workflow Designer',
    icon: '⚡',
    description: 'مصمم سير العمل المرئي مع رسم بياني',
    animation: 'slideRight',
    transitionDuration: 700,
  },
  BrainStateOverlay: {
    id: 'BrainStateOverlay',
    component: 'BrainStateOverlay',
    labelAr: 'تراكب الأدمغة',
    labelEn: 'Brain State Overlay',
    icon: '🧠',
    description: 'حالة تفصيلية لكل دماغ مع المقاييس',
    animation: 'fadeIn',
    transitionDuration: 600,
  },
  UpdatePanel: {
    id: 'UpdatePanel',
    component: 'UpdatePanel',
    labelAr: 'التحديث الذاتي',
    labelEn: 'Update Panel',
    icon: '🔄',
    description: 'لوحة التحديث مع التقدم والتفاصيل',
    animation: 'pulseIn',
    transitionDuration: 600,
  },
};

export function getScreenDefinition(screenId: string): ScreenDefinition | null {
  return SCREEN_REGISTRY[screenId] || null;
}

export async function loadScreenComponent(screenId: string): Promise<ComponentType<Record<string, unknown>> | null> {
  try {
    switch (screenId) {
      case 'ProjectsTracker': { const mod = await import('@/components/brain/ProjectsTracker'); return mod.default; }
      case 'SiteStatsPanel': { const mod = await import('@/components/brain/SiteStatsPanel'); return mod.default; }
      case 'ResearchPanel': { const mod = await import('@/components/brain/ResearchPanel'); return mod.default; }
      case 'TerminalPanel': { const mod = await import('@/components/brain/TerminalPanel'); return mod.default; }
      case 'HealingPanel': { const mod = await import('@/components/brain/HealingPanel'); return mod.default; }
      case 'ToolCreatorPanel': { const mod = await import('@/components/brain/ToolCreatorPanel'); return mod.default; }
      case 'AgentBuilderPanel': { const mod = await import('@/components/brain/AgentBuilderPanel'); return mod.default; }
      case 'DeployPanel': { const mod = await import('@/components/brain/DeployPanel'); return mod.default; }
      case 'DefaultScreen': { const mod = await import('@/components/brain/DefaultScreen'); return mod.default; }
      case 'SelfModifyPanel': { const mod = await import('@/components/brain/SelfModifyPanel'); return mod.default; }
      case 'WorkflowDesigner': { const mod = await import('@/components/brain/WorkflowDesigner'); return mod.default; }
      case 'BrainStateOverlay': { const mod = await import('@/components/brain/BrainStateOverlay'); return mod.default; }
      case 'UpdatePanel': { const mod = await import('@/components/brain/UpdatePanel'); return mod.default; }
      default: return null;
    }
  } catch (err) {
    console.warn(`[ScreenRegistry] Failed to load screen: ${screenId}`, err);
    return null;
  }
}
