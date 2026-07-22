'use client';

import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter, useParams } from 'next/navigation';
import Markdown from 'markdown-to-jsx';
import { 
  Send, 
  Plus, 
  MessageSquare, 
  Sparkles, 
  FileText, 
  ChevronRight, 
  Bot, 
  User, 
  ExternalLink,
  BookOpen,
  Info,
  ThumbsUp,
  ThumbsDown
} from 'lucide-react';

import { fetchWithAuth, API_BASE_URL } from '@/lib/api';


interface Citation {
  document_id: string;
  filename: string;
  title: string;
  page_number?: number;
  snippet: string;
}

interface Message {
  id?: string;
  sender: 'USER' | 'ASSISTANT';
  content: string;
  citations?: Citation[];
}

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
}

export default function ChatPage() {
  const router = useRouter();
  const params = useParams();
  const queryClient = useQueryClient();
  const sessionId = params?.sessionId as string;

  const [activeSessionId, setActiveSessionId] = useState<string | null>(sessionId || null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [feedbackMap, setFeedbackMap] = useState<Record<string, 'THUMBS_UP' | 'THUMBS_DOWN'>>({});

  const chatBottomRef = useRef<HTMLDivElement>(null);

  const handleFeedback = async (messageId: string, rating: 'THUMBS_UP' | 'THUMBS_DOWN') => {
    if (!messageId) return;
    setFeedbackMap((prev) => ({ ...prev, [messageId]: rating }));
    try {
      await fetchWithAuth(`/chat/messages/${messageId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating }),
      });
    } catch (e) {
      // Ignore error
    }
  };


  // Fetch Chat Sessions
  const { data: sessions = [] } = useQuery<ChatSession[]>({
    queryKey: ['chatSessions'],
    queryFn: async () => {
      const res = await fetchWithAuth('/chat/sessions');
      if (!res.ok) return [];
      return res.json();
    },
  });

  // Fetch Messages for Active Session
  useEffect(() => {
    if (activeSessionId) {
      async function loadMessages() {
        const res = await fetchWithAuth(`/chat/sessions/${activeSessionId}/messages`);
        if (res.ok) {
          const data = await res.json();
          setMessages(data);
        }
      }
      loadMessages();
    } else {
      setMessages([]);
    }
  }, [activeSessionId]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Create New Session
  const createSessionMutation = useMutation({
    mutationFn: async (title?: string) => {
      const res = await fetchWithAuth('/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title || 'New Chat' }),
      });
      if (!res.ok) throw new Error('Failed to create session');
      return res.json();
    },
    onSuccess: (newSession) => {
      queryClient.invalidateQueries({ queryKey: ['chatSessions'] });
      setActiveSessionId(newSession.id);
    },
  });

  // Handle Send Query with Streaming
  const handleSend = async (queryText?: string) => {
    const query = queryText || inputQuery;
    if (!query.trim() || isStreaming) return;

    let targetSessionId = activeSessionId;

    // Create session if none exists
    if (!targetSessionId) {
      try {
        const newSession = await createSessionMutation.mutateAsync(query.slice(0, 30));
        targetSessionId = newSession.id;
        setActiveSessionId(targetSessionId);
      } catch (err) {
        return;
      }
    }

    setInputQuery('');
    const userMsg: Message = { sender: 'USER', content: query };
    setMessages((prev) => [...prev, userMsg]);

    // Initial placeholder Assistant Message for Streaming
    const assistantMsgPlaceholder: Message = { sender: 'ASSISTANT', content: '', citations: [] };
    setMessages((prev) => [...prev, assistantMsgPlaceholder]);

    setIsStreaming(true);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/chat/query/stream`, {

        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: targetSessionId,
          query: query,
        }),
      });

      if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After') || '60';
        let detailMsg = `You've hit the rate limit, try again in ${retryAfter} seconds.`;
        try {
          const errData = await response.json();
          if (errData.detail) detailMsg = errData.detail;
        } catch (e) {}

        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            sender: 'ASSISTANT',
            content: `⚠️ **Rate Limit Exceeded**: ${detailMsg}`,
          };
          return updated;
        });
        setIsStreaming(false);
        return;
      }

      if (!response.body) throw new Error('No response body');


      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedText = '';
      let extractedCitations: Citation[] = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {

            try {
              const jsonStr = line.replace('data: ', '').trim();
              if (!jsonStr) continue;
              const parsed = JSON.parse(jsonStr);

              if (parsed.type === 'content') {
                accumulatedText += parsed.text;
                setMessages((prev) => {
                  const updated = [...prev];
                  updated[updated.length - 1] = {
                    sender: 'ASSISTANT',
                    content: accumulatedText,
                    citations: extractedCitations,
                  };
                  return updated;
                });
              } else if (parsed.type === 'citations') {
                extractedCitations = parsed.citations || [];
                setMessages((prev) => {
                  const updated = [...prev];
                  updated[updated.length - 1] = {
                    sender: 'ASSISTANT',
                    content: accumulatedText,
                    citations: extractedCitations,
                  };
                  return updated;
                });
              }
            } catch (e) {
              // Ignore line parse errors
            }
          }
        }
      }
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          sender: 'ASSISTANT',
          content: 'An error occurred while generating the answer. Please check your query or document indexing.',
        };
        return updated;
      });
    } finally {
      setIsStreaming(false);
      queryClient.invalidateQueries({ queryKey: ['chatSessions'] });
    }
  };

  const samplePrompts = [
    'What is our remote work and annual leave policy?',
    'Summarize the core security guidelines for employee devices.',
    'List the key deliverables in our latest engineering report.',
  ];

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Session History Sub-Sidebar */}
      <div className="w-64 border-r border-slate-800 bg-slate-900/40 p-4 flex flex-col justify-between hidden md:flex">
        <div>
          <button
            onClick={() => {
              setActiveSessionId(null);
              setMessages([]);
            }}
            className="w-full py-2.5 px-4 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 font-medium text-sm flex items-center justify-center gap-2 transition-all mb-4"
          >
            <Plus className="w-4 h-4" /> New Chat
          </button>

          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 px-2">Chat History</p>
          <div className="space-y-1 overflow-y-auto max-h-[70vh]">
            {sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => setActiveSessionId(s.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium truncate flex items-center gap-2 transition-all ${
                  activeSessionId === s.id
                    ? 'bg-slate-800 text-white border border-slate-700'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/40'
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                <span className="truncate">{s.title}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col justify-between bg-[#080d1a] relative">
        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-4xl mx-auto w-full">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center py-20">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center shadow-xl shadow-indigo-500/25 mb-4">
                <Sparkles className="w-7 h-7 text-white" />
              </div>
              <h2 className="text-xl font-bold text-white mb-2">How can I assist your document research today?</h2>
              <p className="text-slate-400 text-sm max-w-md mb-8">
                Ask questions about your uploaded company policies, contracts, and technical documents. Answers are strictly grounded in source files with page citations.
              </p>

              <div className="w-full max-w-lg space-y-2">
                {samplePrompts.map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(prompt)}
                    className="w-full p-3 rounded-xl glass-panel glass-panel-hover text-left text-xs text-slate-300 flex items-center justify-between group transition-all"
                  >
                    <span>&quot;{prompt}&quot;</span>

                    <ChevronRight className="w-4 h-4 text-indigo-400 group-hover:translate-x-1 transition-transform" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, index) => (
              <div
                key={index}
                className={`flex gap-4 ${msg.sender === 'USER' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.sender === 'ASSISTANT' && (
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center shadow-md shadow-indigo-500/20 shrink-0">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}

                <div className={`max-w-2xl rounded-2xl p-4 ${
                  msg.sender === 'USER'
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20 rounded-tr-none'
                    : 'glass-panel text-slate-200 rounded-tl-none border border-slate-800'
                }`}>
                  <div className={`prose prose-invert text-sm leading-relaxed ${isStreaming && index === messages.length - 1 ? 'streaming-cursor' : ''}`}>
                    <Markdown>{msg.content}</Markdown>
                  </div>

                  {/* Source Citations Section */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-800/80">
                      <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                        <BookOpen className="w-3 h-3 text-indigo-400" /> Source Citations ({msg.citations.length})
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {msg.citations.map((cit, idx) => (
                          <button
                            key={idx}
                            onClick={() => setSelectedCitation(cit)}
                            className="px-2.5 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 text-indigo-300 text-xs flex items-center gap-1.5 transition-all"
                          >
                            <FileText className="w-3 h-3" />
                            <span>{cit.filename} (p. {cit.page_number || 1})</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Feedback Voting Buttons */}
                  {msg.sender === 'ASSISTANT' && msg.id && (
                    <div className="mt-3 pt-2 border-t border-slate-800/40 flex items-center gap-2">
                      <button
                        onClick={() => handleFeedback(msg.id!, 'THUMBS_UP')}
                        className={`p-1.5 rounded-lg border text-xs flex items-center gap-1 transition-all ${
                          feedbackMap[msg.id!] === 'THUMBS_UP'
                            ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                            : 'text-slate-400 hover:text-white border-slate-800 hover:bg-slate-800/40'
                        }`}
                        title="Good Answer"
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleFeedback(msg.id!, 'THUMBS_DOWN')}
                        className={`p-1.5 rounded-lg border text-xs flex items-center gap-1 transition-all ${
                          feedbackMap[msg.id!] === 'THUMBS_DOWN'
                            ? 'bg-red-500/20 text-red-400 border-red-500/40'
                            : 'text-slate-400 hover:text-white border-slate-800 hover:bg-slate-800/40'
                        }`}
                        title="Poor Answer / Bad Retrieval"
                      >
                        <ThumbsDown className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>


                {msg.sender === 'USER' && (
                  <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                    <User className="w-4 h-4 text-slate-300" />
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={chatBottomRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-slate-800/80 bg-[#0c1324]/90 backdrop-blur-xl">
          <div className="max-w-4xl mx-auto relative flex items-center">
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask a question about your uploaded documents..."
              className="w-full pl-4 pr-12 py-3.5 rounded-xl glass-input text-sm focus:ring-2 focus:ring-indigo-500"
            />
            <button
              onClick={() => handleSend()}
              disabled={!inputQuery.trim() || isStreaming}
              className="absolute right-2 p-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-40 transition-all shadow-md shadow-indigo-500/20"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Citation Preview Modal */}
      {selectedCitation && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel max-w-lg w-full rounded-2xl p-6 relative border border-slate-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-white text-base flex items-center gap-2">
                <FileText className="w-5 h-5 text-indigo-400" /> {selectedCitation.filename}
              </h3>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>
            <div className="space-y-2 text-xs text-slate-300 mb-4">
              <p><span className="text-slate-400">Document Title:</span> {selectedCitation.title}</p>
              <p><span className="text-slate-400">Page Number:</span> {selectedCitation.page_number || 1}</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300 font-mono leading-relaxed">
              &quot;{selectedCitation.snippet}&quot;
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
