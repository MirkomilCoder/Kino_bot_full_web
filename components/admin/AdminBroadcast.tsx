'use client';

import { useEffect, useState } from 'react';

interface BroadcastLog {
  id: number;
  message: string | null;
  status: string;
  totalUsers: number;
  sentCount: number;
  failedCount: number;
  createdAt: string;
  completedAt: string | null;
}

interface AdminBroadcastProps {
  token: string;
}

export default function AdminBroadcast({ token }: AdminBroadcastProps) {
  const [logs, setLogs] = useState<BroadcastLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/admin/broadcast?limit=20', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch broadcast logs');

      const data = await response.json();
      setLogs(data.logs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSendBroadcast = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!message.trim()) return;

    setSending(true);

    try {
      const response = await fetch('/api/admin/broadcast', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: message.trim() }),
      });

      if (!response.ok) throw new Error('Failed to send broadcast');

      const data = await response.json();
      setMessage('');
      fetchLogs();
    } catch (err) {
      console.error(err);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Send form */}
      <form onSubmit={handleSendBroadcast} className="bg-white rounded-lg shadow-sm p-6 border border-gray-100">
        <h2 className="text-lg font-semibold text-primary mb-4">Отправить массовое сообщение</h2>

        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Введите сообщение для всех пользователей..."
          className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-accent outline-none resize-none h-28 mb-4"
          required
        />

        <p className="text-xs text-gray-500 mb-4">Это сообщение будет отправлено всем активным пользователям</p>

        <button
          type="submit"
          disabled={sending || !message.trim()}
          className={`px-6 py-2 rounded-lg font-medium text-white transition-colors ${
            sending || !message.trim()
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-warning hover:bg-amber-600'
          }`}
        >
          {sending ? 'Отправка...' : '📢 Отправить'}
        </button>
      </form>

      {/* Broadcast logs */}
      <div>
        <h2 className="text-lg font-semibold text-primary mb-4">История рассылок</h2>

        {loading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
          </div>
        ) : logs.length > 0 ? (
          <div className="grid gap-4">
            {logs.map((log) => (
              <div key={log.id} className="bg-white rounded-lg shadow-sm p-4 border border-gray-100">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-semibold text-primary">#{log.id}</span>
                      <span
                        className={`text-xs font-medium px-2 py-1 rounded-full ${
                          log.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : log.status === 'sending'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {log.status === 'completed'
                          ? '✓ Завершено'
                          : log.status === 'sending'
                            ? 'Отправка...'
                            : 'В очереди'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 mb-2 line-clamp-2">{log.message || 'No message'}</p>

                    <div className="flex gap-4 text-xs text-gray-600">
                      <span>👥 Всего: {log.totalUsers}</span>
                      <span>✅ Отправлено: {log.sentCount}</span>
                      <span>❌ Ошибок: {log.failedCount}</span>
                    </div>

                    {log.status === 'completed' && log.completedAt && (
                      <p className="text-xs text-gray-400 mt-2">
                        Завершено: {new Date(log.completedAt).toLocaleString('ru-RU')}
                      </p>
                    )}
                  </div>
                </div>

                {log.status !== 'completed' && (
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-accent h-2 rounded-full transition-all"
                      style={{
                        width: `${log.totalUsers > 0 ? Math.round((log.sentCount / log.totalUsers) * 100) : 0}%`,
                      }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">Рассылок не найдено</div>
        )}
      </div>
    </div>
  );
}
