// Test setup — Mock fetch and environment
import { vi } from 'vitest';

// Mock fetch globally
global.fetch = vi.fn();

// Mock environment variables
process.env.MAMOUN_BACKEND_URL = 'http://localhost:8000';

// Suppress console errors in tests
const originalError = console.error;
console.error = (...args: unknown[]) => {
  if (typeof args[0] === 'string' && (args[0].includes('Warning:') || args[0].includes('act('))) {
    return;
  }
  originalError.call(console, ...args);
};
