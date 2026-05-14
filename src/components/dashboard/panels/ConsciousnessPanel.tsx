'use client';

import React, { useState, useEffect } from 'react';
import { Eye, ChevronLeft, RotateCw, Zap, Brain } from 'lucide-react';
import { fetchConsciousnessState, fetchEmotionState } from '@/lib/jarvis-api';

const P = {
  bg: '#070710', card: '#0d0d1a', primary: '#1a6baa', primaryLight: '#1e8aad', primaryDark: '#0a4a6e',
  primaryDim: 'rgba(26,107,170,0.08)', primaryMid: 'rgba(26,107,170,0.15)', primaryStrong: 'rgba(26,107,170,0.3)',
  textPrimary: '#c8d4e8', textSecondary: '#5a6a80',
  white: '#FFFFFF', white90: 'rgba(255,255,255,0.9)', white08: 'rgba(255,255,255,0.08)',
  green: '#4CAF50', orange: '#FF9800', red: '#EF4444',
};

const STAGES = [
  { id: 'perceive', nameAr: 'إدراك', nameEn: 'Perceive', desc: 'استقبال المدخلات الحسية والأحداث الخارجية', color: '#1e8aad', icon: '👁️' },
  { id: 'predict', nameAr: 'تنبؤ', nameEn: 'Predict', desc: 'توقع النتائج المحتملة بناءً على النماذج الداخلية', color: '#2196F3', icon: '🔮' },
  { id: 'surprise', nameAr: 'مفاجأة', nameEn: 'Surprise', desc: 'قياس الفجوة بين التنبؤ والواقع — محرك التعلم', color: '#FF9800', icon: '⚡' },
  { id: 'learn', nameAr: 'تعلم', nameEn: 'Learn', desc: 'تحديث النماذج الذهنية بناءً على الأخطاء', color: '#4CAF50', icon: '📚' },
  { id: 'act', nameAr: 'فعل', nameEn: 'Act', desc: 'تنفيذ القرار الأمثل بناءً على المعرفة المكتسبة', color: '#E91E63', icon: '🎯' },
];

interface Props {
  consciousness?: number; coherence?: number; onBack: () => void;
}

