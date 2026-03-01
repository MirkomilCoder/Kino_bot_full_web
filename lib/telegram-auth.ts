import crypto from 'crypto';

export interface TelegramUser {
  id: number;
  is_bot: boolean;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
  added_to_attachment_menu?: boolean;
}

export interface WebAppInitData {
  user: TelegramUser;
  auth_date: number;
  hash: string;
  chat_instance?: string;
  chat_type?: string;
  start_param?: string;
}

/**
 * Validate Telegram Web App init data
 * This ensures the request is coming from a valid Telegram Web App
 */
export function validateTelegramWebApp(
  initData: string,
  botToken: string
): { valid: boolean; user?: TelegramUser; error?: string } {
  try {
    if (!initData || !botToken) {
      return { valid: false, error: 'Missing initData or botToken' };
    }

    const params = new URLSearchParams(initData);
    const hash = params.get('hash');

    if (!hash) {
      return { valid: false, error: 'Missing hash' };
    }

    // Create a copy of params without the hash
    params.delete('hash');

    // Sort the remaining parameters
    const sortedParams: [string, string][] = Array.from(params.entries()).sort((a, b) =>
      a[0].localeCompare(b[0])
    );

    // Create the data check string
    const dataCheckString = sortedParams.map(([key, value]) => `${key}=${value}`).join('\n');

    // Create HMAC
    const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
    const computedHash = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');

    // Compare hashes
    if (computedHash !== hash) {
      return { valid: false, error: 'Invalid hash' };
    }

    // Check if auth_date is not too old (within 1 day)
    const authDateParam = params.get('auth_date');
    if (authDateParam) {
      const authDate = parseInt(authDateParam, 10);
      const currentTime = Math.floor(Date.now() / 1000);
      const timeDiff = currentTime - authDate;

      if (timeDiff > 86400) {
        // 24 hours
        return { valid: false, error: 'Auth data is too old' };
      }
    }

    // Extract user data
    const userParam = params.get('user');
    if (!userParam) {
      return { valid: false, error: 'Missing user data' };
    }

    const user: TelegramUser = JSON.parse(userParam);

    return { valid: true, user };
  } catch (error) {
    return {
      valid: false,
      error: error instanceof Error ? error.message : 'Unknown error during validation',
    };
  }
}

/**
 * Get user role based on user ID and admin IDs from environment
 */
export function getUserRole(
  userId: number,
  ownerId: number,
  adminIds: number[]
): 'owner' | 'admin' | 'user' {
  if (userId === ownerId) {
    return 'owner';
  }
  if (adminIds.includes(userId)) {
    return 'admin';
  }
  return 'user';
}

/**
 * Create a session token
 */
export function createSessionToken(userId: number, role: string): string {
  const token = crypto
    .randomBytes(32)
    .toString('hex')
    .concat('_')
    .concat(userId.toString());
  return token;
}

/**
 * Hash a token for storage
 */
export function hashToken(token: string): string {
  return crypto.createHash('sha256').update(token).digest('hex');
}
