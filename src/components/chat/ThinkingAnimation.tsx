// ═══════════════════════════════════════════════════════════════════
// ThinkingAnimation — حركة التفكير الحية
// Live deliberation animation showing which brains are active
// ═══════════════════════════════════════════════════════════════════

'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface ThinkingAnimationProps {
  activeBrains: string[];
  tick: number;
}

const BRAIN_DISPLAY: Record<string, { nameAr: string; color: string }> = {
  neural: { nameAr: 'عصبي', color: '#00e5ff' },
  causal: { nameAr: 'سببي', color: '#ff9100' },
  symbolic: { nameAr: 'رمزي', color: '#448aff' },
  bayesian: { nameAr: 'بيزي', color: '#69f0ae' },
  world_model: { nameAr: 'عالمي', color: '#ffd740' },
};

export default function ThinkingAnimation({ activeBrains, tick }: ThinkingAnimationProps) {
  const allBrains = ['neural', 'causal', 'symbolic', 'bayesian', 'world_model'];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      style={{ alignSelf: 'flex-end', width: '85%' }}
    >
      <div style={{
        padding: '10px 16px',
        background: '#1a1a1a',
        border: '1px solid rgba(13,123,181,0.3)',
        borderRadius: '16px 16px 16px 4px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            style={{ fontSize: 12 }}
          >
            🧠
          </motion.div>
          <span style={{ fontSize: 12, color: '#0d7bb5', fontWeight: 700 }}>
            أدمغة مأمون تتنافس...
          </span>
        </div>

        {/* Brain Tags */}
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          {allBrains.map((id, i) => {
            const display = BRAIN_DISPLAY[id];
            const isActive = activeBrains.length > 0
              ? activeBrains.includes(id)
              : (Math.floor(tick / 8) % 5) === i;

            return (
              <motion.div
                key={id}
                animate={isActive ? {
                  boxShadow: `0 0 8px ${display.color}40`,
                } : {}}
                style={{
                  padding: '2px 8px',
                  borderRadius: 6,
                  fontSize: 9,
                  background: isActive ? `${display.color}20` : 'rgba(13,123,181,0.08)',
                  color: isActive ? display.color : '#5a6a80',
                  border: isActive ? `1px solid ${display.color}60` : '1px solid rgba(255,255,255,0.08)',
                  fontWeight: isActive ? 700 : 400,
                }}
              >
                {display.nameAr}
              </motion.div>
            );
          })}
        </div>

        {/* Progress dots */}
        <div style={{ display: 'flex', gap: 3, marginTop: 8, alignItems: 'center' }}>
          {[0, 1, 2, 3, 4].map(i => (
            <motion.div
              key={i}
              animate={{
                opacity: [0.3, 1, 0.3],
                scale: [0.8, 1, 0.8],
              }}
              transition={{
                duration: 0.8,
                repeat: Infinity,
                delay: i * 0.15,
              }}
              style={{
                width: 4, height: 4, borderRadius: '50%',
                background: '#0d7bb5',
              }}
            />
          ))}
          <span style={{ fontSize: 8, color: '#5a6a80', marginRight: 6 }}>مداولة جارية</span>
        </div>
      </div>
    </motion.div>
  );
}
