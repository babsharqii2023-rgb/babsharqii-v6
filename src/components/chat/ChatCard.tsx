// ═══════════════════════════════════════════════════════════════════
// ChatCard — بطاقة الرسالة التفاعلية v63
// Full Human-ON-the-Loop support:
//   - Confirmation buttons (Approve/Reject/Modify)
//   - Countdown timer for Level 1 operations
//   - Brain badge with confidence
//   - Quick actions from BFF response
//   - Feedforward suggestions
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import type { ChatMessage } from '@/lib/store';

interface ChatCardProps {
  message: ChatMessage;
  onAction?: (action: string, messageId: string, payload?: Record<string, unknown>) => void;
  autonomyLevel?: 0 | 1 | 2 | 3;
  confirmationTimeout?: number; // ms for Level 1 auto-proceed
  requiresConfirmation?: boolean;
}

const T = {
  bg: '#080810',
  chatBg: '#0d0d1a',
  primary: '#0d7bb5',
  accent: '#0a9b8a',
  text: '#c8d0e0',
  textDim: '#5a6a80',
  bubble: '#1a1a1a',
  white: '#ffffff',
  primaryDim: 'rgba(13,123,181,0.08)',
  primaryMid: 'rgba(13,123,181,0.15)',
  primaryStrong: 'rgba(13,123,181,0.3)',
  accentDim: 'rgba(10,155,138,0.08)',
  accentMid: 'rgba(10,155,138,0.15)',
  accentStrong: 'rgba(10,155,138,0.3)',
  white90: 'rgba(255,255,255,0.9)',
  white08: 'rgba(255,255,255,0.08)',
  danger: '#EF4444',
  warning: '#FF9800',
  success: '#4CAF50',
};

const RISK_COLORS: Record<number, string> = {
  0: '#EF4444', // Critical
  1: '#FF9800', // Medium
  2: '#4CAF50', // Low
  3: '#9E9E9E', // Autonomous
};

const RISK_LABELS: Record<number, string> = {
  0: 'حرج',
  1: 'متوسط',
  2: 'منخفض',
  3: 'تلقائي',
};

