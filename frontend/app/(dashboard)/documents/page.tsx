'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  UploadCloud, 
  FileText, 
  Trash2, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  Shield, 
  FileSpreadsheet, 
  FileCode,
  Lock,
  Globe
} from 'lucide-react';
import { fetchWithAuth } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

interface DocumentItem {
  id: string;
  title: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  chunk_count: number;
  access_level: 'PUBLIC' | 'MANAGERS_ONLY' | 'ADMIN_ONLY';
  created_at: string;
  error_message?: string;
}

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docTitle, setDocTitle] = useState('');
  const [accessLevel, setAccessLevel] = useState<'PUBLIC' | 'MANAGERS_ONLY' | 'ADMIN_ONLY'>('PUBLIC');
  const [uploading, setUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Permission Modal States
  const [showPermModal, setShowPermModal] = useState(false);
  const [selectedDocForPerms, setSelectedDocForPerms] = useState<DocumentItem | null>(null);
  const [permAccessLevel, setPermAccessLevel] = useState<'PUBLIC' | 'MANAGERS_ONLY' | 'ADMIN_ONLY'>('PUBLIC');
  const [permRoles, setPermRoles] = useState<('ADMIN' | 'MANAGER' | 'EMPLOYEE')[]>([]);
  const [permUserIds, setPermUserIds] = useState<string[]>([]);


  // Fetch Documents
  const { data: documents = [], isLoading } = useQuery<DocumentItem[]>({
    queryKey: ['documents'],
    queryFn: async () => {
      const res = await fetchWithAuth('/documents/');
      if (!res.ok) throw new Error('Failed to load documents');
      return res.json();
    },
    refetchInterval: 4000, // Poll every 4 seconds to reflect ingestion status changes
  });

  // Handle Document Upload
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setErrorMsg('');

    const formData = new FormData();
    formData.append('file', selectedFile);
    if (docTitle.trim()) formData.append('title', docTitle.trim());
    formData.append('access_level', accessLevel);

    try {
      const res = await fetchWithAuth('/documents/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      setSelectedFile(null);
      setDocTitle('');
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setUploading(false);
    }
  };

  // Delete Document Mutation
  const deleteMutation = useMutation({
    mutationFn: async (docId: string) => {
      const res = await fetchWithAuth(`/documents/${docId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const getFileIcon = (type: string) => {
    if (type.includes('pdf')) return <FileText className="w-5 h-5 text-red-400" />;
    if (type.includes('xls') || type.includes('csv')) return <FileSpreadsheet className="w-5 h-5 text-emerald-400" />;
    if (type.includes('doc')) return <FileText className="w-5 h-5 text-blue-400" />;
    return <FileCode className="w-5 h-5 text-purple-400" />;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" /> Indexed
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
            <Clock className="w-3.5 h-3.5 animate-spin" /> Chunking & Embedding
          </span>
        );
      case 'PENDING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Clock className="w-3.5 h-3.5" /> Queued
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
            <AlertCircle className="w-3.5 h-3.5" /> Ingestion Failed
          </span>
        );
    }
  };

  const canUpload = user?.role === 'ADMIN' || user?.role === 'MANAGER';

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Organization Knowledge Base</h1>
        <p className="text-slate-400 text-sm mt-1">Upload and manage internal documents for RAG context retrieval.</p>
      </div>

      {/* Upload Zone (For Admin & Manager) */}
      {canUpload && (
        <div className="glass-panel p-6 rounded-2xl">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <UploadCloud className="w-5 h-5 text-indigo-400" /> Ingest New Document
          </h2>

          {errorMsg && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleUpload} className="space-y-4">
            <div className="border-2 border-dashed border-slate-700/80 hover:border-indigo-500/60 rounded-xl p-6 text-center transition-all cursor-pointer bg-slate-900/40 relative">
              <input
                type="file"
                required
                accept=".pdf,.docx,.doc,.txt,.md,.xlsx,.xls,.csv"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setSelectedFile(e.target.files[0]);
                    if (!docTitle) setDocTitle(e.target.files[0].name.replace(/\.[^/.]+$/, ''));
                  }
                }}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <UploadCloud className="w-10 h-10 text-indigo-400 mx-auto mb-2" />
              {selectedFile ? (
                <p className="text-sm font-semibold text-indigo-300">{selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)</p>
              ) : (
                <>
                  <p className="text-sm text-slate-300 font-medium">Click or Drag & Drop File</p>
                  <p className="text-xs text-slate-500 mt-1">Supports PDF, DOCX, XLSX, TXT, MD (Max 50MB)</p>
                </>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Document Title
                </label>
                <input
                  type="text"
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                  placeholder="e.g. Q3 HR Policy Manual"
                  className="w-full px-4 py-2 rounded-xl glass-input text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Role Access Permission
                </label>
                <select
                  value={accessLevel}
                  onChange={(e: any) => setAccessLevel(e.target.value)}
                  className="w-full px-4 py-2 rounded-xl glass-input text-sm bg-slate-900"
                >
                  <option value="PUBLIC">Public (All Employees)</option>
                  <option value="MANAGERS_ONLY">Managers & Admins Only</option>
                  <option value="ADMIN_ONLY">Admins Only</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={!selectedFile || uploading}
              className="py-2.5 px-6 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm transition-all disabled:opacity-50 flex items-center gap-2"
            >
              {uploading ? (
                <>
                  <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                  Uploading & Queueing...
                </>
              ) : (
                'Start Ingestion Pipeline'
              )}
            </button>
          </form>
        </div>
      )}

      {/* Documents Table */}
      <div className="glass-panel rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex justify-between items-center">
          <h3 className="font-semibold text-white text-base">Indexed Documents ({documents.length})</h3>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-400">Loading documents...</div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center text-slate-400">No documents uploaded yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900/60 text-slate-400 text-xs uppercase font-semibold">
                <tr>
                  <th className="p-4">Document</th>
                  <th className="p-4">Access Level</th>
                  <th className="p-4">Ingestion Status</th>
                  <th className="p-4">Chunks</th>
                  <th className="p-4">Uploaded Date</th>
                  {canUpload && <th className="p-4 text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-800/30 transition-all">
                    <td className="p-4 flex items-center gap-3">
                      {getFileIcon(doc.file_type)}
                      <div>
                        <p className="font-medium text-white">{doc.title}</p>
                        <p className="text-xs text-slate-400">{doc.filename} • {(doc.file_size / 1024).toFixed(1)} KB</p>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="inline-flex items-center gap-1.5 text-xs text-slate-300">
                        {doc.access_level === 'PUBLIC' ? (
                          <><Globe className="w-3.5 h-3.5 text-emerald-400" /> Public</>
                        ) : doc.access_level === 'MANAGERS_ONLY' ? (
                          <><Shield className="w-3.5 h-3.5 text-purple-400" /> Managers Only</>
                        ) : (
                          <><Lock className="w-3.5 h-3.5 text-red-400" /> Admin Only</>
                        )}
                      </span>
                    </td>
                    <td className="p-4">{getStatusBadge(doc.status)}</td>
                    <td className="p-4 font-mono text-xs text-indigo-300">{doc.chunk_count} vectors</td>
                    <td className="p-4 text-xs text-slate-400">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    {canUpload && (
                      <td className="p-4 text-right space-x-2">
                        <button
                          onClick={async () => {
                            setSelectedDocForPerms(doc);
                            setPermAccessLevel(doc.access_level);
                            // Fetch existing permissions
                            const res = await fetchWithAuth(`/documents/${doc.id}/permissions`);
                            if (res.ok) {
                              const data = await res.json();
                              setPermRoles(data.permissions.map((p: any) => p.granted_role).filter(Boolean));
                              setPermUserIds(data.permissions.map((p: any) => p.granted_user_id).filter(Boolean));
                            } else {
                              setPermRoles([]);
                              setPermUserIds([]);
                            }
                            setShowPermModal(true);
                          }}
                          className="p-2 rounded-lg text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10 transition-all inline-flex items-center gap-1 text-xs font-medium"
                          title="Manage Document Permissions"
                        >
                          <Shield className="w-4 h-4" /> Permissions
                        </button>
                        <button
                          onClick={() => deleteMutation.mutate(doc.id)}
                          className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all inline-block"
                          title="Delete Document"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Permissions Modal */}
      {showPermModal && selectedDocForPerms && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel max-w-lg w-full rounded-2xl p-6 border border-slate-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-white text-base flex items-center gap-2">
                <Shield className="w-5 h-5 text-indigo-400" /> Manage Document Access Permissions
              </h3>
              <button onClick={() => setShowPermModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            
            <p className="text-xs text-slate-400 mb-4">
              Document: <span className="text-white font-medium">{selectedDocForPerms.title}</span> ({selectedDocForPerms.filename})
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1.5">
                  Access Level Tier
                </label>
                <select
                  value={permAccessLevel}
                  onChange={(e: any) => setPermAccessLevel(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl glass-input text-sm bg-slate-900"
                >
                  <option value="PUBLIC">Public (All Organization Employees)</option>
                  <option value="MANAGERS_ONLY">Managers & Admins Only</option>
                  <option value="ADMIN_ONLY">Admin Restricted Only</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1.5">
                  Explicit Role Access Grants
                </label>
                <div className="flex gap-4">
                  {['EMPLOYEE', 'MANAGER', 'ADMIN'].map((r) => (
                    <label key={r} className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={permRoles.includes(r as any)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setPermRoles([...permRoles, r as any]);
                          } else {
                            setPermRoles(permRoles.filter((item) => item !== r));
                          }
                        }}
                        className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500"
                      />
                      {r}
                    </label>
                  ))}
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800 flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowPermModal(false)}
                  className="flex-1 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    const res = await fetchWithAuth(`/documents/${selectedDocForPerms.id}/permissions`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        access_level: permAccessLevel,
                        granted_roles: permRoles,
                        granted_user_ids: permUserIds,
                      }),
                    });
                    if (res.ok) {
                      queryClient.invalidateQueries({ queryKey: ['documents'] });
                      setShowPermModal(false);
                    }
                  }}
                  className="flex-1 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium"
                >
                  Save Access Controls
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

