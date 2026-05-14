import { NextRequest, NextResponse } from 'next/server';
import { writeFile, readFile, mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';

// =============================================================================
// BABSHARQII v5.0 — Self-Modification API Endpoint
// Backend endpoint: GET /api/kernel/self-modify/status, POST /api/kernel/self-modify/propose
// Proxies to the Python backend when available, falls back to local logic.
// =============================================================================

const BACKEND_URL = process.env.MAMOUN_BACKEND_URL || 'http://localhost:8000';

const PROJECT_ROOT = process.cwd();
const SRC_DIR = path.join(PROJECT_ROOT, 'src');
const BACKUP_DIR = path.join(PROJECT_ROOT, '.self-modify-backups');

// Files that can NEVER be modified via this endpoint
const IMMUTABLE_FILES = [
  'kernel.ts',
  'watchdog.ts',
  'self-modifier.ts',
  'self-healing.ts',
  'self-awareness.ts',
];

// Dangerous patterns that must never appear in patched code
const DANGEROUS_PATTERNS: Array<{ pattern: RegExp; label: string }> = [
  { pattern: /\beval\s*\(/, label: 'eval() usage' },
  { pattern: /process\.exit/, label: 'process.exit() call' },
  { pattern: /require\s*\(\s*['"]child_process['"]/, label: 'child_process import' },
  { pattern: /require\s*\(\s*['"]fs['"]/, label: 'direct fs require (already imported above)' },
  { pattern: /\.env\b/, label: '.env access' },
  { pattern: /import\s+.*from\s+['"]fs['"]/, label: 'fs import in patched code' },
  { pattern: /import\s+.*from\s+['"]child_process['"]/, label: 'child_process import' },
  { pattern: /import\s+.*from\s+['"]os['"]/, label: 'os import' },
  { pattern: /import\s+.*from\s+['"]crypto['"]/, label: 'crypto import (not allowed in patches)' },
];

// =============================================================================
// Helper: Validate origin (same-origin only)
// =============================================================================

function isSameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get('origin');
  const host = request.headers.get('host');

  if (!origin && !host) return true; // Server-to-server or same-origin

  if (origin) {
    try {
      const originHost = new URL(origin).host;
      return originHost === host;
    } catch {
      return false;
    }
  }

  return true;
}

// =============================================================================
// Helper: Resolve target file path safely
// =============================================================================

function resolveTargetPath(targetFile: string): string | null {
  // Target file should be like /api/chat/route.ts or a relative path
  let relativePath = targetFile;

  // Remove leading slash
  if (relativePath.startsWith('/')) {
    relativePath = relativePath.substring(1);
  }

  // Convert API route path to file system path
  if (relativePath.startsWith('api/')) {
    relativePath = `app/${relativePath}`;
    if (!relativePath.endsWith('/route.ts') && !relativePath.endsWith('/route.js')) {
      relativePath = `${relativePath}/route.ts`;
    }
  }

  const fullPath = path.join(SRC_DIR, relativePath);

  // Security: ensure the resolved path is within src/
  const normalizedFull = path.normalize(fullPath);
  const normalizedSrc = path.normalize(SRC_DIR);

  if (!normalizedFull.startsWith(normalizedSrc)) {
    return null; // Path traversal attack
  }

  // Check immutable files
  const fileName = path.basename(normalizedFull);
  if (IMMUTABLE_FILES.includes(fileName)) {
    return null; // Immutable file
  }

  return normalizedFull;
}

// =============================================================================
// Helper: Validate patched code for safety
// =============================================================================

function validateCode(code: string): { valid: boolean; violations: string[] } {
  const violations: string[] = [];

  for (const { pattern, label } of DANGEROUS_PATTERNS) {
    if (pattern.test(code)) {
      violations.push(label);
    }
  }

  // Check for unknown outbound fetch domains
  const fetchRegex = /fetch\s*\(\s*['"]([^'"]+)['"]/g;
  let fetchMatch: RegExpExecArray | null;
  while ((fetchMatch = fetchRegex.exec(code)) !== null) {
    const url = fetchMatch[1];
    if (url.startsWith('http') && !url.includes('localhost') && !url.includes('127.0.0.1')) {
      violations.push(`External fetch to: ${url}`);
    }
  }

  // Check for empty code
  if (!code.trim()) {
    violations.push('Empty code');
  }

  return { valid: violations.length === 0, violations };
}

// =============================================================================
// Helper: Create backup of original file
// =============================================================================

async function createBackup(filePath: string): Promise<string> {
  if (!existsSync(BACKUP_DIR)) {
    await mkdir(BACKUP_DIR, { recursive: true });
  }

  const relativePath = path.relative(SRC_DIR, filePath);
  const timestamp = Date.now();
  const backupFileName = `${relativePath.replace(/[/.]/g, '_')}_${timestamp}.bak`;
  const backupPath = path.join(BACKUP_DIR, backupFileName);

  const originalContent = await readFile(filePath, 'utf-8');
  await writeFile(backupPath, originalContent, 'utf-8');

  return backupPath;
}

// =============================================================================
// Helper: Read source code (for GET requests)
// =============================================================================

async function readSourceCode(filePath: string): Promise<string | null> {
  try {
    if (!existsSync(filePath)) return null;
    return await readFile(filePath, 'utf-8');
  } catch {
    return null;
  }
}

// =============================================================================
// GET: Read source code of a file
// =============================================================================

export async function GET(request: NextRequest) {
  // Auth check — self-modify requires authenticated session
  const authToken = request.cookies.get('mamoun_auth_token')?.value
    || request.headers.get('authorization')?.replace('Bearer ', '');
  if (!authToken) {
    return NextResponse.json(
      { error: 'مطلوب تسجيل الدخول — هذا المسار محمي بالمصادقة' },
      { status: 401 }
    );
  }

  // Try real backend first
  try {
    const headers: Record<string, string> = {};
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    const res = await fetch(`${BACKEND_URL}/api/kernel/self-modify/history`, {
      headers,
      signal: AbortSignal.timeout(3000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch {}

  // Fallback to local file-based logic
  // Same-origin check
  if (!isSameOrigin(request)) {
    return NextResponse.json(
      { error: 'طلب من مصدر غير مصرح به' },
      { status: 403 }
    );
  }

  const { searchParams } = new URL(request.url);
  const targetFile = searchParams.get('file') || searchParams.get('_source') && request.nextUrl.pathname.replace('/api/self-modify', '');

  if (!targetFile) {
    return NextResponse.json(
      { error: 'يجب تحديد الملف المطلوب' },
      { status: 400 }
    );
  }

  const resolvedPath = resolveTargetPath(targetFile);
  if (!resolvedPath) {
    return NextResponse.json(
      { error: 'الملف غير موجود أو محمي من القراءة' },
      { status: 404 }
    );
  }

  const source = await readSourceCode(resolvedPath);
  if (source === null) {
    return NextResponse.json(
      { error: 'لم يتم العثور على الكود المصدري' },
      { status: 404 }
    );
  }

  return NextResponse.json({
    source,
    filePath: targetFile,
    // VULN-002 Fix: Removed resolvedPath (internal server path)
    lineCount: source.split('\n').length,
    lastModified: Date.now(),
  });
}

// =============================================================================
// POST: Apply patch or rollback
// =============================================================================

export async function POST(request: NextRequest) {
  // Auth check — self-modify requires authenticated session
  const authToken = request.cookies.get('mamoun_auth_token')?.value
    || request.headers.get('authorization')?.replace('Bearer ', '');
  if (!authToken) {
    return NextResponse.json(
      { error: 'مطلوب تسجيل الدخول — هذا المسار محمي بالمصادقة' },
      { status: 401 }
    );
  }

  // Read body once so it can be used by both backend proxy and fallback
  let body: any;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }

  // Try real backend first
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    const res = await fetch(`${BACKEND_URL}/api/kernel/self-modify/propose`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(3000),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch {}

  // Fallback to local file-based logic
  // Same-origin check
  if (!isSameOrigin(request)) {
    return NextResponse.json(
      { error: 'طلب من مصدر غير مصرح به' },
      { status: 403 }
    );
  }

  try {
    const { action, targetFile, patchedCode, originalCode, backupPath } = body as {
      action: 'apply_patch' | 'rollback' | 'list_backups';
      targetFile?: string;
      patchedCode?: string;
      originalCode?: string;
      backupPath?: string;
    };

    switch (action) {
      // ----- Apply Patch -----
      case 'apply_patch': {
        if (!targetFile || !patchedCode) {
          return NextResponse.json(
            { error: 'يجب تحديد الملف والكود المصحح' },
            { status: 400 }
          );
        }

        const resolvedPath = resolveTargetPath(targetFile);
        if (!resolvedPath) {
          return NextResponse.json(
            { error: 'الملف محمي أو غير صالح للتعديل' },
            { status: 403 }
          );
        }

        // Validate the patched code
        const validation = validateCode(patchedCode);
        if (!validation.valid) {
          return NextResponse.json(
            {
              error: 'الكود المصحح يحتوي على أنماط غير آمنة',
              violations: validation.violations,
            },
            { status: 400 }
          );
        }

        // Verify the current file content matches what we expect
        const currentContent = await readSourceCode(resolvedPath);
        if (currentContent && originalCode) {
          // Soft match: check if the first 200 chars match
          const currentTrimmed = currentContent.trim().substring(0, 200);
          const expectedTrimmed = originalCode.trim().substring(0, 200);
          if (currentTrimmed !== expectedTrimmed) {
            return NextResponse.json(
              {
                error: 'محتوى الملف الحالي لا يتطابق مع المتوقع — قد يكون تم تعديله خارجياً',
                currentPreview: currentTrimmed,
                expectedPreview: expectedTrimmed,
              },
              { status: 409 }
            );
          }
        }

        // Create backup before modifying
        let createdBackupPath = '';
        if (existsSync(resolvedPath)) {
          try {
            createdBackupPath = await createBackup(resolvedPath);
          } catch (backupError) {
            console.error('[SelfModify] Failed to create backup:', backupError);
            return NextResponse.json(
              { error: 'فشل في إنشاء نسخة احتياطية — تم إلغاء التعديل' },
              { status: 500 }
            );
          }
        }

        // Write the patched code
        try {
          // Ensure directory exists
          const dir = path.dirname(resolvedPath);
          if (!existsSync(dir)) {
            await mkdir(dir, { recursive: true });
          }

          await writeFile(resolvedPath, patchedCode, 'utf-8');
        } catch (writeError) {
          console.error('[SelfModify] Failed to write patched code:', writeError);

          // Attempt to restore from backup
          if (createdBackupPath && existsSync(createdBackupPath)) {
            try {
              const backupContent = await readFile(createdBackupPath, 'utf-8');
              await writeFile(resolvedPath, backupContent, 'utf-8');
            } catch {
              // Restore failed — critical!
              console.error('[SelfModify] CRITICAL: Failed to restore backup after write failure');
            }
          }

          return NextResponse.json(
            { error: 'فشل في كتابة الكود المصحح — تمت استعادة النسخة الأصلية' },
            { status: 500 }
          );
        }

        return NextResponse.json({
          success: true,
          message: `تم تطبيق التصحيح على ${targetFile}`,
          backupPath: createdBackupPath,
          timestamp: Date.now(),
        });
      }

      // ----- Rollback -----
      case 'rollback': {
        if (!targetFile && !backupPath) {
          return NextResponse.json(
            { error: 'يجب تحديد الملف أو مسار النسخة الاحتياطية' },
            { status: 400 }
          );
        }

        let restoreContent: string | null = null;

        // Try to restore from backup path first
        if (backupPath && existsSync(backupPath)) {
          try {
            restoreContent = await readFile(backupPath, 'utf-8');
          } catch {
            // Backup read failed
          }
        }

        // If no backup, use the originalCode provided
        if (!restoreContent && originalCode) {
          restoreContent = originalCode;
        }

        if (!restoreContent) {
          return NextResponse.json(
            { error: 'لا توجد نسخة احتياطية متاحة للاستعادة' },
            { status: 404 }
          );
        }

        // Resolve the target file
        const resolvedPath = targetFile
          ? resolveTargetPath(targetFile)
          : null;

        if (!resolvedPath) {
          return NextResponse.json(
            { error: 'الملف غير صالح للاستعادة' },
            { status: 400 }
          );
        }

        // Write the original content back
        try {
          await writeFile(resolvedPath, restoreContent, 'utf-8');
        } catch (writeError) {
          console.error('[SelfModify] Failed to restore original code:', writeError);
          return NextResponse.json(
            { error: 'فشل في استعادة الكود الأصلي' },
            { status: 500 }
          );
        }

        return NextResponse.json({
          success: true,
          message: `تمت استعادة الكود الأصلي لـ ${targetFile}`,
          timestamp: Date.now(),
        });
      }

      // ----- List Backups -----
      case 'list_backups': {
        const backups: Array<{ path: string; size: number; created: number }> = [];

        if (existsSync(BACKUP_DIR)) {
          const { readdir } = await import('fs/promises');
          const files = await readdir(BACKUP_DIR);

          for (const file of files) {
            if (file.endsWith('.bak')) {
              const fullPath = path.join(BACKUP_DIR, file);
              const { stat } = await import('fs/promises');
              const info = await stat(fullPath);
              backups.push({
                path: fullPath,
                size: info.size,
                created: info.birthtimeMs,
              });
            }
          }
        }

        return NextResponse.json({
          backupDir: BACKUP_DIR,
          backups: backups.sort((a, b) => b.created - a.created),
          count: backups.length,
        });
      }

      default:
        return NextResponse.json(
          { error: 'إجراء غير معروف. استخدم: apply_patch, rollback, أو list_backups' },
          { status: 400 }
        );
    }
  } catch (error: unknown) {
    console.error('[SelfModify] POST Error:', error);
    return NextResponse.json(
      {
        error: 'حدث خطأ أثناء معالجة طلب التعديل الذاتي',
        // VULN-002 Fix: Removed internal error details
      },
      { status: 500 }
    );
  }
}
