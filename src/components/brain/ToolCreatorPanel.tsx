// ═══════════════════════════════════════════════════════════════════
// ToolCreatorPanel — لوحة إنشاء الأدوات (v62 CONNECTED)
// Tool creation wizard — NOW CONNECTED TO REAL BACKEND API
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface ToolCreatorPanelProps {
  onBack?: () => void;
}

type Step = 'type' | 'details' | 'create';

export default function ToolCreatorPanel({ onBack }: ToolCreatorPanelProps) {
  const [step, setStep] = useState<Step>('type');
  const [toolType, setToolType] = useState('web_search');
  const [toolName, setToolName] = useState('');
  const [toolDescription, setToolDescription] = useState('');
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const toolTypes = [
    { id: 'web_search', label: '🔍 بحث ويب', desc: 'أداة للبحث في الإنترنت' },
    { id: 'code_gen', label: '💻 توليد كود', desc: 'أداة لتوليد أكواد برمجية' },
    { id: 'data_processor', label: '📊 معالجة بيانات', desc: 'أداة لمعالجة وتحليل البيانات' },
    { id: 'api_connector', label: '🔗 ربط API', desc: 'أداة للاتصال بخدمات خارجية' },
    { id: 'file_handler', label: '📁 معالجة ملفات', desc: 'أداة لقراءة وكتابة الملفات' },
    { id: 'custom', label: '⚡ أداة مخصصة', desc: 'أنشئ أداة حسب احتياجك' },
  ];

  const handleCreate = async () => {
    setCreating(true);
    setResult(null);
    setError(null);

    try {
      // Call the real backend evolution/create-tool endpoint
      const res = await fetch('/api/mamoun/evolution/create-tool', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: toolName || `${toolType}_tool`,
          description: toolDescription,
          tool_type: toolType,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setResult(data);
      } else {
        const errorData = await res.json().catch(() => ({}));
        setError(errorData.detail || `خطأ HTTP: ${res.status}`);
      }
    } catch (err) {
      setError(`فشل الاتصال: ${err instanceof Error ? err.message : 'غير معروف'}`);
    }

    setCreating(false);
  };

  return (
    <div style={{ padding: 16, height: '100%', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Step Indicator */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        {['type', 'details', 'create'].map((s, i) => (
          <React.Fragment key={s}>
            <div style={{
              width: 24, height: 24, borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 10, fontWeight: 700,
              background: step === s ? 'rgba(139,92,246,0.3)' : i < ['type', 'details', 'create'].indexOf(step) ? 'rgba(105,240,174,0.2)' : 'rgba(255,255,255,0.05)',
              color: step === s ? '#c084fc' : i < ['type', 'details', 'create'].indexOf(step) ? '#69f0ae' : '#5a6a80',
              border: `1px solid ${step === s ? 'rgba(139,92,246,0.5)' : 'rgba(255,255,255,0.1)'}`,
            }}>
              {i + 1}
            </div>
            {i < 2 && <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.06)' }} />}
          </React.Fragment>
        ))}
      </div>

      {/* Step: Type Selection */}
      {step === 'type' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#c084fc', marginBottom: 4 }}>
            اختر نوع الأداة
          </div>
          {toolTypes.map((t, i) => (
            <motion.button
              key={t.id}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => { setToolType(t.id); setStep('details'); }}
              style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 14px',
                background: toolType === t.id ? 'rgba(139,92,246,0.15)' : 'rgba(255,255,255,0.02)',
                border: `1px solid ${toolType === t.id ? 'rgba(139,92,246,0.4)' : 'rgba(255,255,255,0.06)'}`,
                borderRadius: 8,
                color: '#c8d0e0',
                fontSize: 11,
                cursor: 'pointer',
                textAlign: 'right',
                transition: 'all 0.2s',
              }}
            >
              <span style={{ fontSize: 16 }}>{t.label}</span>
              <span style={{ fontSize: 9, color: '#5a6a80' }}>{t.desc}</span>
            </motion.button>
          ))}
        </div>
      )}

      {/* Step: Details */}
      {step === 'details' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#c084fc' }}>
            تفاصيل الأداة
          </div>
          <div>
            <label style={{ fontSize: 10, color: '#5a6a80', display: 'block', marginBottom: 4 }}>
              اسم الأداة
            </label>
            <input
              value={toolName}
              onChange={e => setToolName(e.target.value)}
              placeholder={`${toolType}_tool`}
              dir="ltr"
              style={{
                width: '100%', padding: '8px 12px',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 6, color: '#c8d0e0',
                fontSize: 11, outline: 'none',
              }}
            />
          </div>
          <div>
            <label style={{ fontSize: 10, color: '#5a6a80', display: 'block', marginBottom: 4 }}>
              وصف الأداة
            </label>
            <textarea
              value={toolDescription}
              onChange={e => setToolDescription(e.target.value)}
              placeholder="صف ما الذي يجب أن تفعله هذه الأداة..."
              rows={3}
              style={{
                width: '100%', padding: '8px 12px',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 6, color: '#c8d0e0',
                fontSize: 11, outline: 'none', resize: 'vertical',
              }}
            />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => setStep('type')}
              style={{
                padding: '8px 16px',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 6, color: '#5a6a80',
                fontSize: 11, cursor: 'pointer',
              }}
            >
              رجوع
            </button>
            <button
              onClick={() => setStep('create')}
              style={{
                flex: 1, padding: '8px 16px',
                background: 'rgba(139,92,246,0.15)',
                border: '1px solid rgba(139,92,246,0.3)',
                borderRadius: 6, color: '#c084fc',
                fontSize: 11, fontWeight: 600, cursor: 'pointer',
              }}
            >
              التالي ← إنشاء
            </button>
          </div>
        </div>
      )}

      {/* Step: Create */}
      {step === 'create' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#c084fc' }}>
            إنشاء الأداة
          </div>
          
          <div style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: 8, padding: 12,
          }}>
            <div style={{ fontSize: 10, color: '#5a6a80', marginBottom: 8 }}>ملخص الأداة</div>
            <div style={{ fontSize: 11, color: '#c8d0e0' }}>
              <div>النوع: {toolTypes.find(t => t.id === toolType)?.label}</div>
              <div>الاسم: {toolName || `${toolType}_tool`}</div>
              <div style={{ fontSize: 9, color: '#5a6a80', marginTop: 4 }}>
                {toolDescription || 'بدون وصف'}
              </div>
            </div>
          </div>

          <button
            onClick={handleCreate}
            disabled={creating}
            style={{
              padding: '12px 20px',
              background: creating ? 'rgba(139,92,246,0.1)' : 'rgba(139,92,246,0.2)',
              border: '1px solid rgba(139,92,246,0.4)',
              borderRadius: 8, color: '#c084fc',
              fontSize: 13, fontWeight: 700,
              cursor: creating ? 'default' : 'pointer',
              opacity: creating ? 0.5 : 1,
            }}
          >
            {creating ? '⏳ جاري الإنشاء...' : '⚡ إنشاء الأداة'}
          </button>

          {error && (
            <div style={{
              background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 6, padding: 8,
              fontSize: 10, color: '#EF4444',
            }}>
              {error}
            </div>
          )}

          {result && (
            <div style={{
              background: 'rgba(105,240,174,0.1)',
              border: '1px solid rgba(105,240,174,0.3)',
              borderRadius: 6, padding: 8,
              fontSize: 10, color: '#69f0ae',
            }}>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>✓ تم إنشاء الأداة بنجاح</div>
              <pre dir="ltr" style={{ fontSize: 9, overflow: 'auto', maxHeight: 100 }}>
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}

          <button
            onClick={() => { setStep('details'); setResult(null); setError(null); }}
            style={{
              padding: '8px 16px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 6, color: '#5a6a80',
              fontSize: 11, cursor: 'pointer',
            }}
          >
            رجوع
          </button>
        </div>
      )}
    </div>
  );
}