export default function ChatCard({
  message,
  onAction,
  autonomyLevel,
  confirmationTimeout = 30000,
  requiresConfirmation = false,
}: ChatCardProps) {
  const [showActions, setShowActions] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const isUser = message.role === 'user';
  const needsConfirmation = requiresConfirmation || autonomyLevel === 0 || autonomyLevel === 1;
  const riskColor = RISK_COLORS[autonomyLevel ?? 2];
  const riskLabel = RISK_LABELS[autonomyLevel ?? 2];

  // Countdown timer for Level 1 auto-proceed
  useEffect(() => {
    if (autonomyLevel !== 1 || !needsConfirmation || confirmed) return;

    const timeoutSeconds = Math.floor(confirmationTimeout / 1000);
    setCountdown(timeoutSeconds);

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(timer);
          // Auto-proceed after timeout for Level 1
          onAction?.('auto_approve', message.id);
          setConfirmed(true);
          return null;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [autonomyLevel, needsConfirmation, confirmationTimeout, confirmed, message.id, onAction]);

  const handleApprove = useCallback(() => {
    setConfirmed(true);
    setCountdown(null);
    onAction?.('approve', message.id);
  }, [message.id, onAction]);

  const handleReject = useCallback(() => {
    setConfirmed(true);
    setCountdown(null);
    onAction?.('reject', message.id);
  }, [message.id, onAction]);

  const handleModify = useCallback(() => {
    onAction?.('modify', message.id);
  }, [message.id, onAction]);

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      style={{
        maxWidth: '85%',
        alignSelf: isUser ? 'flex-start' : 'flex-end',
      }}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div style={{
        padding: '8px 12px',
        background: isUser ? T.accentMid : T.bubble,
        border: isUser
          ? `1px solid ${T.accentStrong}`
          : `1px solid ${T.primaryDim}`,
        borderRadius: isUser
          ? '16px 16px 4px 16px'
          : '16px 16px 16px 4px',
        position: 'relative',
      }}>
        {/* Brain Badge + Risk Level */}
        {!isUser && (message.brain || message.confidence || autonomyLevel !== undefined) && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            marginBottom: 4, fontSize: 9,
          }}>
            {message.brain && (
              <span style={{ color: T.primary, fontWeight: 600 }}>
                {message.brain}
              </span>
            )}
            {message.confidence && (
              <span style={{ color: T.textDim }}>
                {Math.round(message.confidence * 100)}%
              </span>
            )}
            {Boolean(message.metadata?.isRealDeliberation) && (
              <span style={{
                fontSize: 7, color: T.accent,
                background: T.accentDim,
                padding: '1px 4px',
                borderRadius: 3,
              }}>
                مداولة حقيقية
              </span>
            )}
            {autonomyLevel !== undefined && autonomyLevel <= 1 && (
              <span style={{
                fontSize: 7, color: riskColor,
                background: `${riskColor}15`,
                padding: '1px 6px',
                borderRadius: 3,
                border: `1px solid ${riskColor}40`,
                fontWeight: 700,
              }}>
                {riskLabel}
              </span>
            )}
          </div>
        )}

        {/* Content */}
        {isUser ? (
          <p style={{
            fontSize: 12, lineHeight: 1.7,
            color: T.white90, margin: 0,
            whiteSpace: 'pre-wrap',
          }}>{message.content}</p>
        ) : (
          <div style={{
            fontSize: 12, lineHeight: 1.8,
            color: T.text,
            whiteSpace: 'pre-wrap',
          }}>
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}

        {/* Confidence Warning */}
        {message.warningMessage && (
          <div style={{
            fontSize: 9, color: '#ffd740',
            background: 'rgba(255,215,64,0.08)',
            padding: '4px 8px',
            borderRadius: 4,
            marginTop: 6,
            borderRight: '2px solid #ffd740',
          }}>
            {message.warningMessage}
          </div>
        )}

        {/* Human-ON-the-Loop Confirmation Panel */}
        <AnimatePresence>
          {needsConfirmation && !confirmed && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              style={{
                marginTop: 8,
                padding: '8px 10px',
                background: `${riskColor}08`,
                border: `1px solid ${riskColor}30`,
                borderRadius: 8,
              }}
            >
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', marginBottom: 6,
              }}>
                <span style={{ fontSize: 10, color: riskColor, fontWeight: 700 }}>
                  يتطلب تأكيد{autonomyLevel === 0 ? ' إلزامي' : ''}
                </span>
                {autonomyLevel === 1 && countdown !== null && (
                  <span style={{
                    fontSize: 11, fontFamily: 'monospace',
                    color: countdown <= 5 ? T.danger : T.text,
                    background: T.white08,
                    padding: '2px 8px',
                    borderRadius: 6,
                  }}>
                    {countdown}ث
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleApprove}
                  style={{
                    padding: '4px 12px',
                    borderRadius: 6,
                    background: 'rgba(76,175,80,0.15)',
                    color: T.success,
                    border: `1px solid rgba(76,175,80,0.3)`,
                    cursor: 'pointer',
                    fontSize: 10,
                    fontWeight: 600,
                  }}
                >
                  تأكيد
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleReject}
                  style={{
                    padding: '4px 12px',
                    borderRadius: 6,
                    background: 'rgba(239,68,68,0.15)',
                    color: T.danger,
                    border: `1px solid rgba(239,68,68,0.3)`,
                    cursor: 'pointer',
                    fontSize: 10,
                    fontWeight: 600,
                  }}
                >
                  رفض
                </motion.button>
                {autonomyLevel === 0 && (
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handleModify}
                    style={{
                      padding: '4px 12px',
                      borderRadius: 6,
                      background: T.primaryMid,
                      color: T.primary,
                      border: `1px solid ${T.primaryStrong}`,
                      cursor: 'pointer',
                      fontSize: 10,
                      fontWeight: 600,
                    }}
                  >
                    تعديل
                  </motion.button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Quick Actions */}
        {message.quickActions && message.quickActions.length > 0 && (
          <div style={{
            display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap',
          }}>
            {message.quickActions.map((action, i) => (
              <button
                key={i}
                onClick={() => onAction?.('quick_action', message.id, { intent: action.intent })}
                style={{
                  padding: '2px 8px',
                  borderRadius: 4,
                  background: T.primaryDim,
                  border: `1px solid ${T.primaryMid}`,
                  color: T.primary,
                  fontSize: 8,
                  cursor: 'pointer',
                }}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}

        {/* Timestamp + Actions */}
        <div style={{
          fontSize: 7, color: T.textDim,
          marginTop: 4, textAlign: isUser ? 'left' : 'right',
          display: 'flex',
          justifyContent: isUser ? 'flex-start' : 'flex-end',
          alignItems: 'center',
          gap: 6,
        }}>
          <span>{formatTime(message.timestamp)}</span>
          {showActions && !isUser && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ display: 'flex', gap: 4 }}
            >
              <button
                onClick={() => onAction?.('copy', message.id)}
                style={{
                  background: T.primaryDim, border: 'none',
                  borderRadius: 3, padding: '1px 4px',
                  color: T.textDim, fontSize: 7, cursor: 'pointer',
                }}
              >
                نسخ
              </button>
              <button
                onClick={() => onAction?.('regenerate', message.id)}
                style={{
                  background: T.primaryDim, border: 'none',
                  borderRadius: 3, padding: '1px 4px',
                  color: T.textDim, fontSize: 7, cursor: 'pointer',
                }}
              >
                إعادة
              </button>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
