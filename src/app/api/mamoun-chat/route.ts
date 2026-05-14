import { NextRequest, NextResponse } from 'next/server';
import ZAI from 'z-ai-web-dev-sdk';
import { chatGovernor, type GovernorDecision } from '@/lib/chat-governor';
import { BRAIN_PERSONAS, getBrainSystemPrompt, getBrainTemperature } from '@/lib/brains';
import { calculateFallbackConfidence, calculateRealConfidence } from '@/lib/chat-confidence';
import { setMode, type MamounModeId } from '@/lib/mode-engine';
import type { ChatMessage } from '@/lib/store';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { message, model, context, history = [] } = body;

    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { error: 'الرسالة مطلوبة' },
        { status: 400 },
      );
    }

    // ═══ ChatGovernor: التحليل المركزي ═══════════════════════
    const decision = chatGovernor.analyze(message, history);

    // ─── حقن أوامر مكتشفة → رد فوري ────────────────────────
    if (decision.injectionScore >= 0.5) {
      return NextResponse.json({
        response: 'تم اكتشاف محاولة حقن أوامر في رسالتك. يُرجى إعادة صياغة السؤال بشكل طبيعي.',
        content: 'تم اكتشاف محاولة حقن أوامر في رسالتك. يُرجى إعادة صياغة السؤال بشكل طبيعي.',
        brain: 'safety',
        winning_brain: 'safety',
        confidence: 0.1,
        source: 'security_filter',
        injection_score: decision.injectionScore,
      });
    }

    // ─── أوامر التحكم المباشر (رد فوري بدون LLM) ───────────
    if (decision.action === 'mode_change' && decision.parsedCommand.immediateResponse) {
      return NextResponse.json({
        response: decision.parsedCommand.immediateResponse,
        content: decision.parsedCommand.immediateResponse,
        brain: 'governor',
        winning_brain: 'governor',
        confidence: 1.0,
        source: 'command',
        is_real_deliberation: false,
        current_mode: decision.currentMode,
        routing: decision.routing,
        metadata: { action: decision.parsedCommand.action, params: decision.parsedCommand.params },
      });
    }

    // ═══ جسر التنفيذ: أوامر تُرسل فعلاً للباك إند ═════════════════════

    // ─── كشف التوكن — إذا أرسل المستخدم توكن GitHub ────────────
    const tokenMatch = message.match(/(?:توكن|token)\s+(ghp_\S+|gho_\S+|github_pat_\S+)/i);
    if (tokenMatch) {
      try {
        const configResponse = await fetch(`${BACKEND_URL}/api/update/configure`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: tokenMatch[1], repo: 'babsharqii2023-rgb/babsharqii-v5', branch: 'main' }),
          signal: AbortSignal.timeout(10000),
        });
        if (configResponse.ok) {
          return NextResponse.json({
            response: '✅ تم حفظ توكن GitHub بنجاح! الآن يمكنك قول "اسحب التحديثات" وسأقوم بالسحب.',
            content: '✅ تم حفظ توكن GitHub بنجاح! الآن يمكنك قول "اسحب التحديثات" وسأقوم بالسحب.',
            brain: 'governor', winning_brain: 'governor', confidence: 1.0,
            source: 'execution_bridge', is_real_deliberation: false,
          });
        }
      } catch { /* */ }
    }

    // ─── GIT_SYNC: سحب تحديثات من GitHub ─────────────────────
    if (decision.action === 'git_sync') {
      try {
        const syncResponse = await fetch(`${BACKEND_URL}/api/update/pull`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: AbortSignal.timeout(60000),
        });
        if (syncResponse.ok) {
          const data = await syncResponse.json();
          const resultMsg = data.status === 'up_to_date'
            ? '✅ النظام مُحدّث بالفعل — لا توجد تحديثات جديدة.'
            : `✅ تم سحب التحديثات!\n- Commit: ${data.new_commit || 'غير محدد'}\n- الوقت: ${data.elapsed_seconds || 0} ثانية\n- تعارضات: ${data.conflicts_resolved ? 'تم حلها' : 'لا يوجد'}\n- إعادة تشغيل: ${data.restart_recommended ? 'يُنصح' : 'لا يحتاج'}`;
          return NextResponse.json({
            response: resultMsg, content: resultMsg,
            brain: 'governor', winning_brain: 'governor', confidence: 0.95,
            source: 'execution_bridge', is_real_deliberation: false,
            metadata: { action: 'git_sync', result: data },
          });
        }
        // فشل — ربما يحتاج توكن
        const errData = await syncResponse.json().catch(() => ({}));
        const needsToken = syncResponse.status === 401 || String(errData.detail || '').includes('token');
        const msg = needsToken
          ? '⚠️ أحتاج توكن GitHub. أرسله: `توكن ghp_xxxxx`'
          : `❌ فشل السحب: ${errData.detail || 'خطأ غير معروف'}`;
        return NextResponse.json({
          response: msg, content: msg,
          brain: 'governor', winning_brain: 'governor', confidence: 0.8,
          source: 'execution_bridge', metadata: { action: 'git_sync_failed', needsToken },
        });
      } catch {
        return NextResponse.json({
          response: '❌ الباك إند غير متصل — لا أستطيع سحب التحديثات.',
          content: '❌ الباك إند غير متصل — لا أستطيع سحب التحديثات.',
          brain: 'governor', confidence: 0.5, source: 'execution_bridge',
        });
      }
    }

    // ─── SELF_MODIFY: تعديل ذاتي ─────────────────────────────
    if (decision.action === 'self_modify') {
      try {
        const specification = decision.parsedCommand.params.specification || decision.sanitizedMessage;
        const modifyResponse = await fetch(`${BACKEND_URL}/api/self-modify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ specification, auto_approve: false }),
          signal: AbortSignal.timeout(120000),
        });
        if (modifyResponse.ok) {
          const data = await modifyResponse.json();
          const statusMsg = data.status === 'approved'
            ? `✅ تم التعديل!\n- الملف: ${data.target_file || 'غير محدد'}\n- الأمان: ${Math.round((data.safety_score || 0.8) * 100)}%`
            : data.status === 'pending'
              ? `⏳ التعديل بانتظار الموافقة:\n- ${data.description || specification}\n- الخطر: ${data.risk_level || 'متوسط'}`
              : `❌ رُفض التعديل: ${data.validation_errors?.join(', ') || 'فحص الأمان'}`;
          return NextResponse.json({
            response: statusMsg, content: statusMsg,
            brain: 'governor', winning_brain: 'governor', confidence: 0.85,
            source: 'execution_bridge', is_real_deliberation: false,
            metadata: { action: 'self_modify', result: data },
          });
        }
      } catch { /* fall through */ }
    }

    // ─── SEARCH: بحث عميق ────────────────────────────────────
    if (decision.action === 'search') {
      const searchQuery = decision.parsedCommand.params.query || decision.sanitizedMessage;
      try {
        const searchResponse = await fetch(`${BACKEND_URL}/api/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: searchQuery, deep: true }),
          signal: AbortSignal.timeout(60000),
        });
        if (searchResponse.ok) {
          const data = await searchResponse.json();
          if (data.results?.length > 0) {
            const resultsText = data.results.slice(0, 5).map((r: { title?: string; url?: string; snippet?: string }, i: number) =>
              `${i + 1}. **${r.title || 'بدون عنوان'}**\n   ${r.snippet || ''}\n   🔗 ${r.url || ''}`
            ).join('\n\n');
            return NextResponse.json({
              response: `🔍 نتائج البحث عن "${searchQuery}":\n\n${resultsText}`,
              content: `🔍 نتائج البحث عن "${searchQuery}":\n\n${resultsText}`,
              brain: 'researcher', winning_brain: 'researcher', confidence: 0.85,
              source: 'execution_bridge', metadata: { action: 'deep_search', query: searchQuery },
            });
          }
        }
      } catch { /* */ }

      // Fallback: z-ai SDK للبحث
      try {
        const zai = await ZAI.create();
        const searchResult = await zai.functions.invoke('web_search', { query: searchQuery as string, num: 8 });
        if (Array.isArray(searchResult) && searchResult.length > 0) {
          const resultsText = searchResult.slice(0, 5).map((r: { name?: string; url?: string; snippet?: string }, i: number) =>
            `${i + 1}. **${r.name || 'بدون عنوان'}**\n   ${r.snippet || ''}\n   🔗 ${r.url || ''}`
          ).join('\n\n');
          return NextResponse.json({
            response: `🔍 نتائج البحث عن "${searchQuery}":\n\n${resultsText}`,
            content: `🔍 نتائج البحث عن "${searchQuery}":\n\n${resultsText}`,
            brain: 'researcher', winning_brain: 'researcher', confidence: 0.8,
            source: 'execution_bridge_zai', metadata: { action: 'deep_search', provider: 'z-ai-sdk' },
          });
        }
      } catch { /* */ }
    }

    // ─── SELF_ANALYZE: تحليل ذاتي ─────────────────────────────
    if (decision.action === 'self_analyze') {
      try {
        const [statusRes, brainsRes, healthRes] = await Promise.allSettled([
          fetch(`${BACKEND_URL}/api/kernel/status`, { signal: AbortSignal.timeout(5000) }),
          fetch(`${BACKEND_URL}/api/brains`, { signal: AbortSignal.timeout(5000) }),
          fetch(`${BACKEND_URL}/api/health-monitor`, { signal: AbortSignal.timeout(5000) }),
        ]);
        const kernelData = statusRes.status === 'fulfilled' && statusRes.value.ok ? await statusRes.value.json() : {};
        const brainsData = brainsRes.status === 'fulfilled' && brainsRes.value.ok ? await brainsRes.value.json() : {};
        const healthData = healthRes.status === 'fulfilled' && healthRes.value.ok ? await healthRes.value.json() : {};
        const analysisMsg = `📊 **تحليل ذاتي لمأمون v40.0:**\n\n` +
          `🟢 النواة: ${kernelData.kernel_status || 'غير متصلة'}\n` +
          `⏱ التشغيل: ${Math.round((kernelData.uptime || 0) / 60)} دقيقة\n` +
          `🧠 أدمغة نشطة: ${brainsData.brains?.filter((b: { status: string }) => b.status === 'active').length || 5}/5\n` +
          `💚 صحة عامة: ${healthData.overall_health || 'غير متاحة'}%\n` +
          `⚠️ تنبيهات: ${healthData.active_alerts || 0}\n` +
          `🔧 الوضع: ${decision.currentMode.nameAr}`;
        return NextResponse.json({
          response: analysisMsg, content: analysisMsg,
          brain: 'governor', winning_brain: 'governor', confidence: 0.9,
          source: 'execution_bridge', is_real_deliberation: false,
          current_mode: decision.currentMode,
          metadata: { action: 'self_analyze', kernelData, brainsData, healthData },
        });
      } catch { /* backend unavailable */ }
    }

    // ═══ Priority 1: Kernel Deliberation (5 real brains) ══════
    if (decision.needsFullDeliberation) {
      try {
        const kernelPayload: Record<string, unknown> = {
          message: decision.sanitizedMessage,
          model: model || 'auto',
          context: context || {},
        };

        // Smart context from governor
        if (decision.smartContext.messages.length > 0) {
          kernelPayload.history = decision.smartContext.messages;
        }

        // Mode information for backend
        if (decision.currentMode.id !== 'default') {
          kernelPayload.mode = decision.currentMode.id;
          kernelPayload.active_brains = decision.activatedBrains;
          kernelPayload.temperature = decision.suggestedTemperature;
        }

        const kernelResponse = await fetch(`${BACKEND_URL}/api/kernel/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(kernelPayload),
          signal: AbortSignal.timeout(60000),
        });

        if (kernelResponse.ok) {
          const data = await kernelResponse.json();
          const confidenceResult = calculateRealConfidence({
            responseText: data.response || data.content || '',
            isRealDeliberation: true,
            consensusLevel: data.consensus_level,
            conflictDetected: data.conflict_detected,
            cjs: data.cjs,
            fallbackCount: 0,
            latencyMs: 0,
            temperature: decision.suggestedTemperature,
          });

          // Generate feedforward suggestions
          const feedforwardSuggestions = chatGovernor.generateFeedforward(decision, data.response || '');

          return NextResponse.json({
            response: data.response || data.content,
            content: data.response || data.content,
            brain: data.winning_brain,
            winning_brain: data.winning_brain,
            confidence: data.confidence ?? confidenceResult.confidence,
            confidenceResult,
            escalation: data.escalation,
            concerns: data.concerns,
            needs_approval: data.needs_approval,
            needs_user_input: data.needs_user_input,
            brain_responses: data.brain_responses || {},
            consensus_level: data.consensus_level || 0,
            cjs: data.cjs || 0,
            conflict_detected: data.conflict_detected || false,
            mirror_reflection: data.mirror_reflection || '',
            query_type: data.query_type || '',
            source: 'kernel',
            is_real_deliberation: true,
            current_mode: decision.currentMode,
            routing: decision.routing,
            feedforward_suggestions: feedforwardSuggestions,
            metadata: { model: model || 'auto', governorAction: decision.action },
          });
        }
      } catch (kernelError) {
        console.log('[mamoun-chat] Kernel unavailable, falling back to z-ai SDK:', kernelError instanceof Error ? kernelError.message : 'unknown');
      }
    }

    // ═══ Priority 2: z-ai SDK fallback (single-brain) ════════
    const primaryBrain = decision.routing.primaryBrain;
    const brainPersona = BRAIN_PERSONAS.find(b => b.id === primaryBrain) || BRAIN_PERSONAS[0];

    const fullSystemPrompt = chatGovernor.buildFullSystemPrompt(decision);
    const selectedModel = model || brainPersona.model || 'glm-5.1';

    // Context messages from governor
    const contextMessages = decision.smartContext.messages.map(m => ({
      role: (m.role === 'user' ? 'user' : 'assistant') as 'user' | 'assistant',
      content: m.content.substring(0, 4000),
    }));

    const messages = [
      { role: 'system' as const, content: fullSystemPrompt },
      ...contextMessages,
      { role: 'user' as const, content: decision.sanitizedMessage },
    ];

    try {
      const zai = await ZAI.create();
      const startTime = Date.now();

      const response = await zai.chat.completions.create({
        model: selectedModel,
        messages,
        stream: false,
        temperature: decision.suggestedTemperature,
      });

      const latency = Date.now() - startTime;
      let assistantContent = '';

      if (response?.choices?.[0]?.message?.content) {
        assistantContent = response.choices[0].message.content;
      } else if (typeof response === 'string') {
        assistantContent = response;
      } else {
        assistantContent = 'عذراً، لم أتمكن من معالجة طلبك.';
      }

      const confidence = calculateFallbackConfidence(assistantContent, 1, latency, decision.suggestedTemperature);

      // Feedforward suggestions
      const feedforwardSuggestions = chatGovernor.generateFeedforward(decision, assistantContent);

      return NextResponse.json({
        response: assistantContent,
        content: assistantContent,
        brain: primaryBrain,
        winning_brain: primaryBrain,
        confidence,
        latency,
        brain_responses: {
          [primaryBrain]: {
            response: assistantContent.substring(0, 300),
            confidence,
            stance: 'support',
            model_used: selectedModel,
            simulated: true,
          },
        },
        consensus_level: confidence,
        cjs: confidence,
        conflict_detected: false,
        query_type: decision.parsedCommand.action === 'DEEP_SEARCH' ? 'search' : 'general',
        source: 'fallback_single_brain',
        deliberation_simulated: true,
        is_real_deliberation: false,
        current_mode: decision.currentMode,
        routing: decision.routing,
        feedforward_suggestions: feedforwardSuggestions,
        metadata: {
          model: selectedModel,
          brainPersona: { nameAr: brainPersona.nameAr, nameEn: brainPersona.nameEn, thinkingStyle: brainPersona.thinkingStyle },
          wasFiltered: decision.wasFiltered,
          governorAction: decision.action,
        },
      });
    } catch (sdkError) {
      console.error('[mamoun-chat] z-ai SDK fallback also failed:', sdkError);
    }

    return NextResponse.json(
      { error: 'جميع نقاط النهاية غير متاحة. يرجى المحاولة لاحقاً.' },
      { status: 503 },
    );
  } catch (error: unknown) {
    const errMsg = error instanceof Error ? error.message : 'Internal server error';
    console.error('[mamoun-chat] Error:', errMsg);
    return NextResponse.json(
      { error: errMsg },
      { status: 500 },
    );
  }
}

// ═══ Kernel status endpoint ═══════════════════════════════════
export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/kernel/status`, {
      signal: AbortSignal.timeout(5000),
    });
    if (response.ok) {
      const data = await response.json();
      return NextResponse.json(data);
    }
  } catch { /* offline */ }

  return NextResponse.json({
    running: false,
    brains_registered: [],
    version: 'v40.0',
    source: 'local_fallback',
    current_mode: chatGovernor.analyze('').currentMode,
  });
}
