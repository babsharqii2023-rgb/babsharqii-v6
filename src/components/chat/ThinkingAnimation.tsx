// ═══════════════════════════════════════════════════════════════════
// ThinkingAnimation — حركة التفكير الحية v63
// Shows which brains are actively deliberating with:
//   - Brain-specific pulse animations
//   - Deliberation progress bar
//   - Current deliberation stage
//   - Brain confidence indicators
//   - Consensus level meter
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ThinkingAnimationProps {
  activeBrains: string[];
  tick: number;
  progress?: number;
  stage?: 'analyzing' | 'deliberating' | 'synthesizing' | 'responding';
  consensusLevel?: number;
  brainConfidences?: Record<string, number>;
}

const BRAIN_DISPLAY: Record<string, { nameAr: string; color: string; model: string; icon: string }> = {
  neural: { nameAr: 'عصبي', color: '#00e5ff', model: 'GLM-5.1', icon: '🧠' },
  causal: { nameAr: 'سببي', color: '#ff9100', model: 'DeepSeek-R', icon: '🔍' },
  symbolic: { nameAr: 'رمزي', color: '#448aff', model: 'GLM-4+', icon: '📐' },
  bayesian: { nameAr: 'بيزي', color: '#69f0ae', model: 'Gemini-2.0', icon: '📊' },
  world_model: { nameAr: 'عالمي', color: '#ffd740', model: 'DeepSeek-C', icon: '🌍' },
};

const STAGE_LABELS: Record<string, string> = {
  analyzing: 'تحليل الطلب',
  deliberating: 'مداولة الأدمغة',
  synthesizing: 'توليف الإجابة',
  responding: 'صياغة الرد',
};

export default function ThinkingAnimation({
  activeBrains,
  tick,
  progress = 0,
  stage = 'deliberating',
  consensusLevel = 0,
  brainConfidences = {},
}: ThinkingAnimationProps) {
  const [currentStage, setCurrentStage] = useState(stage);
  const allBrains = ['neural', 'causal', 'symbolic', 'bayesian', 'world_model'];

  // Animate through stages based on tick
  useEffect(() => {
    const stages = ['analyzing', 'deliberating', 'synthesizing', 'responding'];
    const idx = Math.floor(tick / 12) % stages.length;
    setCurrentStage(stages[idx]);
  }, [tick]);

  const displayStage = stage || currentStage;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      style={{ alignSelf: 'flex-end', width: '85%' }}
    >
      <div style={{
        padding: '12px 16px',
        background: '#1a1a1a',
        border: '1px solid rgba(13,123,181,0.3)',
        borderRadius: '16px 16px 16px 4px',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
          <motion.div
            animate={{ scale: [1, 1.3, 1], rotate: [0, 10, -10, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
            style={{ fontSize: 14 }}
          >
            🧠
          </motion.div>
          <span style={{ fontSize: 12, color: '#0d7bb5', fontWeight: 700 }}>
            أدمغة مأمون تتنافس...
          </span>
          <span style={{
            fontSize: 8,
            color: '#0a9b8a',
            background: 'rgba(10,155,138,0.1)',
            padding: '2px 6px',
            borderRadius: 4,
            border: '1px solid rgba(10,155,138,0.2)',
          }}>
            {STAGE_LABELS[displayStage]}
          </span>
        </div>

        {/* Brain Tags with Confidence */}
        <div style={{ display: 'flex', gap: 6, alignItems: 'stretch', flexWrap: 'wrap' }}>
          {allBrains.map((id, i) => {
            const display = BRAIN_DISPLAY[id];
            const isActive = activeBrains.length > 0
              ? activeBrains.includes(id)
              : (Math.floor(tick / 8) % 5) === i;
            const confidence = brainConfidences[id] || 0;

            return (
              <motion.div
                key={id}
                animate={isActive ? {
                  boxShadow: [`0 0 4px ${display.color}20`, `0 0 12px ${display.color}60`, `0 0 4px ${display.color}20`],
                } : {}}
                transition={{ duration: 1.5, repeat: Infinity }}
                style={{
                  padding: '4px 10px',
                  borderRadius: 8,
                  fontSize: 9,
                  background: isActive ? `${display.color}20` : 'rgba(13,123,181,0.08)',
                  color: isActive ? display.color : '#5a6a80',
                  border: isActive ? `1px solid ${display.color}60` : '1px solid rgba(255,255,255,0.08)',
                  fontWeight: isActive ? 700 : 400,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 2,
                  minWidth: 60,
                }}
              >
                <span>{display.icon} {display.nameAr}</span>
                {isActive && confidence > 0 && (
                  <span style={{ fontSize: 7, opacity: 0.8 }}>
                    {Math.round(confidence * 100)}%
                  </span>
                )}
              </motion.div>
            );
          })}
        </div>

        {/* Progress Bar */}
        {progress > 0 && (
          <div style={{ marginTop: 10 }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between',
              marginBottom: 3,
            }}>
              <span style={{ fontSize: 8, color: '#5a6a80' }}>تقدم المداولة</span>
              <span style={{ fontSize: 8, color: '#0d7bb5', fontWeight: 600 }}>{Math.round(progress)}%</span>
            </div>
            <div style={{
              width: '100%', height: 4,
              background: 'rgba(255,255,255,0.08)',
              borderRadius: 2,
              overflow: 'hidden',
            }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5 }}
                style={{
                  height: '100%',
                  background: 'linear-gradient(90deg, #0d7bb5, #0a9b8a)',
                  borderRadius: 2,
                }}
              />
            </div>
          </div>
        )}

        {/* Consensus Level */}
        {consensusLevel > 0 && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            marginTop: 8,
          }}>
            <span style={{ fontSize: 8, color: '#5a6a80' }}>الإجماع:</span>
            <div style={{
              display: 'flex', gap: 2,
            }}>
              {[0.2, 0.4, 0.6, 0.8, 1.0].map((level, i) => (
                <div
                  key={i}
                  style={{
                    width: 12, height: 4,
                    borderRadius: 1,
                    background: consensusLevel >= level
                      ? (level >= 0.8 ? '#4CAF50' : level >= 0.6 ? '#FF9800' : '#EF4444')
                      : 'rgba(255,255,255,0.08)',
                  }}
                />
              ))}
            </div>
            <span style={{
              fontSize: 8, fontWeight: 600,
              color: consensusLevel >= 0.8 ? '#4CAF50' : consensusLevel >= 0.6 ? '#FF9800' : '#EF4444',
            }}>
              {Math.round(consensusLevel * 100)}%
            </span>
          </div>
        )}

        {/* Progress dots animation */}
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
          <span style={{ fontSize: 8, color: '#5a6a80', marginRight: 6 }}>
            {STAGE_LABELS[displayStage]}
          </span>
        </div>
      </div>
    </motion.div>
  );
}
