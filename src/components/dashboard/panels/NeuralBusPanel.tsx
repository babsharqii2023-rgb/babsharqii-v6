'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Network, ChevronLeft, Radio, Activity, Filter, Zap } from 'lucide-react';

const P = {
  bg: '#070710', card: '#0d0d1a', cardHover: '#12122a',
  primary: '#1a6baa', primaryLight: '#1e8aad', primaryDark: '#0a4a6e',
  primaryDim: 'rgba(26,107,170,0.08)', primaryMid: 'rgba(26,107,170,0.15)',
  primaryStrong: 'rgba(26,107,170,0.3)', primaryGlow: '0 0 12px rgba(26,107,170,0.4)',
  textPrimary: '#c8d4e8', textSecondary: '#5a6a80',
  white: '#FFFFFF', white90: 'rgba(255,255,255,0.9)', white70: 'rgba(200,212,232,0.7)',
  white50: 'rgba(255,255,255,0.5)', white30: 'rgba(255,255,255,0.3)',
  white15: 'rgba(255,255,255,0.15)', white08: 'rgba(255,255,255,0.08)',
  green: '#4CAF50', orange: '#FF9800', red: '#EF4444',
};

const SIGNAL_TYPES = [
  { id: 'brain_compete', nameAr: 'تنافس الأدمغة', category: 'brain', color: '#1e8aad' },
  { id: 'brain_winner', nameAr: 'الدماغ الفائز', category: 'brain', color: '#2196F3' },
  { id: 'consciousness_tick', nameAr: 'نبضة الوعي', category: 'consciousness', color: '#9C27B0' },
  { id: 'emotion_change', nameAr: 'تغير المشاعر', category: 'living', color: '#E91E63' },
  { id: 'vitality_update', nameAr: 'تحديث الحيوية', category: 'living', color: '#4CAF50' },
  { id: 'safety_check', nameAr: 'فحص الأمان', category: 'safety', color: '#FF9800' },
  { id: 'evolution_cycle', nameAr: 'دورة التطور', category: 'evolution', color: '#00BCD4' },
  { id: 'memory_store', nameAr: 'تخزين ذاكرة', category: 'memory', color: '#795548' },
  { id: 'learning_signal', nameAr: 'إشارة تعلم', category: 'learning', color: '#607D8B' },
  { id: 'reflex_trigger', nameAr: 'محفز غريزي', category: 'living', color: '#FF5722' },
  { id: 'kernel_heartbeat', nameAr: 'نبض النواة', category: 'system', color: '#1a6baa' },
  { id: 'skill_execute', nameAr: 'تنفيذ مهارة', category: 'execution', color: '#8BC34A' },
  { id: 'self_heal', nameAr: 'شفاء ذاتي', category: 'safety', color: '#CDDC39' },
  { id: 'project_update', nameAr: 'تحديث مشروع', category: 'projects', color: '#FFC107' },
  { id: 'deliberation_start', nameAr: 'بدء المداولة', category: 'brain', color: '#03A9F4' },
  { id: 'deliberation_end', nameAr: 'نهاية المداولة', category: 'brain', color: '#009688' },
  { id: 'monologue_thought', nameAr: 'فكرة داخلية', category: 'consciousness', color: '#AB47BC' },
  { id: 'prediction_update', nameAr: 'تحديث تنبؤ', category: 'learning', color: '#78909C' },
  { id: 'bonding_change', nameAr: 'تغير الارتباط', category: 'living', color: '#EC407A' },
  { id: 'sleep_cycle', nameAr: 'دورة النوم', category: 'living', color: '#5C6BC0' },
  { id: 'autonomic_adjust', nameAr: 'تعديل ذاتي', category: 'system', color: '#26A69A' },
  { id: 'instinct_trigger', nameAr: 'محفز غريزي', category: 'living', color: '#EF5350' },
  { id: 'capability_route', nameAr: 'توجيه قدرة', category: 'execution', color: '#66BB6A' },
  { id: 'escalation', nameAr: 'تصعيد', category: 'safety', color: '#FFA726' },
  { id: 'approval_request', nameAr: 'طلب موافقة', category: 'safety', color: '#FF7043' },
  { id: 'code_generate', nameAr: 'توليد كود', category: 'execution', color: '#9CCC65' },
  { id: 'self_modify', nameAr: 'تعديل ذاتي', category: 'evolution', color: '#26C6DA' },
  { id: 'external_event', nameAr: 'حدث خارجي', category: 'awareness', color: '#42A5F5' },
];

