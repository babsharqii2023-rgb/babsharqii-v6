// ═══════════════════════════════════════════════════════════════════
// مأمون v63 — Unified Store (SuperMind) — Full Slice Architecture
// Separated slices: ChatSlice, BrainSlice, ProjectSlice, SoundSlice, ScreenSlice
// Persists to localStorage + syncs with backend API
// ═══════════════════════════════════════════════════════════════════

import { create } from 'zustand';
import {
  saveMessagesToLocal,
  loadMessagesFromLocal,
  clearLocalMessages,
  saveUserPreferences,
  loadUserPreferences,
} from './chat-memory';

// ─── Types ─────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'brain';
  content: string;
  timestamp: number;
  brain?: string;
  confidence?: number;
  metadata?: Record<string, unknown>;
  isRealDeliberation?: boolean;
  warningMessage?: string;
  cards?: Array<{ title: string; content: string; actions?: string[] }>;
  quickActions?: Array<{ label: string; intent: string }>;
}

export interface BrainInfo {
  id: string;
  name: string;
  nameAr: string;
  nameEn: string;
  status: 'active' | 'idle' | 'sleeping' | 'error';
  confidence: number;
  latency: number;
  model?: string;
  enabled?: boolean;
  color: string;
  icon?: string;
  lastActivity?: number;
  deliberationCount?: number;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  category: string;
  status: string;
  priority: string;
  progress: number;
  tags: string[];
  source: string;
}

export interface AppNotification {
  id: string;
  title: string;
  message: string;
  type: string;
  timestamp: number;
  read: boolean;
}

export interface DeliberationData {
  brainResponses?: Record<string, unknown>;
  consensusLevel?: number;
  cjs?: number;
  conflictDetected?: boolean;
  mirrorReflection?: string;
  queryType?: string;
  winner?: string;
}

export interface Approval {
  id: string;
  title: string;
  description: string;
  riskLevel: 'low' | 'medium' | 'high';
  status: 'pending' | 'approved' | 'rejected';
  timestamp: number;
  autonomyLevel: 0 | 1 | 2 | 3;
  countdownMs?: number;
}

export interface BrainVote {
  brainId: string;
  brainName: string;
  content: string;
  confidence: number;
  weight: number;
  stance: 'support' | 'oppose' | 'neutral';
}

export interface FeedforwardSuggestion {
  id: string;
  type: 'clarification' | 'related' | 'next_step' | 'tool_suggestion';
  text: string;
  confidence: number;
  brainSource?: string;
}

export interface SelfModification {
  id: string;
  type: string;
  description: string;
  status: 'pending' | 'approved' | 'applied' | 'rejected';
  risk_level: number;
}

export type BrainVoteType = BrainVote;

// v63 SuperMind: Full Project type matching specification
export interface Project {
  id: string;
  name: string;
  nameAr: string;
  category: string;
  description?: string;
  status: 'thinking' | 'proposed' | 'working' | 'done';
  progress: number;
  leadingBrain?: string;
  assignedBrains: string[];
  milestones: Array<{ id: string; title: string; status: 'pending' | 'in_progress' | 'completed'; dueDate?: string; completedDate?: string }>;
  tags: string[];
  priority: 'low' | 'medium' | 'high' | 'critical';
  progressPercent: number;
  relatedProjects: string[];
  sourceConversationId?: string;
  researchReferences: string[];
  createdAt: string;
  updatedAt: string;
}

// v63 SuperMind: Research task type
export interface ResearchTask {
  id: string;
  query: string;
  status: 'discovering' | 'extracting' | 'synthesizing' | 'recommending' | 'completed' | 'failed';
  progress: number;
  sources: Array<{ url: string; title: string; relevance: number }>;
  findings: string[];
  recommendations: string[];
  depth: 'quick' | 'standard' | 'extended';
  estimatedMinutes: number;
  startedAt: string;
  completedAt?: string;
}

// v63 SuperMind: Brain state for BrainSlice
export interface BrainState {
  id: string;
  status: 'active' | 'idle' | 'sleeping' | 'error';
  confidence: number;
  latency: number;
  model: string;
  lastActivity: number;
  deliberationCount: number;
  temperature: number;
  memoryUsage: number;
}

