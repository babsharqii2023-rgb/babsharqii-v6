// ═══════════════════════════════════════════════════════════════════
// ScreenRegistry — سجل الشاشات الديناميكية
// Maps intent names to React component references
// Components are loaded dynamically to reduce initial bundle
// ═══════════════════════════════════════════════════════════════════

import type { ComponentType } from 'react';

export interface ScreenDefinition {
  id: string;
  component: string; // component file name (for dynamic import)
  labelAr: string;
  labelEn: string;
  icon: string;
  description: string;
}

export const SCREEN_REGISTRY: Record<string, ScreenDefinition> = {
  ProjectsTracker: {
    id: 'ProjectsTracker',
    component: 'ProjectsTracker',
    labelAr: 'متتبع المشاريع',
    labelEn: 'Projects Tracker',
    icon: '📁',
    description: 'عرض وإدارة المشاريع بنظام كانبان',
  },
  SiteStatsPanel: {
    id: 'SiteStatsPanel',
    component: 'SiteStatsPanel',
    labelAr: 'إحصائيات الموقع',
    labelEn: 'Site Statistics',
    icon: '📊',
    description: 'لوحة إحصائيات الموقع والمقاييس',
  },
  ResearchPanel: {
    id: 'ResearchPanel',
    component: 'ResearchPanel',
    labelAr: 'البحث العميق',
    labelEn: 'Deep Research',
    icon: '🔍',
    description: 'لوحة البحث العميق مع التحديثات المباشرة',
  },
  TerminalPanel: {
    id: 'TerminalPanel',
    component: 'TerminalPanel',
    labelAr: 'الطرفية',
    labelEn: 'Terminal',
    icon: '💻',
    description: 'محاكي طرفية مع إدخال/إخراج الأوامر',
  },
  HealingPanel: {
    id: 'HealingPanel',
    component: 'HealingPanel',
    labelAr: 'الإصلاح الذاتي',
    labelEn: 'Self-Healing',
    icon: '💚',
    description: 'تشخيصات الإصلاح الذاتي',
  },
  ToolCreatorPanel: {
    id: 'ToolCreatorPanel',
    component: 'ToolCreatorPanel',
    labelAr: 'منشئ الأدوات',
    labelEn: 'Tool Creator',
    icon: '🔧',
    description: 'معالج إنشاء الأدوات',
  },
  AgentBuilderPanel: {
    id: 'AgentBuilderPanel',
    component: 'AgentBuilderPanel',
    labelAr: 'بناء الوكلاء',
    labelEn: 'Agent Builder',
    icon: '🤖',
    description: 'منشئ الوكلاء الأذكياء',
  },
  DeployPanel: {
    id: 'DeployPanel',
    component: 'DeployPanel',
    labelAr: 'لوحة النشر',
    labelEn: 'Deploy Panel',
    icon: '🚀',
    description: 'لوحة النشر والتحكم بالإصدارات',
  },
};

/**
 * الحصول على تعريف شاشة بواسطة المعرف
 */
export function getScreenDefinition(screenId: string): ScreenDefinition | null {
  return SCREEN_REGISTRY[screenId] || null;
}

/**
 * الحصول على مكون الشاشة ديناميكياً
 * Dynamic import of screen components
 */
export async function loadScreenComponent(screenId: string): Promise<ComponentType<Record<string, unknown>> | null> {
  try {
    switch (screenId) {
      case 'ProjectsTracker': {
        const mod = await import('@/components/brain/ProjectsTracker');
        return mod.default;
      }
      case 'SiteStatsPanel': {
        const mod = await import('@/components/brain/SiteStatsPanel');
        return mod.default;
      }
      case 'ResearchPanel': {
        const mod = await import('@/components/brain/ResearchPanel');
        return mod.default;
      }
      case 'TerminalPanel': {
        const mod = await import('@/components/brain/TerminalPanel');
        return mod.default;
      }
      case 'HealingPanel': {
        const mod = await import('@/components/brain/HealingPanel');
        return mod.default;
      }
      case 'ToolCreatorPanel': {
        const mod = await import('@/components/brain/ToolCreatorPanel');
        return mod.default;
      }
      case 'AgentBuilderPanel': {
        const mod = await import('@/components/brain/AgentBuilderPanel');
        return mod.default;
      }
      case 'DeployPanel': {
        const mod = await import('@/components/brain/DeployPanel');
        return mod.default;
      }
      default:
        return null;
    }
  } catch (err) {
    console.warn(`[ScreenRegistry] Failed to load screen: ${screenId}`, err);
    return null;
  }
}
