'use client';

// ─── Mamoun Auth System — Client-side with PBKDF2 + AES-GCM ───
// No server required — all auth data stored locally in encrypted form

const AUTH_KEY = 'mamoun_auth';
const SESSION_KEY = 'mamoun_session';
const LOCKOUT_KEY = 'mamoun_lockout';
const MAX_ATTEMPTS = 3;
const LOCKOUT_DURATION = 5 * 60 * 1000; // 5 minutes

interface AuthData {
  username: string;
  passwordHash: string; // PBKDF2-derived hash
  salt: string;         // Random salt for PBKDF2
  createdAt: number;
}

interface SessionData {
  username: string;
  token: string;
  expiresAt: number;
  rememberMe: boolean;
}

interface LockoutData {
  attempts: number;
  lockedUntil: number;
}

// ─── Crypto Utilities ────────────────────────────────────────
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

function generateSalt(): string {
  const salt = crypto.getRandomValues(new Uint8Array(32));
  return arrayBufferToBase64(salt.buffer as ArrayBuffer);
}

async function deriveKey(password: string, salt: string): Promise<CryptoKey> {
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(password),
    'PBKDF2',
    false,
    ['deriveBits', 'deriveKey']
  );

  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: base64ToArrayBuffer(salt),
      iterations: 100000,
      hash: 'SHA-256',
    },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );
}

async function hashPassword(password: string, salt: string): Promise<string> {
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(password),
    'PBKDF2',
    false,
    ['deriveBits']
  );

  const bits = await crypto.subtle.deriveBits(
    {
      name: 'PBKDF2',
      salt: base64ToArrayBuffer(salt),
      iterations: 100000,
      hash: 'SHA-256',
    },
    keyMaterial,
    256
  );

  return arrayBufferToBase64(bits);
}

function generateToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return arrayBufferToBase64(bytes.buffer as ArrayBuffer);
}

// ─── Lockout Management ─────────────────────────────────────
function getLockout(): LockoutData {
  try {
    const data = localStorage.getItem(LOCKOUT_KEY);
    if (!data) return { attempts: 0, lockedUntil: 0 };
    return JSON.parse(data);
  } catch {
    return { attempts: 0, lockedUntil: 0 };
  }
}

function setLockout(data: LockoutData): void {
  localStorage.setItem(LOCKOUT_KEY, JSON.stringify(data));
}

function isLockedOut(): { locked: boolean; remainingMs: number } {
  const lockout = getLockout();
  if (lockout.lockedUntil > Date.now()) {
    return { locked: true, remainingMs: lockout.lockedUntil - Date.now() };
  }
  if (lockout.lockedUntil > 0 && lockout.lockedUntil <= Date.now()) {
    // Lockout expired, reset
    setLockout({ attempts: 0, lockedUntil: 0 });
  }
  return { locked: false, remainingMs: 0 };
}

// ─── Auth Storage ────────────────────────────────────────────
function getAuthData(): AuthData | null {
  try {
    const data = localStorage.getItem(AUTH_KEY);
    if (!data) return null;
    return JSON.parse(data);
  } catch {
    return null;
  }
}

function setAuthData(data: AuthData): void {
  localStorage.setItem(AUTH_KEY, JSON.stringify(data));
}

// ─── Session Management ──────────────────────────────────────
function getSession(): SessionData | null {
  try {
    const data = localStorage.getItem(SESSION_KEY);
    if (!data) return null;
    const session: SessionData = JSON.parse(data);
    if (session.expiresAt < Date.now()) {
      // Session expired
      localStorage.removeItem(SESSION_KEY);
      return null;
    }
    return session;
  } catch {
    return null;
  }
}

function setSession(session: SessionData): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

// ─── Public API ──────────────────────────────────────────────

export async function register(username: string, password: string): Promise<{ success: boolean; error?: string }> {
  if (!username || username.length < 3) {
    return { success: false, error: 'اسم المستخدم يجب أن يكون 3 أحرف على الأقل' };
  }
  if (!password || password.length < 6) {
    return { success: false, error: 'كلمة المرور يجب أن تكون 6 أحرف على الأقل' };
  }
  if (getAuthData()) {
    return { success: false, error: 'يوجد حساب مسجل بالفعل' };
  }

  const salt = generateSalt();
  const passwordHash = await hashPassword(password, salt);

  setAuthData({
    username,
    passwordHash,
    salt,
    createdAt: Date.now(),
  });

  return { success: true };
}

