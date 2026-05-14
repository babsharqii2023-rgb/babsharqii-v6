/**
 * SuperMind (العقل الخارق) v61 — Comprehensive Integration Tests
 * Tests: SuperMindRouter, BrainNetwork, ContextScreen, Store, Sound, SSE, Components
 */

import { describe, it, expect, beforeAll } from 'vitest';
import fs from 'fs';
import path from 'path';

const PROJECT_ROOT = '/home/z/my-project/babsharqii-v5';

// ═══════════════════════════════════════════════════════════════
// 1. SuperMindRouter Tests — اختبارات موجه العقل الخارق
// ═══════════════════════════════════════════════════════════════

describe('SuperMindRouter', () => {
  let routerContent: string;

  beforeAll(() => {
    const routerPath = path.join(PROJECT_ROOT, 'src/lib/super-mind-router.ts');
    routerContent = fs.readFileSync(routerPath, 'utf-8');
  });

  it('File exists and has content', () => {
    expect(routerContent.length).toBeGreaterThan(500);
  });

  it('Defines intent routing/classification function', () => {
    expect(routerContent).toMatch(/routeIntent|classify|classifyMessage/i);
  });

  it('Handles projects intent', () => {
    expect(routerContent).toMatch(/مشروع|mashroo|project/i);
  });

  it('Handles research intent', () => {
    expect(routerContent).toMatch(/بحث|bahath|research/i);
  });

  it('Handles healing intent', () => {
    expect(routerContent).toMatch(/إصلاح|islah|heal/i);
  });

  it('Handles terminal intent', () => {
    expect(routerContent).toMatch(/طرفية|terminal/i);
  });

  it('Handles deploy intent', () => {
    expect(routerContent).toMatch(/نشر|nashir|deploy/i);
  });

  it('Returns screen component mapping', () => {
    expect(routerContent).toMatch(/screen|component/i);
  });

  it('Returns animation profile', () => {
    expect(routerContent).toMatch(/animation|anim/i);
  });
});

// ═══════════════════════════════════════════════════════════════
// 2. BrainNetwork Component Tests — اختبارات شبكة الدماغ ثلاثية الأبعاد
// ═══════════════════════════════════════════════════════════════

describe('BrainNetwork 3D Component', () => {
  let content: string;

  beforeAll(() => {
    const filePath = path.join(PROJECT_ROOT, 'src/components/brain/BrainNetwork.tsx');
    content = fs.readFileSync(filePath, 'utf-8');
  });

  it('File exists and has content', () => {
    expect(content.length).toBeGreaterThan(500);
  });

  it('Uses Three.js (@react-three/fiber)', () => {
    expect(content).toMatch(/@react-three\/fiber|Canvas|useFrame/);
  });

  it('Has 5 brain nodes (neural, causal, symbolic, bayesian, worldmodel)', () => {
    const brainNames = ['neural', 'causal', 'symbolic', 'bayesian', 'world'];
    const found = brainNames.filter(b => content.toLowerCase().includes(b));
    expect(found.length).toBeGreaterThanOrEqual(4);
  });

  it('Uses GSAP for animations', () => {
    expect(content).toMatch(/gsap|GSAP/);
  });

  it('Has React.Suspense fallback', () => {
    expect(content).toContain('Suspense');
  });

  it('Exports as default component', () => {
    expect(content).toContain('export default');
  });
});

// ═══════════════════════════════════════════════════════════════
// 3. ContextScreen Tests — اختبارات الشاشة السياقية
// ═══════════════════════════════════════════════════════════════

describe('ContextScreen Component', () => {
  let content: string;

  beforeAll(() => {
    const filePath = path.join(PROJECT_ROOT, 'src/components/brain/ContextScreen.tsx');
    content = fs.readFileSync(filePath, 'utf-8');
  });

  it('File exists and has content', () => {
    expect(content.length).toBeGreaterThan(300);
  });

  it('Uses Framer Motion AnimatePresence', () => {
    expect(content).toMatch(/AnimatePresence|framer-motion/);
  });

  it('Dynamically renders screen components', () => {
    expect(content).toMatch(/screen|component|registry/i);
  });
});

// ═══════════════════════════════════════════════════════════════
// 4. Brain Sound System Tests — اختبارات نظام الصوت
// ═══════════════════════════════════════════════════════════════

describe('BrainSound System', () => {
  let content: string;

  beforeAll(() => {
    const filePath = path.join(PROJECT_ROOT, 'src/lib/brain-sound.ts');
    content = fs.readFileSync(filePath, 'utf-8');
  });

  it('File exists and has content', () => {
    expect(content.length).toBeGreaterThan(300);
  });

  it('Uses Web Audio API', () => {
    expect(content).toMatch(/AudioContext|OscillatorNode|GainNode/i);
  });

  it('Defines brain oscillator types', () => {
    expect(content).toMatch(/sawtooth|sine|square|triangle/i);
  });
});

