// ═══════════════════════════════════════════════════════════════════
// مأمون v40.0 — Conversational Memory (Persistent Chat Storage)
// ذاكرة محادثة دائمة: localStorage + API backend
// Episodic + Semantic + Procedural memory layers
// ═══════════════════════════════════════════════════════════════════

import type { ChatMessage } from './store';

const STORAGE_KEY = 'mamoun_chat_history';
const MAX_LOCAL_MESSAGES = 200; // أقصى عدد رسائل محلية
const SUMMARY_TRIGGER = 50; // بعد كم رسالة يبدأ التلخيص

export interface ConversationSummary {
  id: string;
  timestamp: number;
  messageCount: number;
  summary: string;
  keyTopics: string[];
  userPreferences: string[];
  brainUsage: Record<string, number>;
}

export interface UserPreferences {
  preferredLanguage: 'ar' | 'en' | 'auto';
  preferredDetail: 'concise' | 'detailed' | 'auto';
  preferredBrain?: string;
  interactionCount: number;
  lastActiveTimestamp: number;
}

// ─── Local Storage Operations ──────────────────────────────────

/**
 * حفظ الرسائل في localStorage
 */
export function saveMessagesToLocal(messages: ChatMessage[]): void {
  if (typeof window === 'undefined') return;
  try {
    const toSave = messages.slice(-MAX_LOCAL_MESSAGES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
  } catch (e) {
    console.warn('[ChatMemory] Failed to save to localStorage:', e);
  }
}

/**
 * استرجاع الرسائل من localStorage
 */
export function loadMessagesFromLocal(): ChatMessage[] {
  if (typeof window === 'undefined') return [];
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];
    return parsed as ChatMessage[];
  } catch (e) {
    console.warn('[ChatMemory] Failed to load from localStorage:', e);
    return [];
  }
}

/**
 * مسح الرسائل المحلية
 */
export function clearLocalMessages(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch { /* ignore */ }
}

// ─── User Preferences ──────────────────────────────────────────

const PREFS_KEY = 'mamoun_user_prefs';

/**
 * حفظ تفضيلات المستخدم
 */
export function saveUserPreferences(prefs: Partial<UserPreferences>): void {
  if (typeof window === 'undefined') return;
  try {
    const existing = loadUserPreferences();
    const updated = { ...existing, ...prefs, lastActiveTimestamp: Date.now() };
    localStorage.setItem(PREFS_KEY, JSON.stringify(updated));
  } catch { /* ignore */ }
}

/**
 * استرجاع تفضيلات المستخدم
 */
export function loadUserPreferences(): UserPreferences {
  if (typeof window === 'undefined') {
    return {
      preferredLanguage: 'auto',
      preferredDetail: 'auto',
      interactionCount: 0,
      lastActiveTimestamp: 0,
    };
  }
  try {
    const stored = localStorage.getItem(PREFS_KEY);
    if (!stored) {
      return {
        preferredLanguage: 'auto',
        preferredDetail: 'auto',
        interactionCount: 0,
        lastActiveTimestamp: 0,
      };
    }
    return JSON.parse(stored) as UserPreferences;
  } catch {
    return {
      preferredLanguage: 'auto',
      preferredDetail: 'auto',
      interactionCount: 0,
      lastActiveTimestamp: 0,
    };
  }
}

// ─── Smart Context Management ──────────────────────────────────

export interface SmartContextResult {
  /** الرسائل المختارة للسياق */
  messages: Array<{ role: string; content: string }>;
  /** عدد الرسائل الكلية (للمعلومات) */
  totalMessages: number;
  /** هل تم تلخيص رسائل قديمة؟ */
  wasSummarized: boolean;
  /** التوكنات المقدرة */
  estimatedTokens: number;
}

/**
 * إدارة ذكية للسياق — تختار الرسائل الأهم بدل آخر N فقط
 */
export function buildSmartContext(
  allMessages: ChatMessage[],
  maxTokens: number = 8000,
): SmartContextResult {
  // تقدير التوكنات (1 توكن ≈ 4 أحرف للعربي، 1 توكن ≈ 0.75 كلمة للإنجليزي)
  const estimateTokens = (text: string): number => {
    const arabicChars = (text.match(/[\u0600-\u06FF]/g) || []).length;
    const otherChars = text.length - arabicChars;
    return Math.ceil(arabicChars / 3 + otherChars / 4);
  };

  let totalTokens = 0;
  const selectedMessages: Array<{ role: string; content: string }> = [];

  // 1. دائماً أضف آخر 6 رسائل (السياق المباشر)
  const recentMessages = allMessages.slice(-6);
  for (const msg of recentMessages) {
    const role = msg.role === 'user' ? 'user' : 'assistant';
    const content = msg.content.substring(0, 4000);
    const tokens = estimateTokens(content);
    if (totalTokens + tokens <= maxTokens) {
      selectedMessages.push({ role, content });
      totalTokens += tokens;
    }
  }

  // 2. أضف رسائل مهمة أقدم (أسئلة المستخدم الرئيسية)
  const olderMessages = allMessages.slice(0, -6).reverse(); // من الأحدث للأقدم
  for (const msg of olderMessages) {
    if (totalTokens >= maxTokens * 0.8) break; // اترك 20% هامش
    if (msg.role !== 'user') continue; // أسئلة المستخدم أهم

    const role = 'user';
    const content = msg.content.substring(0, 2000); // ضغط الرسائل القديمة
    const tokens = estimateTokens(content);
    if (totalTokens + tokens <= maxTokens) {
      selectedMessages.unshift({ role, content }); // أضف في البداية
      totalTokens += tokens;
    }
  }

  return {
    messages: selectedMessages,
    totalMessages: allMessages.length,
    wasSummarized: allMessages.length > SUMMARY_TRIGGER,
    estimatedTokens: totalTokens,
  };
}

// ─── Conversation Statistics ────────────────────────────────────

/**
 * حساب إحصائيات المحادثة الحالية
 */
export function getConversationStats(messages: ChatMessage[]): {
  totalMessages: number;
  userMessages: number;
  assistantMessages: number;
  brainUsage: Record<string, number>;
  avgConfidence: number;
  dominantTopic: string;
} {
  const userMessages = messages.filter(m => m.role === 'user').length;
  const assistantMessages = messages.filter(m => m.role === 'assistant').length;

  // استخدام الأدمغة
  const brainUsage: Record<string, number> = {};
  let totalConfidence = 0;
  let confidenceCount = 0;

  for (const msg of messages) {
    if (msg.brain) {
      brainUsage[msg.brain] = (brainUsage[msg.brain] || 0) + 1;
    }
    if (msg.confidence !== undefined) {
      totalConfidence += msg.confidence;
      confidenceCount++;
    }
  }

  // الموضوع المهيمن (من أكثر الكلمات تكراراً في أسئلة المستخدم)
  const userWords = messages
    .filter(m => m.role === 'user')
    .flatMap(m => m.content.split(/\s+/))
    .filter(w => w.length > 3)
    .reduce((acc, w) => { acc[w] = (acc[w] || 0) + 1; return acc; }, {} as Record<string, number>);

  const dominantTopic = Object.entries(userWords)
    .sort((a, b) => b[1] - a[1])[0]?.[0] || '';

  return {
    totalMessages: messages.length,
    userMessages,
    assistantMessages,
    brainUsage,
    avgConfidence: confidenceCount > 0 ? totalConfidence / confidenceCount : 0,
    dominantTopic,
  };
}
