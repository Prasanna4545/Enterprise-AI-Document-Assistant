'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  BarChart3, 
  Users, 
  FileText, 
  Database, 
  ShieldAlert, 
  UserPlus, 
  Activity,
  Layers
} from 'lucide-react';
import { fetchWithAuth } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

interface AnalyticsData {
  total_documents: number;
  total_chunks: number;
  total_users: number;
  total_queries: number;
  doc_usage: Array<{ document_id: string; title: string; filename: string; reference_count: number }>;
  queries_last_7_days: Record<string, number>;
}

interface AuditLog {
  id: string;
  user_name?: string;
  user_email?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  timestamp: string;
}

interface NegativeFeedbackDebugItem {
  feedback_id: string;
  message_id: string;
  user_name?: string;
  user_email?: string;
  user_query: string;
  assistant_answer: string;
  rating: string;
  retrieved_chunks: Array<{
    chunk_id?: string;
    document_id: string;
    filename: string;
    title: string;
    page_number?: number;
    snippet: string;
  }>;
  timestamp: string;
}

interface OrgUser {
  id: string;
  email: string;
  full_name: string;
  role: 'ADMIN' | 'MANAGER' | 'EMPLOYEE';
  is_active: boolean;
  created_at: string;
}

export default function AdminPage() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'analytics' | 'users' | 'audit' | 'feedback'>('analytics');

  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [newFullName, setNewFullName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState<'ADMIN' | 'MANAGER' | 'EMPLOYEE'>('EMPLOYEE');

  // Fetch Analytics
  const { data: analytics } = useQuery<AnalyticsData>({
    queryKey: ['analytics'],
    queryFn: async () => {
      const res = await fetchWithAuth('/admin/analytics');
      if (!res.ok) throw new Error('Failed to load analytics');
      return res.json();
    },
  });

  // Fetch Users
  const { data: users = [] } = useQuery<OrgUser[]>({
    queryKey: ['adminUsers'],
    queryFn: async () => {
      const res = await fetchWithAuth('/admin/users');
      if (!res.ok) return [];
      return res.json();
    },
    enabled: user?.role === 'ADMIN',
  });

  // Fetch Audit Logs
  const { data: auditLogs = [] } = useQuery<AuditLog[]>({
    queryKey: ['auditLogs'],
    queryFn: async () => {
      const res = await fetchWithAuth('/admin/audit-logs');
      if (!res.ok) return [];
      return res.json();
    },
    enabled: user?.role === 'ADMIN',
  });

  // Fetch Negative Feedback Debug Items
  const { data: negativeFeedback = [] } = useQuery<NegativeFeedbackDebugItem[]>({
    queryKey: ['negativeFeedback'],
    queryFn: async () => {
      const res = await fetchWithAuth('/admin/negative-feedback');
      if (!res.ok) return [];
      return res.json();
    },
    enabled: user?.role === 'ADMIN' || user?.role === 'MANAGER',
  });


  // Add User Mutation
  const addUserMutation = useMutation({
    mutationFn: async () => {
      const res = await fetchWithAuth('/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: newFullName,
          email: newEmail,
          password: newPassword,
          role: newRole,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to add user');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      setShowAddUserModal(false);
      setNewFullName('');
      setNewEmail('');
      setNewPassword('');
    },
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header & Tabs */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Admin & Usage Analytics</h1>
          <p className="text-slate-400 text-sm mt-1">Track document queries, token vectors, user access, and audit trails.</p>
        </div>

        <div className="flex bg-slate-900/80 p-1.5 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('analytics')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'analytics' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Analytics Overview
          </button>
          {user?.role === 'ADMIN' && (
            <>
              <button
                onClick={() => setActiveTab('users')}
                className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'users' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                User Management
              </button>
              <button
                onClick={() => setActiveTab('audit')}
                className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === 'audit' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Audit Trail
              </button>
            </>
          )}
          <button
            onClick={() => setActiveTab('feedback')}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'feedback' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Retrieval Quality & Feedback
          </button>

        </div>
      </div>

      {activeTab === 'analytics' && (
        <div className="space-y-8">
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="glass-panel p-5 rounded-2xl flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 font-semibold uppercase">Total Indexed Docs</p>
                <h3 className="text-2xl font-bold text-white mt-1">{analytics?.total_documents || 0}</h3>
              </div>
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <FileText className="w-5 h-5" />
              </div>
            </div>

            <div className="glass-panel p-5 rounded-2xl flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 font-semibold uppercase">Embedded Chunks</p>
                <h3 className="text-2xl font-bold text-white mt-1">{analytics?.total_chunks || 0}</h3>
              </div>
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                <Layers className="w-5 h-5" />
              </div>
            </div>

            <div className="glass-panel p-5 rounded-2xl flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 font-semibold uppercase">Active Users</p>
                <h3 className="text-2xl font-bold text-white mt-1">{analytics?.total_users || 0}</h3>
              </div>
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <Users className="w-5 h-5" />
              </div>
            </div>

            <div className="glass-panel p-5 rounded-2xl flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 font-semibold uppercase">RAG Queries Run</p>
                <h3 className="text-2xl font-bold text-white mt-1">{analytics?.total_queries || 0}</h3>
              </div>
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                <Activity className="w-5 h-5" />
              </div>
            </div>
          </div>

          {/* Top Referenced Documents */}
          <div className="glass-panel rounded-2xl p-6">
            <h3 className="text-base font-semibold text-white mb-4">Most Referenced Documents in RAG Answers</h3>
            <div className="space-y-3">
              {analytics?.doc_usage?.map((doc) => (
                <div key={doc.document_id} className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center gap-3">
                    <FileText className="w-4 h-4 text-indigo-400" />
                    <div>
                      <p className="text-sm font-medium text-white">{doc.title}</p>
                      <p className="text-xs text-slate-400">{doc.filename}</p>
                    </div>
                  </div>
                  <span className="px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold">
                    {doc.reference_count} citations
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'users' && user?.role === 'ADMIN' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-white">Organization Accounts</h3>
            <button
              onClick={() => setShowAddUserModal(true)}
              className="py-2 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium flex items-center gap-2 transition-all"
            >
              <UserPlus className="w-4 h-4" /> Add Team Member
            </button>
          </div>

          <div className="glass-panel rounded-2xl overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900/60 text-slate-400 text-xs uppercase font-semibold">
                <tr>
                  <th className="p-4">Name & Email</th>
                  <th className="p-4">Role</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Created Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-800/30">
                    <td className="p-4">
                      <p className="font-medium text-white">{u.full_name}</p>
                      <p className="text-xs text-slate-400">{u.email}</p>
                    </td>
                    <td className="p-4">
                      <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        {u.role}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className="text-xs text-emerald-400">Active</span>
                    </td>
                    <td className="p-4 text-xs text-slate-400">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'audit' && user?.role === 'ADMIN' && (
        <div className="glass-panel rounded-2xl overflow-hidden">
          <div className="p-5 border-b border-slate-800">
            <h3 className="font-semibold text-white text-base flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-indigo-400" /> Security Audit Log
            </h3>
          </div>
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/60 text-slate-400 text-xs uppercase font-semibold">
              <tr>
                <th className="p-4">Timestamp</th>
                <th className="p-4">User</th>
                <th className="p-4">Action</th>
                <th className="p-4">Resource Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {auditLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/30">
                  <td className="p-4 text-xs font-mono text-slate-400">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="p-4">
                    <p className="font-medium text-white">{log.user_name || 'System'}</p>
                    <p className="text-xs text-slate-400">{log.user_email}</p>
                  </td>
                  <td className="p-4 font-mono text-xs text-indigo-300">{log.action}</td>
                  <td className="p-4 text-xs text-slate-400">{log.resource_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Retrieval Quality & Negative Feedback Debugger Tab */}
      {activeTab === 'feedback' && (
        <div className="space-y-6">
          <div className="glass-panel p-6 rounded-2xl border border-slate-800">
            <h2 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-red-400" /> Negative Feedback & Retrieval Tracing
            </h2>
            <p className="text-slate-400 text-xs">
              Inspect user queries flagged with 👎 negative feedback side-by-side with generated answers and exact retrieved vector chunks to isolate bad retrieval chunks.
            </p>
          </div>

          {negativeFeedback.length === 0 ? (
            <div className="glass-panel p-12 text-center rounded-2xl border border-slate-800">
              <p className="text-slate-400 text-sm">No negative feedback items recorded yet.</p>
            </div>
          ) : (
            <div className="space-y-6">
              {negativeFeedback.map((fb) => (
                <div key={fb.feedback_id} className="glass-panel p-6 rounded-2xl border border-red-500/20 space-y-4">
                  <div className="flex justify-between items-center pb-3 border-b border-slate-800">
                    <div>
                      <span className="text-xs font-semibold text-red-400 bg-red-500/10 px-2.5 py-1 rounded-md border border-red-500/20">
                        👎 Thumbs Down
                      </span>
                      <span className="text-slate-400 text-xs ml-3">
                        Reported by <strong className="text-slate-200">{fb.user_name}</strong> ({fb.user_email}) on {new Date(fb.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <span className="text-slate-500 text-[11px] font-mono">Msg ID: {fb.message_id.slice(0, 8)}...</span>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Left Column: Question & Answer */}
                    <div className="space-y-4">
                      <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800">
                        <p className="text-[11px] font-semibold text-indigo-400 uppercase tracking-wider mb-1">Original User Question</p>
                        <p className="text-sm font-medium text-white">{fb.user_query}</p>
                      </div>

                      <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800">
                        <p className="text-[11px] font-semibold text-purple-400 uppercase tracking-wider mb-1">Generated Assistant Answer</p>
                        <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{fb.assistant_answer}</p>
                      </div>
                    </div>

                    {/* Right Column: Retrieved Chunks Side-by-Side */}
                    <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-3">
                      <p className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider flex items-center justify-between">
                        <span>Retrieved Chunks Used ({fb.retrieved_chunks.length})</span>
                      </p>

                      {fb.retrieved_chunks.length === 0 ? (
                        <p className="text-xs text-slate-500 italic">No retrieved chunks recorded for this response.</p>
                      ) : (
                        <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                          {fb.retrieved_chunks.map((chk, cIdx) => (
                            <div key={cIdx} className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1">
                              <div className="flex justify-between items-center font-medium text-slate-300">
                                <span>📄 {chk.filename || chk.title} (Page {chk.page_number || 1})</span>
                                <span className="text-[10px] text-slate-500 font-mono">Chunk #{chk.chunk_id || cIdx + 1}</span>
                              </div>
                              <p className="text-slate-400 italic line-clamp-3 bg-slate-900/50 p-2 rounded border border-slate-800/60">
                                &quot;{chk.snippet}&quot;
                              </p>

                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add User Modal */}

      {showAddUserModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel max-w-md w-full rounded-2xl p-6 border border-slate-700">
            <h3 className="font-bold text-white text-lg mb-4">Add Team Member</h3>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                addUserMutation.mutate();
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl glass-input text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Email</label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl glass-input text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Password</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl glass-input text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Role</label>
                <select
                  value={newRole}
                  onChange={(e: any) => setNewRole(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl glass-input text-sm bg-slate-900"
                >
                  <option value="EMPLOYEE">Employee (Query docs only)</option>
                  <option value="MANAGER">Manager (Upload & query docs)</option>
                  <option value="ADMIN">Admin (Full permissions)</option>
                </select>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddUserModal(false)}
                  className="flex-1 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addUserMutation.isPending}
                  className="flex-1 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium"
                >
                  {addUserMutation.isPending ? 'Adding...' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