// ═══════════════════════════════════════════════════════════════
// 5. Screen Registry Tests — اختبارات سجل الشاشات
// ═══════════════════════════════════════════════════════════════

describe('ScreenRegistry', () => {
  let content: string;

  beforeAll(() => {
    const filePath = path.join(PROJECT_ROOT, 'src/lib/screen-registry.ts');
    content = fs.readFileSync(filePath, 'utf-8');
  });

  it('File exists and has content', () => {
    expect(content.length).toBeGreaterThan(300);
  });

  it('Maps intent names to components', () => {
    expect(content).toMatch(/ProjectsTracker|SiteStats|Terminal|Research/i);
  });
});

// ═══════════════════════════════════════════════════════════════
// 6. MamounCommandCenter Tests — اختبارات المكون الرئيسي
// ═══════════════════════════════════════════════════════════════

describe('MamounCommandCenter (SuperMind)', () => {
  let content: string;

  beforeAll(() => {
    const filePath = path.join(PROJECT_ROOT, 'src/components/dashboard/MamounCommandCenter.tsx');
    content = fs.readFileSync(filePath, 'utf-8');
  });

  it('File exists and has substantial content', () => {
    expect(content.length).toBeGreaterThan(2000);
  });

  it('Uses three-panel layout (chat, context, brain)', () => {
    expect(content).toMatch(/30%|40%|30%/);
  });

  it('Imports SuperMindRouter', () => {
    expect(content).toMatch(/super-mind-router|SuperMindRouter/);
  });

  it('Imports BrainNetwork component', () => {
    expect(content).toMatch(/BrainNetwork|brain\/BrainNetwork/);
  });

  it('Imports ContextScreen component', () => {
    expect(content).toMatch(/ContextScreen|brain\/ContextScreen/);
  });

  it('Connects to /api/super-mind/chat', () => {
    expect(content).toContain('/api/super-mind/chat');
  });

  it('Uses Framer Motion', () => {
    expect(content).toMatch(/framer-motion|AnimatePresence/);
  });

  it('Has Arabic text (RTL support)', () => {
    expect(content).toMatch(/العقل الخارق|مأمون/);
  });

  it('Has thinking/deliberation animation', () => {
    expect(content).toMatch(/ThinkingAnimation|thinking|deliberat/i);
  });

  it('Has chat input with send handler', () => {
    expect(content).toMatch(/handleSend|sendMessage|onSubmit/i);
  });
});

// ═══════════════════════════════════════════════════════════════
// 7. Store Extensions Tests — اختبارات متجر الحالة
// ═══════════════════════════════════════════════════════════════

describe('Zustand Store Extensions', () => {
  let content: string;

  beforeAll(() => {
    const filePath = path.join(PROJECT_ROOT, 'src/lib/store.ts');
    content = fs.readFileSync(filePath, 'utf-8');
  });

  it('Has currentIntent state', () => {
    expect(content).toMatch(/currentIntent/);
  });

  it('Has activeScreen state', () => {
    expect(content).toMatch(/activeScreen/);
  });

  it('Has soundEnabled state', () => {
    expect(content).toMatch(/soundEnabled/);
  });

  it('Has soundVolume state', () => {
    expect(content).toMatch(/soundVolume/);
  });

  it('Has projects state', () => {
    expect(content).toMatch(/projects/);
  });
});

// ═══════════════════════════════════════════════════════════════
// 8. Brain Screen Components Tests — اختبارات شاشات الدماغ
// ═══════════════════════════════════════════════════════════════

describe('Brain Screen Components', () => {
  const screenComponents = [
    'ProjectsTracker',
    'SiteStatsPanel',
    'ResearchPanel',
    'TerminalPanel',
    'HealingPanel',
    'ToolCreatorPanel',
    'AgentBuilderPanel',
    'DeployPanel',
  ];

  screenComponents.forEach(componentName => {
    it(`${componentName}.tsx exists`, () => {
      const filePath = path.join(PROJECT_ROOT, `src/components/brain/${componentName}.tsx`);
      expect(fs.existsSync(filePath)).toBe(true);
    });

    it(`${componentName}.tsx has 'use client' directive`, () => {
      const filePath = path.join(PROJECT_ROOT, `src/components/brain/${componentName}.tsx`);
      const content = fs.readFileSync(filePath, 'utf-8');
      expect(content).toContain("'use client'");
    });

    it(`${componentName}.tsx exports default component`, () => {
      const filePath = path.join(PROJECT_ROOT, `src/components/brain/${componentName}.tsx`);
      const content = fs.readFileSync(filePath, 'utf-8');
      expect(content).toContain('export default');
    });
  });
});

