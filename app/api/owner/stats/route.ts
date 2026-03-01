import { NextRequest, NextResponse } from 'next/server';
import { requireAuth, requireRole } from '@/lib/api-middleware';
import { getStats, getMovieStats } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const auth = requireAuth(request);
    if (auth instanceof NextResponse) {
      return auth;
    }

    if (!requireRole(auth, 'owner')) {
      return NextResponse.json({ error: 'Owner access required' }, { status: 403 });
    }

    const stats = getStats();
    const movieStats = getMovieStats();

    return NextResponse.json({
      success: true,
      stats: {
        users: {
          total: stats.totalUsers,
          active: stats.activeUsers,
          blocked: stats.blockedUsers,
        },
        movies: {
          total: movieStats.totalMovies,
          channels: movieStats.totalChannels,
          avgPerChannel: movieStats.avgMoviesPerChannel,
        },
        support: {
          openTickets: stats.openTickets,
        },
      },
    });
  } catch (error) {
    console.error('[v0] Owner stats error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
