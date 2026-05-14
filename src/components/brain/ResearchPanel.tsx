// ═══════════════════════════════════════════════════════════════════
// ResearchPanel — لوحة البحث العميق (v62 CONNECTED)
// Deep research panel — NOW CONNECTED TO REAL BACKEND API
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';

interface ResearchPanelProps {
  onBack?: () => void;
}

interface ResearchStep {
  label: string;
  status: 'pending' | 'running' | 'done' | 'failed';
}

interface ResearchFinding {
  text: string;
  confidence: number;
  verification: string;
}

export default function ResearchPanel({ onBack }: ResearchPanelProps) {
  const [query, setQuery] = useState('');
  const [depth, setDepth] = useState(3);
  const [researching, setResearching] = useState(false);
  const [steps, setSteps] = useState<ResearchStep[]>([]);
  const [findings, setFindings] = useState<ResearchFinding[]>([]);
  const [summary, setSummary] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const handleResearch = async () => {
    if (!query.trim()) return;
    
    setResearching(true);
    setError(null);
    setFindings([]);
    setSummary('');
    
    const researchSteps: ResearchStep[] = [
      { label: 'البحث عن مصادر', status: 'pending' },
      { label: 'استخراج المحتوى', status: 'pending' },
      { label: 'تحليل المصادر', status: 'pending' },
      { label: 'التحقق من الحقائق', status: 'pending' },
      { label: 'تجميع التقرير', status: 'pending' },
    ];
    setSteps(researchSteps);

    try {
      // Step 1: Search
      setSteps(prev => prev.map((s, i) => i === 0 ? { ...s, status: 'running' } : s));
      
      const res = await fetch('/api/mamoun/research/deep', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, depth, verify: true }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();
      
      // Update all steps based on response
      if (data.status === 'success' && data.report) {
        setSteps(prev => prev.map(s => ({ ...s, status: 'done' as const })));
        
        // Extract findings
        const reportFindings = data.report.key_findings || [];
        const claims = data.report.claims || [];
        
        const mappedFindings: ResearchFinding[] = [
          ...reportFindings.map((f: string) => ({
            text: f,
            confidence: data.report.confidence || 0.5,
            verification: 'verified',
          })),
          ...claims.map((c: any) => ({
            text: c.claim,
            confidence: c.confidence || 0.5,
            verification: c.verification || 'unverified',
          })),
        ];
        
        setFindings(mappedFindings);
        setSummary(data.report.summary || '');
      } else {
        const errMsg = data.message || 'فشل البحث';
        setError(errMsg);
        setSteps(prev => prev.map((s, i) => i < 2 ? { ...s, status: 'done' } : { ...s, status: 'failed' }));
      }
    } catch (err) {
      setError(`فشل البحث: ${err instanceof Error ? err.message : 'غير معروف'}`);
      setSteps(prev => prev.map((s, i) => s.status === 'running' ? { ...s, status: 'failed' } : s));
    }

    setResearching(false);
  };

  const depthLabels: Record<number, string> = {
    1: 'سريع',
    2: 'قياسي',
    3: 'عميق',
    4: 'شامل',
  };

  return (
    <div style={{ padding: 16, height: '100%', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Header */}
      <div style={{ fontSize: 13, fontWeight: 700, color: '#818cf8' }}>
        🔬 بحث عميق
      </div>

      {/* Query Input */}
      <div>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="ادخل سؤال البحث..."
          onKeyDown={e => e.key === 'Enter' && handleResearch()}
          style={{
            width: '100%', padding: '10px 14px',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 8, color: '#c8d0e0',
            fontSize: 12, outline: 'none',
          }}
        />
      </div>

      {/* Depth Selector */}
      <div style={{ display: 'flex', gap: 6 }}>
        {[1, 2, 3, 4].map(d => (
          <button
            key={d}
            onClick={() => setDepth(d)}
            style={{
              flex: 1, padding: '6px 4px',
              background: depth === d ? 'rgba(129,140,248,0.2)' : 'rgba(255,255,255,0.02)',
              border: `1px solid ${depth === d ? 'rgba(129,140,248,0.4)' : 'rgba(255,255,255,0.06)'}`,
              borderRadius: 6, cursor: 'pointer',
              fontSize: 9, color: depth === d ? '#818cf8' : '#5a6a80',
              fontWeight: depth === d ? 700 : 400,
            }}
          >
            {depthLabels[d]}
          </button>
        ))}
      </div>

      {/* Search Button */}
      <button
        onClick={handleResearch}
        disabled={researching || !query.trim()}
        style={{
          padding: '10px 20px',
          background: researching ? 'rgba(129,140,248,0.1)' : 'rgba(129,140,248,0.2)',
          border: '1px solid rgba(129,140,248,0.4)',
          borderRadius: 8, color: '#818cf8',
          fontSize: 12, fontWeight: 700,
          cursor: researching ? 'default' : 'pointer',
          opacity: researching || !query.trim() ? 0.5 : 1,
        }}
      >
        {researching ? '⏳ جاري البحث...' : '🔍 بدء البحث العميق'}
      </button>

      {/* Steps */}
      {steps.length > 0 && (
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: 8, padding: 10,
        }}>
          {steps.map((step, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span style={{
                fontSize: 9,
                color: step.status === 'done' ? '#69f0ae' : step.status === 'running' ? '#ffd740' : step.status === 'failed' ? '#EF4444' : '#5a6a80',
              }}>
                {step.status === 'running' ? '⟳' : step.status === 'done' ? '✓' : step.status === 'failed' ? '✗' : '○'}
              </span>
              <span style={{ fontSize: 9, color: '#c8d0e0' }}>{step.label}</span>
            </div>
          ))}
        </div>
      )}

      {/* Error */}
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

      {/* Summary */}
      {summary && (
        <div style={{
          background: 'rgba(129,140,248,0.1)',
          border: '1px solid rgba(129,140,248,0.2)',
          borderRadius: 8, padding: 12,
        }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#818cf8', marginBottom: 6 }}>
            📋 ملخص البحث
          </div>
          <div style={{ fontSize: 10, color: '#c8d0e0', lineHeight: 1.6 }}>
            {summary}
          </div>
        </div>
      )}

      {/* Findings */}
      {findings.length > 0 && (
        <div style={{
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: 8, padding: 12,
        }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#69f0ae', marginBottom: 8 }}>
            🔑 النتائج الرئيسية ({findings.length})
          </div>
          {findings.map((finding, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              style={{
                padding: '6px 8px',
                marginBottom: 4,
                background: 'rgba(255,255,255,0.02)',
                borderRadius: 4,
                borderRight: `3px solid ${finding.verification === 'verified' ? '#69f0ae' : finding.verification === 'disputed' ? '#ffd740' : '#5a6a80'}`,
              }}
            >
              <div style={{ fontSize: 9, color: '#c8d0e0' }}>{finding.text}</div>
              <div style={{ fontSize: 8, color: '#5a6a80', marginTop: 2 }}>
                ثقة: {Math.round(finding.confidence * 100)}% | {finding.verification === 'verified' ? 'متحقق' : finding.verification === 'disputed' ? 'متنازع' : 'غير متحقق'}
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
