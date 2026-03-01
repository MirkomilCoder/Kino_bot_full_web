'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import OwnerDashboard from '@/components/dashboards/OwnerDashboard';
import AdminDashboard from '@/components/dashboards/AdminDashboard';
import UserDashboard from '@/components/dashboards/UserDashboard';
import AuthPage from '@/components/AuthPage';

interface User {
  id: number;
  firstName: string | null;
  lastName: string | null;
  username: string | null;
  role: 'owner' | 'admin' | 'user';
  joinedAt: string;
}

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const authenticate = async () => {
      try {
        // Get init data from Telegram Web App
        if (typeof window !== 'undefined' && (window as any).Telegram?.WebApp) {
          const webApp = (window as any).Telegram.WebApp;
          const initData = webApp.initData;

          if (initData) {
            // Send init data to backend for validation
            const response = await fetch('/api/auth/login', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ initData }),
            });

            if (response.ok) {
              const data = await response.json();
              if (data.success) {
                setUser(data.user);
                // Store token in localStorage for subsequent requests
                localStorage.setItem('auth_token', data.token);
                setLoading(false);
              } else {
                setError('Authentication failed');
                setLoading(false);
              }
            } else {
              setError('Authentication error');
              setLoading(false);
            }
          } else {
            setError('Telegram Web App not available');
            setLoading(false);
          }
        } else {
          setError('Telegram Web App not available');
          setLoading(false);
        }
      } catch (err) {
        console.error('[v0] Auth error:', err);
        setError('Authentication failed');
        setLoading(false);
      }
    };

    authenticate();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-primary to-primary/80">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-accent mb-4"></div>
          <p className="text-white">Загрузка приложения...</p>
        </div>
      </div>
    );
  }

  if (error || !user) {
    return <AuthPage error={error} />;
  }

  return (
    <main className="min-h-screen bg-light">
      {user.role === 'owner' && <OwnerDashboard user={user} />}
      {user.role === 'admin' && <AdminDashboard user={user} />}
      {user.role === 'user' && <UserDashboard user={user} />}
    </main>
  );
}
