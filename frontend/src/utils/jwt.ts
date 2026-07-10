import type { UserRole } from '../types';

export interface JwtPayload {
  sub?: string;
  username?: string;
  role?: UserRole;
  exp?: number;
  type?: string;
}

export function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(normalized)) as JwtPayload;
  } catch {
    return null;
  }
}