// ─── Store Interface ───────────────────────────────────────────

interface AppStore {
  // ── Chat Slice ────────────────────────────────────────────────
  messages: ChatMessage[];
  isThinking: boolean;
  defaultModel: string;
  sendMessage: (text: string) => void;
  addMessage: (msg: Partial<ChatMessage> & { id: string; role: ChatMessage['role']; content: string; timestamp: number }) => void;
  setThinking: (v: boolean) => void;
  clearChat: () => void;
  hydrateFromDB: () => void;
  isHydrated: boolean;
  isStreaming: boolean;
  setIsStreaming: (v: boolean) => void;

  // ── Brain Slice ───────────────────────────────────────────────
  brains: BrainInfo[];
  currentBrain: string;
  setCurrentBrain: (id: string) => void;
  systemHealth: number;
  isConscious: boolean;
  setSystemHealth: (v: number) => void;
  updateBrainStatus: (id: string, status: BrainInfo['status']) => void;
  updateBrainConfidence: (id: string, confidence: number) => void;
  brainStates: Record<string, BrainState>;
  setBrainStates: (states: Record<string, BrainState>) => void;
  deliberationProgress: number;
  setDeliberationProgress: (p: number) => void;
  thinkingBrains: string[];
  setThinkingBrains: (brains: string[]) => void;
  deliberationData: DeliberationData | null;
  updateDeliberationData: (data: DeliberationData) => void;
  isActive: boolean;
  currentTopic: string;
  brainResponses: Record<string, unknown>;
  consensusLevel: number;
  brainVotes: BrainVote[];
  startDeliberation: (topic: string) => void;
  endDeliberation: () => void;
  setBrainVotes: (votes: BrainVote[]) => void;

  // ── Project Slice ─────────────────────────────────────────────
  projects: Project[];
  setProjects: (projects: Project[]) => void;
  addProject: (project: Omit<Project, 'id' | 'createdAt' | 'updatedAt'>) => void;
  updateProjectStatus: (id: string, status: Project['status']) => void;
  updateProjectProgress: (id: string, progress: number) => void;
  selectedProject: string | null;
  setSelectedProject: (id: string | null) => void;
  projectStatuses: Record<string, 'thinking' | 'proposed' | 'working' | 'done'>;
  researchTasks: ResearchTask[];
  addResearchTask: (task: ResearchTask) => void;
  updateResearchTask: (id: string, updates: Partial<ResearchTask>) => void;

  // ── Screen Slice ──────────────────────────────────────────────
  currentIntent: string | null;
  setCurrentIntent: (intent: string | null) => void;
  activeScreen: string | null;
  setActiveScreen: (screen: string | null) => void;
  screenProps: Record<string, any>;
  setScreenProps: (props: Record<string, any>) => void;
  screenTransition: 'entering' | 'active' | 'exiting' | null;
  setScreenTransition: (t: 'entering' | 'active' | 'exiting' | null) => void;
  intentHistory: string[];
  addIntentToHistory: (intent: string) => void;

  // ── Sound Slice ───────────────────────────────────────────────
  soundEnabled: boolean;
  soundVolume: number;
  soundMode: 'immersive' | 'ambient' | 'minimal';
  setSoundEnabled: (v: boolean) => void;
  setSoundVolume: (v: number) => void;
  setSoundMode: (m: 'immersive' | 'ambient' | 'minimal') => void;

  // ── Tasks & Notifications ─────────────────────────────────────
  tasks: Task[];
  addTask: (task: Omit<Task, 'id'>) => void;
  notifications: AppNotification[];
  addNotification: (n: Omit<AppNotification, 'id' | 'timestamp' | 'read'>) => void;
  markNotificationRead: (id: string) => void;

  // ── Approvals Slice ───────────────────────────────────────────
  approvals: Approval[];
  addApproval: (a: Omit<Approval, 'id' | 'timestamp' | 'status'>) => void;
  respondApproval: (id: string, response: 'approved' | 'rejected') => void;

