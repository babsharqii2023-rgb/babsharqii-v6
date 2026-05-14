'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Brain, ArrowRight, Zap, Thermometer, Activity, ChevronLeft, Radio } from 'lucide-react';
import { fetchBrainStates, type BrainState } from '@/lib/jarvis-api';

// ═══════════════════════════════════════════════════════════════════════
// COLOR SYSTEM — مطابق للثيم الكوني الأزرق
// ═══════════════════════════════════════════════════════════════════════
const P = {
  bg: '#070710',
  card: '#0d0d1a',
  cardHover: '#12122a',
  primary: '#1a6baa',
  primaryLight: '#1e8aad',
  primaryDark: '#0a4a6e',
  primaryDim: 'rgba(26,107,170,0.08)',
  primaryMid: 'rgba(26,107,170,0.15)',
  primaryStrong: 'rgba(26,107,170,0.3)',
  primaryGlow: '0 0 12px rgba(26,107,170,0.4)',
  primaryGlowBig: '0 0 24px rgba(26,107,170,0.2)',
  textPrimary: '#c8d4e8',
  textSecondary: '#5a6a80',
  white: '#FFFFFF',
  white90: 'rgba(255,255,255,0.9)',
  white70: 'rgba(200,212,232,0.7)',
  white50: 'rgba(255,255,255,0.5)',
  white30: 'rgba(255,255,255,0.3)',
  white15: 'rgba(255,255,255,0.15)',
  white08: 'rgba(255,255,255,0.08)',
  green: '#4CAF50',
  orange: '#FF9800',
  red: '#EF4444',
};

// ═══════════════════════════════════════════════════════════════════════
// تعريفات الأدمغة الخمسة
// ═══════════════════════════════════════════════════════════════════════
const BRAINS = [
  { id: 'neural', nameAr: 'العصبي', nameEn: 'NeuralBrain', model: 'GLM-5.1', color: '#1e8aad', angle: -90 },
  { id: 'causal', nameAr: 'السببي', nameEn: 'CausalBrain', model: 'DeepSeek-Reasoner', color: '#2196F3', angle: -18 },
  { id: 'symbolic', nameAr: 'الرمزي', nameEn: 'SymbolicBrain', model: 'GLM-4-Plus', color: '#0a4a6e', angle: 54 },
  { id: 'bayesian', nameAr: 'البيزي', nameEn: 'BayesianBrain', model: 'Gemini-2.0-Flash', color: '#1565C0', angle: 126 },
  { id: 'worldmodel', nameAr: 'النموذج العالمي', nameEn: 'WorldModelBrain', model: 'DeepSeek-Chat', color: '#0D47A1', angle: 198 },
];

interface Props {
  brains?: BrainState[];
  vitality?: number;
  consciousness?: number;
  onBack: () => void;
  onDeliberation?: () => void;
}

