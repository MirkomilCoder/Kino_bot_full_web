'use client';

interface User {
  id: number;
  firstName: string | null;
  lastName: string | null;
  username: string | null;
  role: string;
  joinedAt: string;
}

interface ProfileSectionProps {
  user: User;
}

export default function ProfileSection({ user }: ProfileSectionProps) {
  const fullName = `${user.firstName || ''} ${user.lastName || ''}`.trim() || user.username || 'Unknown';
  const joinDate = new Date(user.joinedAt).toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className="space-y-6">
      {/* Profile card */}
      <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-100">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 mb-8">
          <div className="flex items-center justify-center w-20 h-20 bg-gradient-to-br from-accent to-blue-600 rounded-full text-white text-2xl font-bold">
            {fullName.charAt(0).toUpperCase()}
          </div>
          <div>
            <h1 className="text-2xl font-bold text-primary">{fullName}</h1>
            <p className="text-gray-600">@{user.username || 'anonymous'}</p>
            <div className="flex items-center gap-2 mt-2">
              <span className="px-3 py-1 bg-accent/10 text-accent text-xs font-medium rounded-full capitalize">
                {user.role === 'owner' ? 'Владелец' : user.role === 'admin' ? 'Администратор' : 'Пользователь'}
              </span>
            </div>
          </div>
        </div>

        {/* Profile info grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {/* User ID */}
          <div className="bg-light rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">ID пользователя</p>
            <p className="text-lg font-mono text-primary">{user.id}</p>
          </div>

          {/* Joined date */}
          <div className="bg-light rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Дата присоединения</p>
            <p className="text-lg font-medium text-primary">{joinDate}</p>
          </div>

          {/* First name */}
          <div className="bg-light rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Имя</p>
            <p className="text-lg text-primary">{user.firstName || '-'}</p>
          </div>

          {/* Last name */}
          <div className="bg-light rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Фамилия</p>
            <p className="text-lg text-primary">{user.lastName || '-'}</p>
          </div>
        </div>
      </div>

      {/* Account info */}
      <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-100">
        <h2 className="text-lg font-semibold text-primary mb-4">Информация об аккаунте</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <span className="text-gray-600">Статус</span>
            <span className="text-green-600 font-medium">✓ Активен</span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <span className="text-gray-600">Верификация</span>
            <span className="text-accent font-medium">Telegram Web App</span>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-gray-600">Доступ</span>
            <span className="text-success font-medium">Полный доступ</span>
          </div>
        </div>
      </div>

      {/* Security info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="font-semibold text-blue-900 mb-2">🔒 Безопасность</h3>
        <p className="text-sm text-blue-800">
          Ваш аккаунт защищен Telegram Web App. Все коммуникации зашифрованы и защищены.
        </p>
      </div>
    </div>
  );
}
