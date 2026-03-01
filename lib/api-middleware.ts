import { NextRequest, NextResponse } from 'next/server';
import { getAdminSession, hashToken } from '@/lib/db';

export interface AuthContext {
  userId: number;
  role: 'owner' | 'admin' | 'user';
  username: string;
}

export function extractToken(request: NextRequest): string | null {
  // Try to get token from Authorization header
  const authHeader = request.headers.get('Authorization');
  if (authHeader && authHeader.startsWith('Bearer ')) {
    return authHeader.slice(7);
  }

  // Try to get token from cookies
  const cookies = request.cookies;
  const token = cookies.get('auth_token')?.value;
  return token || null;
}

export function validateToken(token: string | null): AuthContext | null {
  if (!token) {
    return null;
  }

  try {
    const tokenHash = hashToken(token);
    const session = getAdminSession(tokenHash);

    if (!session) {
      return null;
    }

    return {
      userId: session.user_id || 0,
      role: (session.role as 'owner' | 'admin' | 'user') || 'user',
      username: session.username,
    };
  } catch (error) {
    return null;
  }
}

export function requireAuth(request: NextRequest): AuthContext | NextResponse {
  const token = extractToken(request);
  const auth = validateToken(token);

  if (!auth) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  return auth;
}

export function requireRole(auth: AuthContext | NextResponse, requiredRole: 'owner' | 'admin' | 'user'): boolean {
  if (auth instanceof NextResponse) {
    return false;
  }

  const roleHierarchy: Record<string, number> = {
    owner: 3,
    admin: 2,
    user: 1,
  };

  return (roleHierarchy[auth.role] || 0) >= (roleHierarchy[requiredRole] || 0);
}
