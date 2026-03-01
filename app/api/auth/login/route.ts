import { NextRequest, NextResponse } from 'next/server';
import { validateTelegramWebApp, getUserRole, createSessionToken, hashToken } from '@/lib/telegram-auth';
import { getOrCreateUser, createAdminSession } from '@/lib/db';

const BOT_TOKEN = process.env.MAIN_BOT_TOKEN || '';
const OWNER_ID = parseInt(process.env.OWNER_ID || '0');
const ADMIN_IDS = (process.env.ADMIN_IDS || '')
  .split(',')
  .map((id) => parseInt(id.trim()))
  .filter((id) => !isNaN(id));

export async function POST(request: NextRequest) {
  try {
    const { initData } = await request.json();

    if (!initData) {
      return NextResponse.json({ error: 'Missing initData' }, { status: 400 });
    }

    // Validate Telegram Web App
    const validation = validateTelegramWebApp(initData, BOT_TOKEN);

    if (!validation.valid || !validation.user) {
      return NextResponse.json({ error: validation.error || 'Invalid authentication' }, { status: 401 });
    }

    const user = validation.user;

    // Get or create user in database
    const dbUser = getOrCreateUser(user.id, {
      first_name: user.first_name,
      last_name: user.last_name,
      username: user.username,
    });

    // Determine user role
    const role = getUserRole(user.id, OWNER_ID, ADMIN_IDS);

    // Create session token
    const sessionToken = createSessionToken(user.id, role);
    const tokenHash = hashToken(sessionToken);

    // Store session in database
    createAdminSession(tokenHash, user.username || `user_${user.id}`, user.id, role);

    // Return session token and user info
    return NextResponse.json(
      {
        success: true,
        token: sessionToken,
        user: {
          id: dbUser.user_id,
          firstName: dbUser.first_name,
          lastName: dbUser.last_name,
          username: dbUser.username,
          role,
          joinedAt: dbUser.joined_at,
        },
      },
      {
        headers: {
          'Set-Cookie': `auth_token=${sessionToken}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${24 * 60 * 60}`,
        },
      }
    );
  } catch (error) {
    console.error('[v0] Auth error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
