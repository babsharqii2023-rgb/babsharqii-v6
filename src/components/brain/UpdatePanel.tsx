// ═══════════════════════════════════════════════════════════════════
// UpdatePanel — لوحة التحديث الذاتي
// Shows system update status, commit history, and progress
// Displays download progress with animation
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface UpdatePanelProps {
  status?: string;
  newCommit?: string;
  elapsedSeconds?: number;
  hadLocalChanges?: boolean;
  conflictsResolved?: boolean;
  isUpdating?: boolean;
  currentCommit?: string;
  _isOffline?: boolean;
  onBack?: () => void;
  [key: string]: unknown;
}

export default function UpdatePanel(props: UpdatePanelProps) {
  const isOffline = props._isOffline || false;
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState<string>(
    props.status === 'success' ? 'مكتمل'
    : props.status === 'up_to_date' ? 'محدث'
    : props.status === 'offline' ? 'غير متصل'
    : 'جاري الفحص'
  );

  // Animate progress if updating
  useEffect(() => {
    if (props.isUpdating || props.status === 'updating') {
      const iv = setInterval(() => {
        setProgress(p => {
          if (p >= 95) return p;
          return p + Math.random() * 8;
        });
      }, 500);
      return () => clearInterval(iv);
    }
    if (props.status === 'success' || props.status === 'up_to_date') {
      setProgress(100);
    }
  }, [props.status, props.isUpdating]);

  const statusColor = phase === 'مكتمل' || phase === 'محدث' ? '#4CAF50'
    : phase === 'غير متصل' ? '#EF4444' : '#0d7bb5';

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', padding: 16, gap: 14,
      color: '#c8d0e0', fontFamily: "'Cairo', system-ui, sans-serif",
      overflow: 'auto',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <motion.div
          animate={progress < 100 ? { rotate: 360 } : {}}
          transition={progress < 100 ? { duration: 2, repeat: Infinity, ease: 'linear' } : {}}
          style={{ fontSize: 24 }}
        >
          🔄
        </motion.div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>التحديث الذاتي</div>
          <div style={{ fontSize: 10, color: '#5a6a80' }}>
            سحب التحديثات من GitHub
          </div>
        </div>
        <div style={{
          marginRight: 'auto',
          background: `${statusColor}15`,
          border: `1px solid ${statusColor}40`,
          borderRadius: 8, padding: '4px 10px',
          fontSize: 11, fontWeight: 600, color: statusColor,
        }}>
          {phase}
        </div>
      </div>

      {/* Progress Bar */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 10, color: '#5a6a80' }}>التقدم</span>
          <span style={{ fontSize: 10, color: statusColor, fontWeight: 600 }}>
            {Math.round(progress)}%
          </span>
        </div>
        <div style={{
          height: 6, background: 'rgba(255,255,255,0.04)',
          borderRadius: 3, overflow: 'hidden',
        }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
            style={{
              height: '100%',
              background: `linear-gradient(90deg, ${statusColor}80, ${statusColor})`,
              borderRadius: 3,
            }}
          />
        </div>
      </div>

      {/* Update Details */}
      <div style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: 10, padding: 14,
        display: 'flex', flexDirection: 'column', gap: 10,
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#0d7bb5', marginBottom: 4 }}>
          تفاصيل التحديث
        </div>

        {[
          { label: 'الحالة', value: phase, color: statusColor },
          { label: 'Commit الجديد', value: props.newCommit || 'لا يوجد', color: '#c8d0e0' },
          { label: 'الوقت المستغرق', value: props.elapsedSeconds ? `${props.elapsedSeconds} ثانية` : '-', color: '#c8d0e0' },
          { label: 'تعديلات محلية', value: props.hadLocalChanges ? 'نعم — تم الحفظ' : 'لا', color: props.hadLocalChanges ? '#FF9800' : '#4CAF50' },
          { label: 'تعارضات حُلت', value: props.conflictsResolved ? 'نعم — تلقائياً' : 'لا', color: props.conflictsResolved ? '#FF9800' : '#4CAF50' },
          { label: 'Commit الحالي', value: props.currentCommit || 'غير معروف', color: '#5a6a80' },
        ].map((item, i) => (
          <div key={i} style={{
            display: 'flex', justifyContent: 'space-between',
            fontSize: 11, padding: '2px 0',
            borderBottom: '1px solid rgba(255,255,255,0.03)',
          }}>
            <span style={{ color: '#5a6a80' }}>{item.label}</span>
            <span style={{ color: item.color, fontWeight: 600, fontFamily: 'monospace' }}>
              {item.value}
            </span>
          </div>
        ))}
      </div>

      {/* Update Steps */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#0d7bb5', marginBottom: 8 }}>
          مراحل التحديث
        </div>
        {[
          { label: 'فحص التحديثات', done: progress > 10, icon: '🔍' },
          { label: 'سحب التغييرات', done: progress > 40, icon: '📥' },
          { label: 'حل التعارضات', done: progress > 70, icon: '🔧' },
          { label: 'إعادة البناء', done: progress > 90, icon: '🔨' },
          { label: 'إعادة التشغيل', done: progress >= 100, icon: '✅' },
        ].map((step, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '4px 0', fontSize: 11,
            color: step.done ? '#4CAF50' : '#5a6a80',
          }}>
            <span style={{ fontSize: 12 }}>{step.done ? '✅' : step.icon}</span>
            <span style={{ fontWeight: step.done ? 600 : 400 }}>{step.label}</span>
          </div>
        ))}
      </div>

      {isOffline && (
        <div style={{
          fontSize: 10, color: '#FF9800',
          background: 'rgba(255,152,0,0.05)',
          border: '1px solid rgba(255,152,0,0.2)',
          borderRadius: 6, padding: '6px 10px',
        }}>
          ⚠️ الخادم غير متصل — لن يتم التحديث حتى يتم الاتصال
        </div>
      )}
    </div>
  );
}
