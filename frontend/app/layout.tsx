'use client';

import './globals.css';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';
import { fetchWithAuth } from '@/lib/api';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: 1,
      },
    },
  }));

  const setUser = useAuthStore((state) => state.setUser);

  useEffect(() => {
    async function loadUser() {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const res = await fetchWithAuth('/auth/me');
          if (res.ok) {
            const userData = await res.json();
            setUser(userData);
          } else {
            setUser(null);
          }
        } catch (e) {
          setUser(null);
        }
      } else {
        setUser(null);
      }
    }
    loadUser();
  }, [setUser]);

  return (
    <html lang="en" className="dark">
      <head>
        <title>Enterprise AI Document Assistant</title>
        <meta name="description" content="Secure multi-tenant AI Document Assistant with RAG & source citations" />
      </head>
      <body className="min-h-screen antialiased bg-[#090d16] text-slate-100 selection:bg-indigo-500 selection:text-white">
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </body>
    </html>
  );
}
