import { NextResponse } from 'next/server';

// Working Memory API — Tries real backend first, falls back to simulated data
const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

// Fallback working memory items
const fallbackItems = [
  { id: 'wm-001', content: 'المستخدم يريد بناء تطبيق توصيل طعام', type: 'goal', salience: 0.95, accessCount: 12, createdAt: Date.now() - 300000, lastAccessed: Date.now() - 30000 },
  { id: 'wm-002', content: 'دراسة جدوى لمشروع التوصيل — التكاليف 50K-200K', type: 'research', salience: 0.88, accessCount: 8, createdAt: Date.now() - 250000, lastAccessed: Date.now() - 60000 },
  { id: 'wm-003', content: 'المستخدم فضّل Next.js + React Native', type: 'context', salience: 0.82, accessCount: 6, createdAt: Date.now() - 200000, lastAccessed: Date.now() - 90000 },
  { id: 'wm-004', content: 'خطة تسويقية — منصات: انستغرام + تيك توك', type: 'task', salience: 0.75, accessCount: 4, createdAt: Date.now() - 150000, lastAccessed: Date.now() - 120000 },
  { id: 'wm-005', content: 'API endpoint للتواصل مع المطاعم — REST + WebSocket', type: 'skill', salience: 0.68, accessCount: 3, createdAt: Date.now() - 100000, lastAccessed: Date.now() - 180000 },
  { id: 'wm-006', content: 'خطأ: DeepSeek API timeout — يستخدم fallback لـ GLM', type: 'error', salience: 0.45, accessCount: 2, createdAt: Date.now() - 80000, lastAccessed: Date.now() - 200000 },
  { id: 'wm-007', content: 'المستخدم يتحدث بالعربية — جميع الردود عربي', type: 'general', salience: 0.30, accessCount: 15, createdAt: Date.now() - 500000, lastAccessed: Date.now() - 5000 },
];

export async function GET() {
  // Try real backend first
  try {
    const res = await fetch(`${BACKEND_URL}/api/kernel/working-memory`, {
      signal: AbortSignal.timeout(3000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch {
    // Backend not available — use fallback
  }

  // Fallback: simulated data
  return NextResponse.json({
    items: fallbackItems,
    capacity: 7,
    utilization: fallbackItems.length / 7,
    avgSalience: fallbackItems.reduce((a, b) => a + b.salience, 0) / fallbackItems.length,
    lastUpdated: Date.now(),
    source: 'fallback',
  });
}
