// ═══════════════════════════════════════════════════════════════════
// مأمون v61 — Unified Store (SuperMind)
// Provides all interfaces needed by components + missing methods from slices
//
// v61 SuperMind Changes:
// - currentIntent / activeScreen / screenProps for SuperMindRouter
// - Sound preferences (enabled, volume, mode)
// - Projects list
// - Brain states map
// - Persistent chat memory (localStorage + API)
// - Feedforward mechanism (suggestions, clarifications)
// - Real confidence tracking
// - User preferences learning
// ═══════════════════════════════════════════════════════════════════

import { create } from 'zustand';
import {
  saveMessagesToLocal,
  loadMessagesFromLocal,
  clearLocalMessages,
  saveUserPreferences,
  loadUserPreferences,
  getConversationStats,
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
  isRealDeliberation?: boolean; // v40: Was this from real 5-brain deliberation?
  warningMessage?: string; // v40: Confidence warning
}

export interface BrainInfo {
  id: string;
  name: string;
  nameAr: string;
  nameEn: string;
  status: 'active' | 'idle' | 'sleeping';
  confidence: number;
  latency: number;
  model?: string;
  enabled?: boolean;
  color: string;
  icon?: string;
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
}

export interface BrainVote {
  brainId: string;
  brainName: string;
  content: string;
  confidence: number;
  weight: number;
  stance: 'support' | 'oppose' | 'neutral';
}

// v40: Feedforward suggestions
export interface FeedforwardSuggestion {
  id: string;
  type: 'clarification' | 'related' | 'next_step' | 'tool_suggestion';
  text: string;
  confidence: number;
  brainSource?: string;
}

// Types previously from store/types.ts (deleted during cleanup)
export interface SelfModification {
  id: string;
  type: string;
  description: string;
  status: 'pending' | 'approved' | 'applied' | 'rejected';
  risk_level: number;
}
export type BrainVoteType = BrainVote;

// v61 SuperMind: Project type for ProjectsTracker
export interface Project {
  id: string;
  name: string;
  nameAr: string;
  category: string;
  status: 'thinking' | 'proposed' | 'working' | 'done';
  progress: number;
  leadingBrain?: string;
  description?: string;
}

// ─── Store Interface ───────────────────────────────────────────

interface AppStore {
  // Chat
  messages: ChatMessage[];
  isThinking: boolean;
  defaultModel: string;
  sendMessage: (text: string) => void;
  addMessage: (msg: Partial<ChatMessage> & { id: string; role: ChatMessage['role']; content: string; timestamp: number }) => void;
  setThinking: (v: boolean) => void;
  clearChat: () => void;

  // v40: Persistent Hydration
  hydrateFromDB: () => void;
  isHydrated: boolean;

  // Brains
  brains: BrainInfo[];
  currentBrain: string;
  setCurrentBrain: (id: string) => void;
  systemHealth: number;
  isConscious: boolean;
  setSystemHealth: (v: number) => void;
  updateBrainStatus: (id: string, status: BrainInfo['status']) => void;
  updateBrainConfidence: (id: string, confidence: number) => void;

  // Tasks
  tasks: Task[];
  addTask: (task: Omit<Task, 'id'>) => void;

  // Notifications
  notifications: AppNotification[];
  addNotification: (n: Omit<AppNotification, 'id' | 'timestamp' | 'read'>) => void;
  markNotificationRead: (id: string) => void;

  // Deliberation
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

  // Approvals
  approvals: Approval[];
  respondApproval: (id: string, response: 'approved' | 'rejected') => void;

  // v34: Instincts
  triggerInstinct: (id: string) => void;
  activeInstincts: string[];

  // v40: Feedforward
  feedforwardSuggestions: FeedforwardSuggestion[];
  setFeedforwardSuggestions: (suggestions: FeedforwardSuggestion[]) => void;
  clearFeedforwardSuggestions: () => void;

  // v40: User interaction tracking
  interactionCount: number;
  incrementInteraction: () => void;

  // v61 SuperMind: Intent & Screen routing
  currentIntent: string | null;
  setCurrentIntent: (intent: string | null) => void;
  activeScreen: string | null;
  setActiveScreen: (screen: string | null) => void;
  screenProps: Record<string, any>;
  setScreenProps: (props: Record<string, any>) => void;
  screenTransition: 'entering' | 'active' | 'exiting' | null;
  setScreenTransition: (t: 'entering' | 'active' | 'exiting' | null) => void;

