import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

/**
 * GET /api/health-monitor — حالة صحة كل الأنظمة
 * POST /api/health-monitor — إصلاح تلقائي أو إبعاد تنبيه
 */
export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/health-monitor`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(10000),
    });
    if (response.ok) {
      const data = await response.json();
      return NextResponse.json(data);
    }
  } catch { /* backend offline */ }

  // Fallback: حالة تقريبية
  return NextResponse.json({
    overall_health: 85,
    components: [
      { id: 'brain_neural', name: 'Neural Brain', name_ar: 'الدماغ العصبي', healthy: true, status: 'active', auto_heal_available: true },
      { id: 'brain_causal', name: 'Causal Brain', name_ar: 'الدماغ السببي', healthy: true, status: 'active', auto_heal_available: true },
      { id: 'brain_symbolic', name: 'Symbolic Brain', name_ar: 'الدماغ الرمزي', healthy: true, status: 'active', auto_heal_available: true },
      { id: 'brain_bayesian', name: 'Bayesian Brain', name_ar: 'الدماغ البيزي', healthy: true, status: 'active', auto_heal_available: true },
      { id: 'brain_world_model', name: 'World Model Brain', name_ar: 'الدماغ العالمي', healthy: true, status: 'active', auto_heal_available: true },
      { id: 'llm_client', name: 'LLM Client', name_ar: 'عميل LLM', healthy: true, status: 'active', auto_heal_available: true },
      { id: 'github_updater', name: 'GitHub Updater', name_ar: 'محدّث GitHub', healthy: true, status: 'active', auto_heal_available: true },
      { id: 'web_search', name: 'Web Search', name_ar: 'البحث الويب', healthy: true, status: 'active', auto_heal_available: true },
    ],
    active_alerts: 0,
    alerts: [],
    healthy_count: 8,
    unhealthy_count: 0,
    total_count: 8,
    _isOffline: true,
    _fallbackWarning: 'الباك إند غير متصل — البيانات تقريبية',
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, component_id, alert_id } = body;

    let endpoint = `${BACKEND_URL}/api/health-monitor`;
    if (action === 'auto-heal' && component_id) {
      endpoint += '/auto-heal';
    } else if (action === 'dismiss-alert' && alert_id) {
      endpoint += '/dismiss-alert';
    } else if (action === 'check') {
      endpoint += '/check';
    }

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(30000),
    });

    if (response.ok) {
      const data = await response.json();
      return NextResponse.json(data);
    }
  } catch { /* backend offline */ }

  return NextResponse.json({ success: false, message: 'الباك إند غير متصل' });
}