export async function login(
  username: string,
  password: string,
  rememberMe: boolean = false
): Promise<{ success: boolean; error?: string }> {
  // Check lockout first
  const lockoutStatus = isLockedOut();
  if (lockoutStatus.locked) {
    const remainingMin = Math.ceil(lockoutStatus.remainingMs / 60000);
    return { success: false, error: `الحساب مقفل. حاول مرة أخرى بعد ${remainingMin} دقيقة` };
  }

  const authData = getAuthData();
  if (!authData) {
    return { success: false, error: 'لا يوجد حساب مسجل. أنشئ حساباً أولاً' };
  }

  if (username !== authData.username) {
    // Wrong username — still count as failed attempt
    const lockout = getLockout();
    lockout.attempts++;
    if (lockout.attempts >= MAX_ATTEMPTS) {
      lockout.lockedUntil = Date.now() + LOCKOUT_DURATION;
    }
    setLockout(lockout);
    return { success: false, error: `اسم المستخدم أو كلمة المرور غير صحيحة (${MAX_ATTEMPTS - lockout.attempts} محاولات متبقية)` };
  }

  const passwordHash = await hashPassword(password, authData.salt);
  if (passwordHash !== authData.passwordHash) {
    const lockout = getLockout();
    lockout.attempts++;
    if (lockout.attempts >= MAX_ATTEMPTS) {
      lockout.lockedUntil = Date.now() + LOCKOUT_DURATION;
      setLockout(lockout);
      return { success: false, error: `تم قفل الحساب لمدة 5 دقائق بسبب ${MAX_ATTEMPTS} محاولات خاطئة` };
    }
    setLockout(lockout);
    return { success: false, error: `كلمة المرور غير صحيحة (${MAX_ATTEMPTS - lockout.attempts} محاولات متبقية)` };
  }

  // Success — reset lockout
  setLockout({ attempts: 0, lockedUntil: 0 });

  // Create session
  const sessionDuration = rememberMe ? 30 * 24 * 60 * 60 * 1000 : 24 * 60 * 60 * 1000; // 30 days or 1 day
  const sessionToken = generateToken();
  const session: SessionData = {
    username,
    token: sessionToken,
    expiresAt: Date.now() + sessionDuration,
    rememberMe,
  };
  setSession(session);

  // Set encryption key for encrypted storage
  sessionStorage.setItem('mamoun_enc_key', sessionToken);

  return { success: true };
}

export function logout(): void {
  localStorage.removeItem(SESSION_KEY);
  sessionStorage.removeItem('mamoun_enc_key');
}

export function isAuthenticated(): boolean {
  return getSession() !== null;
}

export function getCurrentUser(): string | null {
  const session = getSession();
  return session?.username || null;
}

export function hasAccount(): boolean {
  return getAuthData() !== null;
}

export function getLockoutStatus(): { locked: boolean; remainingMs: number } {
  return isLockedOut();
}

export function getRemainingAttempts(): number {
  const lockout = getLockout();
  return Math.max(0, MAX_ATTEMPTS - lockout.attempts);
}

// ─── Encrypt/Decrypt data with user password (for Task 3) ───
export async function encryptData(data: string, password: string): Promise<string> {
  const salt = generateSalt();
  const key = await deriveKey(password, salt);
  const encoder = new TextEncoder();
  const iv = crypto.getRandomValues(new Uint8Array(12));

  const encrypted = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv },
    key,
    encoder.encode(data)
  );

  // Format: salt:iv:ciphertext (all base64)
  return `${salt}:${arrayBufferToBase64(iv.buffer as ArrayBuffer)}:${arrayBufferToBase64(encrypted)}`;
}

export async function decryptData(encryptedString: string, password: string): Promise<string> {
  const parts = encryptedString.split(':');
  if (parts.length !== 3) throw new Error('Invalid encrypted data format');

  const [saltB64, ivB64, cipherB64] = parts;
  const key = await deriveKey(password, saltB64);
  const iv = base64ToArrayBuffer(ivB64);
  const ciphertext = base64ToArrayBuffer(cipherB64);

  const decrypted = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv },
    key,
    ciphertext
  );

  const decoder = new TextDecoder();
  return decoder.decode(decrypted);
}
