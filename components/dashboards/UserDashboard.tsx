'use client';

import { useEffect, useState } from 'react';
import Header from '@/components/Header';
import MoviesList from '@/components/user/MoviesList';
import ProfileSection from '@/components/user/ProfileSection';
import SupportTickets from '@/components/user/SupportTickets';

interface User {
  id: number;
  firstName: string | null;
  lastName: string | null;
  username: string | null;
  role: string;
  joinedAt: string;
}

interface UserDashboardProps {
  user: User;
}

export default function UserDashboard({ user }: UserDashboardProps) {
  const [activeTab, setActiveTab] = useState<'movies' | 'profile' | 'support'>('movies');
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
      <Header title="Мой профиль" user={user} onLogout={handleLogout} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation tabs */}
        <div className="flex gap-2 mb-8 border-b border-gray-200 overflow-x-auto">
          {(['movies', 'profile', 'support'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 font-medium text-sm whitespace-nowrap border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-accent text-accent'
                  : 'border-transparent text-gray-600 hover:text-gray-800'
              }`}
            >
              {tab === 'movies' && '🎬 Фильмы'}
              {tab === 'profile' && '👤 Профиль'}
              {tab === 'support' && '💬 Поддержка'}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="animate-fadeIn">
          {activeTab === 'movies' && <MoviesList token={token} />}
          {activeTab === 'profile' && <ProfileSection user={user} />}
          {activeTab === 'support' && <SupportTickets token={token} userId={user.id} />}
        </div>
      </div>
    </div>
  );
}
