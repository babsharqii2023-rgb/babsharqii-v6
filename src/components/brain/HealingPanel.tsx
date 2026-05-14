// ═══════════════════════════════════════════════════════════════════
// HealingPanel — لوحة الإصلاح الذاتي (v62 CONNECTED)
// Self-healing diagnostics panel — NOW CONNECTED TO REAL BACKEND APIs
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState, useEffect, useCallback } from 'react';
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
  const [checks, setChecks] = useState<DiagnosticCheck[]>([]);
  const [healing, setHealing] = useState(false);
  const [healLog, setHealLog] = useState<string[]>([]);
  const [lastCheck, setLastCheck] = useState<number>(0);
  const [overallStatus, setOverallStatus] = useState<string>('checking');

  // Run real health check from backend
  const runDiagnostics = useCallback(async () => {
    setChecks([
      { id: 'health', nameAr: 'فحص صحة الخادم', status: 'checking' },
      { id: 'brains', nameAr: 'أدمغة الذكاء الاصطناعي', status: 'checking' },
      { id: 'neural_bus', nameAr: 'الناقل العصبي', status: 'checking' },
      { id: 'kernel', nameAr: 'نواة مأمون', status: 'checking' },
      { id: 'api', nameAr: 'واجهة البرمجة', status: 'checking' },
      { id: 'healing', nameAr: 'نظام الإصلاح الذاتي', status: 'checking' },
    ]);

    const results: DiagnosticCheck[] = [];

    // Check 1: Backend health
    try {
      const res = await fetch('/api/mamoun/health');
      if (res.ok) {
        const data = await res.json();
        results.push({ id: 'health', nameAr: 'فحص صحة الخادم', status: 'healthy', detail: `v${data.version || 'active'}` });
      } else {
        results.push({ id: 'health', nameAr: 'فحص صحة الخادم', status: 'error', detail: `HTTP ${res.status}` });
      }
    } catch {
      results.push({ id: 'health', nameAr: 'فحص صحة الخادم', status: 'error', detail: 'غير متصل' });
    }

    // Check 2: Brains
    try {
      const res = await fetch('/api/mamoun/brains/status');
      if (res.ok) {
        const data = await res.json();
        const brainCount = data.brains ? Object.keys(data.brains).length : 0;
        results.push({ id: 'brains', nameAr: 'أدمغة الذكاء الاصطناعي', status: brainCount > 0 ? 'healthy' : 'warning', detail: `${brainCount} أدمغة` });
      } else {
        results.push({ id: 'brains', nameAr: 'أدمغة الذكاء الاصطناعي', status: 'warning', detail: 'لا يمكن الوصول' });
      }
    } catch {
      results.push({ id: 'brains', nameAr: 'أدمغة الذكاء الاصطناعي', status: 'warning', detail: 'غير متصل' });
    }

    // Check 3: Neural Bus
    try {
      const res = await fetch('/api/mamoun/v23/neural-bus/status');
      if (res.ok) {
        const data = await res.json();
        results.push({ id: 'neural_bus', nameAr: 'الناقل العصبي', status: 'healthy', detail: 'نشط' });
      } else {
        results.push({ id: 'neural_bus', nameAr: 'الناقل العصبي', status: 'warning', detail: `HTTP ${res.status}` });
      }
    } catch {
      results.push({ id: 'neural_bus', nameAr: 'الناقل العصبي', status: 'warning', detail: 'غير متصل' });
    }

    // Check 4: Kernel
    try {
      const res = await fetch('/api/mamoun/kernel/status');
      if (res.ok) {
        const data = await res.json();
        results.push({ id: 'kernel', nameAr: 'نواة مأمون', status: 'healthy', detail: data.status || 'نشط' });
      } else {
        results.push({ id: 'kernel', nameAr: 'نواة مأمون', status: 'warning', detail: `HTTP ${res.status}` });
      }
    } catch {
      results.push({ id: 'kernel', nameAr: 'نواة مأمون', status: 'warning', detail: 'غير متصل' });
    }

    // Check 5: API Routes
    try {
      const res = await fetch('/api/mamoun/health');
      const latency = res.headers.get('x-response-time');
      results.push({ id: 'api', nameAr: 'واجهة البرمجة', status: res.ok ? 'healthy' : 'error', detail: res.ok ? `استجابة ${latency || 'جيدة'}` : `خطأ ${res.status}` });
    } catch {
      results.push({ id: 'api', nameAr: 'واجهة البرمجة', status: 'error', detail: 'غير متصل' });
    }

    // Check 6: Self-Healing system
    try {
      const res = await fetch('/api/mamoun/v23/healing/status');
      if (res.ok) {
        const data = await res.json();
        results.push({ id: 'healing', nameAr: 'نظام الإصلاح الذاتي', status: 'healthy', detail: data.status || 'جاهز' });
      } else {
        results.push({ id: 'healing', nameAr: 'نظام الإصلاح الذاتي', status: 'warning', detail: 'لا يمكن الوصول' });
      }
    } catch {
      results.push({ id: 'healing', nameAr: 'نظام الإصلاح الذاتي', status: 'warning', detail: 'غير متصل' });
    }

    setChecks(results);
    setLastCheck(Date.now());
    
    const hasError = results.some(r => r.status === 'error');
    const hasWarning = results.some(r => r.status === 'warning');
    setOverallStatus(hasError ? 'error' : hasWarning ? 'warning' : 'healthy');
  }, []);

  useEffect(() => {
    runDiagnostics();
    // Auto-refresh every 30s
    const interval = setInterval(runDiagnostics, 30000);
    return () => clearInterval(interval);
  }, [runDiagnostics]);

  // Real healing via backend API
  const handleHeal = async () => {
    setHealing(true);
    setHealLog([]);
    
    try {
      // Step 1: Trigger health check
      setHealLog(prev => [...prev, '🔍 جاري فحص المكونات...']);
      const checkRes = await fetch('/api/mamoun/v23/healing/check', { method: 'POST' });
      const checkData = checkRes.ok ? await checkRes.json() : null;
      
      await new Promise(r => setTimeout(r, 500));
      setHealLog(prev => [...prev, `📋 تم العثور على ${checkData?.issues_found || 0} مشاكل`]);
      
      // Step 2: Trigger healing for each issue
      if (checkData?.issues && checkData.issues.length > 0) {
        for (const issue of checkData.issues) {
          setHealLog(prev => [...prev, `🔧 إصلاح: ${issue.message || issue.component}...`]);
          
          try {
            const healRes = await fetch('/api/mamoun/v23/healing/trigger', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ component: issue.component }),
            });
            
            if (healRes.ok) {
              setHealLog(prev => [...prev, `  ✓ تم إصلاح ${issue.component}`]);
            } else {
              setHealLog(prev => [...prev, `  ⚠ لم يتم إصلاح ${issue.component}`]);
            }
          } catch {
            setHealLog(prev => [...prev, `  ✗ فشل الاتصال لإصلاح ${issue.component}`]);
          }
          
          await new Promise(r => setTimeout(r, 300));
        }
      } else {
        setHealLog(prev => [...prev, '💚 النظام بحالة جيدة — لا توجد مشاكل تحتاج إصلاح']);
      }
      
      setHealLog(prev => [...prev, '✅ اكتملت دورة الإصلاح الذاتي']);
      
      // Re-run diagnostics to update status
      await runDiagnostics();
    } catch (error) {
      setHealLog(prev => [...prev, `❌ خطأ: ${error instanceof Error ? error.message : 'غير معروف'}`]);
    }
    
    setHealing(false);
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
      {/* Status Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: statusColors[overallStatus] }}>
          {overallStatus === 'healthy' ? '💚' : overallStatus === 'warning' ? '💛' : '❤️'} تشخيصات النظام
        </div>
        {lastCheck > 0 && (
          <div style={{ fontSize: 9, color: '#5a6a80' }}>
            آخر فحص: {new Date(lastCheck).toLocaleTimeString('ar-SA')}
          </div>
        )}
      </div>

      {/* Diagnostics */}
      <div style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: 10,
        padding: 16,
      }}>
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

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={handleHeal}
          disabled={healing}
          style={{
            flex: 1,
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
        <button
          onClick={runDiagnostics}
          disabled={healing}
          style={{
            padding: '10px 16px',
            background: 'rgba(100,150,255,0.1)',
            border: '1px solid rgba(100,150,255,0.2)',
            borderRadius: 8,
            color: '#6496ff',
            fontSize: 12,
            fontWeight: 600,
            cursor: healing ? 'default' : 'pointer',
            opacity: healing ? 0.5 : 1,
            transition: 'all 0.2s',
          }}
        >
          ⟳ إعادة الفحص
        </button>
      </div>

      {/* Heal Log */}
      {healLog.length > 0 && (
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: 8,
          padding: 12,
          fontFamily: 'monospace',
          fontSize: 10,
          maxHeight: 200,
          overflow: 'auto',
        }}>
          {healLog.map((log, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              style={{ color: log.startsWith('✗') || log.startsWith('❌') ? '#EF4444' : '#69f0ae', marginBottom: 4 }}
            >
              {log}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
