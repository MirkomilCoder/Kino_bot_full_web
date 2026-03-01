'use client';

export default function AuthPage({ error }: { error?: string | null }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-primary to-primary/80 px-4">
      <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full text-center">
        <div className="mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-accent rounded-full mb-4">
            <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 11 8.5 11zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-primary mb-2">Kino Bot</h1>
          <p className="text-gray-600 text-sm">Web Application</p>
        </div>

        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-700 text-sm font-medium">Ошибка подтверждения</p>
            <p className="text-red-600 text-xs mt-1">{error}</p>
          </div>
        ) : (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <p className="text-blue-700 text-sm font-medium">Откройте приложение в Telegram</p>
            <p className="text-blue-600 text-xs mt-1">Это приложение можно открыть только через веб-приложение Telegram бота</p>
          </div>
        )}

        <div className="space-y-3">
          <div className="flex items-center text-left bg-gray-50 p-3 rounded-lg">
            <div className="flex-shrink-0">
              <svg className="w-5 h-5 text-accent" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-gray-700">
                <span className="font-medium">Безопасно:</span> Данные проверены Telegram
              </p>
            </div>
          </div>

          <div className="flex items-center text-left bg-gray-50 p-3 rounded-lg">
            <div className="flex-shrink-0">
              <svg className="w-5 h-5 text-accent" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-gray-700">
                <span className="font-medium">Приватно:</span> Ваша информация защищена
              </p>
            </div>
          </div>
        </div>

        <p className="text-gray-500 text-xs mt-6">
          Чтобы получить доступ, откройте это веб-приложение через своего Telegram бота
        </p>
      </div>
    </div>
  );
}
