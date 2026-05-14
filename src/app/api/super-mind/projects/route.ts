// ═══════════════════════════════════════════════════════════════════
// SuperMind Projects BFF Route — نظام تتبع المشاريع
// Full project lifecycle: thinking → proposed → working → done
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

// Project lifecycle stages
type ProjectStatus = 'thinking' | 'proposed' | 'working' | 'done';

interface Project {
  id: string;
  name: string;
  nameAr: string;
  description: string;
  status: ProjectStatus;
  progress: number;
  category: string;
  leadingBrain?: string;
  assignedBrains: string[];
  milestones: Array<{ id: string; title: string; status: string }>;
  tags: string[];
  priority: 'low' | 'medium' | 'high' | 'critical';
  createdAt: string;
  updatedAt: string;
  sourceConversationId?: string;
  relatedProjects: string[];
}

// In-memory project store (will be backed by backend DB)
let projectsStore: Project[] = [
  { id: 'p1', nameAr: 'متجر إلكتروني ذكي', name: 'Smart E-commerce', description: 'منصة تجارة إلكترونية مع وكيل ذكي', status: 'working', progress: 65, category: 'ecommerce', leadingBrain: 'neural', assignedBrains: ['neural', 'causal'], milestones: [{ id: 'm1', title: 'التصميم', status: 'completed' }, { id: 'm2', title: 'التطوير', status: 'in_progress' }], tags: ['تجارة', 'ذكاء اصطناعي'], priority: 'high', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), relatedProjects: [] },
  { id: 'p2', nameAr: 'نظام تحليل البيانات', name: 'Data Analytics System', description: 'نظام تحليل بيانات متقدم', status: 'proposed', progress: 20, category: 'analytics', leadingBrain: 'causal', assignedBrains: ['causal', 'bayesian'], milestones: [{ id: 'm3', title: 'البحث', status: 'completed' }], tags: ['بيانات', 'تحليل'], priority: 'medium', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), relatedProjects: ['p1'] },
  { id: 'p3', nameAr: 'روبوت تداول', name: 'Trading Bot', description: 'وكيل تداول ذكي', status: 'thinking', progress: 5, category: 'trading', leadingBrain: 'bayesian', assignedBrains: ['bayesian', 'world_model'], milestones: [], tags: ['تداول', 'مخاطر'], priority: 'critical', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), relatedProjects: [] },
  { id: 'p4', nameAr: 'مدير وسائل التواصل', name: 'Social Media Manager', description: 'أتمتة إدارة حسابات التواصل', status: 'done', progress: 100, category: 'social', leadingBrain: 'symbolic', assignedBrains: ['symbolic', 'neural'], milestones: [{ id: 'm4', title: 'الإطلاق', status: 'completed' }], tags: ['تواصل', 'أتمتة'], priority: 'low', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), relatedProjects: [] },
];

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const status = searchParams.get('status') as ProjectStatus | null;
  const category = searchParams.get('category');

  // Try backend first
  try {
    const backendRes = await fetch(`${BACKEND_URL}/api/project-mgmt/projects?status=${status || ''}&category=${category || ''}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(10000),
    });
    if (backendRes.ok) {
      const data = await backendRes.json();
      if (data.projects && data.projects.length > 0) {
        return NextResponse.json({ projects: data.projects, total: data.projects.length, source: 'backend' });
      }
    }
  } catch { /* backend unavailable */ }

  // Fallback to local store
  let filtered = [...projectsStore];
  if (status) filtered = filtered.filter(p => p.status === status);
  if (category) filtered = filtered.filter(p => p.category === category);

  return NextResponse.json({
    projects: filtered,
    total: filtered.length,
    stats: {
      thinking: projectsStore.filter(p => p.status === 'thinking').length,
      proposed: projectsStore.filter(p => p.status === 'proposed').length,
      working: projectsStore.filter(p => p.status === 'working').length,
      done: projectsStore.filter(p => p.status === 'done').length,
    },
    source: 'local',
  });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { action, projectId, projectData } = body;

  switch (action) {
    case 'create': {
      const newProject: Project = {
        id: `p-${Date.now()}`,
        nameAr: projectData?.nameAr || 'مشروع جديد',
        name: projectData?.name || 'New Project',
        description: projectData?.description || '',
        status: 'thinking',
        progress: 0,
        category: projectData?.category || 'general',
        assignedBrains: projectData?.assignedBrains || ['neural'],
        milestones: [],
        tags: projectData?.tags || [],
        priority: projectData?.priority || 'medium',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        relatedProjects: [],
      };
      projectsStore.push(newProject);

      // Try to sync with backend
      try {
        await fetch(`${BACKEND_URL}/api/project-mgmt/projects`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newProject),
          signal: AbortSignal.timeout(5000),
        });
      } catch { /* ignore */ }

      return NextResponse.json({ project: newProject, source: 'local' });
    }

    case 'promote': {
      const project = projectsStore.find(p => p.id === projectId);
      if (!project) {
        return NextResponse.json({ error: 'المشروع غير موجود' }, { status: 404 });
      }
      const statusOrder: ProjectStatus[] = ['thinking', 'proposed', 'working', 'done'];
      const currentIndex = statusOrder.indexOf(project.status);
      if (currentIndex < statusOrder.length - 1) {
        project.status = statusOrder[currentIndex + 1];
        project.updatedAt = new Date().toISOString();
      }
      return NextResponse.json({ project, source: 'local' });
    }

    case 'demote': {
      const project = projectsStore.find(p => p.id === projectId);
      if (!project) {
        return NextResponse.json({ error: 'المشروع غير موجود' }, { status: 404 });
      }
      const statusOrder: ProjectStatus[] = ['thinking', 'proposed', 'working', 'done'];
      const currentIndex = statusOrder.indexOf(project.status);
      if (currentIndex > 0) {
        project.status = statusOrder[currentIndex - 1];
        project.updatedAt = new Date().toISOString();
      }
      return NextResponse.json({ project, source: 'local' });
    }

    case 'update': {
      const project = projectsStore.find(p => p.id === projectId);
      if (!project) {
        return NextResponse.json({ error: 'المشروع غير موجود' }, { status: 404 });
      }
      Object.assign(project, projectData, { updatedAt: new Date().toISOString() });
      return NextResponse.json({ project, source: 'local' });
    }

    default:
      return NextResponse.json({ error: 'إجراء غير معروف' }, { status: 400 });
  }
}