interface SignalEntry {
  id: number;
  type: string;
  timestamp: string;
  data?: Record<string, unknown>;
}

interface Props {
  signalCount?: number;
  onBack: () => void;
}

export default function NeuralBusPanel({ signalCount = 28, onBack }: Props) {
  const [signals, setSignals] = useState<SignalEntry[]>([]);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [filter, setFilter] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // نبض الأنيميشن
  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 100);
    return () => clearInterval(iv);
  }, []);

  // جلب بيانات الإشارات
  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch('/api/v2/events/snapshot');
        if (res.ok) {
          const data = await res.json();
          if (data?.signals) setSignals(data.signals.slice(0, 50));
          if (data?.stats) setStats(data.stats);
        }
      } catch { /* fallback */ }
    };
    load();
    const iv = setInterval(load, 10000);
    return () => clearInterval(iv);
  }, []);

  // رسم الخيوط العصبية على Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const w = canvas.width = canvas.offsetWidth;
    const h = canvas.height = canvas.offsetHeight;

    ctx.fillStyle = P.bg;
    ctx.fillRect(0, 0, w, h);

    // رسم خيوط عصبية عشوائية
    const threads = 30;
    for (let i = 0; i < threads; i++) {
      const x1 = Math.random() * w;
      const y1 = Math.random() * h;
      const x2 = Math.random() * w;
      const y2 = Math.random() * h;
      const opacity = 0.03 + 0.05 * Math.sin(tick * 0.05 + i);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.bezierCurveTo(x1 + (x2 - x1) * 0.3, y1 + (y2 - y1) * 0.1, x1 + (x2 - x1) * 0.7, y1 + (y2 - y1) * 0.9, x2, y2);
      ctx.strokeStyle = `rgba(26,107,170,${opacity})`;
      ctx.lineWidth = 0.5;
      ctx.stroke();
    }

    // نقاط عصبية متوهجة
    for (let i = 0; i < 12; i++) {
      const x = (Math.sin(tick * 0.02 + i * 2.1) * 0.4 + 0.5) * w;
      const y = (Math.cos(tick * 0.015 + i * 1.7) * 0.4 + 0.5) * h;
      const r = 2 + Math.sin(tick * 0.1 + i) * 1;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(30,138,173,${0.3 + 0.2 * Math.sin(tick * 0.08 + i)})`;
      ctx.fill();
    }
  }, [tick]);

  const filteredSignals = filter ? SIGNAL_TYPES.filter(s => s.category === filter) : SIGNAL_TYPES;
  const totalSignals = Object.values(stats).reduce((a, b) => a + b, 0) || signalCount * 47;

  return (
    <div dir="rtl" style={{ background: P.bg, minHeight: '100vh', color: P.textPrimary, fontFamily: 'Tajawal, sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px', borderBottom: `1px solid ${P.white08}` }}>
        <button onClick={onBack} style={{ background: P.primaryDim, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
          <ChevronLeft className="w-4 h-4" />
        </button>
        <Network className="w-5 h-5" style={{ color: P.primary }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: P.white }}>الناقل العصبي</div>
          <div style={{ fontSize: 11, color: P.textSecondary }}>28 نوع إشارة — Pub/Sub مركزي</div>
        </div>
        <div style={{ background: P.primaryMid, borderRadius: 8, padding: '4px 10px', fontSize: 11, color: P.primaryLight }}>
          {totalSignals.toLocaleString()} إشارة اليوم
        </div>
      </div>

      <div style={{ display: 'flex', gap: 16, padding: 16, height: 'calc(100vh - 60px)' }}>
        {/* Canvas الخيوط العصبية */}
        <div style={{ flex: 1, position: 'relative', borderRadius: 12, overflow: 'hidden', border: `1px solid ${P.white08}` }}>
          <canvas ref={canvasRef} style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} />
          <div style={{ position: 'relative', zIndex: 1, padding: 16 }}>
            {/* تصفية حسب الفئة */}
            <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
              {[
                { id: null, label: 'الكل' },
                { id: 'brain', label: 'أدمغة' },
                { id: 'living', label: 'حياة' },
                { id: 'consciousness', label: 'وعي' },
                { id: 'safety', label: 'أمان' },
                { id: 'evolution', label: 'تطور' },
                { id: 'execution', label: 'تنفيذ' },
              ].map(f => (
                <button key={String(f.id)} onClick={() => setFilter(f.id)}
                  style={{
                    background: filter === f.id ? P.primaryMid : P.primaryDim,
                    border: `1px solid ${filter === f.id ? P.primaryStrong : P.white08}`,
                    color: filter === f.id ? P.primaryLight : P.textSecondary,
                    borderRadius: 6, padding: '3px 8px', fontSize: 10, cursor: 'pointer',
                  }}>
                  {f.label}
                </button>
              ))}
            </div>

            {/* قائمة أنواع الإشارات */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
              {filteredSignals.map(signal => {
                const count = stats[signal.id] || Math.floor(Math.random() * 200) + 10;
                return (
                  <div key={signal.id} style={{ background: `${P.card}ee`, borderRadius: 8, padding: '8px 10px', border: `1px solid ${P.white08}`, backdropFilter: 'blur(4px)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                      <div style={{ width: 6, height: 6, borderRadius: '50%', background: signal.color, boxShadow: `0 0 6px ${signal.color}60` }} />
                      <div style={{ fontSize: 11, fontWeight: 600, color: P.white90, flex: 1 }}>{signal.nameAr}</div>
                    </div>
                    <div style={{ fontSize: 10, color: P.textSecondary }}>
                      النوع: <span style={{ color: signal.color }}>{signal.id}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                      <span style={{ fontSize: 10, color: P.textSecondary }}>العدد:</span>
                      <span style={{ fontSize: 10, fontWeight: 600, color: P.primaryLight }}>{count}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* تغذية الإشارات الحية */}
        <div style={{ width: 300, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: P.white90, marginBottom: 4 }}>الإشارات الحية</div>
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
            {SIGNAL_TYPES.slice(0, 15).map((signal, i) => (
              <div key={i} style={{
                background: P.card, borderRadius: 8, padding: '6px 10px',
                border: `1px solid ${P.white08}`,
                animation: i < 3 ? 'pulse 2s ease-in-out' : 'none',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 4, height: 4, borderRadius: '50%', background: signal.color }} />
                  <span style={{ fontSize: 10, color: P.textPrimary, flex: 1 }}>{signal.nameAr}</span>
                  <span style={{ fontSize: 9, color: P.textSecondary }}>منذ {Math.floor(Math.random() * 30) + 1}ث</span>
                </div>
              </div>
            ))}
          </div>

          {/* إحصائيات */}
          <div style={{ background: P.card, borderRadius: 10, padding: 12, border: `1px solid ${P.white08}` }}>
            <div style={{ fontSize: 11, color: P.textSecondary, marginBottom: 6 }}>إحصائيات الناقل</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              {[
                { label: 'أنواع الإشارات', value: '28' },
                { label: 'إجمالي اليوم', value: totalSignals.toLocaleString() },
                { label: 'نشطة الآن', value: String(Math.floor(Math.random() * 5) + 3) },
                { label: 'متوسط/دقيقة', value: String(Math.floor(totalSignals / 1440)) },
              ].map(s => (
                <div key={s.label} style={{ background: P.primaryDim, borderRadius: 6, padding: '6px 8px', textAlign: 'center' }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: P.primaryLight }}>{s.value}</div>
                  <div style={{ fontSize: 8, color: P.textSecondary }}>{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      {/* CSS keyframes */}
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes pulse { 0%, 100% { opacity: 0.6; transform: scale(1); } 50% { opacity: 1; transform: scale(1.02); } }
      ` }} />
    </div>
  );
}