  // ── Instincts & Feedforward ───────────────────────────────────
  triggerInstinct: (id: string) => void;
  activeInstincts: string[];
  feedforwardSuggestions: FeedforwardSuggestion[];
  setFeedforwardSuggestions: (suggestions: FeedforwardSuggestion[]) => void;
  clearFeedforwardSuggestions: () => void;
  interactionCount: number;
  incrementInteraction: () => void;
}

// ─── Default Brains ────────────────────────────────────────────

const DEFAULT_BRAINS: BrainInfo[] = [
  { id: 'neural', name: 'عصبي', nameAr: 'عصبي', nameEn: 'Neural', status: 'active', confidence: 0.85, latency: 0, enabled: true, color: '#7C3AED', model: 'glm-5.1', lastActivity: Date.now(), deliberationCount: 0 },
  { id: 'causal', name: 'سببي', nameAr: 'سببي', nameEn: 'Causal', status: 'active', confidence: 0.80, latency: 0, enabled: true, color: '#2563EB', model: 'deepseek-reasoner', lastActivity: Date.now(), deliberationCount: 0 },
  { id: 'symbolic', name: 'رمزي', nameAr: 'رمزي', nameEn: 'Symbolic', status: 'active', confidence: 0.75, latency: 0, enabled: true, color: '#059669', model: 'glm-4-plus', lastActivity: Date.now(), deliberationCount: 0 },
  { id: 'bayesian', name: 'بيزي', nameAr: 'بيزي', nameEn: 'Bayesian', status: 'active', confidence: 0.78, latency: 0, enabled: true, color: '#D97706', model: 'gemini-2.0-flash', lastActivity: Date.now(), deliberationCount: 0 },
  { id: 'world_model', name: 'عالمي', nameAr: 'عالمي', nameEn: 'World Model', status: 'active', confidence: 0.72, latency: 0, enabled: true, color: '#DC2626', model: 'deepseek-chat', lastActivity: Date.now(), deliberationCount: 0 },
];

// ─── Store ─────────────────────────────────────────────────────

