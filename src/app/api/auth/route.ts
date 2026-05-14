import { NextRequest, NextResponse } from 'next/server';

// Use the globally available Web Crypto API (crypto.randomUUID, crypto.subtle, crypto.getRandomValues)

// =============================================================================
// BABSHARQII v5.0 — Enhanced Authentication
// - Password stored as SHA-256 hash with random salt
// - Secure session tokens via crypto.randomUUID()
// - Rate limiting: max 5 attempts per IP, 15-minute lockout
// - Minimum password length: 8 characters
// =============================================================================

// --- Password Storage (hashed) ---
interface PasswordRecord {
  salt: string;
  hash: string;
}

let adminPasswordRecord: PasswordRecord | null = null;

// --- Session Management ---
interface SessionInfo {
  createdAt: number;
  ip: string;
}
const activeSessions = new Map<string, SessionInfo>();
const SESSION_DURATION = 24 * 60 * 60 * 1000; // 24 hours

// --- Rate Limiting ---
interface RateLimitEntry {
  attempts: number;
  lockedUntil: number;
}
const rateLimits = new Map<string, RateLimitEntry>();
const MAX_ATTEMPTS = 5;
const LOCKOUT_DURATION = 15 * 60 * 1000; // 15 minutes

// --- Crypto Helpers ---

/**
 * Generate a random hex salt (32 bytes = 64 hex chars)
 */
function generateSalt(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Hash a password with a salt using SHA-256
 */
async function hashPassword(password: string, salt: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(salt + password);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hashBuffer), (b) =>
    b.toString(16).padStart(2, '0')
  ).join('');
}

/**
 * Verify a password against a stored hash+salt
 */
async function verifyPassword(
  password: string,
  record: PasswordRecord
): Promise<boolean> {
  const computedHash = await hashPassword(password, record.salt);
  return computedHash === record.hash;
}

// --- Rate Limiting Helpers ---

function getClientIp(request: NextRequest): string {
  // Try common headers first, then fall back to a generic identifier
  const forwarded = request.headers.get('x-forwarded-for');
  if (forwarded) {
    return forwarded.split(',')[0].trim();
  }
  const realIp = request.headers.get('x-real-ip');
  if (realIp) {
    return realIp.trim();
  }
  return 'unknown';
}

function checkRateLimit(ip: string): { allowed: boolean; remainingAttempts: number; lockedUntil: number } {
  const entry = rateLimits.get(ip);
  const now = Date.now();

  if (!entry) {
    return { allowed: true, remainingAttempts: MAX_ATTEMPTS, lockedUntil: 0 };
  }

  // If lockout period has expired, reset
  if (entry.lockedUntil > 0 && now >= entry.lockedUntil) {
    rateLimits.delete(ip);
    return { allowed: true, remainingAttempts: MAX_ATTEMPTS, lockedUntil: 0 };
  }

  // If currently locked out
  if (entry.lockedUntil > 0 && now < entry.lockedUntil) {
    return { allowed: false, remainingAttempts: 0, lockedUntil: entry.lockedUntil };
  }

  return {
    allowed: entry.attempts < MAX_ATTEMPTS,
    remainingAttempts: Math.max(0, MAX_ATTEMPTS - entry.attempts),
    lockedUntil: 0,
  };
}

function recordFailedAttempt(ip: string): void {
  const entry = rateLimits.get(ip) || { attempts: 0, lockedUntil: 0 };
  entry.attempts += 1;
  if (entry.attempts >= MAX_ATTEMPTS) {
    entry.lockedUntil = Date.now() + LOCKOUT_DURATION;
  }
  rateLimits.set(ip, entry);
}

function resetRateLimit(ip: string): void {
  rateLimits.delete(ip);
}

// --- Helper: validate session ---
function validateSession(sessionToken: string | undefined): boolean {
  if (!sessionToken) return false;
  const session = activeSessions.get(sessionToken);
  if (!session) return false;
  if (Date.now() - session.createdAt > SESSION_DURATION) {
    activeSessions.delete(sessionToken);
    return false;
  }
  return true;
}

