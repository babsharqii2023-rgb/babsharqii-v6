'use client';

import React, { useState, useEffect } from 'react';
import { Users, ChevronLeft, Play, Pause, CheckCircle2, XCircle, Loader2, Bot } from 'lucide-react';
import { fetchSwarmStatus } from '@/lib/jarvis-api';

const P = {
  bg: '#070710', card: '#0d0d1a', primary: '#1a6baa', primaryLight: '#1e8aad', primaryDark: '#0a4a6e',
  primaryDim: 'rgba(26,107,170,0.08)', primaryMid: 'rgba(26,107,170,0.15)', primaryStrong: 'rgba(26,107,170,0.3)',
  textPrimary: '#c8d4e8', textSecondary: '#5a6a80',
  white: '#FFFFFF', white90: 'rgba(255,255,255,0.9)', white08: 'rgba(255,255,255,0.08)',
  green: '#4CAF50', orange: '#FF9800', red: '#EF4444',
};

interface Agent {
  id: string; name: string; role: string; status: 'idle' | 'working' | 'waiting' | 'error';
  task?: string; progress?: number;
}

const DEMO_AGENTS: Agent[] = [
  { id: 'coder', name: 'المبرمج', role: 'كتابة وتعديل الكود', status: 'working', task: 'تحسين محرك الذاكرة', progress: 65 },
  { id: 'researcher', name: 'الباحث', role: 'البحث والتحليل', status: 'idle' },
  { id: 'analyzer', name: 'المحلل', role: 'تحليل البيانات والأنماط', status: 'working', task: 'تحليل أداء الأدمغة', progress: 40 },
  { id: 'planner', name: 'المخطط', role: 'التخطيط والتنسيق', status: 'waiting', task: 'ينتظر مهمة جديدة' },
  { id: 'fixer', name: 'المصلح', role: 'إصلاح الأخطاء تلقائياً', status: 'idle' },
  { id: 'tester', name: 'المختبر', role: 'اختبار الكود والوظائف', status: 'error', task: 'فشل اختبار API' },
  { id: 'doc', name: 'الموثق', role: 'كتابة التوثيق', status: 'idle' },
  { id: 'reviewer', name: 'المراجع', role: 'مراجعة التغييرات', status: 'working', task: 'مراجعة تحديثات الأمان', progress: 80 },
];

const STATUS_CONFIG = {
  idle: { color: P.textSecondary, label: 'خامل', icon: <Pause className="w-3.5 h-3.5" /> },
  working: { color: P.green, label: 'يعمل', icon: <Loader2 className="w-3.5 h-3.5" /> },
  waiting: { color: P.orange, label: 'ينتظر', icon: <Loader2 className="w-3.5 h-3.5" /> },
  error: { color: P.red, label: 'خطأ', icon: <XCircle className="w-3.5 h-3.5" /> },
};

interface Props { onBack: () => void; }

