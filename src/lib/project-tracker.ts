// ═══════════════════════════════════════════════════════════════════
// Project Tracker — نظام تتبع المشاريع
// Full project lifecycle: thinking → proposed → working → done
// LocalStorage persistence + API sync
// ═══════════════════════════════════════════════════════════════════

export type ProjectStatus = 'thinking' | 'proposed' | 'working' | 'done';
export type ProjectPriority = 'low' | 'medium' | 'high' | 'critical';

export interface Milestone {
  id: string;
  title: string;
  status: 'pending' | 'in_progress' | 'completed';
  dueDate?: string;
  completedDate?: string;
}

export interface Project {
  id: string;
  name: string;
  nameAr?: string;
  description: string;
  status: ProjectStatus;
  priority: ProjectPriority;
  category: string;
  createdAt: number;
  updatedAt: number;
  progressPercent: number;
  assignedBrains: string[];
  tags: string[];
  milestones: Milestone[];
  sourceConversationId?: string;
  researchReferences: string[];
  relatedProjects: string[];
}

const STORAGE_KEY = 'supermind_projects';

function generateId(): string {
  return `proj_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function getProjects(): Project[] {
  if (typeof window === 'undefined') return [];
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

export function saveProjects(projects: Project[]): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(projects));
}

export function createProject(partial: Partial<Project>): Project {
  const project: Project = {
    id: generateId(),
    name: partial.name || 'مشروع جديد',
    nameAr: partial.nameAr || partial.name,
    description: partial.description || '',
    status: 'thinking',
    priority: partial.priority || 'medium',
    category: partial.category || 'general',
    createdAt: Date.now(),
    updatedAt: Date.now(),
    progressPercent: 0,
    assignedBrains: partial.assignedBrains || ['neural'],
    tags: partial.tags || [],
    milestones: [],
    researchReferences: partial.researchReferences || [],
    relatedProjects: partial.relatedProjects || [],
  };

  const projects = getProjects();
  projects.unshift(project);
  saveProjects(projects);
  return project;
}

export function updateProjectStatus(projectId: string, newStatus: ProjectStatus): Project | null {
  const projects = getProjects();
  const idx = projects.findIndex((p) => p.id === projectId);
  if (idx === -1) return null;

  projects[idx].status = newStatus;
  projects[idx].updatedAt = Date.now();

  // Update progress based on status
  const statusProgress: Record<ProjectStatus, number> = {
    thinking: 10,
    proposed: 30,
    working: 60,
    done: 100,
  };
  projects[idx].progressPercent = Math.max(projects[idx].progressPercent, statusProgress[newStatus]);

  saveProjects(projects);
  return projects[idx];
}

export function deleteProject(projectId: string): boolean {
  const projects = getProjects();
  const filtered = projects.filter((p) => p.id !== projectId);
  if (filtered.length === projects.length) return false;
  saveProjects(filtered);
  return true;
}

export function getProjectById(projectId: string): Project | undefined {
  return getProjects().find((p) => p.id === projectId);
}

export function getProjectsByStatus(status: ProjectStatus): Project[] {
  return getProjects().filter((p) => p.status === status);
}

export function getProjectStats(): {
  total: number;
  thinking: number;
  proposed: number;
  working: number;
  done: number;
} {
  const projects = getProjects();
  return {
    total: projects.length,
    thinking: projects.filter((p) => p.status === 'thinking').length,
    proposed: projects.filter((p) => p.status === 'proposed').length,
    working: projects.filter((p) => p.status === 'working').length,
    done: projects.filter((p) => p.status === 'done').length,
  };
}

export async function syncWithBackend(): Promise<Project[]> {
  try {
    const res = await fetch('/api/super-mind/projects');
    if (res.ok) {
      const data = await res.json();
      if (data.projects && Array.isArray(data.projects)) {
        // Merge backend data with local data
        const local = getProjects();
        const localIds = new Set(local.map((p) => p.id));
        const merged = [
          ...data.projects.filter((p: Project) => !localIds.has(p.id)),
          ...local,
        ];
        saveProjects(merged);
        return merged;
      }
    }
  } catch {
    // Offline — return local data
  }
  return getProjects();
}