// --- Route Handlers ---

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, password, currentPassword, newPassword, token } = body;
    const clientIp = getClientIp(request);

    // Setup initial password (during onboarding)
    if (action === 'setup') {
      if (adminPasswordRecord) {
        return NextResponse.json(
          { error: 'تم إعداد كلمة المرور مسبقاً' },
          { status: 400 }
        );
      }
      if (!password || password.length < 8) {
        return NextResponse.json(
          { error: 'كلمة المرور يجب أن تكون 8 أحرف على الأقل' },
          { status: 400 }
        );
      }

      const salt = generateSalt();
      const hash = await hashPassword(password, salt);
      adminPasswordRecord = { salt, hash };

      const sessionToken = crypto.randomUUID();
      activeSessions.set(sessionToken, { createdAt: Date.now(), ip: clientIp });

      const response = NextResponse.json({
        success: true,
        message: 'تم إنشاء كلمة المرور بنجاح',
        token: sessionToken,
      });
      response.cookies.set('babsharqii_session', sessionToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 86400,
        path: '/',
      });
      return response;
    }

    // Login
    if (action === 'login') {
      // Check rate limit first
      const rateCheck = checkRateLimit(clientIp);
      if (!rateCheck.allowed) {
        const minutesLeft = Math.ceil((rateCheck.lockedUntil - Date.now()) / 60000);
        return NextResponse.json(
          {
            error: `تم تجاوز عدد المحاولات المسموح. حاول مرة أخرى بعد ${minutesLeft} دقيقة`,
            lockedUntil: rateCheck.lockedUntil,
          },
          { status: 429 }
        );
      }

      if (!adminPasswordRecord) {
        return NextResponse.json(
          { error: 'لم يتم إعداد كلمة المرور بعد', needsSetup: true },
          { status: 400 }
        );
      }

      const passwordValid = await verifyPassword(password, adminPasswordRecord);
      if (!passwordValid) {
        recordFailedAttempt(clientIp);
        const updated = checkRateLimit(clientIp);
        return NextResponse.json(
          {
            error: 'كلمة المرور غير صحيحة',
            remainingAttempts: updated.remainingAttempts,
          },
          { status: 401 }
        );
      }

      // Successful login — reset rate limit
      resetRateLimit(clientIp);

      const sessionToken = crypto.randomUUID();
      activeSessions.set(sessionToken, { createdAt: Date.now(), ip: clientIp });

      const response = NextResponse.json({
        success: true,
        message: 'تم تسجيل الدخول بنجاح',
        token: sessionToken,
      });
      response.cookies.set('babsharqii_session', sessionToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 86400,
        path: '/',
      });
      return response;
    }

    // Change password
    if (action === 'change-password') {
      const sessionToken = token || request.cookies.get('babsharqii_session')?.value;
      if (!validateSession(sessionToken)) {
        return NextResponse.json(
          { error: 'جلسة غير صالحة' },
          { status: 401 }
        );
      }

      if (!adminPasswordRecord) {
        return NextResponse.json(
          { error: 'لم يتم إعداد كلمة المرور بعد' },
          { status: 400 }
        );
      }

      const currentValid = await verifyPassword(currentPassword, adminPasswordRecord);
      if (!currentValid) {
        return NextResponse.json(
          { error: 'كلمة المرور الحالية غير صحيحة' },
          { status: 401 }
        );
      }

      if (!newPassword || newPassword.length < 8) {
        return NextResponse.json(
          { error: 'كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل' },
          { status: 400 }
        );
      }

      // Hash and store the new password
      const newSalt = generateSalt();
      const newHash = await hashPassword(newPassword, newSalt);
      adminPasswordRecord = { salt: newSalt, hash: newHash };

      return NextResponse.json({
        success: true,
        message: 'تم تغيير كلمة المرور بنجاح',
      });
    }

    // Verify session
    if (action === 'verify') {
      const sessionToken = token || request.cookies.get('babsharqii_session')?.value;
      const isValid = validateSession(sessionToken);
      return NextResponse.json({
        valid: isValid,
        needsSetup: !adminPasswordRecord,
      });
    }

    // Logout
    if (action === 'logout') {
      const sessionToken = token || request.cookies.get('babsharqii_session')?.value;
      if (sessionToken) {
        activeSessions.delete(sessionToken);
      }
      const response = NextResponse.json({
        success: true,
        message: 'تم تسجيل الخروج',
      });
      response.cookies.set('babsharqii_session', '', {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 0,
        path: '/',
      });
      return response;
    }

    return NextResponse.json(
      { error: 'إجراء غير معروف' },
      { status: 400 }
    );
  } catch (error) {
    console.error('Auth Error:', error);
    return NextResponse.json(
      { error: 'حدث خطأ في المصادقة' },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  const sessionToken = request.cookies.get('babsharqii_session')?.value;
  const hasPassword = adminPasswordRecord !== null;

  if (!validateSession(sessionToken)) {
    return NextResponse.json({
      authenticated: false,
      needsSetup: !hasPassword,
    });
  }

  return NextResponse.json({
    authenticated: true,
    needsSetup: false,
  });
}