  // v61 SuperMind: Sound preferences
  soundEnabled: boolean;
  soundVolume: number;
  soundMode: 'immersive' | 'ambient' | 'minimal';

  // v61 SuperMind: Projects
  projects: Project[];
  setProjects: (projects: Project[]) => void;

  // v61 SuperMind: Brain states map
  brainStates: Record<string, any>;
  setBrainStates: (states: Record<string, any>) => void;

  // v62 SuperMind: Deliberation tracking
  deliberationProgress: number;
  setDeliberationProgress: (p: number) => void;
  thinkingBrains: string[];
  setThinkingBrains: (brains: string[]) => void;
  isStreaming: boolean;
  setIsStreaming: (v: boolean) => void;
}

// ─── Default Brains ────────────────────────────────────────────

const DEFAULT_BRAINS: BrainInfo[] = [
  { id: 'neural', name: 'عصبي', nameAr: 'عصبي', nameEn: 'Neural', status: 'active', confidence: 0.85, latency: 0, enabled: true, color: '#7C3AED' },
  { id: 'causal', name: 'سببي', nameAr: 'سببي', nameEn: 'Causal', status: 'active', confidence: 0.80, latency: 0, enabled: true, color: '#2563EB' },
  { id: 'symbolic', name: 'رمزي', nameAr: 'رمزي', nameEn: 'Symbolic', status: 'active', confidence: 0.75, latency: 0, enabled: true, color: '#059669' },
  { id: 'bayesian', name: 'بيزي', nameAr: 'بيزي', nameEn: 'Bayesian', status: 'active', confidence: 0.78, latency: 0, enabled: true, color: '#D97706' },
  { id: 'world_model', name: 'عالمي', nameAr: 'عالمي', nameEn: 'World Model', status: 'active', confidence: 0.72, latency: 0, enabled: true, color: '#DC2626' },
];

// ─── Store ─────────────────────────────────────────────────────

export const useAppStore = create<AppStore>()((set, get) => ({
  // Chat — v40: Start with empty, will hydrate from localStorage
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
      // v40: Auto-save to localStorage
      saveMessagesToLocal(newMessages);
      return {
        messages: newMessages,
        isThinking: true,
        interactionCount: state.interactionCount + 1,
      };
    });

    // v40: Generate feedforward suggestions based on the message
    generateFeedforward(text, get().messages);
  },
  addMessage: (msg) => {
    set((state) => {
      const newMessages = [...state.messages, msg as ChatMessage];
      // v40: Auto-save to localStorage
      saveMessagesToLocal(newMessages);
      return { messages: newMessages };
    });
  },
  setThinking: (v: boolean) => set({ isThinking: v }),
  clearChat: () => {
    set({ messages: [] });
    clearLocalMessages();
  },

  // v40: Real hydration from localStorage
  hydrateFromDB: () => {
    const savedMessages = loadMessagesFromLocal();
    const prefs = loadUserPreferences();
    set({
      messages: savedMessages,
      isHydrated: true,
      interactionCount: prefs.interactionCount,
    });
    // Update user preferences timestamp
    saveUserPreferences({ lastActiveTimestamp: Date.now() });
  },
  isHydrated: false,

  // Brains
  brains: DEFAULT_BRAINS,
  currentBrain: 'neural',
  setCurrentBrain: (id: string) => set({ currentBrain: id }),
  systemHealth: 85,
  isConscious: true,
  setSystemHealth: (v: number) => set({ systemHealth: v }),
  updateBrainStatus: (id: string, status: BrainInfo['status']) => {
    set((state) => ({
      brains: state.brains.map(b => b.id === id ? { ...b, status } : b),
    }));
  },
  updateBrainConfidence: (id: string, confidence: number) => {
    set((state) => ({
      brains: state.brains.map(b => b.id === id ? { ...b, confidence } : b),
    }));
  },

  // Tasks
  tasks: [],
  addTask: (task) => {
    set((state) => ({
      tasks: [...state.tasks, { ...task, id: `task-${Date.now()}` }],
    }));
  },

  // Notifications
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

  // Deliberation
  deliberationData: null,
  updateDeliberationData: (data: DeliberationData) => set({ deliberationData: data }),
  isActive: false,
  currentTopic: '',
  brainResponses: {},
  consensusLevel: 0,
  brainVotes: [],
  startDeliberation: (topic: string) => set({ isActive: true, currentTopic: topic }),
  endDeliberation: () => set({ isActive: false, currentTopic: '' }),
  setBrainVotes: (votes: BrainVote[]) => set({ brainVotes: votes }),

  // Approvals
  approvals: [],
  respondApproval: (id: string, response: 'approved' | 'rejected') => {
    set((state) => ({
      approvals: state.approvals.map(a => a.id === id ? { ...a, status: response } : a),
    }));
  },

  // v34: Instincts
  activeInstincts: [],
  triggerInstinct: (id: string) => {
    set((state) => ({
      activeInstincts: state.activeInstincts.includes(id)
        ? state.activeInstincts
        : [...state.activeInstincts, id],
    }));
    // Auto-deactivate after 5 seconds
    setTimeout(() => {
      set((state) => ({
        activeInstincts: state.activeInstincts.filter((i) => i !== id),
      }));
    }, 5000);
  },

  // v40: Feedforward
  feedforwardSuggestions: [],
  setFeedforwardSuggestions: (suggestions: FeedforwardSuggestion[]) => set({ feedforwardSuggestions: suggestions }),
  clearFeedforwardSuggestions: () => set({ feedforwardSuggestions: [] }),

  // v40: User interaction tracking
  interactionCount: 0,
  incrementInteraction: () => {
    set((state) => {
      const newCount = state.interactionCount + 1;
      saveUserPreferences({ interactionCount: newCount });
      return { interactionCount: newCount };
    });
  },

  // v61 SuperMind: Intent & Screen routing
  currentIntent: null,
  setCurrentIntent: (intent: string | null) => set({ currentIntent: intent }),
  activeScreen: null,
  setActiveScreen: (screen: string | null) => set({ activeScreen: screen }),
  screenProps: {},
  setScreenProps: (props: Record<string, any>) => set({ screenProps: props }),
  screenTransition: null,
  setScreenTransition: (t: 'entering' | 'active' | 'exiting' | null) => set({ screenTransition: t }),

  // v61 SuperMind: Sound preferences
  soundEnabled: true,
  soundVolume: 50,
  soundMode: 'ambient',

  // v61 SuperMind: Projects
  projects: [],
  setProjects: (projects: Project[]) => set({ projects }),

  // v61 SuperMind: Brain states map
  brainStates: {},
  setBrainStates: (states: Record<string, any>) => set({ brainStates: states }),

  // v62 SuperMind: Deliberation tracking
  deliberationProgress: 0,
  setDeliberationProgress: (p: number) => set({ deliberationProgress: p }),
  thinkingBrains: [],
  setThinkingBrains: (brains: string[]) => set({ thinkingBrains: brains }),
  isStreaming: false,
  setIsStreaming: (v: boolean) => set({ isStreaming: v }),
}));

