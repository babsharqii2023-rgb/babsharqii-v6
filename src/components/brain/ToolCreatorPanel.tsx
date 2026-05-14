// ═══════════════════════════════════════════════════════════════════
// ToolCreatorPanel — منشئ الأدوات
// Tool creation wizard
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface ToolCreatorPanelProps {
  onBack?: () => void;
}

export default function ToolCreatorPanel({ onBack }: ToolCreatorPanelProps) {
  const [step, setStep] = useState(0);
  const [toolName, setToolName] = useState('');
  const [toolDesc, setToolDesc] = useState('');
  const [toolType, setToolType] = useState('web_search');
  const [creating, setCreating] = useState(false);

  const toolTypes = [
    { id: 'web_search', labelAr: 'بحث ويب', icon: '🔍' },
    { id: 'code_gen', labelAr: 'توليد كود', icon: '⌨️' },
    { id: 'data_analysis', labelAr: 'تحليل بيانات', icon: '📊' },
    { id: 'api_connector', labelAr: 'رابط API', icon: '🔗' },
    { id: 'file_manager', labelAr: 'إدارة ملفات', icon: '📁' },
    { id: 'custom', labelAr: 'مخصص', icon: '⚙️' },
  ];

  return (
    <div style={{ padding: 16, height: '100%', overflow: 'auto' }}>
      {/* Step Indicator */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20 }}>
        {['النوع', 'التفاصيل', 'الإنشاء'].map((s, i) => (
          <div key={s} style={{
            flex: 1, height: 4, borderRadius: 2,
            background: i <= step ? '#0d7bb5' : 'rgba(255,255,255,0.06)',
          }} />
        ))}
      </div>

      {step === 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#0d7bb5', marginBottom: 16 }}>
            اختر نوع الأداة
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
            {toolTypes.map(t => (
              <button
                key={t.id}
                onClick={() => { setToolType(t.id); setStep(1); }}
                style={{
                  background: toolType === t.id ? 'rgba(13,123,181,0.15)' : 'rgba(255,255,255,0.03)',
                  border: toolType === t.id ? '1px solid #0d7bb5' : '1px solid rgba(255,255,255,0.06)',
                  borderRadius: 8,
                  padding: 16,
                  cursor: 'pointer',
                  textAlign: 'center',
                  color: '#c8d0e0',
                }}
              >
                <div style={{ fontSize: 28, marginBottom: 6 }}>{t.icon}</div>
                <div style={{ fontSize: 11 }}>{t.labelAr}</div>
              </button>
            ))}
          </div>
        </motion.div>
      )}

      {step === 1 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#0d7bb5', marginBottom: 16 }}>
            تفاصيل الأداة
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label style={{ fontSize: 10, color: '#5a6a80', marginBottom: 4, display: 'block' }}>اسم الأداة</label>
              <input
                value={toolName}
                onChange={e => setToolName(e.target.value)}
                placeholder="أدخل اسم الأداة"
                dir="rtl"
                style={{
                  width: '100%', background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 8, padding: '10px 12px',
                  color: '#c8d0e0', fontSize: 12, outline: 'none',
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: 10, color: '#5a6a80', marginBottom: 4, display: 'block' }}>وصف الأداة</label>
              <textarea
                value={toolDesc}
                onChange={e => setToolDesc(e.target.value)}
                placeholder="ماذا تفعل هذه الأداة؟"
                dir="rtl"
                rows={3}
                style={{
                  width: '100%', background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 8, padding: '10px 12px',
                  color: '#c8d0e0', fontSize: 12, outline: 'none',
                  resize: 'vertical',
                }}
              />
            </div>
            <button
              onClick={() => setStep(2)}
              disabled={!toolName.trim()}
              style={{
                padding: '10px 20px',
                background: '#0d7bb5',
                border: 'none',
                borderRadius: 8,
                color: '#fff',
                fontSize: 12,
                fontWeight: 600,
                cursor: toolName.trim() ? 'pointer' : 'default',
                opacity: toolName.trim() ? 1 : 0.4,
              }}
            >
              التالي ←
            </button>
          </div>
        </motion.div>
      )}

      {step === 2 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#0d7bb5', marginBottom: 16 }}>
            إنشاء الأداة
          </div>
          <div style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: 10,
            padding: 16,
            marginBottom: 16,
          }}>
            <div style={{ fontSize: 11, color: '#5a6a80', marginBottom: 6 }}>النوع: {toolTypes.find(t => t.id === toolType)?.icon} {toolTypes.find(t => t.id === toolType)?.labelAr}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#c8d0e0', marginBottom: 4 }}>{toolName}</div>
            <div style={{ fontSize: 11, color: '#5a6a80' }}>{toolDesc}</div>
          </div>
          <button
            onClick={async () => {
              setCreating(true);
              await new Promise(r => setTimeout(r, 2000));
              setCreating(false);
            }}
            disabled={creating}
            style={{
              padding: '10px 20px',
              background: '#69f0ae',
              border: 'none',
              borderRadius: 8,
              color: '#080810',
              fontSize: 12,
              fontWeight: 700,
              cursor: creating ? 'default' : 'pointer',
              opacity: creating ? 0.5 : 1,
            }}
          >
            {creating ? '⏳ جاري الإنشاء...' : '🔧 إنشاء الأداة'}
          </button>
        </motion.div>
      )}
    </div>
  );
}
