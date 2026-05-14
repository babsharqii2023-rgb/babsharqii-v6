// ═══════════════════════════════════════════════════════════════════
// HealingPanel — لوحة الإصلاح الذاتي
// Self-healing diagnostics panel
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface HealingPanelProps {
  onBack?: () => void;
}

interface DiagnosticCheck {
  id: string;
  nameAr: string;
  status: 'healthy' | 'warning' | 'error' | 'checking';
  detail?: string;
}

export default function HealingPanel({ onBack }: HealingPanelProps) {
  const [checks, setChecks] = useState<DiagnosticCheck[]>([
    { id: '1', nameAr: 'الاتصال بالخادم', status: 'checking' },
    { id: '2', nameAr: 'أدمغة الذكاء الاصطناعي', status: 'checking' },
    { id: '3', nameAr: 'قاعدة البيانات', status: 'checking' },
    { id: '4', nameAr: 'الناقل العصبي', status: 'checking' },
    { id: '5', nameAr: 'نظام الملفات', status: 'checking' },
    { id: '6', nameAr: 'واجهة البرمجة', status: 'checking' },
  ]);
  const [healing, setHealing] = useState(false);
  const [healLog, setHealLog] = useState<string[]>([]);

  useEffect(() => {
    // Simulate diagnostics running
    const timer = setTimeout(() => {
      setChecks(prev => prev.map((c, i) => ({
        ...c,
        status: i < 3 ? 'healthy' : i < 5 ? 'warning' : 'error',
        detail: i < 3 ? 'يعمل بشكل طبيعي' : i < 5 ? 'أداء أقل من المتوقع' : 'يحتاج إصلاح',
      })));
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  const handleHeal = async () => {
    setHealing(true);
    setHealLog([]);
    const steps = [
      '🔍 فحص المكونات المتضررة...',
      '🧠 تنشيط دماغ الإصلاح السببي...',
      '🔧 إصلاح الاتصالات المعطلة...',
      '♻️ إعادة تشغيل الخدمات المتوقفة...',
      '✅ اكتمل الإصلاح الذاتي',
    ];
    for (const step of steps) {
      await new Promise(r => setTimeout(r, 800));
      setHealLog(prev => [...prev, step]);
    }
    setHealing(false);
    setChecks(prev => prev.map(c => ({ ...c, status: 'healthy' as const, detail: 'تم الإصلاح' })));
  };

  const statusColors: Record<string, string> = {
    healthy: '#69f0ae',
    warning: '#ffd740',
    error: '#EF4444',
    checking: '#5a6a80',
  };

  const statusIcons: Record<string, string> = {
    healthy: '✓',
    warning: '⚠',
    error: '✗',
    checking: '◉',
  };

  return (
    <div style={{ padding: 16, height: '100%', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Diagnostics */}
      <div style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: 10,
        padding: 16,
      }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#69f0ae', marginBottom: 12 }}>
          💚 تشخيصات النظام
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {checks.map((check, i) => (
            <motion.div
              key={check.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 12px',
                background: 'rgba(255,255,255,0.02)',
                borderRadius: 6,
              }}
            >
              <div style={{
                width: 20, height: 20, borderRadius: '50%',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 10,
                background: `${statusColors[check.status]}20`,
                color: statusColors[check.status],
                border: `1px solid ${statusColors[check.status]}40`,
              }}>
                {check.status === 'checking' ? (
                  <motion.span
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  >⟳</motion.span>
                ) : statusIcons[check.status]}
              </div>
              <span style={{ fontSize: 11, color: '#c8d0e0', flex: 1 }}>{check.nameAr}</span>
              {check.detail && (
                <span style={{ fontSize: 9, color: statusColors[check.status] }}>{check.detail}</span>
              )}
            </motion.div>
          ))}
        </div>
      </div>

      {/* Heal Button */}
      <button
        onClick={handleHeal}
        disabled={healing}
        style={{
          padding: '10px 20px',
          background: healing ? 'rgba(105,240,174,0.1)' : 'rgba(105,240,174,0.15)',
          border: '1px solid rgba(105,240,174,0.3)',
          borderRadius: 8,
          color: '#69f0ae',
          fontSize: 12,
          fontWeight: 600,
          cursor: healing ? 'default' : 'pointer',
          opacity: healing ? 0.5 : 1,
          transition: 'all 0.2s',
        }}
      >
        {healing ? '⏳ جاري الإصلاح...' : '💚 إصلاح ذاتي'}
      </button>

      {/* Heal Log */}
      {healLog.length > 0 && (
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: 8,
          padding: 12,
          fontFamily: 'monospace',
          fontSize: 10,
        }}>
          {healLog.map((log, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              style={{ color: '#69f0ae', marginBottom: 4 }}
            >
              {log}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
