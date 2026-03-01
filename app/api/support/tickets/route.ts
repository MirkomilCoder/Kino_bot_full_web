import { NextRequest, NextResponse } from 'next/server';
import { requireAuth } from '@/lib/api-middleware';
import { createSupportTicket, getSupportTicketsByUser, getUser } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const auth = requireAuth(request);
    if (auth instanceof NextResponse) {
      return auth;
    }

    const tickets = getSupportTicketsByUser(auth.userId);

    return NextResponse.json({
      success: true,
      tickets: tickets.map((t) => ({
        id: t.id,
        message: t.message_text,
        status: t.status,
        answer: t.answer_text,
        createdAt: t.created_at,
        answeredAt: t.answered_at,
      })),
    });
  } catch (error) {
    console.error('[v0] Get tickets error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const auth = requireAuth(request);
    if (auth instanceof NextResponse) {
      return auth;
    }

    const { message } = await request.json();

    if (!message || !message.trim()) {
      return NextResponse.json({ error: 'Message is required' }, { status: 400 });
    }

    const user = getUser(auth.userId);
    if (!user) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 });
    }

    const ticket = createSupportTicket(auth.userId, message.trim(), {
      first_name: user.first_name,
      last_name: user.last_name,
      username: user.username,
    });

    return NextResponse.json({
      success: true,
      ticket: {
        id: ticket.id,
        message: ticket.message_text,
        status: ticket.status,
        createdAt: ticket.created_at,
      },
    });
  } catch (error) {
    console.error('[v0] Create ticket error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
