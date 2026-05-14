// ═══════════════════════════════════════════════════════════════════
// BrainStateOverlay — تراكب حالة الأدمغة
// Detailed brain status overlay showing each brain's
// activity, confidence, model, and real-time metrics
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface BrainData {
  id: string;
  name: string;
  nameAr: string;
  status: string;
  confidence: number;
  model?: string;
  weight?: number;
  is_on_fallback?: boolean;
  has_api_key?: boolean;
  argument?: string;
  latency?: number;
}

interface BrainStateOverlayProps {
  brains?: BrainData[];
  brain_responses?: Record<string, unknown>;
  activeBrain?: string;
  _isOffline?: boolean;
  onBack?: () => void;
  [key: string]: unknown;
}

const BRAIN_VISUAL: Record<string, {
  color: string; shape: string; oscillator: string; model: string;
}> = {
  neural: { color: '#00e5ff', shape: 'كرة', oscillator: 'موجة منشارية', model: 'GLM-5.1' },
  causal: { color: '#ff9100', shape: 'عشريني الأوجه', oscillator: 'موجة جيبية', model: 'DeepSeek-Reasoner' },
  symbolic: { color: '#448aff', shape: 'ثماني السطوح', oscillator: 'موجة مربعة', model: 'GLM-4-Plus' },
  bayesian: { color: '#69f0ae', shape: 'اثنا عشري الأوجه', oscillator: 'موجة مثلثية', model: 'Gemini-2.0-Flash' },
  world_model: { color: '#ffd740', shape: 'عقدة طوريّة', oscillator: 'جيبية منخفضة', model: 'DeepSeek-Chat' },
};

const DEFAULT_BRAINS: BrainData[] = [
  { id: 'neural', name: 'Neural', nameAr: 'العصبي', status: 'idle', confidence: 0.85, model: 'GLM-5.1', weight: 0.25 },
  { id: 'causal', name: 'Causal', nameAr: 'السببي', status: 'idle', confidence: 0.80, model: 'DeepSeek-Reasoner', weight: 0.22 },
  { id: 'symbolic', name: 'Symbolic', nameAr: 'الرمزي', status: 'idle', confidence: 0.75, model: 'GLM-4-Plus', weight: 0.18 },
  { id: 'bayesian', name: 'Bayesian', nameAr: 'الاحتمالي', status: 'idle', confidence: 0.78, model: 'Gemini-2.0-Flash', weight: 0.17 },
  { id: 'world_model', name: 'World Model', nameAr: 'العالمي', status: 'idle', confidence: 0.72, model: 'DeepSeek-Chat', weight: 0.18 },
];

