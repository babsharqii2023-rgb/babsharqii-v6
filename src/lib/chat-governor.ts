// ═══════════════════════════════════════════════════════════════════
// مأمون v40.0 — Chat Governor (الحاكم المركزي للمحادثة)
// يوحّد مسارات المحادثة الثلاثة ويدير كل شيء من مركز واحد
// ═══════════════════════════════════════════════════════════════════

import { CORE_SYSTEM_PROMPT, buildBrainSystemPrompt } from './system-prompt';
import { BRAIN_PERSONAS, determinePrimaryBrain, getBrainSystemPrompt, getBrainTemperature, setBrainEnabled, adjustBrainTemperature, type BrainRoutingResult } from './brains';
import { calculateRealConfidence, calculateFallbackConfidence, type ConfidenceResult } from './chat-confidence';
import { sanitizeMessage, type sanitizeMessage as sanitizeMessageType } from './chat-security';
import { buildSmartContext, type SmartContextResult } from './chat-memory';
import { parseCommand, type ParsedCommand } from './command-parser';
import { getCurrentMode, setMode, detectModeFromMessage, type MamounModeId, type MamounMode } from './mode-engine';

// ─── Types ────────────────────────────────────────────────────

export type ChatSource = 'kernel' | 'fallback_single_brain' | 'security_filter' | 'command' | 'offline';
export type GovernorAction = 'chat' | 'command' | 'search' | 'self_modify' | 'self_improve' | 'git_sync' | 'self_analyze' | 'mode_change' | 'create_file' | 'read_file' | 'edit_file' | 'list_files' | 'build_agent' | 'build_project' | 'create_tool' | 'set_api_key' | 'brain_status' | 'assess_capabilities' | 'external_modify' | 'external_deploy' | 'self_test' | 'unified_mind';

export interface GovernorDecision {
  /** ماذا يقرر الحاكم أن يفعل */
  action: GovernorAction;
  /** هل يحتاج لمداولة كاملة (5 أدمغة)؟ */
  needsFullDeliberation: boolean;
  /** أي أدمغة تُفعّل */
  activatedBrains: string[];
  /** درجة الحرارة المقترحة */
  suggestedTemperature: number;
  /** الوضع الحالي */
  currentMode: MamounMode;
  /** الأمر المُحلّل (إن وُجد) */
  parsedCommand: ParsedCommand;
  /** رسالة مُنظفة */
  sanitizedMessage: string;
  /** معلومات التوجيه */
  routing: BrainRoutingResult;
  /** السياق الذكي */
  smartContext: SmartContextResult;
  /** هل تم فلترة الرسالة؟ */
  wasFiltered: boolean;
  /** مستوى حقن الأوامر */
  injectionScore: number;
}

export interface GovernorResponse {
  /** رد مأمون */
  content: string;
  /** الدماغ الفائز */
  brain: string;
  /** مستوى الثقة */
  confidence: number;
  /** نتيجة الثقة التفصيلية */
  confidenceResult?: ConfidenceResult;
  /** مصدر الرد */
  source: ChatSource;
  /** هل كانت مداولة حقيقية؟ */
  isRealDeliberation: boolean;
  /** بيانات المداولة */
  deliberationData?: {
    brainResponses?: Record<string, unknown>;
    consensusLevel?: number;
    cjs?: number;
    conflictDetected?: boolean;
    mirrorReflection?: string;
    queryType?: string;
  };
  /** رد فوري (للأوامر) */
  immediateResponse?: string;
  /** بيانات التوجيه */
  routing: BrainRoutingResult;
  /** الوضع الحالي */
  mode: MamounMode;
  /** اقتراحات Feedforward */
  feedforwardSuggestions?: string[];
  /** بيانات وصفية */
  metadata: Record<string, unknown>;
}

// ─── Governor Class ───────────────────────────────────────────

class ChatGovernor {
  private _interactionCount: number = 0;
  private _lastCommandHistory: ParsedCommand[] = [];

