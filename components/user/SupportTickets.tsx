'use client';

import { useEffect, useState } from 'react';

interface Ticket {
  id: number;
  message: string;
  status: string;
  answer: string | null;
  createdAt: string;
  answeredAt: string | null;
}

interface SupportTicketsProps {
  token: string;
  userId: number;
}

export default function SupportTickets({ token, userId }: SupportTicketsProps) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newMessage, setNewMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchTickets();
  }, []);

  const fetchTickets = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/support/tickets', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch tickets');
      }

      const data = await response.json();
      setTickets(data.tickets || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newMessage.trim()) {
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch('/api/support/tickets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: newMessage }),
      });

      if (!response.ok) {
        throw new Error('Failed to create ticket');
      }

      const data = await response.json();
      setTickets([data.ticket, ...tickets]);
      setNewMessage('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* New ticket form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm p-6 border border-gray-100">
        <h2 className="text-lg font-semibold text-primary mb-4">Создать обращение в поддержку</h2>

        <textarea
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          placeholder="Опишите вашу проблему..."
          className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-accent focus:border-transparent outline-none resize-none h-28 mb-4"
        />

        <button
          type="submit"
          disabled={submitting || !newMessage.trim()}
          className={`px-6 py-2 rounded-lg font-medium text-white transition-colors ${
            submitting || !newMessage.trim()
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-accent hover:bg-blue-600'
          }`}
        >
          {submitting ? 'Отправка...' : 'Отправить'}
        </button>
      </form>

      {/* Error message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
        </div>
      )}

      {/* Tickets list */}
      {!loading && tickets.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-primary">История обращений ({tickets.length})</h3>
          {tickets.map((ticket) => (
            <div key={ticket.id} className="bg-white rounded-lg shadow-sm p-6 border border-gray-100">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-mono text-gray-500">#{ticket.id}</span>
                    <span
                      className={`text-xs font-medium px-2 py-1 rounded-full ${
                        ticket.status === 'answered'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {ticket.status === 'answered' ? '✓ Ответ получен' : 'Ожидание ответа'}
                    </span>
                  </div>
                  <p className="text-gray-700">{ticket.message}</p>
                </div>
              </div>

              {ticket.answer && (
                <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-sm font-medium text-green-900 mb-2">Ответ администратора:</p>
                  <p className="text-sm text-green-800">{ticket.answer}</p>
                  {ticket.answeredAt && (
                    <p className="text-xs text-green-600 mt-2">
                      {new Date(ticket.answeredAt).toLocaleString('ru-RU')}
                    </p>
                  )}
                </div>
              )}

              <p className="text-xs text-gray-400 mt-3">{new Date(ticket.createdAt).toLocaleString('ru-RU')}</p>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && tickets.length === 0 && !error && (
        <div className="bg-white rounded-lg p-8 text-center border border-gray-100">
          <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-gray-600 font-medium">Обращений не создано</p>
          <p className="text-gray-400 text-sm mt-1">Создайте первое обращение, если вам нужна помощь</p>
        </div>
      )}
    </div>
  );
}
