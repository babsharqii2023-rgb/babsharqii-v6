'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface ActionButton {
  label: string;
  intentId: string;
  variant: 'approve' | 'reject' | 'modify';
  payload?: Record<string, unknown>;
}

interface ActionButtonsProps {
  buttons: ActionButton[];
  onAction: (button: ActionButton) => void;
}

const VARIANT_STYLES: Record<string, { bg: string; color: string; border: string }> = {
  approve: { bg: 'rgba(76,175,80,0.15)', color: '#4CAF50', border: 'rgba(76,175,80,0.3)' },
  reject: { bg: 'rgba(239,68,68,0.15)', color: '#EF4444', border: 'rgba(239,68,68,0.3)' },
  modify: { bg: 'rgba(13,123,181,0.15)', color: '#0d7bb5', border: 'rgba(13,123,181,0.3)' },
};

export default function ActionButtons({ buttons, onAction }: ActionButtonsProps) {
  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      {buttons.map((btn) => {
        const style = VARIANT_STYLES[btn.variant] || VARIANT_STYLES.modify;
        return (
          <motion.button
            key={btn.label}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => onAction(btn)}
            style={{
              padding: '6px 16px',
              borderRadius: 8,
              background: style.bg,
              color: style.color,
              border: `1px solid ${style.border}`,
              cursor: 'pointer',
              fontSize: 12,
              fontWeight: 600,
              transition: 'all 0.15s',
            }}
          >
            {btn.label}
          </motion.button>
        );
      })}
    </div>
  );
}