export default function ConsciousnessPanel({ consciousness = 0.7, coherence = 82, onBack }: Props) {
  const [currentStage, setCurrentStage] = useState(0);
  const [stageData, setStageData] = useState<Record<string, { active: boolean; signals: number }>>({
    perceive: { active: true, signals: 45 },
    predict: { active: true, signals: 38 },
    surprise: { active: false, signals: 12 },
    learn: { active: true, signals: 28 },
    act: { active: true, signals: 33 },
  });
  const [tick, setTick] = useState(0);
  const [conscLevel, setConscLevel] = useState(consciousness);
  const [rotation, setRotation] = useState(0);

  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 100);
    return () => clearInterval(iv);
  }, []);

  // دوران حلقة الوعي
  useEffect(() => {
    const iv = setInterval(() => {
      setCurrentStage(s => (s + 1) % 5);
      setRotation(r => r + 72);
    }, 3000);
    return () => clearInterval(iv);
  }, []);

  // جلب البيانات
  useEffect(() => {
    const load = async () => {
      try {
        const [c, e] = await Promise.allSettled([fetchConsciousnessState(), fetchEmotionState()]);
        if (c.status === 'fulfilled') {
          const d = c.value as Record<string, unknown>;
          // الباكند يعيد current_phase أو stage أو phase
          // والـ level يأتي من overall_accuracy أو level مباشرة
          const rawLevel = (d.level as number) ?? (d.overall_accuracy as number) ?? undefined;
          if (rawLevel !== undefined) setConscLevel(rawLevel);
          
          // تحديد المرحلة الحالية — تدعم كل الصيغ
          const rawStage = (d.stage as string) || (d.current_phase as string) || (d.phase as string) || '';
          if (rawStage) {
            // تحويل أسماء المراحل: الباكند قد يعيد perceive/predict/surprise/learn/act
            // أو perception/prediction/surprise/learning/action
            const stageMap: Record<string, string> = {
              'perceive': 'perceive', 'perception': 'perceive',
              'predict': 'predict', 'prediction': 'predict',
              'surprise': 'surprise',
              'learn': 'learn', 'learning': 'learn',
              'act': 'act', 'action': 'act',
            };
            const mappedStage = stageMap[rawStage] || rawStage;
            const idx = STAGES.findIndex(s => s.id === mappedStage);
            if (idx >= 0) setCurrentStage(idx);
          }
          
          // تحديث بيانات المراحل إذا توفرت إحصائيات
          const newData: Record<string, { active: boolean; signals: number }> = {};
          STAGES.forEach(stage => { newData[stage.id] = stageData[stage.id] || { active: false, signals: 0 }; });
          if (d.perception_count !== undefined) newData.perceive = { active: true, signals: (d.perception_count as number) || 0 };
          if (d.total_expectations !== undefined) newData.predict = { active: true, signals: (d.total_expectations as number) || 0 };
          if (d.surprise_count !== undefined) newData.surprise = { active: (d.surprise_count as number) > 0, signals: (d.surprise_count as number) || 0 };
          if (d.learning_count !== undefined) newData.learn = { active: true, signals: (d.learning_count as number) || 0 };
          if (d.action_count !== undefined) newData.act = { active: true, signals: (d.action_count as number) || 0 };
          setStageData(newData);
        }
      } catch { /* fallback */ }
    };
    load();
    const iv = setInterval(load, 15000); // 15 ثانية — البيانات لا تتغير بسرعة
    return () => clearInterval(iv);
  }, []);

  const cx = 200, cy = 200, radius = 140;
  const stagePositions = STAGES.map((_, i) => {
    const angle = (i * 72 - 90) * (Math.PI / 180);
    return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
  });

  return (
    <div dir="rtl" style={{ background: P.bg, minHeight: '100vh', color: P.textPrimary, fontFamily: 'Tajawal, sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px', borderBottom: `1px solid ${P.white08}` }}>
        <button onClick={onBack} style={{ background: P.primaryDim, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
          <ChevronLeft className="w-4 h-4" />
        </button>
        <Eye className="w-5 h-5" style={{ color: P.primaryLight }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: P.white }}>حلقة الوعي</div>
          <div style={{ fontSize: 11, color: P.textSecondary }}>ConsciousnessLoop — 5 مراحل تدور باستمرار</div>
        </div>
        <div style={{ background: P.primaryMid, borderRadius: 8, padding: '4px 10px', fontSize: 11, color: P.primaryLight }}>
          مستوى الوعي: {Math.round(conscLevel * 100)}%
        </div>
      </div>

      <div style={{ display: 'flex', gap: 20, padding: 20, height: 'calc(100vh - 60px)' }}>
        {/* الحلقة الدائرية */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg width="420" height="420" viewBox="0 0 420 420">
            {/* خطوط الاتصال بين المراحل */}
            {stagePositions.map((pos, i) => {
              const nextPos = stagePositions[(i + 1) % 5];
              const isCurrent = i === currentStage;
              return (
                <line key={i} x1={pos.x} y1={pos.y} x2={nextPos.x} y2={nextPos.y}
                  stroke={isCurrent ? STAGES[i].color : P.primary}
                  strokeWidth={isCurrent ? 2.5 : 1}
                  strokeOpacity={isCurrent ? 0.6 : 0.15}
                />
              );
            })}

            {/* الدائرة المركزية */}
            <circle cx={cx} cy={cy} r={60} fill={P.primaryDim} stroke={P.primary} strokeWidth="1.5" strokeOpacity={0.3} />
            <text x={cx} y={cy - 8} textAnchor="middle" fill={P.primaryLight} fontSize="24" fontWeight="700">
              {Math.round(conscLevel * 100)}%
            </text>
            <text x={cx} y={cy + 12} textAnchor="middle" fill={P.textSecondary} fontSize="10">مستوى الوعي</text>
            <text x={cx} y={cy + 26} textAnchor="middle" fill={P.textSecondary} fontSize="9">التماسك: {coherence}%</text>

            {/* عقود المراحل */}
            {STAGES.map((stage, i) => {
              const pos = stagePositions[i];
              const isCurrent = i === currentStage;
              const pulse = isCurrent ? 1 + 0.05 * Math.sin(tick * 0.15) : 1;
              const data = stageData[stage.id];

              return (
                <g key={stage.id}>
                  {/* هالة المرحلة الحالية */}
                  {isCurrent && (
                    <circle cx={pos.x} cy={pos.y} r={36 * pulse} fill="none"
                      stroke={stage.color} strokeWidth="2" strokeOpacity={0.4 + 0.3 * Math.sin(tick * 0.1)} />
                  )}
                  <circle cx={pos.x} cy={pos.y} r={30}
                    fill={isCurrent ? `${stage.color}30` : P.primaryDim}
                    stroke={isCurrent ? stage.color : P.primary}
                    strokeWidth={isCurrent ? 2 : 1}
                  />
                  <text x={pos.x} y={pos.y + 2} textAnchor="middle" fontSize="16">{stage.icon}</text>
                  <text x={pos.x} y={pos.y + 44} textAnchor="middle" fill={P.white90} fontSize="11" fontWeight={isCurrent ? '700' : '400'}>
                    {stage.nameAr}
                  </text>
                  <text x={pos.x} y={pos.y + 56} textAnchor="middle" fill={P.textSecondary} fontSize="8">
                    {stage.nameEn}
                  </text>
                  {data && (
                    <text x={pos.x} y={pos.y - 38} textAnchor="middle" fill={stage.color} fontSize="9" fontWeight="600">
                      {data.signals} إشارة
                    </text>
                  )}
                </g>
              );
            })}

            {/* سهم الدوران */}
            <g transform={`rotate(${rotation}, ${cx}, ${cy})`}>
              <line x1={cx} y1={cy - 65} x2={cx} y2={cy - 80}
                stroke={P.primaryLight} strokeWidth="2" markerEnd="url(#arrowhead)" />
            </g>
            <defs>
              <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill={P.primaryLight} />
              </marker>
            </defs>
          </svg>
        </div>

        {/* تفاصيل المراحل */}
        <div style={{ width: 340, display: 'flex', flexDirection: 'column', gap: 8, overflowY: 'auto' }}>
          {STAGES.map((stage, i) => {
            const isCurrent = i === currentStage;
            const data = stageData[stage.id];
            return (
              <div key={stage.id} style={{
                background: isCurrent ? P.primaryMid : P.card,
                borderRadius: 10, padding: '10px 14px',
                border: `1px solid ${isCurrent ? P.primaryStrong : P.white08}`,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={{ fontSize: 16 }}>{stage.icon}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: P.white90 }}>{stage.nameAr}</div>
                    <div style={{ fontSize: 9, color: P.textSecondary }}>{stage.nameEn}</div>
                  </div>
                  {isCurrent && (
                    <div style={{ background: `${stage.color}30`, color: stage.color, borderRadius: 6, padding: '2px 8px', fontSize: 9, fontWeight: 600 }}>
                      المرحلة الحالية
                    </div>
                  )}
                </div>
                <div style={{ fontSize: 10, color: P.textSecondary, lineHeight: 1.5, marginBottom: 6 }}>{stage.desc}</div>
                <div style={{ display: 'flex', gap: 8, fontSize: 9 }}>
                  <span style={{ color: data?.active ? P.green : P.textSecondary }}>
                    {data?.active ? '● نشط' : '○ متوقف'}
                  </span>
                  <span style={{ color: P.textSecondary }}>الإشارات: {data?.signals || 0}</span>
                </div>
              </div>
            );
          })}

          {/* إحصائيات */}
          <div style={{ background: P.card, borderRadius: 10, padding: 14, border: `1px solid ${P.white08}`, marginTop: 8 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: P.white90, marginBottom: 8 }}>إحصائيات الوعي</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {[
                { label: 'الدورات اليوم', value: '1,247' },
                { label: 'مفاجآت', value: '89' },
                { label: 'تعلم جديد', value: '34' },
                { label: 'أفعال منفذة', value: '156' },
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
    </div>
  );
}
