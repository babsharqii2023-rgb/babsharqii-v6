'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface ProgressBarProps {
  label: string;
  value: number;  // 0-100
  color?: string;
  showPercent?: boolean;
}

export default function ProgressBar({ label, value, color = '#0d7bb5', showPercent = true }: ProgressBarProps) {
  const clampedValue = Math.max(0, Math.min(100, value));

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      style={{ display: 'flex', flexDirection: 'column', gap: 6 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: '#c8d0e0', fontSize: 13, fontWeight: 500 }}>{label}</span>
        {showPercent && (
          <span style={{ color: '#5a6a80', fontSize: 12, fontFamily: 'monospace' }}>{clampedValue}%</span>
        )}
      </div>
      <div style={{
        width: '100%',
        height: 8,
        background: 'rgba(255,255,255,0.08)',
        borderRadius: 4,
        overflow: 'hidden',
      }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${clampedValue}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          style={{
            height: '100%',
            background: `linear-gradient(90deg, ${color}, ${color}cc)`,
            borderRadius: 4,
            boxShadow: `0 0 8px ${color}44`,
          }}
        />
      </div>
    </motion.div>
  );
}
