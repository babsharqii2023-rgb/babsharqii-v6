'use client';

import React, { useState, useEffect } from 'react';
import { FolderOpen, ChevronLeft, Plus, Clock, Users, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { fetchProjects, setAuthToken } from '@/lib/jarvis-api';

const P = {
  bg: '#070710', card: '#0d0d1a', primary: '#1a6baa', primaryLight: '#1e8aad', primaryDark: '#0a4a6e',
  primaryDim: 'rgba(26,107,170,0.08)', primaryMid: 'rgba(26,107,170,0.15)', primaryStrong: 'rgba(26,107,170,0.3)',
  textPrimary: '#c8d4e8', textSecondary: '#5a6a80',
  white: '#FFFFFF', white90: 'rgba(255,255,255,0.9)', white08: 'rgba(255,255,255,0.08)',
  green: '#4CAF50', orange: '#FF9800', red: '#EF4444',
};

interface Props { onBack: () => void; }

export default function ProjectsPanel({ onBack }: Props) {
  const [projects, setProjects] = useState<Record<string, unknown>[]>([]);
  const [filter, setFilter] = useState<'all' | 'active' | 'completed' | 'paused'>('all');
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchProjects();
        if (data?.projects?.length) setProjects(data.projects as unknown as Record<string, unknown>[]);
      } catch { /* fallback */ }
    };
    load();
    const iv = setInterval(load, 15000);
    return () => clearInterval(iv);
  }, []);

  // بيانات تجريبية
  useEffect(() => {
    if (projects.length === 0) {
      setProjects([
        { id: '1', name: 'تطوير واجهة المستخدم', status: 'active', progress: 72, tasks: 18, completed_tasks: 13, priority: 'high', agents: 3 },
        { id: '2', name: 'نظام التداول الآلي', status: 'active', progress: 45, tasks: 24, completed_tasks: 11, priority: 'medium', agents: 2 },
        { id: '3', name: 'تحسين نموذج اللغة', status: 'paused', progress: 30, tasks: 10, completed_tasks: 3, priority: 'low', agents: 1 },
        { id: '4', name: 'تكامل انستقرام', status: 'completed', progress: 100, tasks: 8, completed_tasks: 8, priority: 'medium', agents: 2 },
      ]);
    }
  }, [projects.length]);

  const filtered = filter === 'all' ? projects : projects.filter(p => p.status === filter);

  const statusConfig: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
    active: { color: P.green, label: 'نشط', icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
    paused: { color: P.orange, label: 'متوقف', icon: <AlertCircle className="w-3.5 h-3.5" /> },
    completed: { color: P.primaryLight, label: 'مكتمل', icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
  };

  const createProject = async () => {
    if (!newName.trim()) return;
    try {
      // استخدام مسار الباكند الصحيح مع auth headers
      const token = typeof window !== 'undefined' ? localStorage.getItem('mamoun_auth_token') : '';
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      
      const res = await fetch('/api/project-mgmt/registry/register', {
        method: 'POST',
        headers,
        body: JSON.stringify({ name: newName, description: '', category: '' }),
      });
      if (res.ok) { setNewName(''); setShowNew(false); }
    } catch { /* */ }
  };

  return (
    <div dir="rtl" style={{ background: P.bg, minHeight: '100vh', color: P.textPrimary, fontFamily: 'Tajawal, sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px', borderBottom: `1px solid ${P.white08}` }}>
        <button onClick={onBack} style={{ background: P.primaryDim, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
          <ChevronLeft className="w-4 h-4" />
        </button>
        <FolderOpen className="w-5 h-5" style={{ color: P.primary }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: P.white }}>المشاريع</div>
          <div style={{ fontSize: 11, color: P.textSecondary }}>إدارة المشاريع والمهام — ProjectOrchestrator</div>
        </div>
        <button onClick={() => setShowNew(true)} style={{ background: P.primaryMid, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
          <Plus className="w-3.5 h-3.5" /> مشروع جديد
        </button>
      </div>

      <div style={{ padding: 20, height: 'calc(100vh - 60px)', overflowY: 'auto' }}>
        {/* تصفية */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
          {(['all', 'active', 'paused', 'completed'] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              style={{
                background: filter === f ? P.primaryMid : P.primaryDim,
                border: `1px solid ${filter === f ? P.primaryStrong : P.white08}`,
                color: filter === f ? P.primaryLight : P.textSecondary,
                borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontSize: 10,
              }}>
              {{ all: 'الكل', active: 'نشط', paused: 'متوقف', completed: 'مكتمل' }[f]}
            </button>
          ))}
        </div>

        {/* نموذج مشروع جديد */}
        {showNew && (
          <div style={{ background: P.card, borderRadius: 12, padding: 16, border: `1px solid ${P.primaryStrong}`, marginBottom: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: P.white90, marginBottom: 10 }}>مشروع جديد</div>
            <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="اسم المشروع..."
              style={{ width: '100%', background: P.primaryDim, border: `1px solid ${P.white08}`, borderRadius: 8, padding: '8px 12px', color: P.white, fontSize: 12, outline: 'none', marginBottom: 10 }}
              dir="rtl" />
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={createProject} style={{ background: P.primaryMid, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px 16px', cursor: 'pointer', fontSize: 11 }}>إنشاء</button>
              <button onClick={() => setShowNew(false)} style={{ background: P.primaryDim, border: `1px solid ${P.white08}`, color: P.textSecondary, borderRadius: 8, padding: '6px 16px', cursor: 'pointer', fontSize: 11 }}>إلغاء</button>
            </div>
          </div>
        )}

        {/* بطاقات المشاريع */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {filtered.map(project => {
            const p = project;
            const progress = (p.progress as number) || 0;
            const sc = statusConfig[String(p.status)] || statusConfig.active;
            return (
              <div key={String(project.id)} style={{ background: P.card, borderRadius: 12, padding: 16, border: `1px solid ${P.white08}` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <div style={{ width: 36, height: 36, borderRadius: 8, background: P.primaryMid, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <FolderOpen className="w-4 h-4" style={{ color: P.primaryLight }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: P.white90 }}>{String(project.name)}</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: sc.color, marginTop: 2 }}>
                      {sc.icon} {sc.label}
                    </div>
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: P.primaryLight }}>{progress}%</div>
                </div>

                {/* شريط التقدم */}
                <div style={{ height: 4, borderRadius: 2, background: P.primaryDim, marginBottom: 10 }}>
                  <div style={{ width: `${progress}%`, height: '100%', borderRadius: 2, background: progress === 100 ? P.green : P.primaryLight, transition: 'width 0.5s' }} />
                </div>

                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: P.textSecondary }}>
                  <span>المهام: {String(p.completed_tasks || 0)}/{String(p.tasks || 0)}</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}><Users className="w-3 h-3" /> {String(p.agents || 1)} وكلاء</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}><Clock className="w-3 h-3" /> {p.priority === 'high' ? 'أولوية عالية' : p.priority === 'medium' ? 'أولوية متوسطة' : 'أولوية منخفضة'}</span>
                </div>
              </div>
            );
          })}
        </div>

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <FolderOpen className="w-10 h-10" style={{ color: P.textSecondary, margin: '0 auto 12px' }} />
            <div style={{ fontSize: 13, color: P.textSecondary }}>لا توجد مشاريع</div>
          </div>
        )}
      </div>
    </div>
  );
}
