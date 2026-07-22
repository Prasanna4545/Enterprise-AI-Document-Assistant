'use client';

import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  MessageSquareText, 
  FileText, 
  BarChart3, 
  LogOut, 
  Building2, 
  ShieldCheck, 
  Sparkles,
  UserCheck
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const navItems = [
    { label: 'RAG Chat', href: '/chat', icon: MessageSquareText },
    { label: 'Documents', href: '/documents', icon: FileText },
    ...(user?.role === 'ADMIN' || user?.role === 'MANAGER'
      ? [{ label: 'Admin Analytics', href: '/admin', icon: BarChart3 }]
      : []),
  ];

  return (
    <div className="min-h-screen flex bg-[#080d1a] text-slate-100">
      {/* Sidebar Navigation */}
      <aside className="w-64 border-r border-slate-800/80 bg-[#0c1324]/80 backdrop-blur-xl flex flex-col justify-between p-4 sticky top-0 h-screen z-20">
        <div>
          {/* Logo Branding */}
          <div className="flex items-center gap-3 px-3 py-3 mb-6 rounded-xl bg-gradient-to-r from-indigo-950/60 to-purple-950/60 border border-indigo-500/20">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center shadow-md shadow-indigo-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-sm text-white leading-tight">DocAssistant AI</h1>
              <p className="text-[11px] text-indigo-300 font-medium flex items-center gap-1 mt-0.5">
                <Building2 className="w-3 h-3" /> {user?.organization_name || 'Organization'}
              </p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-indigo-600/90 to-purple-600/90 text-white shadow-lg shadow-indigo-500/20'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Footer Profile & Role Badge */}
        <div className="pt-4 border-t border-slate-800/80">
          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 mb-3">
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs font-semibold text-white truncate max-w-[120px]">{user?.full_name || 'User'}</p>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase ${
                user?.role === 'ADMIN'
                  ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
                  : user?.role === 'MANAGER'
                  ? 'bg-purple-500/10 text-purple-400 border-purple-500/30'
                  : 'bg-slate-500/10 text-slate-400 border-slate-500/30'
              }`}>
                {user?.role || 'EMPLOYEE'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 truncate">{user?.email}</p>
          </div>

          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 py-2 text-xs font-medium text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
          >
            <LogOut className="w-4 h-4" /> Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto min-h-screen">
        {children}
      </main>
    </div>
  );
}