  /**
   * التحليل المركزي لكل رسالة واردة
   * يمر من هنا: chat/route.ts, mamoun-chat/route.ts, stream/route.ts
   */
  analyze(message: string, history?: Array<{ role: string; content: string; timestamp?: number; brain?: string; confidence?: number }>): GovernorDecision {
    this._interactionCount++;

    // ─── Step 1: الأمان والتنظيف ─────────────────────────────
    const { sanitized: sanitizedMessage, wasFiltered, injectionDetected, injectionScore } = sanitizeMessage(message);

    // ─── Step 2: تحليل الأوامر ───────────────────────────────
    const parsedCommand = parseCommandWithContext(
      sanitizedMessage,
      {
        previousCommands: this._lastCommandHistory,
        conversationLength: history?.length || 0,
        currentMode: getCurrentMode().id,
      },
    );

    this._lastCommandHistory.push(parsedCommand);
    if (this._lastCommandHistory.length > 20) {
      this._lastCommandHistory = this._lastCommandHistory.slice(-20);
    }

    // ─── Step 3: كشف تغيير الوضع ────────────────────────────
    if (parsedCommand.action === 'SET_MODE' && parsedCommand.params.modeId) {
      setMode(parsedCommand.params.modeId as MamounModeId, 'chat_command');
    } else {
      // كشف تلقائي للوضع من الرسالة
      const detectedMode = detectModeFromMessage(sanitizedMessage);
      if (detectedMode && detectedMode !== getCurrentMode().id) {
        setMode(detectedMode, 'auto_detect');
      }
    }

    const currentMode = getCurrentMode();

    // ─── Step 4: توجيه الأدمغة ───────────────────────────────
    const routing = determinePrimaryBrain(sanitizedMessage, {
      previousBrain: undefined,
      conversationLength: history?.length,
    });

    // ─── Step 5: تحديد الإجراء ───────────────────────────────
    let action: GovernorAction = 'chat';
    let needsFullDeliberation = true;

    if (injectionDetected) {
      action = 'chat'; // سيتم التعامل معه في الرد
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'SET_MODE') {
      action = 'mode_change';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'DEEP_SEARCH') {
      action = 'search';
      needsFullDeliberation = true;
    } else if (parsedCommand.action === 'SELF_MODIFY') {
      action = 'self_modify';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'GIT_PULL') {
      action = 'git_sync';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'SELF_ANALYZE') {
      action = 'self_analyze';
      needsFullDeliberation = true;
    } else if (parsedCommand.action === 'ADJUST_TEMP') {
      // تعديل حرارة جميع الأدمغة النشطة
      const delta = parsedCommand.params.delta as number || 0;
      for (const brain of BRAIN_PERSONAS) {
        if (currentMode.activeBrains.includes(brain.id)) {
          adjustBrainTemperature(brain.id, delta);
        }
      }
      action = 'mode_change';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'SET_BRAINS') {
      const { brainId, action: brainAction } = parsedCommand.params;
      if (brainId) {
        setBrainEnabled(brainId as string, brainAction !== 'disable');
      }
      action = 'mode_change';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'CLEAR_MEMORY') {
      action = 'command';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'SHOW_STATUS') {
      action = 'self_analyze';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'SELF_IMPROVE') {
      action = 'self_improve';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'CREATE_FILE') {
      action = 'create_file';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'READ_FILE') {
      action = 'read_file';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'EDIT_FILE') {
      action = 'edit_file';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'LIST_FILES') {
      action = 'list_files';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'BUILD_AGENT') {
      action = 'build_agent';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'BUILD_PROJECT') {
      action = 'build_project';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'CREATE_TOOL') {
      action = 'create_tool';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'SET_API_KEY') {
      action = 'set_api_key';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'BRAIN_STATUS') {
      action = 'brain_status';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'ASSESS_CAPABILITIES') {
      action = 'assess_capabilities';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'EXTERNAL_MODIFY') {
      action = 'external_modify';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'EXTERNAL_DEPLOY') {
      action = 'external_deploy';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'SELF_TEST') {
      action = 'self_test';
      needsFullDeliberation = false;
    } else if (parsedCommand.action === 'UNIFIED_MIND') {
      action = 'unified_mind';
      needsFullDeliberation = true;
    }

    // ─── Step 6: بناء السياق الذكي ──────────────────────────
    let smartContext: SmartContextResult;
    if (history && history.length > 0) {
      const chatMessages = history.map(msg => ({
        id: `hist-${Date.now()}-${Math.random()}`,
        role: msg.role as 'user' | 'assistant' | 'system' | 'brain',
        content: msg.content,
        timestamp: msg.timestamp || Date.now(),
        brain: msg.brain,
        confidence: msg.confidence,
      }));
      smartContext = buildSmartContext(chatMessages, 8000);
    } else {
      smartContext = { messages: [], totalMessages: 0, wasSummarized: false, estimatedTokens: 0 };
    }

    // ─── Step 7: الأدمغة المفعّلة والحرارة ───────────────────
    const activatedBrains = currentMode.id === 'default'
      ? routing.activatedBrains
      : currentMode.activeBrains.filter(id => {
          const brain = BRAIN_PERSONAS.find(b => b.id === id);
          return brain?.enabled !== false;
        });

    const suggestedTemperature = currentMode.id === 'default'
      ? getBrainTemperature(routing.primaryBrain)
      : currentMode.defaultTemperature;

    return {
      action,
      needsFullDeliberation,
      activatedBrains,
      suggestedTemperature,
      currentMode,
      parsedCommand,
      sanitizedMessage,
      routing,
      smartContext,
      wasFiltered,
      injectionScore,
    };
  }

