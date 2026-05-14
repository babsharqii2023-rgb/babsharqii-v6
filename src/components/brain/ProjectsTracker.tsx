// ═══════════════════════════════════════════════════════════════════
// ProjectsTracker — متتبع المشاريع (كانبان)
// Kanban-style project list with status columns
// ═══════════════════════════════════════════════════════════════════

'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { fetchProjects, type ProjectInfo } from '@/lib/jarvis-api';

interface ProjectsTrackerProps {
  onBack?: () => void;
}

const COLUMNS = [
  { id: 'thinking', label: 'يفكر', labelEn: 'Thinking', color: '#ffd740' },
  { id: 'proposed', label: 'مقترح', labelEn: 'Proposed', color: '#448aff' },
  { id: 'working', label: 'يعمل', labelEn: 'Working', color: '#69f0ae' },
  { id: 'done', label: 'مكتمل', labelEn: 'Done', color: '#00e5ff' },
];

export default function ProjectsTracker({ onBack }: ProjectsTrackerProps) {
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProjects()
      .then(data => setProjects(data.projects || []))
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));
  }, []);

  const getProjectStatus = (status: string): string => {
    switch (status) {
      case 'active': return 'working';
      case 'paused': return 'proposed';
      case 'idle': return 'thinking';
      case 'completed': return 'done';
      default: return 'thinking';
    }
  };

  return (
    <div style={{ padding: 16, height: '100%', overflow: 'auto' }}>
      <div style={{ display: 'flex', gap: 12, height: '100%', minHeight: 0 }}>
        {COLUMNS.map(col => {
          const colProjects = projects.filter(p => getProjectStatus(p.status) === col.id);
          return (
            <div key={col.id} style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              background: 'rgba(255,255,255,0.02)',
              borderRadius: 8,
              border: `1px solid rgba(255,255,255,0.06)`,
              overflow: 'hidden',
            }}>
              {/* Column header */}
              <div style={{
                padding: '10px 12px',
                borderBottom: `2px solid ${col.color}30`,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: col.color,
                }} />
                <span style={{ fontSize: 12, fontWeight: 700, color: col.color }}>
                  {col.label}
                </span>
                <span style={{
                  fontSize: 10, color: '#5a6a80',
                  background: 'rgba(255,255,255,0.04)',
                  borderRadius: 8,
                  padding: '1px 6px',
                }}>
                  {colProjects.length}
                </span>
              </div>

              {/* Column cards */}
              <div style={{
                flex: 1, overflowY: 'auto', padding: 8,
                display: 'flex', flexDirection: 'column', gap: 6,
              }}>
                {loading ? (
                  <div style={{ textAlign: 'center', color: '#5a6a80', fontSize: 10, padding: 20 }}>
                    جاري التحميل...
                  </div>
                ) : colProjects.length === 0 ? (
                  <div style={{ textAlign: 'center', color: '#5a6a80', fontSize: 10, padding: 20, opacity: 0.5 }}>
                    لا توجد مشاريع
                  </div>
                ) : (
                  colProjects.map((project, i) => (
                    <motion.div
                      key={project.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      style={{
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(255,255,255,0.06)',
                        borderRadius: 6,
                        padding: '8px 10px',
                      }}
                    >
                      <div style={{ fontSize: 11, fontWeight: 600, color: '#c8d0e0', marginBottom: 4 }}>
                        {project.nameAr || project.name}
                      </div>
                      <div style={{ fontSize: 9, color: '#5a6a80' }}>
                        {project.categoryAr || project.category}
                      </div>
                      {project.progress > 0 && (
                        <div style={{ marginTop: 6 }}>
                          <div style={{
                            height: 3, borderRadius: 2,
                            background: 'rgba(255,255,255,0.06)',
                            overflow: 'hidden',
                          }}>
                            <div style={{
                              height: '100%', borderRadius: 2,
                              background: col.color,
                              width: `${project.progress}%`,
                              opacity: 0.7,
                            }} />
                          </div>
                          <div style={{ fontSize: 8, color: '#5a6a80', marginTop: 2 }}>
                            {project.progress}%
                          </div>
                        </div>
                      )}
                    </motion.div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
