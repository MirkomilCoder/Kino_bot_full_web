import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const dbPath = path.join(process.cwd(), 'data.sqlite3');

// Create or open database
const db = new Database(dbPath);

// Enable foreign keys
db.pragma('foreign_keys = ON');

// Create tables
const createTables = () => {
  // Users table
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      user_id INTEGER PRIMARY KEY,
      first_name TEXT,
      last_name TEXT,
      username TEXT,
      joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_users_last_seen ON users(last_seen);
  `);

  // Blocked users
  db.exec(`
    CREATE TABLE IF NOT EXISTS blocked_users (
      user_id INTEGER PRIMARY KEY,
      reason TEXT,
      blocked_by INTEGER,
      blocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (blocked_by) REFERENCES users(user_id)
    );
  `);

  // Movies table
  db.exec(`
    CREATE TABLE IF NOT EXISTS movies (
      code TEXT PRIMARY KEY,
      file_id TEXT NOT NULL,
      file_unique_id TEXT,
      file_type TEXT NOT NULL,
      channel_id INTEGER NOT NULL,
      message_id INTEGER NOT NULL,
      added_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_movies_channel_message ON movies(channel_id, message_id);
  `);

  // Movie metadata
  db.exec(`
    CREATE TABLE IF NOT EXISTS movie_meta (
      code TEXT PRIMARY KEY,
      caption TEXT,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (code) REFERENCES movies(code)
    );
  `);

  // Movie parts (for serials)
  db.exec(`
    CREATE TABLE IF NOT EXISTS movie_parts (
      code TEXT NOT NULL,
      part_number INTEGER NOT NULL,
      content_kind TEXT DEFAULT 'movie',
      file_id TEXT NOT NULL,
      file_unique_id TEXT,
      file_type TEXT NOT NULL,
      channel_id INTEGER NOT NULL,
      message_id INTEGER NOT NULL,
      caption TEXT,
      added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (code, part_number),
      FOREIGN KEY (code) REFERENCES movies(code)
    );
    CREATE INDEX IF NOT EXISTS ix_movie_parts_channel_message ON movie_parts(channel_id, message_id);
    CREATE INDEX IF NOT EXISTS ix_movie_parts_code ON movie_parts(code);
  `);

  // Movie channels
  db.exec(`
    CREATE TABLE IF NOT EXISTS movie_channels (
      chat_id INTEGER PRIMARY KEY,
      title TEXT,
      username TEXT,
      added_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
  `);

  // Subscription channels
  db.exec(`
    CREATE TABLE IF NOT EXISTS subscription_channels (
      chat_id INTEGER PRIMARY KEY,
      title TEXT,
      username TEXT,
      invite_link TEXT,
      added_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
  `);

  // Support tickets
  db.exec(`
    CREATE TABLE IF NOT EXISTS support_tickets (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      first_name TEXT,
      last_name TEXT,
      username TEXT,
      message_text TEXT NOT NULL,
      status TEXT DEFAULT 'open',
      answer_text TEXT,
      answered_by INTEGER,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      answered_at DATETIME,
      FOREIGN KEY (user_id) REFERENCES users(user_id),
      FOREIGN KEY (answered_by) REFERENCES users(user_id)
    );
    CREATE INDEX IF NOT EXISTS ix_support_tickets_status ON support_tickets(status);
    CREATE INDEX IF NOT EXISTS ix_support_tickets_user ON support_tickets(user_id);
  `);

  // Bot settings
  db.exec(`
    CREATE TABLE IF NOT EXISTS bot_settings (
      setting_key TEXT PRIMARY KEY,
      setting_value TEXT NOT NULL,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
  `);

  // Broadcast logs
  db.exec(`
    CREATE TABLE IF NOT EXISTS broadcast_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_by INTEGER,
      message_text TEXT,
      status TEXT DEFAULT 'queued',
      total_users INTEGER DEFAULT 0,
      sent_count INTEGER DEFAULT 0,
      failed_count INTEGER DEFAULT 0,
      error_text TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      completed_at DATETIME,
      FOREIGN KEY (created_by) REFERENCES users(user_id)
    );
    CREATE INDEX IF NOT EXISTS ix_broadcast_logs_created_at ON broadcast_logs(created_at);
  `);

  // Admin sessions
  db.exec(`
    CREATE TABLE IF NOT EXISTS admin_sessions (
      token_hash TEXT PRIMARY KEY,
      username TEXT NOT NULL,
      user_id INTEGER,
      role TEXT DEFAULT 'admin',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      expires_at DATETIME NOT NULL,
      FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    CREATE INDEX IF NOT EXISTS ix_admin_sessions_expires ON admin_sessions(expires_at);
  `);

  console.log('Database tables created successfully!');
};

try {
  createTables();
  console.log(`Database initialized at: ${dbPath}`);
} catch (error) {
  console.error('Error initializing database:', error);
  process.exit(1);
} finally {
  db.close();
}
