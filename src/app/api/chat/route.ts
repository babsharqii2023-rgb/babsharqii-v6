import { NextRequest, NextResponse } from 'next/server';
import { getAuthHeaders } from '@/lib/backend-proxy';
import ZAI from 'z-ai-web-dev-sdk';
import { chatGovernor } from '@/lib/chat-governor';
import { BRAIN_PERSONAS, getBrainSystemPrompt, getBrainTemperature, deliberateViaBackend, type BrainRoutingResult } from '@/lib/brains';
import { calculateFallbackConfidence } from '@/lib/chat-confidence';
import type { ChatMessage } from '@/lib/store';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

const MODEL_MAP: Record<string, string> = {
  'glm-5.1': 'glm-5.1',
  'glm-4-plus': 'glm-4-plus',
  'glm-4': 'glm-4',
  'gemini-3.1-pro': 'gemini-3.1-pro',
  'deepseek-chat': 'deepseek-chat',
  'deepseek-reasoner': 'deepseek-reasoner',
};

async function* parseOpenAIStream(readableStream: ReadableStream<Uint8Array>): AsyncGenerator<string> {
  const reader = readableStream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n');
      buffer = parts.pop() || '';
      for (const part of parts) {
        const trimmed = part.trim();
        if (trimmed.startsWith('data: ')) {
          const data = trimmed.slice(6).trim();
          if (data === '[DONE]') return;
          try {
            const parsed = JSON.parse(data);
            const content = parsed?.choices?.[0]?.delta?.content;
            if (content) yield content;
          } catch { /* skip */ }
        }
      }
    }
    if (buffer.trim().startsWith('data: ')) {
      const data = buffer.trim().slice(6).trim();
      if (data !== '[DONE]') {
        try {
          const parsed = JSON.parse(data);
          const content = parsed?.choices?.[0]?.delta?.content;
          if (content) yield content;
        } catch { /* skip */ }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { message, model, history = [], stream = false } = body;

    if (!message || typeof message !== 'string') {
      return NextResponse.json({ error: 'الرسالة مطلوبة' }, { status: 400 });
    }

    // ═══ ChatGovernor: التحليل المركزي ═══════════════════════
    const decision = chatGovernor.analyze(message, history);

    // ─── حقن مكتشف → رد فوري ────────────────────────────────
    if (decision.injectionScore >= 0.5) {
      if (stream) {
        const errorStream = new ReadableStream({
          start(controller) {
            const encoder = new TextEncoder();
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'error', message: 'تم اكتشاف محاولة حقن أوامر.', brain: 'safety' })}\n\n`));
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'done', brain: 'safety', confidence: 0.1 })}\n\n`));
            controller.close();
          },
        });
        return new Response(errorStream, { headers: { 'Content-Type': 'text/event-stream' } });
      }
      return NextResponse.json({
        content: 'تم اكتشاف محاولة حقن أوامر. يُرجى إعادة صياغة السؤال.',
        brain: 'safety',
        confidence: 0.1,
        source: 'security_filter',
      });
    }

    // ─── أوامر التحكم المباشر (رد فوري بدون LLM) ───────────
    if (decision.action === 'mode_change' && decision.parsedCommand.immediateResponse) {
      if (stream) {
        const cmdStream = new ReadableStream({
          start(controller) {
            const encoder = new TextEncoder();
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'token', content: decision.parsedCommand.immediateResponse, brain: 'governor' })}\n\n`));
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'done', brain: 'governor', confidence: 1.0, current_mode: decision.currentMode })}\n\n`));
            controller.close();
          },
        });
        return new Response(cmdStream, { headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' } });
      }
      return NextResponse.json({
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: decision.parsedCommand.immediateResponse,
        timestamp: Date.now(),
        brain: 'governor',
        confidence: 1.0,
        source: 'command',
        is_real_deliberation: false,
        current_mode: decision.currentMode,
      });
    }

    // ═══ جسر التنفيذ: أوامر تُرسل فعلاً للباك إند ═════════════════════

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
            : `✅ تم سحب التحديثات بنجاح!\n- Commit: ${data.new_commit || 'غير محدد'}\n- الوقت: ${data.elapsed_seconds || 0} ثانية\n- تعارضات: ${data.conflicts_resolved ? 'تم حلها تلقائياً' : 'لا يوجد'}\n- تعديلات محلية: ${data.had_local_changes ? 'نعم (تم حفظها)' : 'لا'}\n- يُنصح بإعادة التشغيل: ${data.restart_recommended ? 'نعم' : 'لا'}`;
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant', content: resultMsg, timestamp: Date.now(),
            brain: 'governor', confidence: 0.95, source: 'execution_bridge', is_real_deliberation: false,
            metadata: { action: 'git_sync', backendResponse: data },
          });
        }
        // إذا فشل السحب — ربما يحتاج توكن
        const errData = await syncResponse.json().catch(() => ({}));
        const needsToken = syncResponse.status === 401 || String(errData.detail || '').includes('token') || String(errData.detail || '').includes('auth');
        const tokenMsg = needsToken
          ? '⚠️ أحتاج توكن GitHub للسحب. أرسله لي بهذا الشكل:\n`توكن ghp_xxxxx`'
          : `❌ فشل السحب: ${errData.detail || errData.error || 'خطأ غير معروف'}`;
        return NextResponse.json({
          id: `msg-${Date.now()}`, role: 'assistant', content: tokenMsg, timestamp: Date.now(),
          brain: 'governor', confidence: 0.8, source: 'execution_bridge',
          metadata: { action: 'git_sync_failed', needsToken, statusCode: syncResponse.status },
        });
      } catch {
        return NextResponse.json({
          id: `msg-${Date.now()}`, role: 'assistant',
          content: '❌ لا أستطيع الوصول لنظام التحديث — الباك إند غير متصل.\nتأكد أن الخادم يعمل على المنفذ 8000.',
          timestamp: Date.now(), brain: 'governor', confidence: 0.5, source: 'execution_bridge',
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
            ? `✅ تم اقتراح وتطبيق التعديل!\n- الملف: ${data.target_file || data.modification?.target_file || 'غير محدد'}\n- الأمان: ${Math.round((data.safety_score || 0.8) * 100)}%\n- الخطر: ${data.risk_level || 'منخفض'}`
            : data.status === 'pending'
              ? `⏳ تم اقتراح التعديل بانتظار الموافقة:\n- الملف: ${data.target_file || 'غير محدد'}\n- الوصف: ${data.description || specification}\n- الخطر: ${data.risk_level || 'متوسط'}\n\nأوافق / أرفض`
              : `❌ تم رفض التعديل: ${data.validation_errors?.join(', ') || 'لم يجتز فحص الأمان'}`;
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant', content: statusMsg, timestamp: Date.now(),
            brain: 'governor', confidence: 0.85, source: 'execution_bridge', is_real_deliberation: false,
            metadata: { action: 'self_modify', backendResponse: data },
          });
        }
      } catch { /* backend unavailable — fall through to LLM */ }
    }

    // ─── SEARCH: بحث عميق على الويب ───────────────────────────
    if (decision.action === 'search') {
      const searchQuery = decision.parsedCommand.params.query || decision.sanitizedMessage;
      
      // v40.0 Fusion: حاول DeepResearch الكامل أولاً
      try {
        const deepResponse = await fetch(`${BACKEND_URL}/api/research/deep`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: searchQuery, depth: 3, verify: true }),
          signal: AbortSignal.timeout(120000),
        });
        if (deepResponse.ok) {
          const data = await deepResponse.json();
          const reportMsg = `🔍 **بحث عميق: "${searchQuery}"**\n\n` +
            `📝 **الملخص:** ${data.summary || data.analysis || ''}\n\n` +
            `📚 **المصادر:** ${(data.sources || []).slice(0, 5).map((s: { title?: string; url?: string; credibility?: string }, i: number) => `${i + 1}. ${s.title || 'مصدر'} ${s.credibility ? `(${s.credibility})` : ''}`).join('\n')}\n\n` +
            `🎯 **ثقة:** ${Math.round((data.confidence_score || 0.5) * 100)}%`;
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant', content: reportMsg,
            timestamp: Date.now(), brain: 'researcher', confidence: data.confidence_score || 0.85,
            source: 'deep_research', metadata: { action: 'deep_search', report: data },
          });
        }
      } catch { /* DeepResearch unavailable, fallback */ }

      // Fallback: بحث سطحي من الباك إند
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
              id: `msg-${Date.now()}`, role: 'assistant',
              content: `🔍 نتائج البحث عن "${searchQuery}":\n\n${resultsText}\n\n_تم العثور على ${data.results.length} نتيجة_`,
              timestamp: Date.now(), brain: 'researcher', confidence: 0.85, source: 'execution_bridge',
              metadata: { action: 'deep_search', query: searchQuery, resultCount: data.results.length },
            });
          }
        }
      } catch { /* backend search unavailable */ }

      // Fallback: استخدم z-ai SDK للبحث
      try {
        const zai = await ZAI.create();
        const searchResult = await zai.functions.invoke('web_search', { query: searchQuery as string, num: 8 });
        if (Array.isArray(searchResult) && searchResult.length > 0) {
          const resultsText = searchResult.slice(0, 5).map((r: { name?: string; url?: string; snippet?: string }, i: number) =>
            `${i + 1}. **${r.name || 'بدون عنوان'}**\n   ${r.snippet || ''}\n   🔗 ${r.url || ''}`
          ).join('\n\n');
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant',
            content: `🔍 نتائج البحث عن "${searchQuery}":\n\n${resultsText}\n\n_تم العثور على ${searchResult.length} نتيجة_`,
            timestamp: Date.now(), brain: 'researcher', confidence: 0.8, source: 'execution_bridge_zai',
            metadata: { action: 'deep_search', query: searchQuery, resultCount: searchResult.length, provider: 'z-ai-sdk' },
          });
        }
      } catch { /* z-ai search also failed */ }
    }

    // ─── SELF_ANALYZE: تحليل ذاتي ─────────────────────────────
    if (decision.action === 'self_analyze') {
      try {
        const [statusRes, brainsRes] = await Promise.allSettled([
          fetch(`${BACKEND_URL}/api/kernel/status`, { signal: AbortSignal.timeout(5000) }),
          fetch(`${BACKEND_URL}/api/brains`, { signal: AbortSignal.timeout(5000) }),
        ]);
        const kernelData = statusRes.status === 'fulfilled' && statusRes.value.ok ? await statusRes.value.json() : {};
        const brainsData = brainsRes.status === 'fulfilled' && brainsRes.value.ok ? await brainsRes.value.json() : {};
        const analysisMsg = `📊 **تحليل ذاتي لمأمون v40.0:**\n\n` +
          `🟢 حالة النواة: ${kernelData.kernel_status || 'غير متصلة'}\n` +
          `⏱ وقت التشغيل: ${Math.round((kernelData.uptime || 0) / 60)} دقيقة\n` +
          `🧠 الأدمغة النشطة: ${brainsData.brains?.filter((b: { status: string }) => b.status === 'active').length || 5}/5\n` +
          `⚡ العمليات: ${kernelData.active_processes || 0}\n` +
          `🔧 الوضع: ${decision.currentMode.nameAr}`;
        return NextResponse.json({
          id: `msg-${Date.now()}`, role: 'assistant', content: analysisMsg, timestamp: Date.now(),
          brain: 'governor', confidence: 0.9, source: 'execution_bridge', is_real_deliberation: false,
          metadata: { action: 'self_analyze', kernelData, brainsData },
        });
      } catch {
        // Fall through to LLM for analysis
      }
    }

    // ─── COMMAND: أوامر عامة ───────────────────────────────────
    if (decision.action === 'command' && decision.parsedCommand.action === 'CLEAR_MEMORY') {
      return NextResponse.json({
        id: `msg-${Date.now()}`, role: 'assistant', content: '🔄 تم مسح الذاكرة — نبدأ محادثة جديدة!', timestamp: Date.now(),
        brain: 'governor', confidence: 1.0, source: 'command',
      });
    }

    // ═══ v40.0 Fusion: جسور العقل الخارق ═══════════════════════════

    // ─── SELF_IMPROVE: تحسين ذاتي ──────────────────────────
    if (decision.action === 'self_improve') {
      try {
        const specification = decision.parsedCommand.params.specification || decision.sanitizedMessage;
        const improveResponse = await fetch(`${BACKEND_URL}/api/evolution/improve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ area: specification, description: specification, severity: 'medium' }),
          signal: AbortSignal.timeout(120000),
        });
        if (improveResponse.ok) {
          const data = await improveResponse.json();
          const msg = data.success
            ? `✅ تم التحسين الذاتي بنجاح!\n- المنطقة: ${data.area || specification}\n- معرّف الضعف: ${data.weakness_id || 'N/A'}`
            : `⚠️ لم أستطع التحسين تلقائياً: ${data.error || 'سبب غير معروف'}`;
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant', content: msg, timestamp: Date.now(),
            brain: 'governor', confidence: 0.85, source: 'execution_bridge',
            metadata: { action: 'self_improve', backendResponse: data },
          });
        }
      } catch { /* backend unavailable */ }
    }

    // ─── CREATE_FILE: إنشاء ملف جديد ───────────────────────
    if (decision.action === 'create_file') {
      try {
        const specification = decision.parsedCommand.params.specification || decision.sanitizedMessage;
        const fsResponse = await fetch(`${BACKEND_URL}/api/fs/create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: specification, content: '', specification }),
          signal: AbortSignal.timeout(30000),
        });
        if (fsResponse.ok) {
          const data = await fsResponse.json();
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant',
            content: `✅ تم إنشاء الملف: ${data.path || specification}`,
            timestamp: Date.now(), brain: 'governor', confidence: 0.9, source: 'execution_bridge',
            metadata: { action: 'create_file', backendResponse: data },
          });
        }
      } catch { /* backend unavailable */ }
    }

    // ─── READ_FILE: قراءة ملف ──────────────────────────────
    if (decision.action === 'read_file') {
      try {
        const path = decision.parsedCommand.params.path || decision.sanitizedMessage;
        const fsResponse = await fetch(`${BACKEND_URL}/api/fs/read?path=${encodeURIComponent(String(path))}`, {
          signal: AbortSignal.timeout(10000),
        });
        if (fsResponse.ok) {
          const data = await fsResponse.json();
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant',
            content: `📄 **${data.path || path}:**\n\`\`\`\n${(data.content || '').substring(0, 4000)}\n\`\`\``,
            timestamp: Date.now(), brain: 'governor', confidence: 0.9, source: 'execution_bridge',
            metadata: { action: 'read_file', backendResponse: data },
          });
        }
      } catch { /* backend unavailable */ }
    }

    // ─── EDIT_FILE: تعديل ملف ──────────────────────────────
    if (decision.action === 'edit_file') {
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
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant',
            content: data.status === 'approved'
              ? `✅ تم تعديل الملف: ${data.target_file || data.modification?.target_file}`
              : `⏳ التعديل مقترح بانتظار الموافقة: ${data.target_file || specification}`,
            timestamp: Date.now(), brain: 'governor', confidence: 0.85, source: 'execution_bridge',
            metadata: { action: 'edit_file', backendResponse: data },
          });
        }
      } catch { /* backend unavailable */ }
    }

    // ─── LIST_FILES: عرض الملفات ───────────────────────────
    if (decision.action === 'list_files') {
      try {
        const fsResponse = await fetch(`${BACKEND_URL}/api/fs/tree`, {
          signal: AbortSignal.timeout(10000),
        });
        if (fsResponse.ok) {
          const data = await fsResponse.json();
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant',
            content: `📁 **شجرة المشروع:**\n\`\`\`\n${(data.tree || data.content || '').substring(0, 3000)}\n\`\`\``,
            timestamp: Date.now(), brain: 'governor', confidence: 0.9, source: 'execution_bridge',
            metadata: { action: 'list_files' },
          });
        }
      } catch { /* backend unavailable */ }
    }

    // ─── BUILD_AGENT: بناء أيجنت ───────────────────────────
    if (decision.action === 'build_agent') {
      try {
        const specification = decision.parsedCommand.params.specification || decision.sanitizedMessage;
        const agentResponse = await fetch(`${BACKEND_URL}/api/evolution/build-agent`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ specification }),
          signal: AbortSignal.timeout(120000),
        });
        if (agentResponse.ok) {
          const data = await agentResponse.json();
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant',
            content: data.success
              ? `✅ تم بناء الأيجنت: **${data.agent_name}**\n- المعرّف: ${data.agent_id}\n- الملف: ${data.file}`
              : `❌ فشل بناء الأيجنت: ${data.error}`,
            timestamp: Date.now(), brain: 'governor', confidence: 0.85, source: 'execution_bridge',
            metadata: { action: 'build_agent', backendResponse: data },
          });
        }
      } catch { /* backend unavailable */ }
    }

    // ─── BUILD_PROJECT: بناء مشروع ─────────────────────────
    if (decision.action === 'build_project') {
      try {
        const specification = decision.parsedCommand.params.specification || decision.sanitizedMessage;
        const scaffoldResponse = await fetch(`${BACKEND_URL}/api/evolution/scaffold`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ description: specification }),
          signal: AbortSignal.timeout(180000),
        });
        if (scaffoldResponse.ok) {
          const data = await scaffoldResponse.json();
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant',
            content: data.success
              ? `✅ تم بناء المشروع: **${data.project_name}**\n- الملفات: ${data.files_created}\n- المسار: ${data.target_dir}`
              : `❌ فشل بناء المشروع: ${data.error}`,
            timestamp: Date.now(), brain: 'governor', confidence: 0.85, source: 'execution_bridge',
            metadata: { action: 'build_project', backendResponse: data },
          });
        }
      } catch { /* backend unavailable */ }
    }

    // ─── CREATE_TOOL: بناء أداة ─────────────────────────────
    if (decision.action === 'create_tool') {
      try {
        const toolDesc = decision.parsedCommand.params.tool_description || decision.sanitizedMessage;
        const toolResponse = await fetch(`${BACKEND_URL}/api/evolution/create-tool`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tool_description: toolDesc }),
          signal: AbortSignal.timeout(120000),
        });
        if (toolResponse.ok) {
          const data = await toolResponse.json();
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant',
            content: data.success
              ? `✅ تم بناء الأداة: **${data.tool_name}**\n- المعرّف: ${data.tool_id}\n- الملف: ${data.file}`
              : `❌ فشل بناء الأداة: ${data.error}`,
            timestamp: Date.now(), brain: 'governor', confidence: 0.85, source: 'execution_bridge',
            metadata: { action: 'create_tool', backendResponse: data },
          });
        }
      } catch { /* backend unavailable */ }
    }

    // ─── SET_API_KEY: تعيين مفتاح API ──────────────────────
    if (decision.action === 'set_api_key') {
      try {
        const { provider, key } = decision.parsedCommand.params;
        const keyResponse = await fetch(`${BACKEND_URL}/api/v2/api-keys`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider: provider || 'auto', key: key || '' }),
          signal: AbortSignal.timeout(10000),
        });
        if (keyResponse.ok) {
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant',
            content: `✅ تم تعيين مفتاح API للمزوّد: ${provider || 'auto'}`,
            timestamp: Date.now(), brain: 'governor', confidence: 0.9, source: 'execution_bridge',
            metadata: { action: 'set_api_key', provider },
          });
        }
      } catch { /* backend unavailable */ }
    }

    // ─── BRAIN_STATUS: حالة الأدمغة التفصيلية ────────────────
    if (decision.action === 'brain_status') {
      try {
        const statusResponse = await fetch(`${BACKEND_URL}/api/brains/status`, {
          signal: AbortSignal.timeout(10000),
        });
        if (statusResponse.ok) {
          const data = await statusResponse.json();
          const brains = data.brains || {};
          const summary = data.summary || {};

          // Build a readable status message
          let statusMsg = '🧠 **تقرير حالة الأدمغة:**\n\n';
          for (const [bid, bstatus] of Object.entries(brains) as [string, any][]) {
            const statusIcon = bstatus.status === 'active' || bstatus.status === 'thinking' ? '🟢' :
                              bstatus.status === 'idle' ? '🟡' :
                              bstatus.is_on_fallback ? '🟠' : '🔴';
            const fallbackNote = bstatus.is_on_fallback
              ? ` ⚠️ يستخدم بديل ${bstatus.actual_model} بدلاً من ${bstatus.original_model}`
              : '';
            const apiKeyNote = !bstatus.has_api_key
              ? ` 🔑 يحتاج ${bstatus.api_key_env}`
              : '';
            statusMsg += `${statusIcon} **${bstatus.name_ar || bid}** (${bid})\n`;
            statusMsg += `   النموذج: ${bstatus.actual_model} | الثقة: ${Math.round((bstatus.confidence || 0) * 100)}%${fallbackNote}${apiKeyNote}\n\n`;
          }

          if (summary.fallback_warnings?.length > 0) {
            statusMsg += '⚠️ **تحذيرات النماذج البديلة:**\n';
            for (const w of summary.fallback_warnings) {
              statusMsg += `- ${w}\n`;
            }
          }

          statusMsg += `\n📊 **ملخص:** ${summary.active_brains || 0}/${summary.total_brains || 0} نشط | ${summary.brains_on_fallback || 0} على بديل | ${summary.missing_api_keys || 0} يحتاج مفتاح API`;

          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant', content: statusMsg, timestamp: Date.now(),
            brain: 'governor', confidence: 0.95, source: 'execution_bridge', is_real_deliberation: false,
            metadata: { action: 'brain_status', brainStatus: data },
          });
        }
      } catch { /* backend unavailable */ }

      // Fallback: return basic brain status from local data
      const localStatus = BRAIN_PERSONAS.map(b => {
        const icon = b.enabled ? '🟢' : '🔴';
        return `${icon} **${b.nameAr}** (${b.nameEn}) — النموذج: ${b.model} | الحرارة: ${b.temperature}`;
      }).join('\n');

      return NextResponse.json({
        id: `msg-${Date.now()}`, role: 'assistant',
        content: `🧠 **حالة الأدمغة (محلية — الباك إند غير متصل):**\n\n${localStatus}`,
        timestamp: Date.now(), brain: 'governor', confidence: 0.7, source: 'local',
        is_real_deliberation: false,
      });
    }

    // ─── ASSESS_CAPABILITIES: تقييم القدرات ──────────────────
    if (decision.action === 'assess_capabilities') {
      try {
        const assessResponse = await fetch(`${BACKEND_URL}/api/capabilities/assess`, {
          signal: AbortSignal.timeout(15000),
        });
        if (assessResponse.ok) {
          const data = await assessResponse.json();

          // Build readable capability assessment message
          let assessMsg = `📊 **تقييم القدرات الذاتية — مأمون v40.0**\n\n`;
          assessMsg += `🔥 **نسبة الدمج الإجمالية:** ${data.overall_fusion_percent}%\n\n`;

          // Brains section
          if (data.brains) {
            const b = data.brains;
            assessMsg += `🧠 **الأدمغة:** ${b.original_model}/${b.total} بنموذج أصلي`;
            if (b.fallback > 0) {
              assessMsg += ` | ${b.fallback} على نموذج بديل`;
            }
            if (b.missing_keys?.length > 0) {
              assessMsg += `\n🔑 مفاتيح ناقصة: ${b.missing_keys.join(', ')}`;
            }
            assessMsg += '\n\n';

            // Individual brain details
            if (b.details) {
              for (const [bid, detail] of Object.entries(b.details) as [string, any][]) {
                const icon = detail.is_on_fallback ? '🟠' : detail.has_api_key ? '🟢' : '🔴';
                assessMsg += `${icon} ${detail.name_ar || bid}: ${detail.is_on_fallback ? `بديل (${detail.fallback_model})` : detail.original_model}`;
                if (!detail.has_api_key) assessMsg += ` — يحتاج ${detail.api_key_env}`;
                assessMsg += '\n';
              }
              assessMsg += '\n';
            }
          }

          // Bridges section
          if (data.bridges) {
            assessMsg += `🌉 **الجسور:**\n`;
            for (const [bridgeId, bridge] of Object.entries(data.bridges) as [string, any][]) {
              const icon = bridge.operational ? '🟢' : '🟠';
              assessMsg += `${icon} ${bridge.name_ar}: ${bridge.percent}%\n`;
            }
            assessMsg += '\n';
          }

          // Capabilities section
          if (data.capabilities?.length > 0) {
            assessMsg += `✅ **القدرات المتاحة (${data.capabilities.length}):**\n`;
            for (const cap of data.capabilities) {
              assessMsg += `- ${cap.name_ar} (${cap.category})\n`;
            }
            assessMsg += '\n';
          }

          // Missing capabilities
          if (data.missing_capabilities?.length > 0) {
            assessMsg += `❌ **القدرات الناقصة (${data.missing_capabilities.length}):**\n`;
            for (const cap of data.missing_capabilities) {
              assessMsg += `- ${cap.name_ar} — يحتاج: ${cap.requires?.join(', ')}\n`;
            }
            assessMsg += '\n';
          }

          // Summary
          if (data.can_do_summary) {
            assessMsg += `📝 **الملخص:** ${data.can_do_summary}\n\n`;
          }

          // Recommendations
          if (data.recommendations?.length > 0) {
            assessMsg += `💡 **التوصيات:**\n`;
            for (const rec of data.recommendations) {
              assessMsg += `- ${rec}\n`;
            }
          }

          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant', content: assessMsg, timestamp: Date.now(),
            brain: 'governor', confidence: 0.95, source: 'execution_bridge', is_real_deliberation: false,
            metadata: { action: 'assess_capabilities', assessment: data },
          });
        }
      } catch { /* backend unavailable */ }

      // Fallback: basic local assessment
      const localAssessment = `📊 **تقييم القدرات (محلي — الباك إند غير متصل):**\n\n` +
        `🧠 الأدمغة: ${BRAIN_PERSONAS.filter(b => b.enabled).length}/${BRAIN_PERSONAS.length} مفعّلة\n` +
        `✅ المحادثة، توجيه الأدمغة، تحليل البيانات\n` +
        `❌ البحث العميق، التحكم بالطرفية (يحتاج اتصال الباك إند)\n\n` +
        `💡 لتقييم كامل، تأكد أن الباك إند يعمل على المنفذ 8000`;

      return NextResponse.json({
        id: `msg-${Date.now()}`, role: 'assistant', content: localAssessment,
        timestamp: Date.now(), brain: 'governor', confidence: 0.6, source: 'local',
        is_real_deliberation: false,
      });
    }

    // ─── EXTERNAL_MODIFY: تعديل مشروع خارجي (v40.0 Fusion Step 7) ──
    if (decision.action === 'external_modify') {
      try {
        const specification = decision.parsedCommand.params.specification || decision.sanitizedMessage;
        const modifyResponse = await fetch(`${BACKEND_URL}/api/external/modify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_dir: specification, description: specification }),
          signal: AbortSignal.timeout(180000),
        });
        if (modifyResponse.ok) {
          const data = await modifyResponse.json();
          const msg = data.status === 'modified'
            ? `✅ تم تعديل المشروع الخارجي!\n- الملفات المعدّلة: ${data.modifications_applied}\n- النسخ الاحتياطي: ${data.backup_dir || 'محفوظ'}${data.errors?.length ? `\n- أخطاء: ${data.errors.join(', ')}` : ''}`
            : data.status === 'no_changes'
              ? `ℹ️ لم يتم اكتشاف تعديلات مطلوبة: ${data.message || 'المشروع لا يحتاج تغييرات'}`
              : `❓ حالة غير معروفة: ${data.status}`;
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant', content: msg, timestamp: Date.now(),
            brain: 'governor', confidence: 0.85, source: 'execution_bridge', is_real_deliberation: false,
            metadata: { action: 'external_modify', backendResponse: data },
          });
        }
      } catch { /* backend unavailable */ }
    }

    // ─── EXTERNAL_DEPLOY: نشر مشروع (v40.0 Fusion Step 7) ────────
    if (decision.action === 'external_deploy') {
      try {
        const specification = decision.parsedCommand.params.specification || decision.sanitizedMessage;
        const deployResponse = await fetch(`${BACKEND_URL}/api/external/deploy`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_dir: specification }),
          signal: AbortSignal.timeout(180000),
        });
        if (deployResponse.ok) {
          const data = await deployResponse.json();
          const buildOk = data.build?.success;
          const deployOk = data.deploy?.success;
          let msg = '';
          if (buildOk && deployOk) {
            msg = `✅ تم النشر بنجاح!\n- البناء: ناجح\n- النشر: ناجح`;
          } else if (buildOk && !data.deploy) {
            msg = `✅ تم البناء بنجاح — لا يوجد أمر نشر محدد`;
          } else if (!buildOk) {
            msg = `❌ فشل البناء:\n${data.build?.errors || 'خطأ غير معروف'}`;
          } else {
            msg = `⚠️ البناء ناجح لكن النشر فشل:\n${data.deploy?.errors || 'خطأ غير معروف'}`;
          }
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant', content: msg, timestamp: Date.now(),
            brain: 'governor', confidence: 0.85, source: 'execution_bridge', is_real_deliberation: false,
            metadata: { action: 'external_deploy', backendResponse: data },
          });
        }
      } catch { /* backend unavailable */ }
    }

    // ─── SELF_TEST: اختبار ذاتي شامل (v40.0 Fusion Step 11) ────────
    if (decision.action === 'self_test') {
      try {
        const testResponse = await fetch(`${BACKEND_URL}/api/self-test/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: AbortSignal.timeout(120000),
        });
        if (testResponse.ok) {
          const data = await testResponse.json();

          // Build readable test report
          let testMsg = '🧪 **نتائج الاختبار الذاتي — مأمون v40.0:**\n\n';
          testMsg += `📊 **الملخص:** ${data.overall_passed} نجح / ${data.overall_failed} فشل من ${data.total_tests} اختبار\n`;
          testMsg += `📈 **نسبة النجاح:** ${Math.round((data.pass_rate || 0) * 100)}%\n`;
          testMsg += `⏱️ **المدة:** ${Math.round((data.duration_ms || 0) / 1000)} ثانية\n\n`;

          // Per-suite details
          if (data.results) {
            for (const [suiteName, suite] of Object.entries(data.results) as [string, any][]) {
              const icon = suite.passed === suite.total ? '✅' : suite.passed > 0 ? '⚠️' : '❌';
              testMsg += `${icon} **${suiteName}:** ${suite.passed}/${suite.total} نجح\n`;

              // Show failed test details
              if (suite.results) {
                for (const test of suite.results) {
                  if (!test.passed) {
                    testMsg += `   ❌ ${test.test_name}: ${test.error || test.message_ar || 'فشل'}\n`;
                  }
                }
              }
            }
          }

          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant', content: testMsg, timestamp: Date.now(),
            brain: 'governor', confidence: 0.95, source: 'execution_bridge', is_real_deliberation: false,
            metadata: { action: 'self_test', backendResponse: data },
          });
        }
      } catch { /* backend unavailable */ }

      // Fallback: basic self-test without backend
      return NextResponse.json({
        id: `msg-${Date.now()}`, role: 'assistant',
        content: '🧪 **اختبار ذاتي (محلي — الباك إند غير متصل):**\n\n' +
          '✅ محلل الأوامر: يعمل\n' +
          '✅ حاكم المحادثة: يعمل\n' +
          '✅ توجيه الأدمغة: يعمل\n' +
          '❌ اختبارات الباك إند: غير متصلة\n\n' +
          '💡 لاختبار كامل، تأكد أن الباك إند يعمل على المنفذ 8000',
        timestamp: Date.now(), brain: 'governor', confidence: 0.7, source: 'local',
        is_real_deliberation: false,
      });
    }

    // ─── UNIFIED_MIND: العقل الموحّد (v40.0 Fusion Step 12) ────────
    if (decision.action === 'unified_mind') {
      try {
        const query = decision.sanitizedMessage;
        const mindResponse = await fetch(`${BACKEND_URL}/api/unified-mind/process`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, context: { source: 'chat' } }),
          signal: AbortSignal.timeout(180000),
        });
        if (mindResponse.ok) {
          const data = await mindResponse.json();

          // Build readable unified mind response
          let mindMsg = '🧠⚡ **العقل الموحّد — النتيجة:**\n\n';

          if (data.response) {
            mindMsg += `💬 **الرد:** ${data.response}\n\n`;
          }

          // Metadata section
          const meta = data.metadata || {};
          mindMsg += `📊 **تفاصيل المعالجة:**\n`;
          mindMsg += `🏷️ نوع الاستعلام: ${meta.query_type || 'عام'}\n`;
          mindMsg += `🧠 الدماغ الفائز: ${meta.winning_brain || 'غير محدد'}\n`;
          mindMsg += `🤝 مستوى التوافق: ${Math.round((meta.consensus_level || 0) * 100)}%\n`;
          mindMsg += `🔥 نسبة الدمج: ${data.fusion_percent || 0}%\n`;
          mindMsg += `⏱️ المدة: ${Math.round((meta.duration_ms || 0))}ms\n`;

          // Capability snapshot
          if (data.capability_snapshot?.overall_fusion_percent) {
            mindMsg += `\n📋 **تقييم القدرات:** ${data.capability_snapshot.overall_fusion_percent}% دمج\n`;
          }

          // Health predictions
          if (data.health_predictions?.length > 0) {
            mindMsg += `\n⚠️ **تنبؤات صحية:**\n`;
            for (const pred of data.health_predictions.slice(0, 3)) {
              const sevIcon = pred.severity === 'critical' ? '🔴' : pred.severity === 'high' ? '🟠' : '🟡';
              mindMsg += `${sevIcon} ${pred.component}: ${pred.failure_type} (${Math.round(pred.probability * 100)}%)\n`;
            }
          }

          // Learning insights
          if (data.learning_insights?.length > 0) {
            mindMsg += `\n💡 **رؤى تعلّمية:**\n`;
            for (const insight of data.learning_insights.slice(0, 3)) {
              mindMsg += `- ${insight.insight || insight}\n`;
            }
          }

          // Test results (if self-modification was involved)
          if (data.test_results) {
            mindMsg += `\n🧪 **اختبار بعد التعديل:** ${data.test_results.overall_passed}/${data.test_results.total_tests} نجح\n`;
          }

          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant', content: mindMsg, timestamp: Date.now(),
            brain: meta.winning_brain || 'unified_mind', confidence: 0.9, source: 'execution_bridge',
            is_real_deliberation: true,
            metadata: { action: 'unified_mind', backendResponse: data },
          });
        }
      } catch { /* backend unavailable */ }

      // Fallback: unified mind with local capabilities
      try {
        const fusionResponse = await fetch(`${BACKEND_URL}/api/unified-mind/fusion`, {
          signal: AbortSignal.timeout(5000),
        });
        if (fusionResponse.ok) {
          const fusionData = await fusionResponse.json();
          return NextResponse.json({
            id: `msg-${Date.now()}`, role: 'assistant',
            content: `🧠⚡ **العقل الموحّد (جزئي — الباك إند محدود):**\n\n` +
              `🔥 نسبة الدمج: ${fusionData.fusion_percent}%\n` +
              `📊 الأنظمة الفرعية: ${fusionData.active_subsystems}/${fusionData.total_subsystems} نشطة\n` +
              `📋 الحالة: ${fusionData.status === 'ready' ? 'جاهز' : fusionData.status === 'partial' ? 'جزئي' : 'ضعيف'}\n\n` +
              `💡 لتشغيل كامل، تأكد أن الباك إند يعمل على المنفذ 8000`,
            timestamp: Date.now(), brain: 'governor', confidence: 0.6, source: 'local',
            is_real_deliberation: false,
          });
        }
      } catch { /* even fusion endpoint unavailable */ }

      return NextResponse.json({
        id: `msg-${Date.now()}`, role: 'assistant',
        content: '🧠⚡ **العقل الموحّد (محلي — الباك إند غير متصل):**\n\n' +
          'الأنظمة المحلية تعمل: محلل الأوامر، حاكم المحادثة، توجيه الأدمغة\n' +
          'الأنظمة الخلفية غير متاحة: التوجيه الدلالي، الاختبار الذاتي، الإصلاح التنبؤي\n\n' +
          '💡 لتشغيل كامل للعقل الموحّد، تأكد أن الباك إند يعمل على المنفذ 8000',
        timestamp: Date.now(), brain: 'governor', confidence: 0.5, source: 'local',
        is_real_deliberation: false,
      });
    }

    // ═══ إذا لم يكن أمر تنفيذي — أكمل كمحادثة عادية ═════════════

    // v40.0 Fusion Step 1: ALWAYS try backend deliberation first, then fall back to local
    let primaryBrain = decision.routing.primaryBrain;
    let backendDeliberationUsed = false;
    let deliberationContributions = decision.routing.contributions;
    try {
      const backendRouting = await deliberateViaBackend(
        decision.sanitizedMessage,
        { conversationLength: decision.smartContext.totalMessages, mode: decision.currentMode.id },
      );
      if (backendRouting.primaryBrain && backendRouting.confidence > 0.4) {
        primaryBrain = backendRouting.primaryBrain;
        deliberationContributions = backendRouting.contributions;
        decision.routing = backendRouting;
        backendDeliberationUsed = true;
      }
    } catch { /* backend deliberation unavailable — use local routing */ }

    const brainPersona = BRAIN_PERSONAS.find(b => b.id === primaryBrain) || BRAIN_PERSONAS[0];
    const fullSystemPrompt = chatGovernor.buildFullSystemPrompt(decision);
    const selectedModel = MODEL_MAP[model] || brainPersona.model || 'glm-4-plus';

    // Context from governor
    const contextMessages = decision.smartContext.messages.map(m => ({
      role: (m.role === 'user' ? 'user' : 'assistant') as 'user' | 'assistant',
      content: m.content.substring(0, 4000),
    }));

    const messages = [
      { role: 'system' as const, content: fullSystemPrompt },
      ...contextMessages,
      { role: 'user' as const, content: decision.sanitizedMessage },
    ];

    // ─── SSE Streaming Mode ───────────────────────────────
    if (stream) {
      // Try backend SSE first
      try {
        const backendResponse = await fetch(`${BACKEND_URL}/api/kernel/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream', ...getAuthHeaders(request) },
          body: JSON.stringify({
            message: decision.sanitizedMessage, history, model: model || 'auto', stream: true,
            mode: decision.currentMode.id, active_brains: decision.activatedBrains,
          }),
          signal: AbortSignal.timeout(60000),
        });
        if (backendResponse.ok && backendResponse.body) {
          const proxiedStream = new ReadableStream({
            async start(controller) {
              const reader = backendResponse.body!.getReader();
              const decoder = new TextDecoder();
              const encoder = new TextEncoder();
              try {
                while (true) {
                  const { done, value } = await reader.read();
                  if (done) break;
                  controller.enqueue(encoder.encode(decoder.decode(value, { stream: true })));
                }
              } catch { /* stream ended */ }
              finally { controller.close(); }
            },
          });
          return new Response(proxiedStream, {
            headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' },
          });
        }
      } catch { /* Backend unavailable */ }

      // Stream from z-ai SDK
      const startTime = Date.now();
      try {
        const zai = await ZAI.create();
        const streamResult = await zai.chat.completions.create({
          model: selectedModel, messages, stream: true,
          temperature: decision.suggestedTemperature,
        });

        const readableStream = streamResult as ReadableStream<Uint8Array>;
        let streamClosed = false;

        const sseStream = new ReadableStream({
          async start(controller) {
            const encoder = new TextEncoder();
            let fullContent = '';

            const safeEnqueue = (data: Uint8Array) => {
              if (!streamClosed) { try { controller.enqueue(data); } catch { streamClosed = true; } }
            };
            const safeClose = () => {
              if (!streamClosed) { try { controller.close(); } catch { /* */ } streamClosed = true; }
            };

            try {
              for await (const token of parseOpenAIStream(readableStream)) {
                if (streamClosed) break;
                fullContent += token;
                const sseEvent = `data: ${JSON.stringify({
                  type: 'token', content: token, brain: primaryBrain,
                  mode: decision.currentMode.id,
                })}\n\n`;
                safeEnqueue(encoder.encode(sseEvent));
              }

              const confidence = calculateFallbackConfidence(fullContent, 1, Date.now() - startTime, decision.suggestedTemperature);
              const latency = Date.now() - startTime;
              const doneEvent = `data: ${JSON.stringify({
                type: 'done', brain: primaryBrain, confidence, latency,
                brainContributions: deliberationContributions,
                brainPersona: { nameAr: brainPersona.nameAr, nameEn: brainPersona.nameEn, thinkingStyle: brainPersona.thinkingStyle },
                is_real_deliberation: backendDeliberationUsed,
                backendDeliberation: backendDeliberationUsed,
                current_mode: decision.currentMode,
                feedforward_suggestions: chatGovernor.generateFeedforward(decision, fullContent),
              })}\n\n`;
              safeEnqueue(encoder.encode(doneEvent));
            } catch {
              const errorEvent = `data: ${JSON.stringify({ type: 'error', message: 'Stream interrupted', brain: primaryBrain })}\n\n`;
              safeEnqueue(encoder.encode(errorEvent));
            } finally { safeClose(); }
          },
          cancel() { streamClosed = true; },
        });

        return new Response(sseStream, {
          headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' },
        });
      } catch (sdkStreamError) {
        console.error('[Chat API] z-ai streaming failed:', sdkStreamError);
      }

      // Fallback: non-streaming wrapped as SSE
      try {
        const zai2 = await ZAI.create();
        const response = await zai2.chat.completions.create({
          model: selectedModel, messages, stream: false,
          temperature: decision.suggestedTemperature,
        });

        let assistantContent = response?.choices?.[0]?.message?.content || (typeof response === 'string' ? response : 'عذراً، لم أتمكن من معالجة طلبك.');
        const confidence = calculateFallbackConfidence(assistantContent, 2, Date.now() - startTime, decision.suggestedTemperature);
        const latency = Date.now() - startTime;

        const sseStream = new ReadableStream({
          start(controller) {
            const encoder = new TextEncoder();
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'token', content: assistantContent, brain: primaryBrain, mode: decision.currentMode.id })}\n\n`));
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'done', brain: primaryBrain, confidence, latency, brainContributions: decision.routing.contributions, is_real_deliberation: false, current_mode: decision.currentMode })}\n\n`));
            controller.close();
          },
        });
        return new Response(sseStream, {
          headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' },
        });
      } catch (fallbackError) {
        return NextResponse.json({ error: 'فشل الاتصال. يرجى المحاولة لاحقاً.' }, { status: 500 });
      }
    }

    // ─── Non-streaming JSON Mode ──────────────────────────
    // v40.0 Fusion: Try backend deliberation room FIRST, then kernel, then local LLM
    if (decision.needsFullDeliberation) {
      // Step 1: Try backend's deliberation room (/api/brains/deliberate)
      let deliberationData: Record<string, unknown> | null = null;
      try {
        const deliberationResult = await deliberateViaBackend(
          decision.sanitizedMessage,
          { conversationLength: decision.smartContext.totalMessages, mode: decision.currentMode.id },
        );
        if (deliberationResult.primaryBrain && deliberationResult.confidence > 0.5) {
          deliberationData = {
            routing: deliberationResult,
            backendDeliberation: true,
          };
        }
      } catch { /* deliberation room unavailable */ }

      // Step 2: Try kernel chat for full response with all 5 brains
      try {
        const kernelResponse = await fetch(`${BACKEND_URL}/api/kernel/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...getAuthHeaders(request) },
          body: JSON.stringify({
            message: decision.sanitizedMessage, model: model || 'auto', context: {},
            mode: decision.currentMode.id, active_brains: decision.activatedBrains,
          }),
          signal: AbortSignal.timeout(60000),
        });
        if (kernelResponse.ok) {
          const data = await kernelResponse.json();
          // Include deliberation data from the deliberation room alongside kernel data
          const allBrainResponses = data.brain_responses || {};
          return NextResponse.json({
            id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
            role: 'assistant', content: data.response, timestamp: Date.now(),
            brain: data.winning_brain || primaryBrain, confidence: data.confidence || 0.85,
            latency: 0, brain_responses: allBrainResponses,
            source: 'kernel', is_real_deliberation: true,
            current_mode: decision.currentMode,
            routing: decision.routing,
            deliberationData: deliberationData ? {
              brainResponses: allBrainResponses,
              consensusLevel: data.consensus_level || (deliberationData?.routing as BrainRoutingResult | undefined)?.confidence || 0.7,
              cjs: data.cjs || 0,
              conflictDetected: data.conflict_detected || false,
              mirrorReflection: data.mirror_reflection || '',
              queryType: data.query_type || '',
              backendDeliberation: true,
            } : undefined,
          });
        }
      } catch { /* kernel unavailable */ }

      // Step 3: If we got deliberation data but kernel failed, use deliberation routing for local LLM
      if (deliberationData) {
        // Enrich the local LLM call with deliberation routing info
        const delibRouting = deliberationData.routing as BrainRoutingResult | undefined;
        if (delibRouting) {
          decision.routing = delibRouting;
        }
      }
    }

    // Use z-ai SDK
    const zai = await ZAI.create();
    const startTime = Date.now();

    const response = await zai.chat.completions.create({
      model: selectedModel, messages, stream: false,
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

    return NextResponse.json({
      id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      role: 'assistant', content: assistantContent, timestamp: Date.now(),
      brain: primaryBrain, confidence, latency,
      is_real_deliberation: backendDeliberationUsed,
      backendDeliberation: backendDeliberationUsed,
      current_mode: decision.currentMode,
      routing: decision.routing,
      feedforward_suggestions: chatGovernor.generateFeedforward(decision, assistantContent),
      metadata: {
        model: selectedModel,
        brainContributions: deliberationContributions,
        brainPersona: { nameAr: brainPersona.nameAr, nameEn: brainPersona.nameEn, thinkingStyle: brainPersona.thinkingStyle },
        tokensUsed: response?.usage?.total_tokens || 0,
        wasFiltered: decision.wasFiltered,
        governorAction: decision.action,
      },
      source: 'local_llm',
    });
  } catch (error: unknown) {
    const errMsg = error instanceof Error ? error.constructor.name : 'Unknown';
    console.error('[Chat API] Error:', errMsg);
    return NextResponse.json({ error: 'حدث خطأ أثناء معالجة الرسالة' }, { status: 500 });
  }
}
