'use client';

import { useEffect, useState } from 'react';

interface Channel {
  id: number;
  title: string | null;
  username: string | null;
}

interface AdminChannelsProps {
  token: string;
}

export default function AdminChannels({ token }: AdminChannelsProps) {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    chatId: '',
    title: '',
    username: '',
  });

  useEffect(() => {
    fetchChannels();
  }, []);

  const fetchChannels = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/admin/channels', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch channels');

      const data = await response.json();
      setChannels(data.channels || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddChannel = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const response = await fetch('/api/admin/channels', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          chatId: parseInt(formData.chatId),
          title: formData.title.trim(),
          username: formData.username.trim(),
        }),
      });

      if (!response.ok) throw new Error('Failed to add channel');

      setFormData({ chatId: '', title: '', username: '' });
      setShowForm(false);
      fetchChannels();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteChannel = async (chatId: number) => {
    if (!confirm('Удалить этот канал?')) return;

    try {
      const response = await fetch('/api/admin/channels', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ chatId }),
      });

      if (!response.ok) throw new Error('Failed to delete channel');

      fetchChannels();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      <button
        onClick={() => setShowForm(!showForm)}
        className="bg-accent text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition-colors font-medium"
      >
        {showForm ? '✕ Закрыть' : '+ Добавить канал'}
      </button>

      {/* Add form */}
      {showForm && (
        <form onSubmit={handleAddChannel} className="bg-white rounded-lg shadow-sm p-6 border border-gray-100 grid gap-4">
          <input
            type="number"
            placeholder="Chat ID"
            value={formData.chatId}
            onChange={(e) => setFormData({ ...formData, chatId: e.target.value })}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent outline-none"
            required
          />
          <input
            type="text"
            placeholder="Название канала"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent outline-none"
          />
          <input
            type="text"
            placeholder="Username (@username)"
            value={formData.username}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent outline-none"
          />
          <button
            type="submit"
            className="bg-success text-white px-6 py-2 rounded-lg hover:bg-green-600 transition-colors font-medium"
          >
            Добавить
          </button>
        </form>
      )}

      {/* Channels list */}
      {loading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
        </div>
      ) : channels.length > 0 ? (
        <div className="grid gap-4">
          {channels.map((channel) => (
            <div key={channel.id} className="bg-white rounded-lg shadow-sm p-4 border border-gray-100">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-primary">{channel.title || 'Unnamed Channel'}</h3>
                  <p className="text-sm text-gray-600">@{channel.username || 'unknown'}</p>
                  <p className="text-xs text-gray-400 mt-1">ID: {channel.id}</p>
                </div>
                <button
                  onClick={() => handleDeleteChannel(channel.id)}
                  className="bg-danger text-white px-3 py-2 rounded text-sm hover:bg-red-600 transition-colors"
                >
                  Удалить
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">Каналы не найдены</div>
      )}
    </div>
  );
}
