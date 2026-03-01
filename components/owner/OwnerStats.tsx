'use client';

import { useEffect, useState } from 'react';

interface Stats {
  users: {
    total: number;
    active: number;
    blocked: number;
  };
  movies: {
    total: number;
    channels: number;
    avgPerChannel: number;
  };
  support: {
    openTickets: number;
  };
}

interface OwnerStatsProps {
  token: string;
}

export default function OwnerStats({ token }: OwnerStatsProps) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats();
    // Refresh stats every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/owner/stats', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch stats');

      const data = await response.json();
      setStats(data.stats);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !stats) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
      </div>
    );
  }

  if (error || !stats) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">{error}</div>;
  }

  const statCards = [
    {
      title: 'Всего пользователей',
      value: stats.users.total,
      icon: '👥',
      color: 'bg-blue-100 text-blue-800',
    },
    {
      title: 'Активных пользователей',
      value: stats.users.active,
      icon: '✓',
      color: 'bg-green-100 text-green-800',
    },
    {
      title: 'Заблокировано',
      value: stats.users.blocked,
      icon: '🚫',
      color: 'bg-red-100 text-red-800',
    },
    {
      title: 'Всего фильмов',
      value: stats.movies.total,
      icon: '🎬',
      color: 'bg-purple-100 text-purple-800',
    },
    {
      title: 'Каналов',
      value: stats.movies.channels,
      icon: '📺',
      color: 'bg-yellow-100 text-yellow-800',
    },
    {
      title: 'Открытых обращений',
      value: stats.support.openTickets,
      icon: '💬',
      color: 'bg-orange-100 text-orange-800',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {statCards.map((card, index) => (
          <div
            key={index}
            className="bg-white rounded-lg shadow-sm p-6 border border-gray-100 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-3xl">{card.icon}</span>
              <button
                onClick={fetchStats}
                className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
                title="Обновить"
              >
                🔄
              </button>
            </div>
            <p className="text-gray-600 text-sm mb-2">{card.title}</p>
            <p className="text-3xl font-bold text-primary">{card.value}</p>
          </div>
        ))}
      </div>

      {/* Detailed info */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Users info */}
        <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-100">
          <h3 className="text-lg font-semibold text-primary mb-4">📊 Информация о пользователях</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b">
              <span className="text-gray-600">Всего пользователей</span>
              <span className="font-bold text-lg">{stats.users.total}</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b">
              <span className="text-gray-600">Активные (7 дней)</span>
              <span className="font-bold text-lg text-green-600">{stats.users.active}</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-gray-600">Заблокировано</span>
              <span className="font-bold text-lg text-red-600">{stats.users.blocked}</span>
            </div>
          </div>
          {stats.users.total > 0 && (
            <div className="mt-4 pt-4 border-t">
              <div className="text-xs text-gray-500 mb-2">Активность</div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{
                    width: `${Math.round((stats.users.active / stats.users.total) * 100)}%`,
                  }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {Math.round((stats.users.active / stats.users.total) * 100)}% активных
              </p>
            </div>
          )}
        </div>

        {/* Movies info */}
        <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-100">
          <h3 className="text-lg font-semibold text-primary mb-4">🎬 Информация о фильмах</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b">
              <span className="text-gray-600">Всего фильмов</span>
              <span className="font-bold text-lg">{stats.movies.total}</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b">
              <span className="text-gray-600">Каналов</span>
              <span className="font-bold text-lg">{stats.movies.channels}</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-gray-600">Среднее на канал</span>
              <span className="font-bold text-lg">{stats.movies.avgPerChannel}</span>
            </div>
          </div>
        </div>
      </div>

      {/* System info */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-sm p-6 border border-blue-200">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">ℹ️ Информация о системе</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm text-blue-800">
          <div>
            <p className="font-medium">Тип приложения</p>
            <p className="text-blue-600">Telegram Web App</p>
          </div>
          <div>
            <p className="font-medium">Статус</p>
            <p className="text-green-600">✓ Активен</p>
          </div>
          <div>
            <p className="font-medium">База данных</p>
            <p className="text-blue-600">SQLite (Local)</p>
          </div>
          <div>
            <p className="font-medium">Последнее обновление</p>
            <p className="text-blue-600">Только что</p>
          </div>
        </div>
      </div>
    </div>
  );
}
