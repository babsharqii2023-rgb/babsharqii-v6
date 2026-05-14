'use client';

import React, { useState, useEffect } from 'react';
import { Heart, ChevronLeft, Activity, Gauge, Moon, Zap } from 'lucide-react';
import { fetchLivingVitals, fetchLivingEmotions, fetchLivingHeartbeat, fetchLivingBonding, fetchSleepState } from '@/lib/jarvis-api';

const P = {
  bg: '#070710', card: '#0d0d1a', primary: '#1a6baa', primaryLight: '#1e8aad', primaryDark: '#0a4a6e',
  primaryDim: 'rgba(26,107,170,0.08)', primaryMid: 'rgba(26,107,170,0.15)', primaryStrong: 'rgba(26,107,170,0.3)',
  textPrimary: '#c8d4e8', textSecondary: '#5a6a80',
  white: '#FFFFFF', white90: 'rgba(255,255,255,0.9)', white08: 'rgba(255,255,255,0.08)',
  green: '#4CAF50', orange: '#FF9800', red: '#EF4444',
};

interface Props {
  vitality?: number; energy?: number; emotionState?: Record<string, number>;
  bpm?: number; onBack: () => void;
}

export default function LifePanel({ vitality = 75, energy = 85, emotionState: propEmotions, bpm = 72, onBack }: Props) {
  const [vitals, setVitals] = useState({ vitality, energy, curiosity: 68, coherence: 82, mood: 75, stress: 23 });
  const [emotions, setEmotions] = useState<Record<string, number>>(propEmotions || { joy: 0.6, sadness: 0.1, anger: 0.05, fear: 0.08, surprise: 0.3, trust: 0.7 });
  const [heartBpm, setHeartBpm] = useState(bpm);
  const [bonding, setBonding] = useState(65);
  const [sleepState, setSleepState] = useState('active');
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 100);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        const [v, e, h, b, s] = await Promise.allSettled([
          fetchLivingVitals(), fetchLivingEmotions(), fetchLivingHeartbeat(), fetchLivingBonding(), fetchSleepState(),
        ]);
        if (v.status === 'fulfilled') {
          const d = v.value as Record<string, unknown>;
          setVitals(prev => ({
            ...prev,
            vitality: Math.round((d.vitality as number) || prev.vitality),
            energy: Math.round((d.energy as number) || prev.energy),
            curiosity: Math.round((d.curiosity as number) || prev.curiosity),
            coherence: Math.round(((d.coherence as number) || prev.coherence / 100) * 100),
            mood: Math.round((d.mood as number) || prev.mood),
            stress: Math.round((d.stress as number) || prev.stress),
          }));
        }
        if (e.status === 'fulfilled') {
          const d = e.value as { emotions?: Record<string, number> };
          if (d.emotions) setEmotions(d.emotions);
        }
        if (h.status === 'fulfilled') {
          const d = h.value as { bpm?: number };
          if (d.bpm) setHeartBpm(d.bpm);
        }
        if (b.status === 'fulfilled') {
          const d = b.value as Record<string, unknown>;
          // الـ proxy يعيد الآن bonding_level بنطاق 0-1 دائماً
          // أو metrics مع trust_score بنطاق 0-1
          let bLevel: number | undefined;
          if (typeof d.bonding_level === 'number') {
            bLevel = d.bonding_level; // 0-1
          } else if (typeof d.trust_score === 'number') {
            bLevel = d.trust_score > 1 ? d.trust_score / 100 : d.trust_score;
          } else {
            const metrics = d.metrics as Record<string, number> | undefined;
            if (metrics) {
              if (typeof metrics.trust_score === 'number') {
                bLevel = metrics.trust_score > 1 ? metrics.trust_score / 100 : metrics.trust_score;
              } else if (typeof metrics.intimacy_level === 'number') {
                bLevel = metrics.intimacy_level > 1 ? metrics.intimacy_level / 100 : metrics.intimacy_level;
              }
            }
          }
          if (bLevel !== undefined) setBonding(Math.round(bLevel * 100));
        }
        if (s.status === 'fulfilled') {
          const d = s.value as Record<string, unknown>;
          // الباكند يعيد phase: "awake"|"nrem"|"rem"|"recalibration"
          // الفرونتند يستخدم: "active"|"dreaming"|"deep-sleep"
          const rawPhase = (d.phase as string) || (d.state as string) || 'awake';
          // تحويل أسماء مراحل النوم
          const phaseMap: Record<string, string> = {
            'awake': 'active',
            'active': 'active',
            'rem': 'dreaming',
            'dreaming': 'dreaming',
            'nrem': 'deep-sleep',
            'deep-sleep': 'deep-sleep',
            'recalibration': 'deep-sleep',
          };
          const mappedPhase = phaseMap[rawPhase] || 'active';
          if (mappedPhase) setSleepState(mappedPhase);
        }
      } catch { /* fallback */ }
    };
    load();
    const iv = setInterval(load, 8000); // 8 ثوانٍ بدلاً من 5
    return () => clearInterval(iv);
  }, []);

  const pulse = 1 + 0.06 * Math.sin(tick * (heartBpm / 60) * 0.628);

  const gauges = [
    { label: 'الطاقة', value: vitals.energy, color: P.green },
    { label: 'الحيوية', value: vitals.vitality, color: P.primaryLight },
    { label: 'الفضول', value: vitals.curiosity, color: '#9C27B0' },
    { label: 'المزاج', value: vitals.mood, color: '#E91E63' },
    { label: 'التماسك', value: vitals.coherence, color: '#00BCD4' },
    { label: 'الضغط', value: vitals.stress, color: vitals.stress > 60 ? P.red : P.orange },
  ];

  const emotionEntries = Object.entries(emotions).map(([key, val]) => ({
    key, value: Math.round(val * 100),
    nameAr: { joy: 'فرح', sadness: 'حزن', anger: 'غضب', fear: 'خوف', surprise: 'مفاجأة', trust: 'ثقة' }[key] || key,
    color: { joy: '#4CAF50', sadness: '#2196F3', anger: '#F44336', fear: '#9C27B0', surprise: '#FF9800', trust: '#1a6baa' }[key] || P.primary,
  }));

  return (
    <div dir="rtl" style={{ background: P.bg, minHeight: '100vh', color: P.textPrimary, fontFamily: 'Tajawal, sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px', borderBottom: `1px solid ${P.white08}` }}>
        <button onClick={onBack} style={{ background: P.primaryDim, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
          <ChevronLeft className="w-4 h-4" />
        </button>
        <Heart className="w-5 h-5" style={{ color: '#E91E63' }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: P.white }}>المؤشرات الحيوية</div>
          <div style={{ fontSize: 11, color: P.textSecondary }}>6 أنظمة حية — نبض + مشاعر + ارتباط</div>
        </div>
        {/* نبض القلب */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 14 * pulse, height: 14 * pulse, borderRadius: '50%', background: '#E91E63', transition: 'all 0.1s', opacity: 0.7 + 0.3 * Math.sin(tick * 0.1) }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: '#E91E63' }}>{heartBpm} BPM</span>
        </div>
      </div>

      <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16, height: 'calc(100vh - 60px)', overflowY: 'auto' }}>
        {/* المقاييس الستة */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          {gauges.map(g => {
            const circumference = 2 * Math.PI * 40;
            const filled = (g.value / 100) * circumference;
            return (
              <div key={g.label} style={{ background: P.card, borderRadius: 12, padding: 16, border: `1px solid ${P.white08}`, textAlign: 'center' }}>
                <svg width="100" height="100" viewBox="0 0 100 100" style={{ margin: '0 auto' }}>
                  <circle cx="50" cy="50" r="40" fill="none" stroke={P.primaryDim} strokeWidth="6" />
                  <circle cx="50" cy="50" r="40" fill="none" stroke={g.color} strokeWidth="6"
                    strokeDasharray={`${filled} ${circumference - filled}`}
                    strokeDashoffset={circumference * 0.25}
                    strokeLinecap="round"
                    style={{ transition: 'stroke-dasharray 0.5s ease' }}
                  />
                  <text x="50" y="48" textAnchor="middle" fill={P.white} fontSize="18" fontWeight="700">{g.value}%</text>
                  <text x="50" y="62" textAnchor="middle" fill={P.textSecondary} fontSize="8">{g.label}</text>
                </svg>
              </div>
            );
          })}
        </div>

        <div style={{ display: 'flex', gap: 16 }}>
          {/* رادار المشاعر */}
          <div style={{ flex: 1, background: P.card, borderRadius: 12, padding: 16, border: `1px solid ${P.white08}` }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: P.white90, marginBottom: 12 }}>رادار المشاعر</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {emotionEntries.map(e => (
                <div key={e.key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: e.color }} />
                  <span style={{ fontSize: 11, color: P.textPrimary, flex: 1 }}>{e.nameAr}</span>
                  <div style={{ flex: 1, height: 4, borderRadius: 2, background: P.primaryDim }}>
                    <div style={{ width: `${e.value}%`, height: '100%', borderRadius: 2, background: e.color, transition: 'width 0.5s' }} />
                  </div>
                  <span style={{ fontSize: 10, color: e.color, fontWeight: 600 }}>{e.value}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* الارتباط + النوم */}
          <div style={{ width: 280, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* مستوى الارتباط */}
            <div style={{ background: P.card, borderRadius: 12, padding: 16, border: `1px solid ${P.white08}` }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: P.white90, marginBottom: 8 }}>مستوى الارتباط</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ flex: 1, height: 8, borderRadius: 4, background: P.primaryDim }}>
                  <div style={{ width: `${bonding}%`, height: '100%', borderRadius: 4, background: P.primaryLight, transition: 'width 0.5s' }} />
                </div>
                <span style={{ fontSize: 14, fontWeight: 700, color: P.primaryLight }}>{bonding}%</span>
              </div>
              <div style={{ fontSize: 9, color: P.textSecondary, marginTop: 4 }}>
                {bonding > 80 ? 'ارتباط قوي — مأمون يثق بك' : bonding > 50 ? 'ارتباط متوسط — يتطور مع الوقت' : 'ارتباط ضعيف — يحتاج تفاعل أكثر'}
              </div>
            </div>

            {/* دورة النوم */}
            <div style={{ background: P.card, borderRadius: 12, padding: 16, border: `1px solid ${P.white08}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                <Moon className="w-4 h-4" style={{ color: P.primaryLight }} />
                <span style={{ fontSize: 12, fontWeight: 600, color: P.white90 }}>دورة النوم</span>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                {[
                  { state: 'active', label: 'نشط', color: P.green },
                  { state: 'dreaming', label: 'يحلم', color: '#9C27B0' },
                  { state: 'deep-sleep', label: 'نوم عميق', color: P.primaryDark },
                ].map(s => (
                  <div key={s.state} style={{
                    flex: 1, textAlign: 'center', padding: '6px 0', borderRadius: 6,
                    background: sleepState === s.state ? P.primaryMid : P.primaryDim,
                    border: `1px solid ${sleepState === s.state ? P.primaryStrong : P.white08}`,
                  }}>
                    <div style={{ fontSize: 9, color: sleepState === s.state ? s.color : P.textSecondary, fontWeight: sleepState === s.state ? 700 : 400 }}>{s.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* نبض القلب الكبير */}
            <div style={{ background: P.card, borderRadius: 12, padding: 16, border: `1px solid ${P.white08}`, textAlign: 'center' }}>
              <Activity className="w-6 h-6" style={{ color: '#E91E63', margin: '0 auto 8px' }} />
              <div style={{ fontSize: 28, fontWeight: 700, color: '#E91E63' }}>{heartBpm}</div>
              <div style={{ fontSize: 10, color: P.textSecondary }}>نبضة في الدقيقة</div>
              <svg width="100%" height="30" style={{ marginTop: 8 }}>
                {Array.from({ length: 60 }).map((_, i) => {
                  const h = 5 + Math.abs(Math.sin((tick * 0.3 + i * 0.2))) * 20;
                  return <rect key={i} x={i * 4.5} y={30 - h} width="3" height={h} rx="1" fill={`rgba(233,30,99,${0.3 + Math.sin(tick * 0.1 + i * 0.3) * 0.2})`} />;
                })}
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