export default function BrainStateOverlay(props: BrainStateOverlayProps) {
  const brains = props.brains || DEFAULT_BRAINS;
  const isOffline = props._isOffline || false;
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 100);
    return () => clearInterval(iv);
  }, []);

  // Fetch live brain states
  const [liveBrains, setLiveBrains] = useState<BrainData[]>(brains);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch('/api/super-mind/brain-state');
        if (res.ok) {
          const data = await res.json();
          if (data.brains?.length) setLiveBrains(data.brains);
        }
      } catch { /* keep current data */ }
    };
    load();
    const iv = setInterval(load, 5000);
    return () => clearInterval(iv);
  }, []);

  const activeCount = liveBrains.filter(b => b.status === 'active' || b.status === 'idle').length;
  const avgConfidence = liveBrains.reduce((sum, b) => sum + (b.confidence || 0), 0) / Math.max(liveBrains.length, 1);

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', padding: 16, gap: 12,
      color: '#c8d0e0', fontFamily: "'Cairo', system-ui, sans-serif",
      overflow: 'auto',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <motion.div
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          style={{ fontSize: 24 }}
        >
          🧠
        </motion.div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>حالة الأدمغة</div>
          <div style={{ fontSize: 10, color: '#5a6a80' }}>
            {activeCount} نشط • ثقة متوسطة: {Math.round(avgConfidence * 100)}%
          </div>
        </div>
        <div style={{
          marginRight: 'auto',
          background: 'rgba(13,123,181,0.1)',
          border: '1px solid rgba(13,123,181,0.3)',
          borderRadius: 8, padding: '4px 10px',
          fontSize: 11, color: '#0d7bb5', fontWeight: 600,
        }}>
          5 أدمغة
        </div>
      </div>

      {/* Summary Metrics */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8,
      }}>
        {[
          { label: 'النشاط', value: `${Math.round(avgConfidence * 100)}%`, color: '#0d7bb5' },
          { label: 'الاتصال', value: isOffline ? 'غير متصل' : 'متصل', color: isOffline ? '#EF4444' : '#4CAF50' },
          { label: 'الاستجابة', value: `${Math.round(200 + Math.sin(tick * 0.1) * 50)}ms`, color: '#FF9800' },
        ].map((metric, i) => (
          <div key={i} style={{
            background: `${metric.color}08`,
            border: `1px solid ${metric.color}20`,
            borderRadius: 8, padding: '8px 10px',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 9, color: '#5a6a80', marginBottom: 2 }}>{metric.label}</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: metric.color }}>{metric.value}</div>
          </div>
        ))}
      </div>

      {/* Brain Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {liveBrains.map((brain, i) => {
          const visual = BRAIN_VISUAL[brain.id] || { color: '#888', shape: '?', oscillator: '?', model: '?' };
          const isActive = brain.status === 'active';
          const pulse = isActive ? 1 + 0.05 * Math.sin(tick * 0.15 + i) : 1;

          return (
            <motion.div
              key={brain.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0, scale: pulse }}
              transition={{ delay: i * 0.08 }}
              style={{
                background: `${visual.color}08`,
                border: `1px solid ${visual.color}25`,
                borderRadius: 10, padding: '10px 14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {/* Status Dot */}
                <div style={{
                  width: 10, height: 10, borderRadius: '50%',
                  background: visual.color,
                  boxShadow: isActive ? `0 0 8px ${visual.color}` : 'none',
                  opacity: isActive ? 1 : 0.4,
                }} />

                {/* Brain Info */}
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: visual.color }}>
                    {brain.nameAr || brain.name}
                  </div>
                  <div style={{ fontSize: 9, color: '#5a6a80', display: 'flex', gap: 8 }}>
                    <span>{visual.model || brain.model}</span>
                    <span>•</span>
                    <span>{visual.shape}</span>
                    <span>•</span>
                    <span>{visual.oscillator}</span>
                  </div>
                </div>

                {/* Confidence */}
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: visual.color }}>
                    {Math.round((brain.confidence || 0) * 100)}%
                  </div>
                  <div style={{ fontSize: 8, color: '#5a6a80' }}>ثقة</div>
                </div>

                {/* Status Badge */}
                <div style={{
                  fontSize: 9, fontWeight: 600,
                  background: isActive ? 'rgba(76,175,80,0.1)' : 'rgba(255,255,255,0.04)',
                  color: isActive ? '#4CAF50' : '#5a6a80',
                  padding: '2px 8px', borderRadius: 4,
                  border: `1px solid ${isActive ? 'rgba(76,175,80,0.3)' : 'rgba(255,255,255,0.08)'}`,
                }}>
                  {isActive ? 'نشط' : 'خامل'}
                </div>

                {/* Fallback indicator */}
                {brain.is_on_fallback && (
                  <div style={{
                    fontSize: 8, color: '#FF9800',
                    background: 'rgba(255,152,0,0.1)',
                    padding: '1px 6px', borderRadius: 3,
                  }}>
                    احتياطي
                  </div>
                )}
              </div>

              {/* Confidence Bar */}
              <div style={{
                marginTop: 6, height: 3,
                background: 'rgba(255,255,255,0.04)',
                borderRadius: 2, overflow: 'hidden',
              }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(brain.confidence || 0) * 100}%` }}
                  transition={{ duration: 0.8, ease: 'easeOut' }}
                  style={{
                    height: '100%',
                    background: `linear-gradient(90deg, ${visual.color}80, ${visual.color})`,
                    borderRadius: 2,
                  }}
                />
              </div>

              {/* Weight */}
              <div style={{ fontSize: 8, color: '#5a6a80', marginTop: 3 }}>
                الوزن: {((brain.weight || 0) * 100).toFixed(0)}%
                {brain.argument && ` • الحجة: ${brain.argument.substring(0, 50)}...`}
              </div>
            </motion.div>
          );
        })}
      </div>

      {isOffline && (
        <div style={{
          fontSize: 10, color: '#FF9800',
          background: 'rgba(255,152,0,0.05)',
          border: '1px solid rgba(255,152,0,0.2)',
          borderRadius: 6, padding: '6px 10px',
        }}>
          ⚠️ البيانات من الذاكرة المحلية — قد لا تكون محدثة
        </div>
      )}
    </div>
  );
}
