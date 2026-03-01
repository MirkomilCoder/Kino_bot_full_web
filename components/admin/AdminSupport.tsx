'use client';

import { useEffect, useState } from 'react';

interface Ticket {
  id: number;
  userId: number;
  userName: string;
  message: string;
  status: string;
  answer: string | null;
  createdAt: string;
  answeredAt: string | null;
}

interface AdminSupportProps {
  token: string;
}

export default function AdminSupport({ token }: AdminSupportProps) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'open' | 'answered' | undefined>(undefined);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [answer, setAnswer] = useState('');

  useEffect(() => {
    fetchTickets();
  }, [status]);

  const fetchTickets = async () => {
    setLoading(true);
    try {
      const url = new URL('/api/admin/support', window.location.origin);
      if (status) url.searchParams.set('status', status);

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch tickets');

      const data = await response.json();
      setTickets(data.tickets || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket || !answer.trim()) return;

    try {
      const response = await fetch('/api/admin/support', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ ticketId: selectedTicket.id, answer: answer.trim() }),
      });

      if (!response.ok) throw new Error('Failed to answer ticket');

      setSelectedTicket(null);
      setAnswer('');
      fetchTickets();
    } catch (err) {
      console.error(err);
    }
  };

  const openTickets = tickets.filter((t) => t.status === 'open').length;

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 pb-2">
        {[
          { id: undefined, label: `Все (${tickets.length})` },
          { id: 'open' as const, label: `Открытые (${openTickets})` },
          { id: 'answered' as const, label: `Ответы отправлены` },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setStatus(tab.id)}
            className={`px-4 py-2 font-medium ${
              status === tab.id
                ? 'border-b-2 border-accent text-accent'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Answer modal */}
      {selectedTicket && (
        <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-100">
          <h3 className="text-lg font-semibold text-primary mb-4">Ответить на обращение #{selectedTicket.id}</h3>
          <p className="text-gray-700 mb-4 p-4 bg-light rounded-lg">{selectedTicket.message}</p>

          <form onSubmit={handleAnswerSubmit} className="space-y-4">
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Введите ответ..."
              className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-accent outline-none resize-none h-28"
              required
            />
            <div className="flex gap-2">
              <button
                type="submit"
                className="bg-success text-white px-6 py-2 rounded-lg hover:bg-green-600 transition-colors font-medium"
              >
                Отправить ответ
              </button>
              <button
                type="button"
                onClick={() => {
                  setSelectedTicket(null);
                  setAnswer('');
                }}
                className="bg-gray-300 text-gray-800 px-6 py-2 rounded-lg hover:bg-gray-400 transition-colors font-medium"
              >
                Отменить
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tickets list */}
      {loading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
        </div>
      ) : tickets.length > 0 ? (
        <div className="grid gap-4">
          {tickets.map((ticket) => (
            <div key={ticket.id} className="bg-white rounded-lg shadow-sm p-4 border border-gray-100">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-semibold text-primary">#{ticket.id}</span>
                    <span
                      className={`text-xs font-medium px-2 py-1 rounded-full ${
                        ticket.status === 'open'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-green-100 text-green-800'
                      }`}
                    >
                      {ticket.status === 'open' ? 'Открыто' : 'Ответ отправлен'}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 mb-2">{ticket.message}</p>
                  <p className="text-xs text-gray-500">
                    От: {ticket.userName} (ID: {ticket.userId})
                  </p>
                </div>
              </div>

              {ticket.answer && (
                <div className="mt-3 p-3 bg-green-50 rounded-lg border border-green-200 mb-3">
                  <p className="text-sm text-green-900">{ticket.answer}</p>
                </div>
              )}

              {ticket.status === 'open' && (
                <button
                  onClick={() => {
                    setSelectedTicket(ticket);
                    setAnswer('');
                  }}
                  className="mt-3 bg-accent text-white px-4 py-2 rounded text-sm hover:bg-blue-600 transition-colors"
                >
                  Ответить
                </button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">Обращений не найдено</div>
      )}
    </div>
  );
}
