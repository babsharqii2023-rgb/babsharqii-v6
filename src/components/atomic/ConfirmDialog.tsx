'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ConfirmDialogProps {
  title: string;
  message: string;
  riskLevel?: 'low' | 'medium' | 'high';
  onConfirm: () => void;
  onCancel: () => void;
  timeout?: number;
}

const T = {
  bg: '#080810',
  card: '#0d0d1a',
  primary: '#0d7bb5',
  text: '#c8d0e0',
  textDim: '#5a6a80',
  white90: 'rgba(255,255,255,0.9)',
  white08: 'rgba(255,255,255,0.08)',
  white15: 'rgba(255,255,255,0.15)',
};

const RISK_STYLES = {
  low: { color: '#10b981', bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.3)', icon: '✓' },
  medium: { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.3)', icon: '⚠' },
  high: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.3)', icon: '⛔' },
};

export default function ConfirmDialog({
  title,
  message,
  riskLevel = 'low',
  onConfirm,
  onCancel,
  timeout,
}: ConfirmDialogProps) {
  const [countdown, setCountdown] = useState(timeout ?? 0);
  const [canConfirm, setCanConfirm] = useState(!timeout);
  const risk = RISK_STYLES[riskLevel];

  useEffect(() => {
    if (!timeout) return;

    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setCanConfirm(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [timeout]);

  const handleConfirm = useCallback(() => {
    if (canConfirm) onConfirm();
  }, [canConfirm, onConfirm]);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          backdropFilter: 'blur(4px)',
        }}
        onClick={onCancel}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          transition={{ duration: 0.25 }}
          onClick={(e) => e.stopPropagation()}
          style={{
            background: T.card,
            border: `1px solid ${risk.border}`,
            borderRadius: 16,
            padding: 28,
            maxWidth: 420,
            width: '90%',
            position: 'relative',
            overflow: 'hidden',
            boxShadow: `0 0 40px ${risk.color}15`,
          }}
        >
          {/* Top accent line */}
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: 3,
            background: `linear-gradient(90deg, transparent, ${risk.color}, transparent)`,
          }} />

          {/* Risk icon */}
          <div style={{
            fontSize: 28,
            marginBottom: 12,
            textAlign: 'center',
            filter: `drop-shadow(0 0 8px ${risk.color}44)`,
          }}>
            {risk.icon}
          </div>

          {/* Title */}
          <h3 style={{
            color: T.white90,
            fontSize: 18,
            fontWeight: 700,
            textAlign: 'center',
            marginBottom: 8,
          }}>
            {title}
          </h3>

          {/* Risk level badge */}
          <div style={{ textAlign: 'center', marginBottom: 12 }}>
            <span style={{
              padding: '2px 12px',
              borderRadius: 12,
              fontSize: 10,
              fontWeight: 600,
              background: risk.bg,
              color: risk.color,
              border: `1px solid ${risk.border}`,
              textTransform: 'uppercase',
              letterSpacing: 1,
            }}>
              {riskLevel} risk
            </span>
          </div>

          {/* Message */}
          <p style={{
            color: T.text,
            fontSize: 14,
            textAlign: 'center',
            lineHeight: 1.5,
            marginBottom: 24,
          }}>
            {message}
          </p>

          {/* Countdown */}
          {timeout && countdown > 0 && (
            <div style={{ textAlign: 'center', marginBottom: 16 }}>
              <motion.div
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ repeat: Infinity, duration: 1 }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 40,
                  height: 40,
                  borderRadius: '50%',
                  background: risk.bg,
                  border: `2px solid ${risk.border}`,
                  color: risk.color,
                  fontSize: 16,
                  fontWeight: 700,
                  fontFamily: 'monospace',
                }}
              >
                {countdown}
              </motion.div>
              <p style={{ color: T.textDim, fontSize: 11, marginTop: 6 }}>
                Confirming in {countdown}s...
              </p>
            </div>
          )}

          {/* Buttons */}
          <div style={{ display: 'flex', gap: 12 }}>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={onCancel}
              style={{
                flex: 1,
                padding: '10px 0',
                borderRadius: 10,
                background: T.white08,
                color: T.text,
                border: `1px solid ${T.white15}`,
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              Cancel
            </motion.button>

            <motion.button
              whileHover={canConfirm ? { scale: 1.02 } : {}}
              whileTap={canConfirm ? { scale: 0.98 } : {}}
              onClick={handleConfirm}
              disabled={!canConfirm}
              style={{
                flex: 1,
                padding: '10px 0',
                borderRadius: 10,
                background: canConfirm ? risk.color : T.white08,
                color: canConfirm ? '#fff' : T.textDim,
                border: `1px solid ${canConfirm ? risk.border : T.white15}`,
                cursor: canConfirm ? 'pointer' : 'not-allowed',
                fontSize: 13,
                fontWeight: 600,
                opacity: canConfirm ? 1 : 0.5,
                transition: 'all 0.2s',
              }}
            >
              {canConfirm ? 'Confirm' : `Wait ${countdown}s`}
            </motion.button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
