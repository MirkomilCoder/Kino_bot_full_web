import { NextRequest, NextResponse } from 'next/server';
import { requireAuth, requireRole } from '@/lib/api-middleware';
import { createBroadcastLog, getBroadcastLogs } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const auth = requireAuth(request);
    if (auth instanceof NextResponse) {
      return auth;
    }

    if (!requireRole(auth, 'admin')) {
      return NextResponse.json({ error: 'Admin access required' }, { status: 403 });
    }

    const page = parseInt(request.nextUrl.searchParams.get('page') || '1');
    const limit = parseInt(request.nextUrl.searchParams.get('limit') || '50');
    const offset = (page - 1) * limit;

    const logs = getBroadcastLogs(limit, offset);

    return NextResponse.json({
      success: true,
      logs: logs.map((log) => ({
        id: log.id,
        message: log.message_text,
        status: log.status,
        totalUsers: log.total_users,
        sentCount: log.sent_count,
        failedCount: log.failed_count,
        createdAt: log.created_at,
        completedAt: log.completed_at,
      })),
      page,
      limit,
    });
  } catch (error) {
    console.error('[v0] Broadcast GET error:', error);
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

    const { message } = await request.json();

    if (!message || !message.trim()) {
      return NextResponse.json({ error: 'Message is required' }, { status: 400 });
    }

    const log = createBroadcastLog(message.trim(), auth.userId);

    return NextResponse.json({
      success: true,
      broadcast: {
        id: log.id,
        message: log.message_text,
        status: log.status,
        totalUsers: log.total_users,
        createdAt: log.created_at,
      },
    });
  } catch (error) {
    console.error('[v0] Broadcast POST error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
