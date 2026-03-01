import { NextRequest, NextResponse } from 'next/server';
import { requireAuth, requireRole } from '@/lib/api-middleware';
import { addMovie, deleteMovie, updateMovieCaption, getAllMovies } from '@/lib/db';

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

    const movies = getAllMovies(limit, offset);

    return NextResponse.json({
      success: true,
      movies: movies.map((m) => ({
        code: m.code,
        caption: m.caption,
        fileType: m.file_type,
        channelId: m.channel_id,
        messageId: m.message_id,
        addedAt: m.added_at,
      })),
      page,
      limit,
    });
  } catch (error) {
    console.error('[v0] Admin movies GET error:', error);
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

    const { code, fileId, fileType, channelId, messageId, caption } = await request.json();

    if (!code || !fileId || !fileType || !channelId || !messageId) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    addMovie({
      code: code.trim(),
      file_id: fileId,
      file_type: fileType,
      channel_id: parseInt(channelId),
      message_id: parseInt(messageId),
      caption: caption?.trim(),
      added_at: new Date().toISOString(),
    });

    return NextResponse.json({
      success: true,
      message: 'Movie added successfully',
    });
  } catch (error) {
    console.error('[v0] Admin movies POST error:', error);
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

    const { code } = await request.json();

    if (!code) {
      return NextResponse.json({ error: 'Code is required' }, { status: 400 });
    }

    deleteMovie(code);

    return NextResponse.json({
      success: true,
      message: 'Movie deleted successfully',
    });
  } catch (error) {
    console.error('[v0] Admin movies DELETE error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const auth = requireAuth(request);
    if (auth instanceof NextResponse) {
      return auth;
    }

    if (!requireRole(auth, 'admin')) {
      return NextResponse.json({ error: 'Admin access required' }, { status: 403 });
    }

    const { code, caption } = await request.json();

    if (!code || !caption) {
      return NextResponse.json({ error: 'Code and caption are required' }, { status: 400 });
    }

    updateMovieCaption(code, caption.trim());

    return NextResponse.json({
      success: true,
      message: 'Movie updated successfully',
    });
  } catch (error) {
    console.error('[v0] Admin movies PATCH error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