  /**
   * بناء System Prompt الكامل مع الوضع والأدمغة
   */
  buildFullSystemPrompt(decision: GovernorDecision): string {
    const mode = decision.currentMode;
    const primaryBrain = decision.routing.primaryBrain;
    const brainPersona = BRAIN_PERSONAS.find(b => b.id === primaryBrain) || BRAIN_PERSONAS[0];

    // البناء الأساسي
    let fullPrompt = buildBrainSystemPrompt(
      primaryBrain,
      getBrainSystemPrompt(primaryBrain),
      brainPersona.nameAr,
      brainPersona.nameEn,
      decision.suggestedTemperature,
    );

    // إضافة وضع المأمون
    if (mode.systemPromptAddition) {
      fullPrompt += `\n\n${mode.systemPromptAddition}`;
    }

    // إضافة معلومات المداولة
    if (decision.needsFullDeliberation) {
      fullPrompt += `\n\nأنت تعمل حالياً مع ${decision.activatedBrains.length} أدمغة نشطة: ${decision.activatedBrains.join('، ')}. 
إن وُجد تناقض بين رأيك ومعلوماتك، عبّر عن ذلك صراحةً.`;
    }

    return fullPrompt;
  }

  /**
   * توليد اقتراحات Feedforward بناءً على السياق
   */
  generateFeedforward(decision: GovernorDecision, responseContent: string): string[] {
    const suggestions: string[] = [];
    const mode = decision.currentMode;

    // اقتراحات حسب الوضع
    if (mode.id === 'researcher') {
      suggestions.push('هل تريد أن أبحث أكثر في هذا الموضوع؟');
      suggestions.push('يمكنني تقديم مصادر إضافية');
    } else if (mode.id === 'creative') {
      suggestions.push('هل تريد المزيد من الأفكار الإبداعية؟');
      suggestions.push('يمكنني تطوير أحد هذه السيناريوهات');
    } else if (mode.id === 'analyst') {
      suggestions.push('هل تريد تحليلاً أعمق لجزء معين؟');
      suggestions.push('يمكنني تقديم برهان رياضي');
    } else if (mode.id === 'companion') {
      suggestions.push('كيف تشعر حيال هذا؟');
    } else if (mode.id === 'engineer') {
      suggestions.push('هل تريد كوداً قابلاً للتنفيذ؟');
      suggestions.push('يمكنني اقتراح تحسينات');
    }

    // اقتراحات عامة
    if (responseContent.length < 100) {
      suggestions.push('هل تريد تفصيلاً أكثر؟');
    }

    // اقتراح ربط المواضيع
    if (this._interactionCount > 5 && this._interactionCount % 5 === 0) {
      suggestions.push('هل تريد أن أربط هذا بمواضيع سابقة؟');
    }

    return suggestions.slice(0, 3); // أقصى 3 اقتراحات
  }

  /**
   * الحصول على إحصائيات الحاكم
   */
  getStats() {
    return {
      interactionCount: this._interactionCount,
      lastCommands: this._lastCommandHistory.slice(-5),
    };
  }
}

// ─── Singleton ────────────────────────────────────────────────

export const chatGovernor = new ChatGovernor();

// ─── Helper: parseCommandWithContext (re-export from command-parser) ──

function parseCommandWithContext(
  message: string,
  context: {
    previousCommands?: ParsedCommand[];
    conversationLength?: number;
    currentMode?: MamounModeId;
  },
): ParsedCommand {
  const basic = parseCommand(message);
  if (basic.isCommand) return basic;

  const lower = message.toLowerCase();
  if (/^(نعم|أي نعم|أكيد|بالتأكيد|yes|sure|ok|okay)$/i.test(lower.trim())) {
    const lastCommand = context.previousCommands?.slice(-1)[0];
    if (lastCommand && lastCommand.action !== 'NORMAL_CHAT') {
      return {
        action: lastCommand.action,
        params: { ...lastCommand.params, confirmed: true },
        isCommand: true,
        confidence: 0.7,
        cleanedMessage: message,
        immediateResponse: undefined,
      };
    }
  }

  return basic;
}