export default function SwarmPanel({ onBack }: Props) {
  const [agents, setAgents] = useState<Agent[]>(DEMO_AGENTS);
  const [activityLog, setActivityLog] = useState<string[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchSwarmStatus();
        if (data && typeof data === 'object') {
          const agentsData = (data as Record<string, unknown>).agents;
          if (Array.isArray(agentsData)) {
            setAgents(agentsData.map((a: Record<string, unknown>) => ({
              id: String(a.id || ''), name: String(a.name || ''), role: String(a.role || ''),
              status: (a.status as Agent['status']) || 'idle', task: String(a.task || ''), progress: (a.progress as number) || 0,
            })));
          }
        }
      } catch { /* fallback demo data */ }
    };
    load();
    const iv = setInterval(load, 12000); // 12 ثانية
    return () => clearInterval(iv);
  }, []);

  // تغذية النشاط
  useEffect(() => {
    const iv = setInterval(() => {
      const working = agents.filter(a => a.status === 'working');
      if (working.length > 0) {
        const a = working[Math.floor(Math.random() * working.length)];
        setActivityLog(prev => [`${a.name}: ${a.task || 'يعمل...'} — ${a.progress || 0}%`, ...prev].slice(0, 20));
      }
    }, 3000);
    return () => clearInterval(iv);
  }, [agents]);

  const counts = { total: agents.length, working: agents.filter(a => a.status === 'working').length, idle: agents.filter(a => a.status === 'idle').length, error: agents.filter(a => a.status === 'error').length };

  return (
    <div dir="rtl" style={{ background: P.bg, minHeight: '100vh', color: P.textPrimary, fontFamily: 'Tajawal, sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px', borderBottom: `1px solid ${P.white08}` }}>
        <button onClick={onBack} style={{ background: P.primaryDim, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
          <ChevronLeft className="w-4 h-4" />
        </button>
        <Users className="w-5 h-5" style={{ color: P.primary }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: P.white }}>السرب</div>
          <div style={{ fontSize: 11, color: P.textSecondary }}>وكلاء متخصصون — Swarm Intelligence</div>
        </div>
        <button style={{ background: P.primaryMid, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
          <Play className="w-3.5 h-3.5" /> إطلاق سرب
        </button>
      </div>

      <div style={{ display: 'flex', gap: 16, padding: 16, height: 'calc(100vh - 60px)' }}>
        {/* شبكة الوكلاء */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {/* إحصائيات */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 16 }}>
            {[
              { label: 'الإجمالي', value: counts.total, color: P.primaryLight },
              { label: 'يعمل', value: counts.working, color: P.green },
              { label: 'خامل', value: counts.idle, color: P.textSecondary },
              { label: 'خطأ', value: counts.error, color: P.red },
            ].map(s => (
              <div key={s.label} style={{ background: P.card, borderRadius: 10, padding: '10px 12px', border: `1px solid ${P.white08}`, textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: s.color }}>{s.value}</div>
                <div style={{ fontSize: 9, color: P.textSecondary }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* بطاقات الوكلاء */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
            {agents.map(agent => {
              const sc = STATUS_CONFIG[agent.status];
              return (
                <div key={agent.id} style={{ background: P.card, borderRadius: 10, padding: 14, border: `1px solid ${agent.status === 'error' ? P.red + '40' : P.white08}` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <div style={{ width: 28, height: 28, borderRadius: 6, background: P.primaryMid, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Bot className="w-3.5 h-3.5" style={{ color: P.primaryLight }} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: P.white90 }}>{agent.name}</div>
                      <div style={{ fontSize: 9, color: P.textSecondary }}>{agent.role}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: sc.color, marginBottom: agent.task ? 6 : 0 }}>
                    {sc.icon} {sc.label}
                  </div>
                  {agent.task && (
                    <div style={{ fontSize: 10, color: P.textSecondary, marginBottom: agent.progress ? 4 : 0 }}>{agent.task}</div>
                  )}
                  {agent.progress !== undefined && agent.progress > 0 && (
                    <div style={{ height: 3, borderRadius: 2, background: P.primaryDim, marginTop: 4 }}>
                      <div style={{ width: `${agent.progress}%`, height: '100%', borderRadius: 2, background: P.green, transition: 'width 0.5s' }} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* تغذية النشاط */}
        <div style={{ width: 280, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: P.white90 }}>النشاط الحي</div>
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
            {activityLog.length > 0 ? activityLog.map((log, i) => (
              <div key={i} style={{ background: P.card, borderRadius: 6, padding: '6px 10px', border: `1px solid ${P.white08}`, fontSize: 10, color: P.textPrimary }}>
                {log}
              </div>
            )) : (
              <div style={{ background: P.card, borderRadius: 10, padding: 20, border: `1px solid ${P.white08}`, textAlign: 'center' }}>
                <Bot className="w-8 h-8" style={{ color: P.textSecondary, margin: '0 auto 8px' }} />
                <div style={{ fontSize: 11, color: P.textSecondary }}>لا يوجد نشاط حالياً</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
