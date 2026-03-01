'use client';

import { useEffect, useState } from 'react';

interface User {
  id: number;
  firstName: string | null;
  lastName: string | null;
  username: string | null;
  joinedAt: string;
  lastSeen: string;
}

interface AdminUsersProps {
  token: string;
}

export default function AdminUsers({ token }: AdminUsersProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [blockedUsers, setBlockedUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<'active' | 'blocked'>('active');

  useEffect(() => {
    fetchUsers();
  }, [tab]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/admin/users?blocked=${tab === 'blocked'}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch users');

      const data = await response.json();
      if (tab === 'active') {
        setUsers(data.users || []);
      } else {
        setBlockedUsers(data.users || []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleBlockUser = async (userId: number, reason: string) => {
    try {
      const response = await fetch('/api/admin/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ userId, action: 'block', reason }),
      });

      if (!response.ok) throw new Error('Failed to block user');

      fetchUsers();
    } catch (err) {
      console.error(err);
    }
  };

  const handleUnblockUser = async (userId: number) => {
    try {
      const response = await fetch('/api/admin/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ userId, action: 'unblock' }),
      });

      if (!response.ok) throw new Error('Failed to unblock user');

      fetchUsers();
    } catch (err) {
      console.error(err);
    }
  };

  const displayUsers = tab === 'active' ? users : blockedUsers;

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200 pb-2">
        {(['active', 'blocked'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 font-medium ${
              tab === t
                ? 'border-b-2 border-accent text-accent'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            {t === 'active' ? `Активные (${users.length})` : `Заблокированные (${blockedUsers.length})`}
          </button>
        ))}
      </div>

      {/* Users list */}
      {loading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
        </div>
      ) : displayUsers.length > 0 ? (
        <div className="grid gap-4">
          {displayUsers.map((user) => (
            <div key={user.id} className="bg-white rounded-lg shadow-sm p-4 border border-gray-100">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-primary">
                    {user.firstName} {user.lastName}
                  </h3>
                  <p className="text-sm text-gray-600">@{user.username || 'unknown'}</p>
                  <p className="text-xs text-gray-400 mt-1">ID: {user.id}</p>
                </div>
                {tab === 'active' ? (
                  <button
                    onClick={() => {
                      const reason = prompt('Причина блокировки:');
                      if (reason !== null) handleBlockUser(user.id, reason);
                    }}
                    className="bg-danger text-white px-3 py-2 rounded text-sm hover:bg-red-600 transition-colors"
                  >
                    Заблокировать
                  </button>
                ) : (
                  <button
                    onClick={() => handleUnblockUser(user.id)}
                    className="bg-success text-white px-3 py-2 rounded text-sm hover:bg-green-600 transition-colors"
                  >
                    Разблокировать
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">Пользователи не найдены</div>
      )}
    </div>
  );
}
