'use client';

import React, { useState, useEffect } from 'react';
import { Globe, ChevronLeft, Cloud, CheckCircle2, XCircle, RefreshCw, Clock, ArrowUpDown } from 'lucide-react';

const P = {
  bg: '#070710', card: '#0d0d1a', primary: '#1a6baa', primaryLight: '#1e8aad', primaryDark: '#0a4a6e',
  primaryDim: 'rgba(26,107,170,0.08)', primaryMid: 'rgba(26,107,170,0.15)', primaryStrong: 'rgba(26,107,170,0.3)',
  textPrimary: '#c8d4e8', textSecondary: '#5a6a80',
  white: '#FFFFFF', white90: 'rgba(255,255,255,0.9)', white08: 'rgba(255,255,255,0.08)',
  green: '#4CAF50', orange: '#FF9800', red: '#EF4444',
};

interface Site {
  id: string; url: string; name: string; status: 'online' | 'offline' | 'deploying';
  health: number; lastDeploy: string; branch: string;
}

const DEMO_SITES: Site[] = [
  { id: '1', url: 'https://ai.babsharqii.com', name: 'مأمون الرئيسي', status: 'online', health: 98, lastDeploy: 'منذ ساعتين', branch: 'main' },
  { id: '2', url: 'https://api.babsharqii.com', name: 'API الباكند', status: 'online', health: 95, lastDeploy: 'منذ 5 ساعات', branch: 'main' },
  { id: '3', url: 'https://staging.babsharqii.com', name: 'بيئة الاختبار', status: 'offline', health: 0, lastDeploy: 'منذ يومين', branch: 'develop' },
];

interface DeployEvent {
  id: number; time: string; message: string; type: 'success' | 'error' | 'info';
}

interface Props { onBack: () => void; }

export default function SitesPanel({ onBack }: Props) {
  const [sites, setSites] = useState<Site[]>(DEMO_SITES);
  const [deploys, setDeploys] = useState<DeployEvent[]>([
    { id: 1, time: '14:30', message: 'نشر ناجح على main — v40.2', type: 'success' },
    { id: 2, time: '12:15', message: 'فحص التحديثات — لا توجد تغييرات', type: 'info' },
    { id: 3, time: '10:00', message: 'فشل النشر على develop — خطأ بناء', type: 'error' },
    { id: 4, time: '08:45', message: 'سحب التحديثات من GitHub — 3 commits', type: 'info' },
    { id: 5, time: '06:00', message: 'نشر ناجح على main — v40.1', type: 'success' },
  ]);
  const [syncing, setSyncing] = useState(false);
  const [updateStatus, setUpdateStatus] = useState<Record<string, unknown> | null>(null);

  // فحص التحديثات
  const checkUpdates = async () => {
    setSyncing(true);
    try {
      const res = await fetch('/api/v2/command', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: 'تحقق من التحديثات', lang: 'ar' }),
      });
      if (res.ok) {
        const data = await res.json();
        setUpdateStatus(data);
      }
    } catch { /* fallback */ }
    setSyncing(false);
  };

  // سحب وتطبيق
  const pullAndApply = async () => {
    setSyncing(true);
    try {
      const res = await fetch('/api/update/pull', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
      if (res.ok) {
        const data = await res.json();
        setDeploys(prev => [{ id: Date.now(), time: new Date().toLocaleTimeString('ar', { hour: '2-digit', minute: '2-digit' }), message: `سحب التحديثات — ${data.commits || 0} commits`, type: 'success' }, ...prev]);
      }
    } catch { /* fallback */ }
    setSyncing(false);
  };

  return (
    <div dir="rtl" style={{ background: P.bg, minHeight: '100vh', color: P.textPrimary, fontFamily: 'Tajawal, sans-serif' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px', borderBottom: `1px solid ${P.white08}` }}>
        <button onClick={onBack} style={{ background: P.primaryDim, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
          <ChevronLeft className="w-4 h-4" />
        </button>
        <Globe className="w-5 h-5" style={{ color: P.primary }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: P.white }}>المواقع والنشر</div>
          <div style={{ fontSize: 11, color: P.textSecondary }}>إدارة النشر + تحديثات GitHub + صحة المواقع</div>
        </div>
        <button onClick={checkUpdates} disabled={syncing}
          style={{ background: P.primaryMid, border: `1px solid ${P.primaryStrong}`, color: P.primaryLight, borderRadius: 8, padding: '6px 12px', cursor: syncing ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, opacity: syncing ? 0.6 : 1 }}>
          <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} /> فحص التحديثات
        </button>
        <button onClick={pullAndApply} disabled={syncing}
          style={{ background: P.green + '20', border: `1px solid ${P.green}40`, color: P.green, borderRadius: 8, padding: '6px 12px', cursor: syncing ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, opacity: syncing ? 0.6 : 1 }}>
          <ArrowUpDown className="w-3.5 h-3.5" /> سحب + تطبيق
        </button>
      </div>

      <div style={{ display: 'flex', gap: 16, padding: 16, height: 'calc(100vh - 60px)' }}>
        {/* بطاقات المواقع */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {sites.map(site => (
            <div key={site.id} style={{ background: P.card, borderRadius: 12, padding: 16, border: `1px solid ${site.status === 'online' ? P.green + '30' : site.status === 'offline' ? P.red + '30' : P.orange + '30'}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                <div style={{ width: 36, height: 36, borderRadius: 8, background: P.primaryMid, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Globe className="w-4 h-4" style={{ color: P.primaryLight }} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: P.white90 }}>{site.name}</div>
                  <div style={{ fontSize: 9, color: P.textSecondary }}>{site.url}</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: site.status === 'online' ? P.green : site.status === 'offline' ? P.red : P.orange }}>
                  {site.status === 'online' ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                  {{ online: 'متصل', offline: 'غير متصل', deploying: 'ينشر' }[site.status]}
                </div>
              </div>

              <div style={{ display: 'flex', gap: 16, fontSize: 10, color: P.textSecondary }}>
                <span>الصحة: <span style={{ color: site.health > 90 ? P.green : P.orange, fontWeight: 600 }}>{site.health}%</span></span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}><Clock className="w-3 h-3" /> آخر نشر: {site.lastDeploy}</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}><Cloud className="w-3 h-3" /> {site.branch}</span>
              </div>

              {/* شريط الصحة */}
              <div style={{ height: 3, borderRadius: 2, background: P.primaryDim, marginTop: 8 }}>
                <div style={{ width: `${site.health}%`, height: '100%', borderRadius: 2, background: site.health > 90 ? P.green : P.orange, transition: 'width 0.5s' }} />
              </div>
            </div>
          ))}

          {/* حالة التحديث */}
          {updateStatus && (
            <div style={{ background: P.card, borderRadius: 12, padding: 16, border: `1px solid ${P.primaryStrong}` }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: P.primaryLight, marginBottom: 8 }}>آخر فحص للتحديثات</div>
              <pre style={{ fontSize: 10, color: P.textPrimary, whiteSpace: 'pre-wrap', maxHeight: 100, overflow: 'auto' }}>
                {JSON.stringify(updateStatus, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* خط زمني النشر */}
        <div style={{ width: 300, display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: P.white90, marginBottom: 10 }}>سجل النشر</div>
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {deploys.map(d => (
              <div key={d.id} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: d.type === 'success' ? P.green : d.type === 'error' ? P.red : P.primary, marginTop: 4, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: P.textPrimary }}>{d.message}</div>
                  <div style={{ fontSize: 9, color: P.textSecondary }}>{d.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
