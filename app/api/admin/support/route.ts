import { NextRequest, NextResponse } from 'next/server';
import { requireAuth, requireRole } from '@/lib/api-middleware';
import { getSupportTickets, answerSupportTicket, getSupportTicket } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const auth = requireAuth(request);
    if (auth instanceof NextResponse) {
      return auth;
    }

    if (!requireRole(auth, 'admin')) {
      return NextResponse.json({ error: 'Admin access required' }, { status: 403 });
    }

    const status = request.nextUrl.searchParams.get('status');
    const page = parseInt(request.nextUrl.searchParams.get('page') || '1');
    const limit = parseInt(request.nextUrl.searchParams.get('limit') || '50');
    const offset = (page - 1) * limit;

    const tickets = getSupportTickets(status || undefined, limit, offset);

    return NextResponse.json({
      success: true,
      tickets: tickets.map((t) => ({
        id: t.id,
        userId: t.user_id,
        userName: `${t.first_name} ${t.last_name}`.trim() || t.username || 'Unknown',
        message: t.message_text,
        status: t.status,
        answer: t.answer_text,
        createdAt: t.created_at,
        answeredAt: t.answered_at,
      })),
      page,
      limit,
    });
  } catch (error) {
    console.error('[v0] Admin support GET error:', error);
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

    const { ticketId, answer } = await request.json();

    if (!ticketId || !answer || !answer.trim()) {
      return NextResponse.json({ error: 'Ticket ID and answer are required' }, { status: 400 });
    }

    const ticket = getSupportTicket(ticketId);
    if (!ticket) {
      return NextResponse.json({ error: 'Ticket not found' }, { status: 404 });
    }

    answerSupportTicket(ticketId, answer.trim(), auth.userId);

    return NextResponse.json({
      success: true,
      message: 'Ticket answered successfully',
    });
  } catch (error) {
    console.error('[v0] Admin support POST error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
