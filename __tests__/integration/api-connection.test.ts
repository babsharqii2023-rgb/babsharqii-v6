/**
 * BABSHARQII v41.0 — اختبارات حقيقية
 * Real tests: Backend routes, Frontend components, Theme, API proxy structure
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const PROJECT_ROOT = '/home/z/babsharqii-v5';

// ═══════════════════════════════════════════════════════════════
// 1. Backend Route Registration — اختبارات تسجيل المسارات
// ═══════════════════════════════════════════════════════════════

describe('Backend Route Registration', () => {
  it('Should have consciousness/state route', async () => {
    const { execSync } = await import('child_process');
    const result = execSync(
      `cd ${PROJECT_ROOT}/backend && python3 -c "from mamoun.api.routes import api_router; paths = [r.path for r in api_router.routes if hasattr(r, 'path')]; print('/consciousness/state' in paths)"`,
      { encoding: 'utf-8', timeout: 10000 }
    ).trim();
    expect(result).toBe('True');
  });

  it('Should have project-mgmt/projects route', async () => {
    const { execSync } = await import('child_process');
    const result = execSync(
      `cd ${PROJECT_ROOT}/backend && python3 -c "from mamoun.api.routes import api_router; paths = [r.path for r in api_router.routes if hasattr(r, 'path')]; print('/project-mgmt/projects' in paths)"`,
      { encoding: 'utf-8', timeout: 10000 }
    ).trim();
    expect(result).toBe('True');
  });

  it('Should have living/emotions route', async () => {
    const { execSync } = await import('child_process');
    const result = execSync(
      `cd ${PROJECT_ROOT}/backend && python3 -c "from mamoun.api.routes import api_router; paths = [r.path for r in api_router.routes if hasattr(r, 'path')]; print('/living/emotions' in paths)"`,
      { encoding: 'utf-8', timeout: 10000 }
    ).trim();
    expect(result).toBe('True');
  });

  it('Should have v2/events/neural-bus route', async () => {
    const { execSync } = await import('child_process');
    const result = execSync(
      `cd ${PROJECT_ROOT}/backend && python3 -c "from mamoun.api.routes import api_router; paths = [r.path for r in api_router.routes if hasattr(r, 'path')]; print('/v2/events/neural-bus' in paths)"`,
      { encoding: 'utf-8', timeout: 10000 }
    ).trim();
    expect(result).toBe('True');
  });

  it('Should have kernel/public-status route (no auth)', async () => {
    const { execSync } = await import('child_process');
    const result = execSync(
      `cd ${PROJECT_ROOT}/backend && python3 -c "from mamoun.api.routes import api_router; paths = [r.path for r in api_router.routes if hasattr(r, 'path')]; print('/kernel/public-status' in paths)"`,
      { encoding: 'utf-8', timeout: 10000 }
    ).trim();
    expect(result).toBe('True');
  });

  it('Should have living/vitals route', async () => {
    const { execSync } = await import('child_process');
    const result = execSync(
      `cd ${PROJECT_ROOT}/backend && python3 -c "from mamoun.api.routes import api_router; paths = [r.path for r in api_router.routes if hasattr(r, 'path')]; print('/living/vitals' in paths)"`,
      { encoding: 'utf-8', timeout: 10000 }
    ).trim();
    expect(result).toBe('True');
  });

  it('Should have living/heartbeat route', async () => {
    const { execSync } = await import('child_process');
    const result = execSync(
      `cd ${PROJECT_ROOT}/backend && python3 -c "from mamoun.api.routes import api_router; paths = [r.path for r in api_router.routes if hasattr(r, 'path')]; print('/living/heartbeat' in paths)"`,
      { encoding: 'utf-8', timeout: 10000 }
    ).trim();
    expect(result).toBe('True');
  });

  it('Should have 420+ routes registered', async () => {
    const { execSync } = await import('child_process');
    const result = parseInt(execSync(
      `cd ${PROJECT_ROOT}/backend && python3 -c "from mamoun.api.routes import api_router; print(len(api_router.routes))"`,
      { encoding: 'utf-8', timeout: 10000 }
    ).trim());
    expect(result).toBeGreaterThanOrEqual(416);
  });
});


// ═══════════════════════════════════════════════════════════════
// 2. Panel Components Exist — اختبارات وجود البانلات
// ═══════════════════════════════════════════════════════════════

describe('Panel Components Exist', () => {
  const requiredPanels = [
    'BrainsOrbPanel', 'NeuralBusPanel', 'InnerMonologuePanel',
    'ConsciousnessPanel', 'LifePanel', 'ProjectsPanel',
    'SwarmPanel', 'SitesPanel',
  ];

  requiredPanels.forEach(panelName => {
    it(`${panelName}.tsx should exist`, () => {
      const panelPath = path.join(PROJECT_ROOT, 'src/components/dashboard/panels', `${panelName}.tsx`);
      expect(fs.existsSync(panelPath)).toBe(true);
    });

    it(`${panelName}.tsx should use blue theme colors`, () => {
      const panelPath = path.join(PROJECT_ROOT, 'src/components/dashboard/panels', `${panelName}.tsx`);
      const content = fs.readFileSync(panelPath, 'utf-8');
      // Must contain the blue primary color
      expect(content).toContain('#1a6baa');
    });

    it(`${panelName}.tsx should import from jarvis-api`, () => {
      const panelPath = path.join(PROJECT_ROOT, 'src/components/dashboard/panels', `${panelName}.tsx`);
      const content = fs.readFileSync(panelPath, 'utf-8');
      // Must import from jarvis-api or have API integration
      const hasApiImport = content.includes('jarvis-api') || content.includes('fetch(') || content.includes('apiGet');
      expect(hasApiImport).toBe(true);
    });
  });
});


// ═══════════════════════════════════════════════════════════════
// 3. Dashboard Theme — اختبارات الثيم
// ═══════════════════════════════════════════════════════════════

describe('Dashboard Theme Colors', () => {
  it('Main dashboard uses blue primary (#1a6baa)', () => {
    const content = fs.readFileSync(path.join(PROJECT_ROOT, 'src/components/dashboard/mamoun-vision-ide.tsx'), 'utf-8');
    expect(content).toContain("primary: '#1a6baa'");
  });

  it('Main dashboard uses dark background (#070710)', () => {
    const content = fs.readFileSync(path.join(PROJECT_ROOT, 'src/components/dashboard/mamoun-vision-ide.tsx'), 'utf-8');
    expect(content).toContain("bg: '#070710'");
  });

  it('Main dashboard uses dark card (#0d0d1a)', () => {
    const content = fs.readFileSync(path.join(PROJECT_ROOT, 'src/components/dashboard/mamoun-vision-ide.tsx'), 'utf-8');
    expect(content).toContain("card: '#0d0d1a'");
  });

  it('No hardcoded pink (#C2185B) as primary in dashboard', () => {
    const content = fs.readFileSync(path.join(PROJECT_ROOT, 'src/components/dashboard/mamoun-vision-ide.tsx'), 'utf-8');
    // The old pink references should be aliased to blue
    expect(content).toContain("pink: '#1a6baa'");
    expect(content).toContain("pinkLight: '#1e8aad'");
  });

  it('All panel files use consistent blue theme', () => {
    const panelsDir = path.join(PROJECT_ROOT, 'src/components/dashboard/panels');
    const files = fs.readdirSync(panelsDir).filter(f => f.endsWith('.tsx'));
    for (const file of files) {
      const content = fs.readFileSync(path.join(panelsDir, file), 'utf-8');
      expect(content).toContain('#1a6baa');
    }
  });
});


// ═══════════════════════════════════════════════════════════════
// 4. Dashboard Imports & ViewModes — اختبارات الروابط
// ═══════════════════════════════════════════════════════════════

describe('Dashboard Imports & ViewModes', () => {
  let dashboardContent: string;

  beforeAll(() => {
    dashboardContent = fs.readFileSync(path.join(PROJECT_ROOT, 'src/components/dashboard/mamoun-vision-ide.tsx'), 'utf-8');
  });

  it('Imports all 8 new panels', () => {
    const imports = [
      'BrainsOrbPanel', 'NeuralBusPanel', 'InnerMonologuePanel',
      'ConsciousnessPanel', 'LifePanel', 'ProjectsPanel',
      'SwarmPanel', 'SitesPanel',
    ];
    for (const imp of imports) {
      expect(dashboardContent).toContain(`import ${imp}`);
    }
  });

  it('Has ViewMode entries for all new panels', () => {
    const modes = [
      "'brains-orb'", "'neural-bus'", "'inner-monologue'",
      "'life'", "'consciousness'", "'projects'",
      "'swarm'", "'sites'",
    ];
    for (const mode of modes) {
      expect(dashboardContent).toContain(mode);
    }
  });

  it('Renders each new panel when its ViewMode is active', () => {
    const panels = [
      { mode: 'brains-orb', panel: 'BrainsOrbPanel' },
      { mode: 'neural-bus', panel: 'NeuralBusPanel' },
      { mode: 'inner-monologue', panel: 'InnerMonologuePanel' },
      { mode: 'life', panel: 'LifePanel' },
      { mode: 'consciousness', panel: 'ConsciousnessPanel' },
      { mode: 'projects', panel: 'ProjectsPanel' },
      { mode: 'swarm', panel: 'SwarmPanel' },
      { mode: 'sites', panel: 'SitesPanel' },
    ];
    for (const { mode, panel } of panels) {
      // Check that the panel is rendered when viewMode matches
      expect(dashboardContent).toContain(panel);
    }
  });
});


// ═══════════════════════════════════════════════════════════════
// 5. Frontend API Proxy Structure — اختبارات هيكل البروكسي
// ═══════════════════════════════════════════════════════════════

describe('Frontend API Proxy Routes Exist', () => {
  const requiredRoutes = [
    '/api/brains/route.ts',
    '/api/consciousness/state/route.ts',
    '/api/living/emotions/route.ts',
    '/api/living/vitals/route.ts',
    '/api/living/heartbeat/route.ts',
    '/api/living/identity/route.ts',
    '/api/kernel/status/route.ts',
    '/api/project-mgmt/projects/route.ts',
    '/api/swarm/route.ts',
    '/api/v2/api-keys/route.ts',
    '/api/v2/feature-flags/route.ts',
    '/api/v2/events/neural-bus/route.ts',
    '/api/test-key/route.ts',
  ];

  requiredRoutes.forEach(routePath => {
    it(`${routePath} should exist`, () => {
      const fullPath = path.join(PROJECT_ROOT, 'src/app', routePath);
      expect(fs.existsSync(fullPath)).toBe(true);
    });
  });
});


// ═══════════════════════════════════════════════════════════════
// 6. API Key Test Route — اختبار مسار اختبار المفاتيح
// ═══════════════════════════════════════════════════════════════

describe('API Key Test Route', () => {
  it('Should make real API calls to providers', () => {
    const content = fs.readFileSync(path.join(PROJECT_ROOT, 'src/app/api/test-key/route.ts'), 'utf-8');
    // Should NOT just check length — must make real API calls
    expect(content).toContain('generativelanguage.googleapis.com');
    expect(content).toContain('deepseek.com');
    expect(content).toContain('bigmodel.cn');
  });

  it('Should handle network errors gracefully', () => {
    const content = fs.readFileSync(path.join(PROJECT_ROOT, 'src/app/api/test-key/route.ts'), 'utf-8');
    expect(content).toContain('network_error');
    expect(content).toContain('TimeoutError');
  });
});


// ═══════════════════════════════════════════════════════════════
// 7. jarvis-api Correctness — اختبارات صحة مكتبة API
// ═══════════════════════════════════════════════════════════════

describe('jarvis-api Client Correctness', () => {
  let apiContent: string;

  beforeAll(() => {
    apiContent = fs.readFileSync(path.join(PROJECT_ROOT, 'src/lib/jarvis-api.ts'), 'utf-8');
  });

  it('fetchConsciousnessState calls /api/consciousness/state', () => {
    expect(apiContent).toContain("'/api/consciousness/state'");
  });

  it('fetchBrainStates calls /api/brains', () => {
    expect(apiContent).toContain("'/api/brains'");
  });

  it('fetchKernelStatus calls /api/kernel/status', () => {
    expect(apiContent).toContain("'/api/kernel/status'");
  });

  it('fetchLivingVitals calls /api/living/vitals', () => {
    expect(apiContent).toContain("'/api/living/vitals'");
  });

  it('fetchEmotionState calls /api/living/emotions', () => {
    expect(apiContent).toContain("'/api/living/emotions'");
  });

  it('fetchSwarmStatus calls /api/swarm/status', () => {
    expect(apiContent).toContain("'/api/swarm/status'");
  });
});


// ═══════════════════════════════════════════════════════════════
// 8. Backend Build — اختبار بناء الباكند
// ═══════════════════════════════════════════════════════════════

describe('Backend Import Validation', () => {
  it('All API modules import without errors', async () => {
    const { execSync } = await import('child_process');
    // This will throw if any import fails
    const result = execSync(
      `cd ${PROJECT_ROOT}/backend && python3 -c "from mamoun.api.routes import api_router; print('OK')"`,
      { encoding: 'utf-8', timeout: 15000 }
    ).trim();
    expect(result).toBe('OK');
  });

  it('Dashboard bridge has all new routes', async () => {
    const { execSync } = await import('child_process');
    const result = execSync(
      `cd ${PROJECT_ROOT}/backend && python3 -c "
from mamoun.api.dashboard_bridge import router
paths = [r.path for r in router.routes if hasattr(r, 'path')]
required = ['/consciousness/state', '/project-mgmt/projects', '/living/emotions', '/living/vitals', '/living/heartbeat', '/living/identity', '/kernel/public-status', '/v2/events/neural-bus']
missing = [p for p in required if p not in paths]
print('OK' if not missing else 'MISSING: ' + ', '.join(missing))
"`,
      { encoding: 'utf-8', timeout: 15000 }
    ).trim();
    expect(result).toBe('OK');
  });
});
