/**
 * BABSHARQII v42.0 — Project Management Projects API Route
 * مسار API لإدارة المشاريع
 * Backend endpoint: GET /api/project-mgmt/registry/projects
 * Fallback: kernel/projects or static data
 */

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

const FALLBACK_PROJECTS = {
  projects: [
    { id: 'p1', name: 'n8n Workflows', nameAr: 'أتمتة n8n', category: 'automation', categoryAr: 'أتمتة', status: 'active', progress: 65, leadingBrain: 'neural', tasks: { total: 20, completed: 12 } },
    { id: 'p2', name: 'E-Commerce Store', nameAr: 'المتجر الإلكتروني', category: 'websites', categoryAr: 'مواقع', status: 'active', progress: 40, leadingBrain: 'causal', tasks: { total: 8, completed: 3 } },
    { id: 'p3', name: 'Mobile App', nameAr: 'تطبيق جوال', category: 'apps', categoryAr: 'تطبيقات', status: 'idle', progress: 15, leadingBrain: 'symbolic', tasks: { total: 15, completed: 2 } },
    { id: 'p4', name: 'UI Design System', nameAr: 'نظام التصميم', category: 'design', categoryAr: 'تصميم', status: 'active', progress: 80, leadingBrain: 'world_model', tasks: { total: 10, completed: 8 } },
    { id: 'p5', name: 'Social Media Bot', nameAr: 'بوت التواصل', category: 'automation', categoryAr: 'أتمتة', status: 'paused', progress: 30, leadingBrain: 'bayesian', tasks: { total: 6, completed: 2 } },
    { id: 'p6', name: 'Portfolio Site', nameAr: 'موقع الأعمال', category: 'websites', categoryAr: 'مواقع', status: 'completed', progress: 100, leadingBrain: 'neural', tasks: { total: 5, completed: 5 } },
  ],
  fallback: true,
};

export async function GET() {
  // Try primary: project-mgmt/registry/projects
  try {
    const res = await fetch(`${BACKEND_URL}/api/project-mgmt/registry/projects`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data, {
        headers: { 'X-Data-Source': 'backend' },
      });
    }
  } catch {
    // project-mgmt unavailable
  }

  // Fallback 1: Try kernel/projects
  try {
    const res = await fetch(`${BACKEND_URL}/api/kernel/projects`, {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(
        { ...data, fallback: true, source: 'kernel/projects' },
        { headers: { 'X-Data-Source': 'backend-fallback' } }
      );
    }
  } catch {
    // kernel/projects also unavailable
  }

  // Fallback 2: Static data
  return NextResponse.json(FALLBACK_PROJECTS, {
    headers: { 'X-Data-Source': 'fallback', 'X-Backend-Online': 'false' },
  });
}
