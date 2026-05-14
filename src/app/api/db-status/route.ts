import { NextResponse } from 'next/server';
import { callBackendJSON, isBackendAvailable } from '@/lib/backend';

// =============================================================================
// BABSHARQII v5.0 — Database Status API
// Checks database connections via Python backend when available,
// falls back to local status when backend is down.
// =============================================================================

interface DbStatus {
  name: string;
  nameAr: string;
  connected: boolean;
  message: string;
  messageAr: string;
  stats?: Record<string, number | string>;
}

const fallbackDatabases: DbStatus[] = [
  {
    name: 'Neo4j',
    nameAr: 'نيو4ج',
    connected: false,
    message: 'Not connected — requires setup',
    messageAr: 'غير متصل — يتطلب إعداد قاعدة البيانات',
  },
  {
    name: 'PostgreSQL',
    nameAr: 'بوستجري إس كيو إل',
    connected: false,
    message: 'Not connected — requires setup',
    messageAr: 'غير متصل — يتطلب إعداد قاعدة البيانات',
  },
  {
    name: 'ChromaDB',
    nameAr: 'كروما دي بي',
    connected: false,
    message: 'Not connected — requires setup',
    messageAr: 'غير متصل — يتطلب إعداد قاعدة البيانات',
  },
];

export async function GET() {
  try {
    // Try fetching real database status from Python backend
    const backendUp = await isBackendAvailable();

    if (backendUp) {
      const backendData = await callBackendJSON<{
        databases?: DbStatus[];
        overall_connected?: boolean;
        connected_count?: number;
        total_count?: number;
      }>('/api/db-status');

      if (backendData && Array.isArray(backendData.databases)) {
        return NextResponse.json({
          databases: backendData.databases,
          overallConnected: backendData.overall_connected ?? backendData.databases.every((db) => db.connected),
          connectedCount: backendData.connected_count ?? backendData.databases.filter((db) => db.connected).length,
          totalCount: backendData.total_count ?? backendData.databases.length,
          source: 'python_backend',
        });
      }
    }

    // Fallback: return local static status
    return NextResponse.json({
      databases: fallbackDatabases,
      overallConnected: fallbackDatabases.every((db) => db.connected),
      connectedCount: fallbackDatabases.filter((db) => db.connected).length,
      totalCount: fallbackDatabases.length,
      source: 'local_fallback',
    });
  } catch (error) {
    console.error('DB Status Error:', error);
    return NextResponse.json(
      { error: 'فشل في جلب حالة قواعد البيانات' },
      { status: 500 }
    );
  }
}
