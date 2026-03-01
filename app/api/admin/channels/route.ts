import { NextRequest, NextResponse } from 'next/server';
import { requireAuth, requireRole } from '@/lib/api-middleware';
import { getChannels, addChannel, deleteChannel } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const auth = requireAuth(request);
    if (auth instanceof NextResponse) {
      return auth;
    }

    if (!requireRole(auth, 'admin')) {
      return NextResponse.json({ error: 'Admin access required' }, { status: 403 });
    }

    const channels = getChannels();

    return NextResponse.json({
      success: true,
      channels: channels.map((c) => ({
        id: c.chat_id,
        title: c.title,
        username: c.username,
      })),
    });
  } catch (error) {
    console.error('[v0] Admin channels GET error:', error);
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

    const { chatId, title, username } = await request.json();

    if (!chatId) {
      return NextResponse.json({ error: 'Chat ID is required' }, { status: 400 });
    }

    addChannel(parseInt(chatId), title?.trim() || null, username?.trim() || null);

    return NextResponse.json({
      success: true,
      message: 'Channel added successfully',
    });
  } catch (error) {
    console.error('[v0] Admin channels POST error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const auth = requireAuth(request);
    if (auth instanceof NextResponse) {
      return auth;
    }

    if (!requireRole(auth, 'admin')) {
      return NextResponse.json({ error: 'Admin access required' }, { status: 403 });
    }

    const { chatId } = await request.json();

    if (!chatId) {
      return NextResponse.json({ error: 'Chat ID is required' }, { status: 400 });
    }

    deleteChannel(parseInt(chatId));

    return NextResponse.json({
      success: true,
      message: 'Channel deleted successfully',
    });
  } catch (error) {
    console.error('[v0] Admin channels DELETE error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
