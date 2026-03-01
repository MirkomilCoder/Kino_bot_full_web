import { NextRequest, NextResponse } from 'next/server';
import { requireAuth, requireRole } from '@/lib/api-middleware';
import { getUser, updateUserLastSeen } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const auth = requireAuth(request);
    if (auth instanceof NextResponse) {
      return auth;
    }

    // Update last seen
    updateUserLastSeen(auth.userId);

    // Get user profile
    const user = getUser(auth.userId);

    if (!user) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 });
    }

    return NextResponse.json({
      success: true,
      user: {
        id: user.user_id,
        firstName: user.first_name,
        lastName: user.last_name,
        username: user.username,
        joinedAt: user.joined_at,
        lastSeen: user.last_seen,
      },
    });
  } catch (error) {
    console.error('[v0] Profile error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
