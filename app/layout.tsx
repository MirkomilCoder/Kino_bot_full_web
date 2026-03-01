import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Kino Bot Web App',
  description: 'Telegram Kino Bot Web Application - Full Stack React with Next.js',
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
    userScalable: false,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta name="theme-color" content="#3b82f6" />
      </head>
      <body>{children}</body>
    </html>
  );
}
