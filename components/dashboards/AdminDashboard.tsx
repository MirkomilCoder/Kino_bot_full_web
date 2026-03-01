'use client';

import { useEffect, useState } from 'react';
import Header from '@/components/Header';
import AdminMovies from '@/components/admin/AdminMovies';
import AdminUsers from '@/components/admin/AdminUsers';
import AdminSupport from '@/components/admin/AdminSupport';
import AdminChannels from '@/components/admin/AdminChannels';
import AdminBroadcast from '@/components/admin/AdminBroadcast';

interface User {
  id: number;
  firstName: string | null;
  lastName: string | null;
  username: string | null;
  role: string;
  joinedAt: string;
}

interface AdminDashboardProps {
  user: User;
}

export default function AdminDashboard({ user }: AdminDashboardProps) {
  const [activeTab, setActiveTab] = useState<'movies' | 'users' | 'support' | 'channels' | 'broadcast'>('movies');
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const savedToken = localStorage.getItem('auth_token');
    setToken(savedToken);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    window.location.reload();
  };

  if (!token) {
    return <div>Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-light">
      <Header title="Админ панель" subtitle="Управление контентом и пользователями" user={user} onLogout={handleLogout} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation tabs */}
        <div className="flex gap-2 mb-8 border-b border-gray-200 overflow-x-auto pb-2">
          {(
            [
              { id: 'movies', label: '🎬 Фильмы' },
              { id: 'channels', label: '📺 Каналы' },
              { id: 'users', label: '👥 Пользователи' },
              { id: 'support', label: '💬 Поддержка' },
              { id: 'broadcast', label: '📢 Рассылка' },
            ] as const
          ).map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`px-4 py-3 font-medium text-sm whitespace-nowrap border-b-2 transition-colors ${
                activeTab === id
                  ? 'border-accent text-accent'
                  : 'border-transparent text-gray-600 hover:text-gray-800'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="animate-fadeIn">
          {activeTab === 'movies' && <AdminMovies token={token} />}
          {activeTab === 'channels' && <AdminChannels token={token} />}
          {activeTab === 'users' && <AdminUsers token={token} />}
          {activeTab === 'support' && <AdminSupport token={token} />}
          {activeTab === 'broadcast' && <AdminBroadcast token={token} />}
        </div>
      </div>
    </div>
  );
}
