// ═══════════════════════════════════════════════════════════════════
// TerminalPanel — لوحة الطرفية
// Terminal emulator with command input/output
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';

interface TerminalPanelProps {
  onBack?: () => void;
}

interface TerminalLine {
  id: string;
  type: 'input' | 'output' | 'error' | 'system';
  content: string;
  timestamp: number;
}

export default function TerminalPanel({ onBack }: TerminalPanelProps) {
  const [lines, setLines] = useState<TerminalLine[]>([
    { id: 'sys-1', type: 'system', content: 'مأمون v61 — العقل الخارق — الطرفية', timestamp: Date.now() },
    { id: 'sys-2', type: 'system', content: 'اكتب "مساعدة" لعرض الأوامر المتاحة', timestamp: Date.now() },
  ]);
  const [input, setInput] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines]);

  const executeCommand = useCallback(async (cmd: string) => {
    const cmdLine: TerminalLine = {
      id: `in-${Date.now()}`,
      type: 'input',
      content: cmd,
      timestamp: Date.now(),
    };
    setLines(prev => [...prev, cmdLine]);

    if (cmd.trim() === 'مساعدة' || cmd.trim() === 'help') {
      setLines(prev => [...prev, {
        id: `out-${Date.now()}`,
        type: 'output',
        content: 'الأوامر المتاحة:\n  حالة — عرض حالة النظام\n  أدمغة — عرض حالة الأدمغة\n  مشاريع — عرض المشاريع\n  صحة — فحص صحة النظام\n  مسح — مسح الشاشة',
        timestamp: Date.now(),
      }]);
      return;
    }

    if (cmd.trim() === 'مسح' || cmd.trim() === 'clear') {
      setLines([]);
      return;
    }

    setIsExecuting(true);
    try {
      const resp = await fetch('/api/terminal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd }),
      });
      const data = await resp.json().catch(() => ({ output: 'فشل الاتصال بالخادم' }));
      setLines(prev => [...prev, {
        id: `out-${Date.now()}`,
        type: data.exit_code === 0 ? 'output' : 'error',
        content: data.output || data.message || 'لا يوجد مخرج',
        timestamp: Date.now(),
      }]);
    } catch {
      setLines(prev => [...prev, {
        id: `err-${Date.now()}`,
        type: 'error',
        content: 'خطأ: فشل الاتصال بالخادم',
        timestamp: Date.now(),
      }]);
    }
    setIsExecuting(false);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && input.trim() && !isExecuting) {
      executeCommand(input.trim());
      setInput('');
    }
  }, [input, isExecuting, executeCommand]);

  const lineColor = (type: TerminalLine['type']) => {
    switch (type) {
      case 'input': return '#0d7bb5';
      case 'output': return '#c8d0e0';
      case 'error': return '#EF4444';
      case 'system': return '#0a9b8a';
    }
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', background: '#050510',
      fontFamily: "'Fira Code', 'Courier New', monospace",
    }}>
      {/* Terminal output */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '12px 16px',
        display: 'flex', flexDirection: 'column', gap: 2,
      }}>
        {lines.map(line => (
          <motion.div
            key={line.id}
            initial={{ opacity: 0, x: -5 }}
            animate={{ opacity: 1, x: 0 }}
            style={{
              fontSize: 11,
              color: lineColor(line.type),
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              lineHeight: 1.6,
            }}
          >
            {line.type === 'input' && (
              <span style={{ color: '#0a9b8a', fontWeight: 700 }}>مأمون $ </span>
            )}
            {line.content}
          </motion.div>
        ))}
        {isExecuting && (
          <motion.div
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity }}
            style={{ fontSize: 11, color: '#0d7bb5' }}
          >
            ▌ جاري التنفيذ...
          </motion.div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Input */}
      <div style={{
        display: 'flex', alignItems: 'center',
        padding: '8px 16px',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        background: 'rgba(0,0,0,0.3)',
      }}>
        <span style={{ color: '#0a9b8a', fontWeight: 700, fontSize: 11, marginLeft: 8 }}>مأمون $</span>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="اكتب أمراً..."
          disabled={isExecuting}
          dir="ltr"
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            color: '#c8d0e0',
            fontSize: 11,
            outline: 'none',
            fontFamily: 'inherit',
          }}
        />
      </div>
    </div>
  );
}
