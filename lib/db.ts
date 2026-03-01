import Database from 'better-sqlite3';
import path from 'path';

let db: Database.Database | null = null;

export function getDatabase(): Database.Database {
  if (!db) {
    const dbPath = path.join(process.cwd(), 'data.sqlite3');
    db = new Database(dbPath);
    db.pragma('foreign_keys = ON');
  }
  return db;
}

export interface User {
  user_id: number;
  first_name: string | null;
  last_name: string | null;
  username: string | null;
  joined_at: string;
  last_seen: string;
}

export interface Movie {
  code: string;
  file_id: string;
  file_type: string;
  channel_id: number;
  message_id: number;
  caption?: string;
  added_at: string;
}

export interface SupportTicket {
  id: number;
  user_id: number;
  first_name: string | null;
  last_name: string | null;
  username: string | null;
  message_text: string;
  status: string;
  answer_text: string | null;
  answered_by: number | null;
  created_at: string;
  answered_at: string | null;
}

export interface BroadcastLog {
  id: number;
  created_by: number | null;
  message_text: string | null;
  status: string;
  total_users: number;
  sent_count: number;
  failed_count: number;
  error_text: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface AdminSession {
  token_hash: string;
  username: string;
  user_id: number | null;
  role: string;
  created_at: string;
  expires_at: string;
}

// User operations
export function getOrCreateUser(userId: number, userData: Partial<User>): User {
  const db = getDatabase();
  const existing = db.prepare('SELECT * FROM users WHERE user_id = ?').get(userId) as User | undefined;

  if (existing) {
    return existing;
  }

  db.prepare(
    `INSERT INTO users (user_id, first_name, last_name, username, joined_at, last_seen)
     VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))`
  ).run(userId, userData.first_name || null, userData.last_name || null, userData.username || null);

  return db.prepare('SELECT * FROM users WHERE user_id = ?').get(userId) as User;
}

export function getUser(userId: number): User | undefined {
  const db = getDatabase();
  return db.prepare('SELECT * FROM users WHERE user_id = ?').get(userId) as User | undefined;
}

export function getAllUsers(): User[] {
  const db = getDatabase();
  return db.prepare('SELECT * FROM users ORDER BY last_seen DESC').all() as User[];
}

export function updateUserLastSeen(userId: number): void {
  const db = getDatabase();
  db.prepare('UPDATE users SET last_seen = datetime("now") WHERE user_id = ?').run(userId);
}

export function blockUser(userId: number, reason: string, blockedBy: number): void {
  const db = getDatabase();
  db.prepare(
    `INSERT OR REPLACE INTO blocked_users (user_id, reason, blocked_by, blocked_at)
     VALUES (?, ?, ?, datetime('now'))`
  ).run(userId, reason, blockedBy);
}

export function unblockUser(userId: number): void {
  const db = getDatabase();
  db.prepare('DELETE FROM blocked_users WHERE user_id = ?').run(userId);
}

export function isUserBlocked(userId: number): boolean {
  const db = getDatabase();
  const blocked = db.prepare('SELECT user_id FROM blocked_users WHERE user_id = ?').get(userId);
  return !!blocked;
}

export function getBlockedUsers(): (User & { reason: string | null; blocked_by: number | null })[] {
  const db = getDatabase();
  return db
    .prepare(
      `SELECT u.*, bu.reason, bu.blocked_by 
       FROM users u 
       JOIN blocked_users bu ON u.user_id = bu.user_id
       ORDER BY bu.blocked_at DESC`
    )
    .all() as (User & { reason: string | null; blocked_by: number | null })[];
}

// Movie operations
export function addMovie(movie: Movie): void {
  const db = getDatabase();
  db.prepare(
    `INSERT OR REPLACE INTO movies (code, file_id, file_type, channel_id, message_id, added_at)
     VALUES (?, ?, ?, ?, ?, datetime('now'))`
  ).run(movie.code, movie.file_id, movie.file_type, movie.channel_id, movie.message_id);

  if (movie.caption) {
    db.prepare(
      `INSERT OR REPLACE INTO movie_meta (code, caption, updated_at)
       VALUES (?, ?, datetime('now'))`
    ).run(movie.code, movie.caption);
  }
}

export function getMovie(code: string): Movie | undefined {
  const db = getDatabase();
  const movie = db
    .prepare(
      `SELECT m.*, mm.caption FROM movies m
       LEFT JOIN movie_meta mm ON m.code = mm.code
       WHERE m.code = ?`
    )
    .get(code) as Movie | undefined;
  return movie;
}

export function searchMovies(query: string, limit: number = 50, offset: number = 0): Movie[] {
  const db = getDatabase();
  const searchTerm = `%${query}%`;
  return db
    .prepare(
      `SELECT DISTINCT m.*, mm.caption FROM movies m
       LEFT JOIN movie_meta mm ON m.code = mm.code
       WHERE m.code LIKE ? OR mm.caption LIKE ?
       ORDER BY m.added_at DESC
       LIMIT ? OFFSET ?`
    )
    .all(searchTerm, searchTerm, limit, offset) as Movie[];
}

export function getAllMovies(limit: number = 100, offset: number = 0): Movie[] {
  const db = getDatabase();
  return db
    .prepare(
      `SELECT m.*, mm.caption FROM movies m
       LEFT JOIN movie_meta mm ON m.code = mm.code
       ORDER BY m.added_at DESC
       LIMIT ? OFFSET ?`
    )
    .all(limit, offset) as Movie[];
}

export function deleteMovie(code: string): void {
  const db = getDatabase();
  db.prepare('DELETE FROM movie_meta WHERE code = ?').run(code);
  db.prepare('DELETE FROM movie_parts WHERE code = ?').run(code);
  db.prepare('DELETE FROM movies WHERE code = ?').run(code);
}

export function updateMovieCaption(code: string, caption: string): void {
  const db = getDatabase();
  db.prepare(
    `INSERT OR REPLACE INTO movie_meta (code, caption, updated_at)
     VALUES (?, ?, datetime('now'))`
  ).run(code, caption);
}

// Support tickets
export function createSupportTicket(
  userId: number,
  messageText: string,
  userData: Partial<User>
): SupportTicket {
  const db = getDatabase();
  const result = db
    .prepare(
      `INSERT INTO support_tickets (user_id, first_name, last_name, username, message_text, status, created_at)
       VALUES (?, ?, ?, ?, ?, 'open', datetime('now'))`
    )
    .run(userId, userData.first_name || null, userData.last_name || null, userData.username || null, messageText);

  return db.prepare('SELECT * FROM support_tickets WHERE id = ?').get(result.lastInsertRowid) as SupportTicket;
}

export function getSupportTickets(status?: string, limit: number = 50, offset: number = 0): SupportTicket[] {
  const db = getDatabase();
  let query = `SELECT * FROM support_tickets`;
  const params: any[] = [];

  if (status) {
    query += ` WHERE status = ?`;
    params.push(status);
  }

  query += ` ORDER BY created_at DESC LIMIT ? OFFSET ?`;
  params.push(limit, offset);

  return db.prepare(query).all(...params) as SupportTicket[];
}

export function getSupportTicketsByUser(userId: number): SupportTicket[] {
  const db = getDatabase();
  return db
    .prepare('SELECT * FROM support_tickets WHERE user_id = ? ORDER BY created_at DESC')
    .all(userId) as SupportTicket[];
}

export function answerSupportTicket(ticketId: number, answer: string, answeredBy: number): void {
  const db = getDatabase();
  db.prepare(
    `UPDATE support_tickets 
     SET status = 'answered', answer_text = ?, answered_by = ?, answered_at = datetime('now')
     WHERE id = ?`
  ).run(answer, answeredBy, ticketId);
}

export function getSupportTicket(ticketId: number): SupportTicket | undefined {
  const db = getDatabase();
  return db.prepare('SELECT * FROM support_tickets WHERE id = ?').get(ticketId) as SupportTicket | undefined;
}

// Broadcast logs
export function createBroadcastLog(message: string, createdBy: number): BroadcastLog {
  const db = getDatabase();
  const result = db
    .prepare(
      `INSERT INTO broadcast_logs (created_by, message_text, status, total_users, created_at)
       VALUES (?, ?, 'queued', (SELECT COUNT(*) FROM users), datetime('now'))`
    )
    .run(createdBy, message);

  return db.prepare('SELECT * FROM broadcast_logs WHERE id = ?').get(result.lastInsertRowid) as BroadcastLog;
}

export function getBroadcastLogs(limit: number = 50, offset: number = 0): BroadcastLog[] {
  const db = getDatabase();
  return db
    .prepare('SELECT * FROM broadcast_logs ORDER BY created_at DESC LIMIT ? OFFSET ?')
    .all(limit, offset) as BroadcastLog[];
}

export function updateBroadcastStatus(logId: number, status: string, sentCount: number, failedCount: number): void {
  const db = getDatabase();
  const query =
    status === 'completed'
      ? `UPDATE broadcast_logs SET status = ?, sent_count = ?, failed_count = ?, completed_at = datetime('now') WHERE id = ?`
      : `UPDATE broadcast_logs SET status = ?, sent_count = ?, failed_count = ? WHERE id = ?`;

  db.prepare(query).run(status, sentCount, failedCount, logId);
}

// Admin sessions
export function createAdminSession(tokenHash: string, username: string, userId: number, role: string): AdminSession {
  const db = getDatabase();
  const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 hours

  db.prepare(
    `INSERT INTO admin_sessions (token_hash, username, user_id, role, created_at, expires_at)
     VALUES (?, ?, ?, ?, datetime('now'), ?)`
  ).run(tokenHash, username, userId, role, expiresAt.toISOString());

  return db.prepare('SELECT * FROM admin_sessions WHERE token_hash = ?').get(tokenHash) as AdminSession;
}

export function getAdminSession(tokenHash: string): AdminSession | undefined {
  const db = getDatabase();
  return db.prepare('SELECT * FROM admin_sessions WHERE token_hash = ? AND expires_at > datetime("now")').get(
    tokenHash
  ) as AdminSession | undefined;
}

export function deleteAdminSession(tokenHash: string): void {
  const db = getDatabase();
  db.prepare('DELETE FROM admin_sessions WHERE token_hash = ?').run(tokenHash);
}

export function getStats(): {
  totalUsers: number;
  activeUsers: number;
  totalMovies: number;
  openTickets: number;
  blockedUsers: number;
} {
  const db = getDatabase();

  const totalUsers = (db.prepare('SELECT COUNT(*) as count FROM users').get() as any).count;
  const activeUsers = (
    db.prepare('SELECT COUNT(*) as count FROM users WHERE last_seen > datetime("now", "-7 days")').get() as any
  ).count;
  const totalMovies = (db.prepare('SELECT COUNT(DISTINCT code) as count FROM movies').get() as any).count;
  const openTickets = (
    db.prepare('SELECT COUNT(*) as count FROM support_tickets WHERE status = "open"').get() as any
  ).count;
  const blockedUsers = (db.prepare('SELECT COUNT(*) as count FROM blocked_users').get() as any).count;

  return { totalUsers, activeUsers, totalMovies, openTickets, blockedUsers };
}

export function getMovieStats(): { totalMovies: number; totalChannels: number; avgMoviesPerChannel: number } {
  const db = getDatabase();

  const totalMovies = (db.prepare('SELECT COUNT(*) as count FROM movies').get() as any).count;
  const totalChannels = (db.prepare('SELECT COUNT(DISTINCT channel_id) as count FROM movies').get() as any).count;
  const avgMoviesPerChannel = totalChannels > 0 ? totalMovies / totalChannels : 0;

  return { totalMovies, totalChannels, avgMoviesPerChannel: Math.round(avgMoviesPerChannel * 100) / 100 };
}

export function getChannels(): { chat_id: number; title: string | null; username: string | null }[] {
  const db = getDatabase();
  return db
    .prepare('SELECT chat_id, title, username FROM movie_channels ORDER BY added_at DESC')
    .all() as { chat_id: number; title: string | null; username: string | null }[];
}

export function addChannel(chatId: number, title: string | null, username: string | null): void {
  const db = getDatabase();
  db.prepare(
    `INSERT OR REPLACE INTO movie_channels (chat_id, title, username, added_at)
     VALUES (?, ?, ?, datetime('now'))`
  ).run(chatId, title, username);
}

export function deleteChannel(chatId: number): void {
  const db = getDatabase();
  db.prepare('DELETE FROM movie_channels WHERE chat_id = ?').run(chatId);
}
