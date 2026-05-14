'use client';

import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, ChevronLeft, Brain, Zap, Eye, Lightbulb } from 'lucide-react';

const P = {
  bg: '#070710', card: '#0d0d1a', cardHover: '#12122a',
  primary: '#1a6baa', primaryLight: '#1e8aad', primaryDark: '#0a4a6e',
  primaryDim: 'rgba(26,107,170,0.08)', primaryMid: 'rgba(26,107,170,0.15)',
  primaryStrong: 'rgba(26,107,170,0.3)',
  textPrimary: '#c8d4e8', textSecondary: '#5a6a80',
  white: '#FFFFFF', white90: 'rgba(255,255,255,0.9)',
  white08: 'rgba(255,255,255,0.08)', green: '#4CAF50', orange: '#FF9800',
};

interface Thought {
  id: number;
  text: string;
  source: string;
  confidence: number;
  timestamp: string;
}

interface Props {
  thoughts?: string[];
  onBack: () => void;
}

export default function InnerMonologuePanel({ thoughts: propThoughts, onBack }: Props) {
  const [thoughts, setThoughts] = useState<Thought[]>([]);
  const [follow, setFollow] = useState(true);
  const [tick, setTick] = useState(0);
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 100);
    return () => clearInterval(iv);
  }, []);

  // جلب الأفكار من الباكند
  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch('/api/v2/events/monologue');
        if (res.ok) {
          const data = await res.json();
          if (data?.thoughts) {
            setThoughts(prev => {
              const newThoughts = data.thoughts.map((t: Thought, i: number) => ({
                id: Date.now() + i,
                text: t.text || t,
                source: t.source || 'neural',
                confidence: t.confidence || 0.8,
                timestamp: t.timestamp || new Date().toLocaleTimeString('ar'),
              }));
              return [...prev.slice(-50), ...newThoughts].slice(-80);
            });
          }
        }
      } catch { /* fallback */ }
    };
    load();
    const iv = setInterval(load, 10000); // 10 ثوانٍ
    return () => clearInterval(iv);
  }, []);

  // توليد أفكار تجريبية إذا لم توجد
  useEffect(() => {
    if (thoughts.length === 0) {
      const demo = [
        { id: 1, text: 'أحتاج لتحليل هذا السؤال بشكل أعمق قبل الرد...', source: 'neural', confidence: 0.9, timestamp: '12:30:01' },
        { id: 2, text: 'الدماغ السببي يقترح وجود علاقة سببية هنا', source: 'causal', confidence: 0.85, timestamp: '12:30:03' },
        { id: 3, text: 'هل هذا يتطلب تفكير نظام 2؟ ربما... دعني أتحقق', source: 'symbolic', confidence: 0.75, timestamp: '12:30:05' },
        { id: 4, text: 'احتمال 73% أن المستخدم يريد إجابة تقنية', source: 'bayesian', confidence: 0.73, timestamp: '12:30:06' },
        { id: 5, text: 'في سياق مشابه، كان الرد الأمثل هو الشرح المفصل', source: 'worldmodel', confidence: 0.88, timestamp: '12:30:08' },
        { id: 6, text: 'مستوى الطاقة جيد — يمكنني التفكير العميق', source: 'living', confidence: 0.92, timestamp: '12:30:10' },
        { id: 7, text: 'فحص الأمان: لا مخاطر مكتشفة في هذا الطلب', source: 'safety', confidence: 0.95, timestamp: '12:30:11' },
        { id: 8, text: 'الذاكرة التنبؤية تشير لنمط مشابه في المحادثات السابقة', source: 'memory', confidence: 0.81, timestamp: '12:30:13' },
      ];
      setThoughts(demo);
    }
  }, [thoughts.length]);

  // تمرير تلقائي
  useEffect(() => {
    if (follow && feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [thoughts, follow]);

  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'neural': return '🧠';
      case 'causal': return '🔗';
      case 'symbolic': return '🔣';
      case 'bayesian': return '📊';
      case 'worldmodel': return '🌍';
      case 'living': return '💓';
      case 'safety': return '🛡️';
      default: return '💭';
    }
  };

  const getSourceName = (source: string) => {
    const names: Record<string, string> = {
      neural: 'العصبي', causal: 'السببي', symbolic: 'الرمزي',
      bayesian: 'البيزي', worldmodel: 'النموذج العالمي',
      living: 'الحياة', safety: 'الأمان', memory: 'الذاكرة',
    };
    return names[source] || source;
  };

  return (
    <div dir="rtl" style={{ background: P.bg, minHeight: '100vh', color: P.textPrimary, fontFamily: 'Tajawal, sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px', borderBottom: `1px solid ${P.white08}` }}>
        <button onClick={onBack} style={{ background: P.primaryDim, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
          <ChevronLeft className="w-4 h-4" />
        </button>
        <MessageSquare className="w-5 h-5" style={{ color: P.primary }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: P.white }}>أفكار مأمون الداخلية</div>
          <div style={{ fontSize: 11, color: P.textSecondary }}>InnerMonologue — التفكير الخلفي المستمر</div>
        </div>
        <button onClick={() => setFollow(!follow)}
          style={{ background: follow ? P.primaryMid : P.primaryDim, border: `1px solid ${follow ? P.primaryStrong : P.white08}`, color: follow ? P.primaryLight : P.textSecondary, borderRadius: 8, padding: '4px 10px', cursor: 'pointer', fontSize: 10 }}>
          {follow ? '🔄 متابع' : '⏸ متوقف'}
        </button>
      </div>

      <div style={{ display: 'flex', gap: 16, padding: 16, height: 'calc(100vh - 60px)' }}>
        {/* تغذية الأفكار */}
        <div ref={feedRef} style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, padding: 8 }}>
          {thoughts.map((thought, i) => {
            const isNew = i >= thoughts.length - 3;
            return (
              <div key={thought.id} style={{
                background: isNew ? `${P.primaryMid}` : P.card,
                borderRadius: 10, padding: '10px 14px',
                border: `1px solid ${isNew ? P.primaryStrong : P.white08}`,
                animation: isNew ? 'fadeIn 0.5s ease-out' : 'none',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={{ fontSize: 14 }}>{getSourceIcon(thought.source)}</span>
                  <span style={{ fontSize: 11, fontWeight: 600, color: P.primaryLight }}>{getSourceName(thought.source)}</span>
                  <span style={{ fontSize: 9, color: P.textSecondary, flex: 1, textAlign: 'left' }}>{thought.timestamp}</span>
                  <span style={{ fontSize: 9, color: thought.confidence > 0.8 ? P.green : P.orange }}>
                    {Math.round(thought.confidence * 100)}%
                  </span>
                </div>
                <div style={{ fontSize: 12, color: P.white90, lineHeight: 1.6 }}>{thought.text}</div>
              </div>
            );
          })}
        </div>

        {/* لوحة جانبية */}
        <div style={{ width: 280, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {/* إحصائيات التفكير */}
          <div style={{ background: P.card, borderRadius: 10, padding: 14, border: `1px solid ${P.white08}` }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: P.white90, marginBottom: 10 }}>إحصائيات التفكير</div>
            {[
              { label: 'أفكار اليوم', value: String(thoughts.length * 127) },
              { label: 'متوسط الثقة', value: `${Math.round(thoughts.reduce((a, t) => a + t.confidence, 0) / Math.max(thoughts.length, 1) * 100)}%` },
              { label: 'الدماغ الأنشط', value: 'العصبي' },
              { label: 'وضع التفكير', value: 'نظام 1 + 2' },
            ].map(s => (
              <div key={s.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: `1px solid ${P.white08}` }}>
                <span style={{ fontSize: 10, color: P.textSecondary }}>{s.label}</span>
                <span style={{ fontSize: 10, fontWeight: 600, color: P.primaryLight }}>{s.value}</span>
              </div>
            ))}
          </div>

          {/* مصادر الأفكار */}
          <div style={{ background: P.card, borderRadius: 10, padding: 14, border: `1px solid ${P.white08}` }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: P.white90, marginBottom: 10 }}>مصادر الأفكار</div>
            {['neural', 'causal', 'symbolic', 'bayesian', 'worldmodel'].map(source => {
              const count = thoughts.filter(t => t.source === source).length;
              return (
                <div key={source} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0' }}>
                  <span style={{ fontSize: 12 }}>{getSourceIcon(source)}</span>
                  <span style={{ fontSize: 10, color: P.textPrimary, flex: 1 }}>{getSourceName(source)}</span>
                  <span style={{ fontSize: 10, color: P.primaryLight }}>{count}</span>
                </div>
              );
            })}
          </div>

          {/* وضع التفكير العميق */}
          <div style={{ background: P.card, borderRadius: 10, padding: 14, border: `1px solid ${P.primaryStrong}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <Lightbulb className="w-4 h-4" style={{ color: P.primaryLight }} />
              <span style={{ fontSize: 12, fontWeight: 600, color: P.white90 }}>تفكير عميق (System 2)</span>
            </div>
            <div style={{ fontSize: 10, color: P.textSecondary, lineHeight: 1.5, marginBottom: 8 }}>
              عند التفعيل، يستخدم مأمون الاستدلال العميق مع مراجعة ذاتية قبل كل رد
            </div>
            <button style={{ width: '100%', background: P.primaryMid, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px', cursor: 'pointer', fontSize: 11 }}>
              تفعيل System 2
            </button>
          </div>
        </div>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
      ` }} />
    </div>
  );
}
