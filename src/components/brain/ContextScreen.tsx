// ═══════════════════════════════════════════════════════════════════
// ContextScreen — شاشة السياق الديناميكية
// Dynamically renders screen components based on detected intent
// Uses AnimatePresence for smooth transitions
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { loadScreenComponent, getScreenDefinition } from '@/lib/screen-registry';
import type { ComponentType } from 'react';

// ─── Animation Variants ────────────────────────────────────────

const animationVariants: Record<string, Record<string, unknown>> = {
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
  },
  slideRight: {
    initial: { opacity: 0, x: -30 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: 30 },
  },
  slideUp: {
    initial: { opacity: 0, y: 30 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -30 },
  },
  expandDown: {
    initial: { opacity: 0, scaleY: 0.8 },
    animate: { opacity: 1, scaleY: 1 },
    exit: { opacity: 0, scaleY: 0.8 },
  },
  zoomIn: {
    initial: { opacity: 0, scale: 0.9 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.9 },
  },
  pulseIn: {
    initial: { opacity: 0, scale: 0.95 },
    animate: { opacity: 1, scale: [0.95, 1.02, 1] },
    exit: { opacity: 0, scale: 0.95 },
  },
};

// ─── Default Welcome Screen ────────────────────────────────────

function WelcomeScreen() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      color: '#5a6a80',
      gap: 16,
      padding: 24,
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 48 }}>⚡</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: '#0d7bb5' }}>
        العقل الخارق
      </div>
      <div style={{ fontSize: 13, lineHeight: 1.8, maxWidth: 400 }}>
        أنا أتحكم بكل شيء: الباك إند، الفرونت إند، الأدمغة، GitHub، البحث، الإصلاح
      </div>
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 6,
        justifyContent: 'center',
        marginTop: 8,
      }}>
        {[
          'أرني المشاريع',
          'إحصائيات الموقع',
          'أصلح الأخطاء',
          'ابحث عن...',
          'أنشئ أداة',
          'افتح الطرفية',
        ].map(cmd => (
          <span key={cmd} style={{
            background: 'rgba(13,123,181,0.08)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 8,
            padding: '4px 10px',
            fontSize: 10,
            color: '#0d7bb5',
          }}>
            {cmd}
          </span>
        ))}
      </div>
    </div>
  );
}

// ─── Loading Screen ────────────────────────────────────────────

function LoadingScreen() {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      color: '#5a6a80',
      gap: 8,
      fontSize: 12,
    }}>
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        style={{ fontSize: 20 }}
      >
        ⚙️
      </motion.div>
      <span>جاري تحميل الشاشة...</span>
    </div>
  );
}

// ─── Main Component ────────────────────────────────────────────

export interface ContextScreenProps {
  activeScreen: string | null;
  animation?: string;
  screenProps?: Record<string, unknown>;
  onBack?: () => void;
}

export default function ContextScreen({
  activeScreen,
  animation = 'fadeIn',
  screenProps = {},
  onBack,
}: ContextScreenProps) {
  const [ScreenComponent, setScreenComponent] = useState<ComponentType<Record<string, unknown>> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load screen component dynamically — uses async IIFE to avoid
  // synchronous setState-in-effect lint violation
  useEffect(() => {
    let cancelled = false;

    const loadAsync = async () => {
      if (!activeScreen) {
        setScreenComponent(null);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const comp = await loadScreenComponent(activeScreen);
        if (!cancelled) {
          setScreenComponent(() => comp);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(`فشل تحميل الشاشة: ${activeScreen}`);
          setLoading(false);
          console.warn('[ContextScreen] Load error:', err);
        }
      }
    };
    loadAsync();

    return () => { cancelled = true; };
  }, [activeScreen]);

  const handleBack = useCallback(() => {
    onBack?.();
  }, [onBack]);

  const variant = animationVariants[animation] || animationVariants.fadeIn;
  const screenDef = activeScreen ? getScreenDefinition(activeScreen) : null;

  return (
    <div style={{
      width: '100%',
      height: '100%',
      overflow: 'auto',
      position: 'relative',
    }}>
      {/* Header bar when a screen is active */}
      {activeScreen && screenDef && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 16px',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(13,13,26,0.9)',
          }}
        >
          <button
            onClick={handleBack}
            style={{
              background: 'rgba(13,123,181,0.08)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 6,
              padding: '2px 8px',
              color: '#5a6a80',
              cursor: 'pointer',
              fontSize: 11,
            }}
          >
            → رجوع
          </button>
          <span style={{ fontSize: 16 }}>{screenDef.icon}</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#0d7bb5' }}>
            {screenDef.labelAr}
          </span>
          <span style={{ fontSize: 10, color: '#5a6a80', flex: 1 }}>
            {screenDef.description}
          </span>
        </motion.div>
      )}

      <AnimatePresence mode="wait">
        {!activeScreen ? (
          <motion.div
            key="welcome"
            {...animationVariants.fadeIn}
            transition={{ duration: 0.3 }}
            style={{ height: 'calc(100% - 40px)' }}
          >
            <WelcomeScreen />
          </motion.div>
        ) : loading ? (
          <motion.div
            key={`loading-${activeScreen}`}
            {...animationVariants.fadeIn}
            transition={{ duration: 0.2 }}
            style={{ height: 'calc(100% - 40px)' }}
          >
            <LoadingScreen />
          </motion.div>
        ) : error ? (
          <motion.div
            key={`error-${activeScreen}`}
            {...animationVariants.fadeIn}
            transition={{ duration: 0.3 }}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: 'calc(100% - 40px)',
              color: '#EF4444',
              fontSize: 12,
            }}
          >
            {error}
          </motion.div>
        ) : ScreenComponent ? (
          <motion.div
            key={activeScreen}
            {...variant}
            transition={{ duration: 0.35, ease: 'easeOut' }}
            style={{ height: 'calc(100% - 40px)' }}
          >
            <ScreenComponent {...screenProps} onBack={handleBack} />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
