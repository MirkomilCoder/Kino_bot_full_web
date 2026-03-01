'use client';

import { useEffect, useState } from 'react';

interface Movie {
  code: string;
  caption: string | null;
  fileType: string;
  channelId: number;
  messageId: number;
  addedAt: string;
}

interface AdminMoviesProps {
  token: string;
}

export default function AdminMovies({ token }: AdminMoviesProps) {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    code: '',
    fileId: '',
    fileType: 'video',
    channelId: '',
    messageId: '',
    caption: '',
  });
  const [page, setPage] = useState(1);

  useEffect(() => {
    fetchMovies();
  }, [page]);

  const fetchMovies = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/admin/movies?page=${page}&limit=50`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch movies');

      const data = await response.json();
      setMovies(data.movies || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleAddMovie = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const response = await fetch('/api/admin/movies', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          code: formData.code.trim(),
          fileId: formData.fileId.trim(),
          fileType: formData.fileType,
          channelId: parseInt(formData.channelId),
          messageId: parseInt(formData.messageId),
          caption: formData.caption.trim(),
        }),
      });

      if (!response.ok) throw new Error('Failed to add movie');

      setFormData({ code: '', fileId: '', fileType: 'video', channelId: '', messageId: '', caption: '' });
      setShowForm(false);
      fetchMovies();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const handleDeleteMovie = async (code: string) => {
    if (!confirm('Удалить этот фильм?')) return;

    try {
      const response = await fetch('/api/admin/movies', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ code }),
      });

      if (!response.ok) throw new Error('Failed to delete movie');

      fetchMovies();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  return (
    <div className="space-y-6">
      <button
        onClick={() => setShowForm(!showForm)}
        className="bg-accent text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition-colors font-medium"
      >
        {showForm ? '✕ Закрыть' : '+ Добавить фильм'}
      </button>

      {/* Add form */}
      {showForm && (
        <form onSubmit={handleAddMovie} className="bg-white rounded-lg shadow-sm p-6 border border-gray-100 grid gap-4">
          <input
            type="text"
            placeholder="Код фильма"
            value={formData.code}
            onChange={(e) => setFormData({ ...formData, code: e.target.value })}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent outline-none"
            required
          />
          <input
            type="text"
            placeholder="File ID"
            value={formData.fileId}
            onChange={(e) => setFormData({ ...formData, fileId: e.target.value })}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent outline-none"
            required
          />
          <select
            value={formData.fileType}
            onChange={(e) => setFormData({ ...formData, fileType: e.target.value })}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent outline-none"
          >
            <option value="video">Видео</option>
            <option value="document">Документ</option>
            <option value="audio">Аудио</option>
          </select>
          <input
            type="number"
            placeholder="Channel ID"
            value={formData.channelId}
            onChange={(e) => setFormData({ ...formData, channelId: e.target.value })}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent outline-none"
            required
          />
          <input
            type="number"
            placeholder="Message ID"
            value={formData.messageId}
            onChange={(e) => setFormData({ ...formData, messageId: e.target.value })}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent outline-none"
            required
          />
          <textarea
            placeholder="Описание (опционально)"
            value={formData.caption}
            onChange={(e) => setFormData({ ...formData, caption: e.target.value })}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-accent outline-none resize-none h-24"
          />
          <button
            type="submit"
            className="bg-success text-white px-6 py-2 rounded-lg hover:bg-green-600 transition-colors font-medium"
          >
            Добавить
          </button>
        </form>
      )}

      {/* Movies list */}
      {!loading && movies.length > 0 && (
        <div className="grid gap-4">
          {movies.map((movie) => (
            <div key={movie.code} className="bg-white rounded-lg shadow-sm p-4 border border-gray-100">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-semibold text-primary">{movie.code}</h3>
                  {movie.caption && <p className="text-sm text-gray-600 mt-1 line-clamp-2">{movie.caption}</p>}
                  <div className="flex gap-2 mt-2">
                    <span className="text-xs bg-accent/10 text-accent px-2 py-1 rounded">{movie.fileType}</span>
                    <span className="text-xs text-gray-500">Ch: {movie.channelId}</span>
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteMovie(movie.code)}
                  className="text-danger hover:bg-red-50 px-3 py-2 rounded transition-colors font-medium text-sm"
                >
                  Удалить
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Loading and empty states */}
      {loading && (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
        </div>
      )}

      {!loading && movies.length === 0 && <div className="text-center py-8 text-gray-500">Фильмы не найдены</div>}
    </div>
  );
}