// ─── Feedforward Generation ──────────────────────────────────

/**
 * توليد اقتراحات Feedforward بناءً على رسالة المستخدم
 * v40: آلية استباقية لمساعدة المستخدم
 */
function generateFeedforward(message: string, history: ChatMessage[]): void {
  const suggestions: FeedforwardSuggestion[] = [];
  const lower = message.toLowerCase();

  // 1. اقتراحات توضيحية للأسئلة الغامضة
  if (message.length < 15 && !lower.includes('?') && !lower.includes('؟')) {
    suggestions.push({
      id: `ff-clarify-${Date.now()}`,
      type: 'clarification',
      text: 'هل يمكنك توضيح سؤالك أكثر؟',
      confidence: 0.7,
    });
  }

  // 2. اقتراح استخدام أدوات
  if (/بحث|ابحث|search|find|google/i.test(message)) {
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

  // 3. اقتراح خطوة تالية بناءً على السياق
  if (/كيف|how/i.test(message) && history.length > 4) {
    suggestions.push({
      id: `ff-next-${Date.now()}`,
      type: 'next_step',
      text: 'هل تريد أن أشرح بمزيد من التفصيل أو أعطيك مثالاً عملياً؟',
      confidence: 0.6,
      brainSource: 'causal',
    });
  }

  // 4. اقتراحات مرتبطة
  if (/برمج|كود|برنامج|code|program/i.test(message)) {
    suggestions.push({
      id: `ff-related-${Date.now()}`,
      type: 'related',
      text: 'يمكنني أيضاً مراجعة الكود أو اقتراح تحسينات. هل تريد؟',
      confidence: 0.7,
      brainSource: 'symbolic',
    });
  }

  // تحديث الـ store
  if (suggestions.length > 0) {
    useAppStore.getState().setFeedforwardSuggestions(suggestions.slice(0, 3)); // Max 3 suggestions
  }
}
