'use client';

import { useEffect, useState } from 'react';

interface Movie {
  code: string;
  caption: string | null;
  fileType: string;
  addedAt: string;
}

interface MoviesListProps {
  token: string;
}

export default function MoviesList({ token }: MoviesListProps) {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    fetchMovies();
  }, [searchQuery, page]);

  const fetchMovies = async () => {
    setLoading(true);
    setError(null);

    try {
      const url = new URL('/api/movies', window.location.origin);
      if (searchQuery) url.searchParams.set('q', searchQuery);
      url.searchParams.set('page', page.toString());
      url.searchParams.set('limit', '20');

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch movies');
      }

      const data = await response.json();
      setMovies(data.movies || []);
      setHasMore(data.movies.length === 20);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchMovies();
  };

  return (
    <div className="space-y-6">
      {/* Search form */}
      <form onSubmit={handleSearch} className="relative">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Поиск фильмов..."
          className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-accent focus:border-transparent outline-none"
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-accent text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors"
        >
          Поиск
        </button>
      </form>

      {/* Loading state */}
      {loading && (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Movies grid */}
      {!loading && movies.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {movies.map((movie) => (
            <div
              key={movie.code}
              className="bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow p-4 border border-gray-100"
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-primary text-sm flex-1 line-clamp-2">{movie.code}</h3>
                <span className="text-xs bg-accent text-white px-2 py-1 rounded whitespace-nowrap ml-2">
                  {movie.fileType.toUpperCase()}
                </span>
              </div>
              {movie.caption && <p className="text-sm text-gray-600 line-clamp-2 mb-3">{movie.caption}</p>}
              <p className="text-xs text-gray-400">{new Date(movie.addedAt).toLocaleDateString('ru-RU')}</p>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && movies.length === 0 && !error && (
        <div className="bg-white rounded-lg p-8 text-center border border-gray-100">
          <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 4v16m10-16v16M7 4h10m-4 0v4m0 8v4M7 12h10"
            />
          </svg>
          <p className="text-gray-600 font-medium">Фильмы не найдены</p>
          <p className="text-gray-400 text-sm mt-1">Попробуйте изменить поисковый запрос</p>
        </div>
      )}

      {/* Pagination */}
      {!loading && movies.length > 0 && (
        <div className="flex justify-center gap-4">
          {page > 1 && (
            <button
              onClick={() => setPage(page - 1)}
              className="px-4 py-2 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 transition-colors"
            >
              Назад
            </button>
          )}
          {hasMore && (
            <button
              onClick={() => setPage(page + 1)}
              className="px-4 py-2 rounded-lg bg-accent text-white hover:bg-blue-600 transition-colors"
            >
              Вперед
            </button>
          )}
        </div>
      )}
    </div>
  );
}
