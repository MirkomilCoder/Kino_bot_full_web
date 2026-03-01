'use client';

import { useState } from 'react';

interface HeaderProps {
  title: string;
  subtitle?: string;
  user: {
    firstName: string | null;
    lastName: string | null;
    username: string | null;
    role: string;
  };
  onLogout?: () => void;
}

export default function Header({ title, subtitle, user, onLogout }: HeaderProps) {
  const [showMenu, setShowMenu] = useState(false);

  const displayName = user.firstName || user.username || 'User';

  return (
    <header className="bg-white shadow-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-primary">{title}</h1>
          {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
        </div>

        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-light hover:bg-gray-200 transition-colors"
          >
            <div className="flex items-center justify-center w-8 h-8 bg-accent rounded-full text-white text-sm font-bold">
              {displayName.charAt(0).toUpperCase()}
            </div>
            <div className="text-left hidden sm:block">
              <p className="text-sm font-medium text-primary">{displayName}</p>
              <p className="text-xs text-gray-500 capitalize">{user.role}</p>
            </div>
            <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 14l-7 7m0 0l-7-7m7 7V3"
              />
            </svg>
          </button>

          {showMenu && (
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-2 z-50">
              <div className="px-4 py-2 border-b">
                <p className="text-sm font-medium text-primary">{displayName}</p>
                <p className="text-xs text-gray-500">@{user.username || 'unknown'}</p>
              </div>

              {onLogout && (
                <button
                  onClick={() => {
                    onLogout();
                    setShowMenu(false);
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-danger hover:bg-red-50 transition-colors"
                >
                  Выход
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
