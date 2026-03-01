import { NextRequest, NextResponse } from 'next/server';
import { requireAuth, requireRole } from '@/lib/api-middleware';
import { getAllUsers, blockUser, unblockUser, getBlockedUsers } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const auth = requireAuth(request);
    if (auth instanceof NextResponse) {
      return auth;
    }

    if (!requireRole(auth, 'admin')) {
      return NextResponse.json({ error: 'Admin access required' }, { status: 403 });
    }

    const showBlocked = request.nextUrl.searchParams.get('blocked') === 'true';

    let users;
    if (showBlocked) {
      users = getBlockedUsers();
    } else {
      users = getAllUsers();
    }

    return NextResponse.json({
      success: true,
      users: users.map((u) => ({
        id: u.user_id,
        firstName: u.first_name,
        lastName: u.last_name,
        username: u.username,
        joinedAt: u.joined_at,
        lastSeen: u.last_seen,
        ...(showBlocked && {
          reason: 'reason' in u ? u.reason : null,
        }),
      })),
      showBlocked,
    });
  } catch (error) {
    console.error('[v0] Admin users GET error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const auth = requireAuth(request);
    if (auth instanceof NextResponse) {
      return auth;
    }

    if (!requireRole(auth, 'admin')) {
      return NextResponse.json({ error: 'Admin access required' }, { status: 403 });
    }

    const { userId, action, reason } = await request.json();

    if (!userId || !action) {
      return NextResponse.json({ error: 'User ID and action are required' }, { status: 400 });
    }

    if (action === 'block') {
      blockUser(userId, reason || 'No reason provided', auth.userId);
      return NextResponse.json({
        success: true,
        message: 'User blocked successfully',
      });
    } else if (action === 'unblock') {
      unblockUser(userId);
      return NextResponse.json({
        success: true,
        message: 'User unblocked successfully',
      });
    } else {
      return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
    }
  } catch (error) {
    console.error('[v0] Admin users POST error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
