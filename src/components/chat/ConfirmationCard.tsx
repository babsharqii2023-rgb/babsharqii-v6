'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { AutonomyConfig } from '@/lib/autonomy';

interface ConfirmationCardProps {
  action: string;
  description: string;
  autonomyConfig: AutonomyConfig;
  onApprove: () => void;
  onReject: () => void;
  onModify?: () => void;
}

export default function ConfirmationCard({
  action,
  description,
  autonomyConfig,
  onApprove,
  onReject,
  onModify,
}: ConfirmationCardProps) {
  const [timeLeft, setTimeLeft] = useState(
    autonomyConfig.level === 1 ? autonomyConfig.confirmTimeoutMs / 1000 : 0
  );
  const [isExpired, setIsExpired] = useState(false);

  useEffect(() => {
    if (autonomyConfig.level !== 1 || timeLeft <= 0) return;
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          setIsExpired(true);
          onApprove(); // Auto-proceed after timeout for Level 1
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [autonomyConfig, timeLeft, onApprove]);

  if (isExpired) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -10, scale: 0.95 }}
        style={{
          background: '#0d0d1a',
          border: `1px solid ${autonomyConfig.riskColor}44`,
          borderRadius: 16,
          padding: '14px 18px',
          marginBottom: 8,
          boxShadow: `0 0 20px ${autonomyConfig.riskColor}15`,
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: autonomyConfig.riskColor,
              boxShadow: `0 0 8px ${autonomyConfig.riskColor}`,
              animation: 'pulse 2s infinite',
            }} />
            <span style={{ color: autonomyConfig.riskColor, fontSize: 12, fontWeight: 700 }}>
              {autonomyConfig.riskLabel}
            </span>
          </div>
          {autonomyConfig.level === 1 && timeLeft > 0 && (
            <span style={{
              color: '#c8d0e0',
              fontSize: 11,
              fontFamily: 'monospace',
              background: 'rgba(255,255,255,0.08)',
              padding: '2px 8px',
              borderRadius: 8,
            }}>
              ⏱ {timeLeft}ث
            </span>
          )}
        </div>

        {/* Action & Description */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ color: '#c8d0e0', fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{action}</div>
          <div style={{ color: '#5a6a80', fontSize: 12, lineHeight: 1.5 }}>{description}</div>
        </div>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: 8 }}>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onApprove}
            style={{
              padding: '6px 16px',
              borderRadius: 8,
              background: 'rgba(76,175,80,0.15)',
              color: '#4CAF50',
              border: '1px solid rgba(76,175,80,0.3)',
              cursor: 'pointer',
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            ✅ تأكيد
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onReject}
            style={{
              padding: '6px 16px',
              borderRadius: 8,
              background: 'rgba(239,68,68,0.15)',
              color: '#EF4444',
              border: '1px solid rgba(239,68,68,0.3)',
              cursor: 'pointer',
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            ❌ رفض
          </motion.button>
          {onModify && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={onModify}
              style={{
                padding: '6px 16px',
                borderRadius: 8,
                background: 'rgba(13,123,181,0.15)',
                color: '#0d7bb5',
                border: '1px solid rgba(13,123,181,0.3)',
                cursor: 'pointer',
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              ✏️ تعديل
            </motion.button>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