export const useAppStore = create<AppStore>()((set, get) => ({
  // ── Chat Slice ────────────────────────────────────────────────
  messages: [],
  isThinking: false,
  defaultModel: 'glm-5.1',
  sendMessage: (text: string) => {
    set((state) => {
      const newMessages = [...state.messages, {
        id: `u-${Date.now()}`,
        role: 'user' as const,
        content: text,
        timestamp: Date.now(),
      }];
      saveMessagesToLocal(newMessages);
      return { messages: newMessages, isThinking: true, interactionCount: state.interactionCount + 1 };
    });
    generateFeedforward(text, get().messages);
  },
  addMessage: (msg) => {
    set((state) => {
      const newMessages = [...state.messages, msg as ChatMessage];
      saveMessagesToLocal(newMessages);
      return { messages: newMessages };
    });
  },
  setThinking: (v: boolean) => set({ isThinking: v }),
  clearChat: () => {
    set({ messages: [] });
    clearLocalMessages();
  },
  hydrateFromDB: () => {
    const savedMessages = loadMessagesFromLocal();
    const prefs = loadUserPreferences();
    set({
      messages: savedMessages,
      isHydrated: true,
      interactionCount: prefs.interactionCount,
      soundVolume: prefs.soundVolume ?? 50,
      soundMode: prefs.soundMode ?? 'ambient',
      soundEnabled: prefs.soundEnabled ?? true,
    });
    saveUserPreferences({ lastActiveTimestamp: Date.now() });
  },
  isHydrated: false,
  isStreaming: false,
  setIsStreaming: (v: boolean) => set({ isStreaming: v }),

  // ── Brain Slice ───────────────────────────────────────────────
  brains: DEFAULT_BRAINS,
  currentBrain: 'neural',
  setCurrentBrain: (id: string) => set({ currentBrain: id }),
  systemHealth: 85,
  isConscious: true,
  setSystemHealth: (v: number) => set({ systemHealth: v }),
  updateBrainStatus: (id: string, status: BrainInfo['status']) => {
    set((state) => ({
      brains: state.brains.map(b => b.id === id ? { ...b, status, lastActivity: Date.now() } : b),
    }));
  },
  updateBrainConfidence: (id: string, confidence: number) => {
    set((state) => ({
      brains: state.brains.map(b => b.id === id ? { ...b, confidence } : b),
    }));
  },
  brainStates: {},
  setBrainStates: (states: Record<string, BrainState>) => set({ brainStates: states }),
  deliberationProgress: 0,
  setDeliberationProgress: (p: number) => set({ deliberationProgress: p }),
  thinkingBrains: [],
  setThinkingBrains: (brains: string[]) => set({ thinkingBrains: brains }),
  deliberationData: null,
  updateDeliberationData: (data: DeliberationData) => set({ deliberationData: data }),
  isActive: false,
  currentTopic: '',
  brainResponses: {},
  consensusLevel: 0,
  brainVotes: [],
  startDeliberation: (topic: string) => set({ isActive: true, currentTopic: topic }),
  endDeliberation: () => set({ isActive: false, currentTopic: '', deliberationProgress: 0, thinkingBrains: [] }),
  setBrainVotes: (votes: BrainVote[]) => set({ brainVotes: votes }),

  // ── Project Slice ─────────────────────────────────────────────
  projects: [],
  setProjects: (projects: Project[]) => set({ projects }),
  addProject: (project) => {
    const now = new Date().toISOString();
    set((state) => ({
      projects: [...state.projects, {
        ...project,
        id: `p-${Date.now()}`,
        createdAt: now,
        updatedAt: now,
      } as Project],
    }));
  },
  updateProjectStatus: (id, status) => {
    set((state) => ({
      projects: state.projects.map(p =>
        p.id === id ? { ...p, status, updatedAt: new Date().toISOString() } : p
      ),
    }));
  },
  updateProjectProgress: (id, progress) => {
    set((state) => ({
      projects: state.projects.map(p =>
        p.id === id ? { ...p, progress, progressPercent: progress, updatedAt: new Date().toISOString() } : p
      ),
    }));
  },
  selectedProject: null,
  setSelectedProject: (id: string | null) => set({ selectedProject: id }),
  projectStatuses: {},
  researchTasks: [],
  addResearchTask: (task: ResearchTask) => {
    set((state) => ({ researchTasks: [...state.researchTasks, task] }));
  },
  updateResearchTask: (id: string, updates: Partial<ResearchTask>) => {
    set((state) => ({
      researchTasks: state.researchTasks.map(t => t.id === id ? { ...t, ...updates } : t),
    }));
  },

  // ── Screen Slice ──────────────────────────────────────────────
  currentIntent: null,
  setCurrentIntent: (intent: string | null) => set({ currentIntent: intent }),
  activeScreen: null,
  setActiveScreen: (screen: string | null) => set({ activeScreen: screen }),
  screenProps: {},
  setScreenProps: (props: Record<string, any>) => set({ screenProps: props }),
  screenTransition: null,
  setScreenTransition: (t: 'entering' | 'active' | 'exiting' | null) => set({ screenTransition: t }),
  intentHistory: [],
  addIntentToHistory: (intent: string) => {
    set((state) => ({
      intentHistory: [...state.intentHistory.slice(-19), intent],
    }));
  },

  // ── Sound Slice ───────────────────────────────────────────────
  soundEnabled: true,
  soundVolume: 50,
  soundMode: 'ambient',
  setSoundEnabled: (v: boolean) => {
    set({ soundEnabled: v });
    saveUserPreferences({ soundEnabled: v });
  },
  setSoundVolume: (v: number) => {
    set({ soundVolume: v });
    saveUserPreferences({ soundVolume: v });
  },
  setSoundMode: (m: 'immersive' | 'ambient' | 'minimal') => {
    set({ soundMode: m });
    saveUserPreferences({ soundMode: m });
  },

  // ── Tasks & Notifications ─────────────────────────────────────
  tasks: [],
  addTask: (task) => {
    set((state) => ({
      tasks: [...state.tasks, { ...task, id: `task-${Date.now()}` }],
    }));
  },
  notifications: [],
  addNotification: (n) => {
    set((state) => ({
      notifications: [...state.notifications, {
        ...n,
        id: `notif-${Date.now()}`,
        timestamp: Date.now(),
        read: false,
      }],
    }));
  },
  markNotificationRead: (id: string) => {
    set((state) => ({
      notifications: state.notifications.map(n => n.id === id ? { ...n, read: true } : n),
    }));
  },

  // ── Approvals Slice ───────────────────────────────────────────
  approvals: [],
  addApproval: (a) => {
    set((state) => ({
      approvals: [...state.approvals, {
        ...a,
        id: `approval-${Date.now()}`,
        timestamp: Date.now(),
        status: 'pending' as const,
      }],
    }));
  },
  respondApproval: (id: string, response: 'approved' | 'rejected') => {
    set((state) => ({
      approvals: state.approvals.map(a => a.id === id ? { ...a, status: response } : a),
    }));
  },

  // ── Instincts & Feedforward ───────────────────────────────────
  activeInstincts: [],
  triggerInstinct: (id: string) => {
    set((state) => ({
      activeInstincts: state.activeInstincts.includes(id)
        ? state.activeInstincts
        : [...state.activeInstincts, id],
    }));
    setTimeout(() => {
      set((state) => ({
        activeInstincts: state.activeInstincts.filter((i) => i !== id),
      }));
    }, 5000);
  },
  feedforwardSuggestions: [],
  setFeedforwardSuggestions: (suggestions: FeedforwardSuggestion[]) => set({ feedforwardSuggestions: suggestions }),
  clearFeedforwardSuggestions: () => set({ feedforwardSuggestions: [] }),
  interactionCount: 0,
  incrementInteraction: () => {
    set((state) => {
      const newCount = state.interactionCount + 1;
      saveUserPreferences({ interactionCount: newCount });
      return { interactionCount: newCount };
    });
  },
}));