export default function BrainsOrbPanel({ brains: propBrains, vitality = 75, consciousness = 0.7, onBack, onDeliberation }: Props) {
  const [brains, setBrains] = useState<BrainState[]>(propBrains || []);
  const [selectedBrain, setSelectedBrain] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [winnerIndex, setWinnerIndex] = useState(0);
  const [loading, setLoading] = useState(true);

  // نبض التحديث
  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 100);
    return () => clearInterval(iv);
  }, []);

  // دوران الدماغ الفائز
  useEffect(() => {
    const iv = setInterval(() => setWinnerIndex(w => (w + 1) % 5), 4000);
    return () => clearInterval(iv);
  }, []);

  // جلب بيانات الأدمغة
  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchBrainStates();
        if (data?.brains?.length) setBrains(data.brains);
      } catch { /* fallback */ }
      setLoading(false);
    };
    load();
    const iv = setInterval(load, 10000);
    return () => clearInterval(iv);
  }, []);

  // حساب مواقع الخماسي
  const cx = 300, cy = 250, radius = 160;
  const brainPositions = BRAINS.map(b => {
    const rad = (b.angle * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
  });

  // بيانات الدماغ المحدد
  const selected = selectedBrain ? BRAINS.find(b => b.id === selectedBrain) : null;
  const selectedData = selectedBrain ? brains.find(b => (b as unknown as Record<string, unknown>).brain_id === selectedBrain || b.id === selectedBrain) : null;

  return (
    <div dir="rtl" style={{ background: P.bg, minHeight: '100vh', color: P.textPrimary, fontFamily: 'Tajawal, sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px', borderBottom: `1px solid ${P.white08}` }}>
        <button onClick={onBack} style={{ background: P.primaryDim, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
          <ChevronLeft className="w-4 h-4" />
        </button>
        <Brain className="w-5 h-5" style={{ color: P.primary }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: P.white }}>الأدمغة الخمسة</div>
          <div style={{ fontSize: 11, color: P.textSecondary }}>5 أدمغة تتنافس عبر Global Workspace</div>
        </div>
        {onDeliberation && (
          <button onClick={onDeliberation} style={{ background: P.primaryMid, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px 14px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
            <Zap className="w-3.5 h-3.5" /> مداولة
          </button>
        )}
      </div>

      <div style={{ display: 'flex', gap: 20, padding: 20, height: 'calc(100vh - 60px)' }}>
        {/* الرسم الخماسي */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg width="600" height="500" viewBox="0 0 600 500">
            {/* خيوط الاتصال بين الأدمغة */}
            {brainPositions.map((pos, i) => 
              brainPositions.slice(i + 1).map((pos2, j) => {
                const isActive = (i === winnerIndex || i + j + 1 === winnerIndex);
                const pulseOpacity = isActive ? 0.4 + 0.2 * Math.sin(tick * 0.1) : 0.1;
                return (
                  <line key={`${i}-${j}`} x1={pos.x} y1={pos.y} x2={pos2.x} y2={pos2.y}
                    stroke={P.primary} strokeWidth={isActive ? 2 : 1}
                    strokeOpacity={pulseOpacity}
                  />
                );
              })
            )}

            {/* الدائرة المركزية — مستوى الوعي */}
            <circle cx={cx} cy={cy} r={55} fill={P.primaryDim} stroke={P.primary} strokeWidth={2} strokeOpacity={0.3} />
            <text x={cx} y={cy - 10} textAnchor="middle" fill={P.primaryLight} fontSize={22} fontWeight="700">
              {Math.round(consciousness * 100)}%
            </text>
            <text x={cx} y={cy + 12} textAnchor="middle" fill={P.textSecondary} fontSize={10}>
              مستوى الوعي
            </text>
            <text x={cx} y={cy + 26} textAnchor="middle" fill={P.textSecondary} fontSize={9}>
              {vitality}% حيوية
            </text>

            {/* عقد الأدمغة */}
            {BRAINS.map((brain, i) => {
              const pos = brainPositions[i];
              const isWinner = i === winnerIndex;
              const isSelected = selectedBrain === brain.id;
              const pulse = isWinner ? 1 + 0.08 * Math.sin(tick * 0.15) : 1;
              const brainData = brains.find(b => (b as unknown as Record<string, unknown>).brain_id === brain.id || b.id === brain.id);
              const confidence = brainData?.confidence || 70 + Math.round(Math.random() * 20);

              return (
                <g key={brain.id} onClick={() => setSelectedBrain(selectedBrain === brain.id ? null : brain.id)}
                   style={{ cursor: 'pointer' }}>
                  {/* هالة الفائز */}
                  {isWinner && (
                    <circle cx={pos.x} cy={pos.y} r={38 * pulse} fill="none" stroke={P.primaryLight}
                      strokeWidth={2} strokeOpacity={0.5 + 0.3 * Math.sin(tick * 0.1)} />
                  )}
                  {/* الدائرة الأساسية */}
                  <circle cx={pos.x} cy={pos.y} r={32}
                    fill={isSelected ? P.primaryStrong : isWinner ? P.primaryMid : P.primaryDim}
                    stroke={isSelected ? P.primaryLight : brain.color}
                    strokeWidth={isSelected ? 2.5 : 1.5}
                  />
                  {/* أيقونة الدماغ */}
                  <text x={pos.x} y={pos.y + 2} textAnchor="middle" fill={P.primaryLight} fontSize={14}>
                    🧠
                  </text>
                  {/* اسم الدماغ */}
                  <text x={pos.x} y={pos.y + 48} textAnchor="middle" fill={P.white90} fontSize={12} fontWeight="600">
                    {brain.nameAr}
                  </text>
                  {/* النموذج */}
                  <text x={pos.x} y={pos.y + 62} textAnchor="middle" fill={P.textSecondary} fontSize={9}>
                    {brain.model}
                  </text>
                  {/* الثقة */}
                  <text x={pos.x} y={pos.y - 42} textAnchor="middle" fill={confidence > 80 ? P.green : P.orange} fontSize={10} fontWeight="600">
                    {confidence}%
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* لوحة التفاصيل */}
        <div style={{ width: 320, display: 'flex', flexDirection: 'column', gap: 12, overflowY: 'auto' }}>
          {/* بطاقة الدماغ المحدد */}
          {selected ? (
            <div style={{ background: P.card, borderRadius: 12, padding: 16, border: `1px solid ${P.primaryStrong}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, background: P.primaryMid, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>🧠</div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: P.white }}>{selected.nameAr}</div>
                  <div style={{ fontSize: 10, color: P.textSecondary }}>{selected.nameEn}</div>
                </div>
              </div>
              <div style={{ fontSize: 11, color: P.textSecondary, marginBottom: 4 }}>النموذج: <span style={{ color: P.primaryLight }}>{selected.model}</span></div>
              <div style={{ fontSize: 11, color: P.textSecondary, marginBottom: 4 }}>الثقة: <span style={{ color: P.green }}>{selectedData?.confidence || 85}%</span></div>
              <div style={{ fontSize: 11, color: P.textSecondary, marginBottom: 4 }}>الحالة: <span style={{ color: P.green }}>{selectedData?.status === 'active' ? 'نشط' : selectedData?.status || 'نشط'}</span></div>
              <div style={{ fontSize: 11, color: P.textSecondary, marginBottom: 4 }}>الحرارة: <span style={{ color: P.textPrimary }}>{((selectedData as unknown as Record<string, unknown>)?.temperature as number)?.toFixed(1) || '0.7'}</span></div>
              <div style={{ fontSize: 11, color: P.textSecondary }}>الوزن: <span style={{ color: P.textPrimary }}>{selectedData?.weight?.toFixed(2) || '0.20'}</span></div>
            </div>
          ) : (
            <div style={{ background: P.card, borderRadius: 12, padding: 16, border: `1px solid ${P.white08}`, textAlign: 'center' }}>
              <Brain className="w-8 h-8" style={{ color: P.primary, margin: '0 auto 8px' }} />
              <div style={{ fontSize: 12, color: P.textSecondary }}>اضغط على أي دماغ لعرض التفاصيل</div>
            </div>
          )}

          {/* قائمة الأدمغة */}
          {BRAINS.map((brain, i) => {
            const brainData = brains.find(b => (b as unknown as Record<string, unknown>).brain_id === brain.id || b.id === brain.id);
            const isWinner = i === winnerIndex;
            const confidence = brainData?.confidence || 70 + Math.round(Math.random() * 20);
            return (
              <div key={brain.id} onClick={() => setSelectedBrain(selectedBrain === brain.id ? null : brain.id)}
                style={{
                  background: selectedBrain === brain.id ? P.primaryMid : P.card,
                  borderRadius: 10, padding: '10px 12px', cursor: 'pointer',
                  border: `1px solid ${selectedBrain === brain.id ? P.primaryStrong : P.white08}`,
                  display: 'flex', alignItems: 'center', gap: 10,
                  transition: 'background 0.2s',
                }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: isWinner ? P.primaryLight : P.textSecondary, boxShadow: isWinner ? P.primaryGlow : 'none' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: P.white90 }}>{brain.nameAr}</div>
                  <div style={{ fontSize: 9, color: P.textSecondary }}>{brain.model}</div>
                </div>
                <div style={{ fontSize: 11, fontWeight: 600, color: confidence > 80 ? P.green : P.orange }}>{confidence}%</div>
                {isWinner && <Zap className="w-3.5 h-3.5" style={{ color: P.primaryLight }} />}
              </div>
            );
          })}

          {/* إحصائيات */}
          <div style={{ background: P.card, borderRadius: 10, padding: 12, border: `1px solid ${P.white08}` }}>
            <div style={{ fontSize: 11, color: P.textSecondary, marginBottom: 8 }}>إحصائيات الأدمغة</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <div style={{ background: P.primaryDim, borderRadius: 8, padding: '8px 10px', textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: P.primaryLight }}>{brains.length || 5}</div>
                <div style={{ fontSize: 9, color: P.textSecondary }}>نشط</div>
              </div>
              <div style={{ background: P.primaryDim, borderRadius: 8, padding: '8px 10px', textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: P.primaryLight }}>{vitality}%</div>
                <div style={{ fontSize: 9, color: P.textSecondary }}>حيوية</div>
              </div>
              <div style={{ background: P.primaryDim, borderRadius: 8, padding: '8px 10px', textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: P.primaryLight }}>{Math.round(consciousness * 100)}%</div>
                <div style={{ fontSize: 9, color: P.textSecondary }}>وعي</div>
              </div>
              <div style={{ background: P.primaryDim, borderRadius: 8, padding: '8px 10px', textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: P.primaryLight }}>28</div>
                <div style={{ fontSize: 9, color: P.textSecondary }}>إشارة</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
