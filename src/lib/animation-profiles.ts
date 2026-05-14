// ═══════════════════════════════════════════════════════════════════
// Animation Profiles — ملفات تعريف التحريك v63
// GSAP + Framer Motion animation presets for SuperMind
// Each intent maps to a specific animation profile
// ═══════════════════════════════════════════════════════════════════

export interface AnimationProfile {
  name: string;
  enter: {
    initial: Record<string, number | string>;
    animate: Record<string, number | string>;
    transition: { duration: number; ease: string; stagger?: number };
  };
  exit: {
    animate: Record<string, number | string>;
    transition: { duration: number; ease: string };
  };
  brainTransition: {
    duration: number;
    ease: string;
    dimOpacity: number;
    brightOpacity: number;
    dimScale: number;
    brightScale: number;
  };
}

export const ANIMATION_PROFILES: Record<string, AnimationProfile> = {
  fadeIn: {
    name: 'fadeIn',
    enter: {
      initial: { opacity: 0 },
      animate: { opacity: 1 },
      transition: { duration: 0.6, ease: 'power2.out' },
    },
    exit: {
      animate: { opacity: 0 },
      transition: { duration: 0.4, ease: 'power2.in' },
    },
    brainTransition: {
      duration: 800,
      ease: 'power2.inOut',
      dimOpacity: 0.3,
      brightOpacity: 1,
      dimScale: 0.85,
      brightScale: 1.2,
    },
  },

  slideRight: {
    name: 'slideRight',
    enter: {
      initial: { opacity: 0, x: -30 },
      animate: { opacity: 1, x: 0 },
      transition: { duration: 0.7, ease: 'power2.out', stagger: 0.08 },
    },
    exit: {
      animate: { opacity: 0, x: 30 },
      transition: { duration: 0.4, ease: 'power2.in' },
    },
    brainTransition: {
      duration: 900,
      ease: 'power2.inOut',
      dimOpacity: 0.2,
      brightOpacity: 1,
      dimScale: 0.8,
      brightScale: 1.3,
    },
  },

  slideUp: {
    name: 'slideUp',
    enter: {
      initial: { opacity: 0, y: 20 },
      animate: { opacity: 1, y: 0 },
      transition: { duration: 0.6, ease: 'power2.out', stagger: 0.06 },
    },
    exit: {
      animate: { opacity: 0, y: -20 },
      transition: { duration: 0.35, ease: 'power2.in' },
    },
    brainTransition: {
      duration: 800,
      ease: 'power2.inOut',
      dimOpacity: 0.25,
      brightOpacity: 1,
      dimScale: 0.85,
      brightScale: 1.25,
    },
  },

  expandDown: {
    name: 'expandDown',
    enter: {
      initial: { opacity: 0, scaleY: 0.8, transformOrigin: 'top' },
      animate: { opacity: 1, scaleY: 1 },
      transition: { duration: 0.7, ease: 'power2.out', stagger: 0.1 },
    },
    exit: {
      animate: { opacity: 0, scaleY: 0.8 },
      transition: { duration: 0.4, ease: 'power2.in' },
    },
    brainTransition: {
      duration: 1000,
      ease: 'power2.inOut',
      dimOpacity: 0.2,
      brightOpacity: 1,
      dimScale: 0.8,
      brightScale: 1.35,
    },
  },

  zoomIn: {
    name: 'zoomIn',
    enter: {
      initial: { opacity: 0, scale: 0.85 },
      animate: { opacity: 1, scale: 1 },
      transition: { duration: 0.8, ease: 'back.out(1.2)', stagger: 0.12 },
    },
    exit: {
      animate: { opacity: 0, scale: 0.9 },
      transition: { duration: 0.4, ease: 'power2.in' },
    },
    brainTransition: {
      duration: 1200,
      ease: 'power2.inOut',
      dimOpacity: 0.15,
      brightOpacity: 1,
      dimScale: 0.75,
      brightScale: 1.4,
    },
  },

  pulseIn: {
    name: 'pulseIn',
    enter: {
      initial: { opacity: 0, scale: 0.9 },
      animate: { opacity: 1, scale: [0.9, 1.05, 1] },
      transition: { duration: 0.8, ease: 'easeOut', stagger: 0.08 },
    },
    exit: {
      animate: { opacity: 0, scale: 0.95 },
      transition: { duration: 0.35, ease: 'power2.in' },
    },
    brainTransition: {
      duration: 900,
      ease: 'power2.inOut',
      dimOpacity: 0.2,
      brightOpacity: 1,
      dimScale: 0.8,
      brightScale: 1.3,
    },
  },
};

/**
 * Get animation profile by name
 */
export function getAnimationProfile(name: string): AnimationProfile {
  return ANIMATION_PROFILES[name] || ANIMATION_PROFILES.fadeIn;
}

/**
 * Get animation config for a specific intent's screen transition
 */
export function getIntentAnimation(intent: string): AnimationProfile {
  const intentToAnimation: Record<string, string> = {
    'projects.list': 'slideRight',
    'projects.monitor': 'fadeIn',
    'projects.promote': 'slideUp',
    'site.stats': 'fadeIn',
    'research.deep': 'expandDown',
    'research.extended': 'expandDown',
    'tool.create': 'slideUp',
    'agent.build': 'slideUp',
    'deploy': 'zoomIn',
    'healing': 'pulseIn',
    'self.modify': 'pulseIn',
    'workflow': 'slideRight',
    'terminal': 'slideUp',
    'brain.state': 'fadeIn',
    'vitals': 'fadeIn',
    'conversations.search': 'fadeIn',
    'update.pull': 'pulseIn',
    'capabilities.list': 'fadeIn',
    'code.generate': 'slideUp',
    'project.scaffold': 'slideUp',
    'evolution.status': 'fadeIn',
    'health.dashboard': 'fadeIn',
    'default': 'fadeIn',
  };

  const animName = intentToAnimation[intent] || 'fadeIn';
  return ANIMATION_PROFILES[animName] || ANIMATION_PROFILES.fadeIn;
}
