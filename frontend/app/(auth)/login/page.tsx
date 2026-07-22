'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Shield, Sparkles, Lock, Mail, ArrowRight } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

export default function LoginPage() {
  const router = useRouter();
  const setUser = useAuthStore((state) => state.setUser);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Login failed');
      }

      const data = await res.json();
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      // Fetch User Info
      const meRes = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      if (meRes.ok) {
        const userData = await meRes.json();
        setUser(userData);
      }

      router.push('/chat');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const setDemoCredentials = (role: 'ADMIN' | 'EMPLOYEE') => {
    if (role === 'ADMIN') {
      setEmail('admin@acmecorp.com');
      setPassword('admin123');
    } else {
      setEmail('employee@acmecorp.com');
      setPassword('employee123');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Ambient Glows */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/20 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md glass-panel rounded-2xl p-8 shadow-2xl relative z-10">
        {/* Header Branding */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30 mb-3">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Enterprise AI Assistant <Sparkles className="w-5 h-5 text-indigo-400" />
          </h1>
          <p className="text-sm text-slate-400 mt-1">Secure Multi-Tenant Knowledge Workspace</p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Work Email
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl glass-input text-sm transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl glass-input text-sm transition-all"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-medium shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-50 mt-2"
          >
            {loading ? (
              <span className="inline-block animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
            ) : (
              <>
                Sign In to Workspace <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Demo Account Quick Pickers */}
        <div className="mt-6 pt-6 border-t border-slate-800">
          <p className="text-xs text-center text-slate-400 mb-3">Quick Demo Credentials:</p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setDemoCredentials('ADMIN')}
              className="flex-1 py-1.5 px-3 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 text-xs text-indigo-300 transition-all text-center"
            >
              Fill Admin Demo
            </button>
            <button
              type="button"
              onClick={() => setDemoCredentials('EMPLOYEE')}
              className="flex-1 py-1.5 px-3 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 text-xs text-purple-300 transition-all text-center"
            >
              Fill Employee Demo
            </button>
          </div>
        </div>

        <div className="mt-6 text-center text-sm text-slate-400">
          Need an organization workspace?{' '}
          <Link href="/signup" className="text-indigo-400 font-medium hover:underline">
            Create Org & Admin
          </Link>
        </div>
      </div>
    </div>
  );
}
