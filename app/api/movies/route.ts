import { NextRequest, NextResponse } from 'next/server';
import { requireAuth } from '@/lib/api-middleware';
import { getAllMovies, searchMovies } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const auth = requireAuth(request);
    if (auth instanceof NextResponse) {
      return auth;
    }

    const searchParams = request.nextUrl.searchParams;
    const query = searchParams.get('q') || '';
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '20');
    const offset = (page - 1) * limit;

    let movies;
    if (query) {
      movies = searchMovies(query, limit, offset);
    } else {
      movies = getAllMovies(limit, offset);
    }

    return NextResponse.json({
      success: true,
      movies: movies.map((m) => ({
        code: m.code,
        caption: m.caption,
        fileType: m.file_type,
        addedAt: m.added_at,
      })),
      page,
      limit,
    });
  } catch (error) {
    console.error('[v0] Movies error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
