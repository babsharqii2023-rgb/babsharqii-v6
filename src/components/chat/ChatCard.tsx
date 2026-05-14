// ═══════════════════════════════════════════════════════════════════
// ChatCard — بطاقة الرسالة التفاعلية
// Interactive card component for chat messages with action buttons
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import type { ChatMessage } from '@/lib/store';

interface ChatCardProps {
  message: ChatMessage;
  onAction?: (action: string, messageId: string) => void;
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
};

export default function ChatCard({ message, onAction }: ChatCardProps) {
  const [showActions, setShowActions] = useState(false);
  const isUser = message.role === 'user';

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
        {/* Brain Badge */}
        {!isUser && (message.brain || message.confidence) && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 4,
            marginBottom: 4, fontSize: 9,
          }}>
            <span style={{ color: T.primary, fontWeight: 600 }}>
              {message.brain || 'مأمون'}
            </span>
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
            ⚠️ {message.warningMessage}
          </div>
        )}

        {/* Timestamp */}
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
