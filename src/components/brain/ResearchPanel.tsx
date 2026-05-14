// ═══════════════════════════════════════════════════════════════════
// ResearchPanel — لوحة البحث العميق
// Research progress with live updates
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

interface ResearchPanelProps {
  onBack?: () => void;
}

interface ResearchStep {
  id: string;
  labelAr: string;
  status: 'pending' | 'active' | 'done' | 'error';
  detail?: string;
}

export default function ResearchPanel({ onBack }: ResearchPanelProps) {
  const [steps, setSteps] = useState<ResearchStep[]>([
    { id: '1', labelAr: 'تحليل الاستعلام', status: 'done' },
    { id: '2', labelAr: 'البحث في المصادر', status: 'done' },
    { id: '3', labelAr: 'تحليل النتائج', status: 'active', detail: 'جاري التحليل...' },
    { id: '4', labelAr: 'تكوين الإجابة', status: 'pending' },
    { id: '5', labelAr: 'مراجعة الدماغ السببي', status: 'pending' },
    { id: '6', labelAr: 'التحقق من الحقائق', status: 'pending' },
  ]);

  const [findings, setFindings] = useState<string[]>([
    'تم العثور على 12 مصدر ذي صلة',
    'الإجماع بين المصادر: 78%',
  ]);

  return (
    <div style={{ padding: 16, height: '100%', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Progress Steps */}
      <div style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: 10,
        padding: 16,
      }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#0d7bb5', marginBottom: 12 }}>
          🔍 مراحل البحث
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {steps.map((step, i) => (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '8px 12px',
                background: step.status === 'active'
                  ? 'rgba(13,123,181,0.08)'
                  : 'transparent',
                borderRadius: 6,
                border: step.status === 'active'
                  ? '1px solid rgba(13,123,181,0.2)'
                  : '1px solid transparent',
              }}
            >
              <div style={{
                width: 20, height: 20, borderRadius: '50%',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 10,
                background: step.status === 'done' ? '#69f0ae30'
                  : step.status === 'active' ? '#0d7bb530'
                  : step.status === 'error' ? '#EF444430' : 'rgba(255,255,255,0.04)',
                color: step.status === 'done' ? '#69f0ae'
                  : step.status === 'active' ? '#0d7bb5'
                  : step.status === 'error' ? '#EF4444' : '#5a6a80',
              }}>
                {step.status === 'done' ? '✓' : step.status === 'active' ? '◉' : step.status === 'error' ? '✗' : (i + 1)}
              </div>
              <span style={{
                fontSize: 11,
                color: step.status === 'done' ? '#69f0ae' : step.status === 'active' ? '#c8d0e0' : '#5a6a80',
                fontWeight: step.status === 'active' ? 600 : 400,
              }}>
                {step.labelAr}
              </span>
              {step.detail && (
                <span style={{ fontSize: 9, color: '#5a6a80', flex: 1, textAlign: 'left' }}>
                  {step.detail}
                </span>
              )}
            </motion.div>
          ))}
        </div>
      </div>

      {/* Findings */}
      <div style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: 10,
        padding: 16,
      }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#0a9b8a', marginBottom: 12 }}>
          📋 النتائج الأولية
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {findings.map((finding, i) => (
            <div key={i} style={{
              fontSize: 11, color: '#c8d0e0',
              padding: '6px 10px',
              background: 'rgba(255,255,255,0.02)',
              borderRadius: 6,
              borderRight: '3px solid #0a9b8a',
            }}>
              {finding}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
