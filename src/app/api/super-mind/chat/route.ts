// ═══════════════════════════════════════════════════════════════════
// SuperMind BFF Main Route — طبقة BFF الرئيسية
// Intelligent intent routing + API proxy + response transformation
// Returns structured data + UI directives for Generative UI system
// ═══════════════════════════════════════════════════════════════════

import { NextRequest, NextResponse } from 'next/server';
import { routeIntent, type SuperMindRoute } from '@/lib/super-mind-router';
import { generateUIDirective, type UIDirective } from '@/lib/ui-directive';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

interface SuperMindResponse {
  chat: {
    text: string;
    cards?: Array<{ title: string; content: string; actions?: string[] }>;
    actions?: Array<{ label: string; intent: string; payload?: Record<string, unknown> }>;
  };
  screen: {
    component: string;
    props: Record<string, unknown>;
    animation: string;
    directive?: UIDirective;
  };
  brain: {
    activeBrain: string | null;
    deliberationState: 'idle' | 'thinking' | 'responding';
    activatedBrains: string[];
    confidence: number;
  };
  sound?: {
    event: string;
    brainOscillator?: string;
  };
  requiresConfirmation?: boolean;
  autonomyLevel?: number;
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { message, model, intent: overrideIntent, activated_brains, context, conversationId } = body;

    if (!message) {
      return NextResponse.json({ error: 'الرسالة مطلوبة' }, { status: 400 });
    }

    // Stage 1: Route the intent
    const route: SuperMindRoute = overrideIntent
      ? { ...routeIntent(overrideIntent), confidence: 1 }
      : routeIntent(message);

    // Stage 2: Call backend API based on route
    const apiData = await callBackendAPI(route, message, { model, activated_brains, context, conversationId });

    // Stage 3: Generate UI directive
    const uiDirective = generateUIDirective(route.intent, apiData);

    // Stage 4: Build structured SuperMind response
    const response: SuperMindResponse = {
      chat: {
        text: apiData.content || apiData.response || apiData.message || 'تم المعالجة',
        cards: buildChatCards(route, apiData),
        actions: buildQuickActions(route),
      },
      screen: {
        component: route.screenComponent,
        props: apiData,
        animation: route.animation,
        directive: uiDirective,
      },
      brain: {
        activeBrain: apiData.winning_brain || apiData.brain || route.activatedBrains[0] || null,
        deliberationState: apiData.consensus_level ? 'responding' : 'idle',
        activatedBrains: route.activatedBrains,
        confidence: apiData.confidence || route.confidence,
      },
      sound: {
        event: route.soundEvent,
        brainOscillator: route.activatedBrains[0],
      },
      requiresConfirmation: route.requiresConfirmation,
      autonomyLevel: route.autonomyLevel,
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error('[SuperMind BFF] Error:', error);
    return NextResponse.json(
      { error: 'حدث خطأ داخلي في معالجة الرسالة' },
      { status: 500 }
    );
  }
}

// ─── Backend API Caller ──────────────────────────────────────

async function callBackendAPI(
  route: SuperMindRoute,
  message: string,
  options: { model?: string; activated_brains?: string[]; context?: unknown; conversationId?: string }
): Promise<Record<string, any>> {
  const endpoint = mapRouteToBackendEndpoint(route);

  try {
    const response = await fetch(`${BACKEND_URL}${endpoint}`, {
      method: route.httpMethod,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        model: options.model || 'glm-5.1',
        intent: route.intent,
        activated_brains: route.activatedBrains,
        context: options.context || {},
        conversation_id: options.conversationId,
      }),
      signal: AbortSignal.timeout(45000),
    });

    if (response.ok) {
      const data = await response.json();
      return { ...data, _source: 'backend' };
    }
  } catch {
    // Backend unavailable — try fallback
  }

  // Fallback: Try the general chat endpoint
  try {
    const chatResponse = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, model: options.model || 'glm-5.1' }),
      signal: AbortSignal.timeout(30000),
    });

    if (chatResponse.ok) {
      const data = await chatResponse.json();
      return { ...data, _source: 'fallback' };
    }
  } catch {
    // All fallbacks failed
  }

  return {
    content: 'عذراً، خدمة المعالجة غير متاحة حالياً.',
    _source: 'offline',
    _intent: route.intent,
  };
}

function mapRouteToBackendEndpoint(route: SuperMindRoute): string {
  const mapping: Record<string, string> = {
    'projects.list': '/api/project-mgmt/projects',
    'projects.monitor': '/api/project-mgmt/projects',
    'projects.promote': '/api/project-mgmt/projects',
    'site.stats': '/api/living/vitals',
    'research.deep': '/api/supermind/research',
    'research.extended': '/api/supermind/research/extended',
    'tool.create': '/api/supermind/tools/create',
    'agent.build': '/api/supermind/agents/create',
    'deploy': '/api/supermind/deploy',
    'healing': '/api/self-heal',
    'self.modify': '/api/self-modify',
    'workflow': '/api/supermind/workflow',
    'terminal': '/api/terminal',
    'brain.state': '/api/brains',
    'vitals': '/api/living/vitals',
    'conversations.search': '/api/supermind/conversations',
    'update.pull': '/api/update/pull',
    'capabilities.list': '/api/capabilities',
    'code.generate': '/api/supermind/code-generate',
    'project.scaffold': '/api/supermind/scaffold',
    'evolution.status': '/api/evolution/current',
    'health.dashboard': '/api/health-monitor',
    'default': '/api/chat',
  };
  return mapping[route.intent] || '/api/chat';
}

// ─── Chat Card Builder ──────────────────────────────────────

function buildChatCards(
  route: SuperMindRoute,
  data: Record<string, any>
): Array<{ title: string; content: string; actions?: string[] }> {
  const cards: Array<{ title: string; content: string; actions?: string[] }> = [];

  if (route.requiresConfirmation) {
    cards.push({
      title: route.labelAr,
      content: `هل تريد تنفيذ: ${route.labelAr}؟`,
      actions: ['تأكيد', 'رفض', 'تعديل'],
    });
  }

  if (data.winning_brain) {
    cards.push({
      title: 'الدماغ الفائز',
      content: data.winning_brain,
    });
  }

  return cards;
}

// ─── Quick Actions Builder ──────────────────────────────────

function buildQuickActions(
  route: SuperMindRoute
): Array<{ label: string; intent: string; payload?: Record<string, unknown> }> {
  const actions: Array<{ label: string; intent: string; payload?: Record<string, unknown> }> = [];

  switch (route.intent) {
    case 'projects.list':
      actions.push(
        { label: 'مراقبة المشاريع', intent: 'projects.monitor' },
        { label: 'إنشاء مشروع جديد', intent: 'project.scaffold' },
      );
      break;
    case 'research.deep':
      actions.push(
        { label: 'بحث ممتد', intent: 'research.extended' },
        { label: 'حالة الأدمغة', intent: 'brain.state' },
      );
      break;
    case 'healing':
      actions.push(
        { label: 'لوحة الصحة', intent: 'health.dashboard' },
        { label: 'تحديث النظام', intent: 'update.pull' },
      );
      break;
    case 'brain.state':
      actions.push(
        { label: 'الحيوية', intent: 'vitals' },
        { label: 'لوحة الصحة', intent: 'health.dashboard' },
      );
      break;
  }

  return actions;
}