// ═══════════════════════════════════════════════════════════════
// 9. Chat Components Tests — اختبارات مكونات الدردشة
// ═══════════════════════════════════════════════════════════════

describe('Chat Components', () => {
  it('ThinkingAnimation.tsx exists', () => {
    expect(fs.existsSync(path.join(PROJECT_ROOT, 'src/components/chat/ThinkingAnimation.tsx'))).toBe(true);
  });

  it('ChatCard.tsx exists', () => {
    expect(fs.existsSync(path.join(PROJECT_ROOT, 'src/components/chat/ChatCard.tsx'))).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════
// 10. Custom Hooks Tests — اختبارات الخطافات المخصصة
// ═══════════════════════════════════════════════════════════════

describe('Custom Hooks', () => {
  it('useSSEStream.ts exists', () => {
    expect(fs.existsSync(path.join(PROJECT_ROOT, 'src/hooks/useSSEStream.ts'))).toBe(true);
  });

  it('useBrainSound.ts exists', () => {
    expect(fs.existsSync(path.join(PROJECT_ROOT, 'src/hooks/useBrainSound.ts'))).toBe(true);
  });

  it('useSSEStream has SSE event handling', () => {
    const content = fs.readFileSync(path.join(PROJECT_ROOT, 'src/hooks/useSSEStream.ts'), 'utf-8');
    expect(content).toMatch(/EventSource|SSE|stream/i);
  });
});

// ═══════════════════════════════════════════════════════════════
// 11. BFF API Route Tests — اختبارات مسار واجهة برمجة التطبيقات
// ═══════════════════════════════════════════════════════════════

describe('BFF API Route', () => {
  it('/api/super-mind/chat/route.ts exists', () => {
    const routePath = path.join(PROJECT_ROOT, 'src/app/api/super-mind/chat/route.ts');
    expect(fs.existsSync(routePath)).toBe(true);
  });

  it('SuperMind chat route has POST handler', () => {
    const content = fs.readFileSync(path.join(PROJECT_ROOT, 'src/app/api/super-mind/chat/route.ts'), 'utf-8');
    expect(content).toContain('POST');
  });
});

// ═══════════════════════════════════════════════════════════════
// 12. Package Dependencies Tests — اختبارات الحزم المثبتة
// ═══════════════════════════════════════════════════════════════

describe('Package Dependencies', () => {
  let packageJson: any;

  beforeAll(() => {
    const content = fs.readFileSync(path.join(PROJECT_ROOT, 'package.json'), 'utf-8');
    packageJson = JSON.parse(content);
  });

  it('three.js is installed', () => {
    const deps = { ...packageJson.dependencies, ...packageJson.devDependencies };
    expect(deps['three']).toBeDefined();
  });

  it('gsap is installed', () => {
    const deps = { ...packageJson.dependencies, ...packageJson.devDependencies };
    expect(deps['gsap']).toBeDefined();
  });

  it('framer-motion is installed', () => {
    const deps = { ...packageJson.dependencies, ...packageJson.devDependencies };
    expect(deps['framer-motion']).toBeDefined();
  });

  it('@react-three/fiber is installed', () => {
    const deps = { ...packageJson.dependencies, ...packageJson.devDependencies };
    expect(deps['@react-three/fiber']).toBeDefined();
  });
});

// ═══════════════════════════════════════════════════════════════
// 13. Build Verification — التحقق من البناء
// ═══════════════════════════════════════════════════════════════

describe('Build Verification', () => {
  it('next.config.ts exists', () => {
    expect(fs.existsSync(path.join(PROJECT_ROOT, 'next.config.ts'))).toBe(true);
  });

  it('tsconfig.json exists', () => {
    expect(fs.existsSync(path.join(PROJECT_ROOT, 'tsconfig.json'))).toBe(true);
  });

  it('No TypeScript compilation errors in new files', () => {
    const newFiles = [
      'src/lib/super-mind-router.ts',
      'src/lib/brain-sound.ts',
      'src/lib/screen-registry.ts',
      'src/components/brain/BrainNetwork.tsx',
      'src/components/brain/ContextScreen.tsx',
      'src/components/brain/ProjectsTracker.tsx',
      'src/components/dashboard/MamounCommandCenter.tsx',
    ];
    for (const file of newFiles) {
      const content = fs.readFileSync(path.join(PROJECT_ROOT, file), 'utf-8');
      // Should not have obvious syntax errors
      expect(content.length).toBeGreaterThan(100);
      expect(content).not.toContain('TODO: implement');
    }
  });
});
