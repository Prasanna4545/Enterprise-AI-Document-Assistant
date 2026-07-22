'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

export default function RootPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuthStore();

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        router.replace('/chat');
      } else {
        router.replace('/login');
      }
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#090d16] text-white">
      <div className="flex items-center gap-3">
        <span className="animate-spin rounded-full h-6 w-6 border-2 border-indigo-500 border-t-transparent" />
        <span className="text-sm font-medium text-slate-400">Loading Enterprise AI Workspace...</span>
      </div>
    </div>
  );
}