// ─── Feedforward Generation ──────────────────────────────────

function generateFeedforward(message: string, history: ChatMessage[]): void {
  const suggestions: FeedforwardSuggestion[] = [];
  const lower = message.toLowerCase();

  if (message.length < 15 && !lower.includes('?') && !lower.includes('؟')) {
    suggestions.push({
      id: `ff-clarify-${Date.now()}`,
      type: 'clarification',
      text: 'هل يمكنك توضيح سؤالك أكثر؟',
      confidence: 0.7,
    });
  }

  if (/بحث|ابحث|search|find/i.test(message)) {
    suggestions.push({
      id: `ff-tool-${Date.now()}`,
      type: 'tool_suggestion',
      text: 'يمكنني البحث في الويب لك. هل تريد تفعيل أداة البحث؟',
      confidence: 0.8,
      brainSource: 'neural',
    });
  }

  if (/صور|ارسم|انشئ صورة|generate image/i.test(message)) {
    suggestions.push({
      id: `ff-tool-img-${Date.now()}`,
      type: 'tool_suggestion',
      text: 'يمكنني إنشاء صور من وصفك. هل تريد استخدام أداة توليد الصور؟',
      confidence: 0.8,
      brainSource: 'world_model',
    });
  }

  if (/كيف|how/i.test(message) && history.length > 4) {
    suggestions.push({
      id: `ff-next-${Date.now()}`,
      type: 'next_step',
      text: 'هل تريد أن أشرح بمزيد من التفصيل أو أعطيك مثالاً عملياً؟',
      confidence: 0.6,
      brainSource: 'causal',
    });
  }

  if (/برمج|كود|برنامج|code|program/i.test(message)) {
    suggestions.push({
      id: `ff-related-${Date.now()}`,
      type: 'related',
      text: 'يمكنني أيضاً مراجعة الكود أو اقتراح تحسينات. هل تريد؟',
      confidence: 0.7,
      brainSource: 'symbolic',
    });
  }

  if (/مشروع|project/i.test(message)) {
    suggestions.push({
      id: `ff-project-${Date.now()}`,
      type: 'related',
      text: 'يمكنني إنشاء مشروع جديد من الصفر أو مراقبة المشاريع الحالية.',
      confidence: 0.8,
      brainSource: 'neural',
    });
  }

  if (suggestions.length > 0) {
    useAppStore.getState().setFeedforwardSuggestions(suggestions.slice(0, 3));
  }
}
