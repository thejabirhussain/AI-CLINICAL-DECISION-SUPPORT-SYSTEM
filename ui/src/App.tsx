import React, { useState, useRef, useEffect } from 'react';
import {
  Send, User, Bot, FileText, Upload, X, ShieldAlert,
  Activity, Database, AlertCircle, FileImage, Stethoscope,
  Paperclip
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Types
interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: Date;
}

interface Source {
  title: string;
  url: string;
  section?: string;
  snippet?: string;
  score?: number;
}

interface UploadedFile {
  name: string;
  type: string;
  size: number;
}

function App() {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "Hello. I am your Clinical Decision Support Assistant. I can analyze patient data against medical guidelines. Please upload a patient report or ask a clinical question.",
      timestamp: new Date()
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [patientContext, setPatientContext] = useState<string>("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const formData = new FormData();
      formData.append('file', file);

      // Optimistic UI
      const newFile = { name: file.name, type: file.type, size: file.size };
      setFiles(prev => [...prev, newFile]);

      // System message
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Processing file: **${file.name}**...`,
        timestamp: new Date()
      }]);

      try {
        const res = await fetch('http://localhost:8000/patient/upload', {
          method: 'POST',
          body: formData,
        });

        if (!res.ok) throw new Error("Upload failed");

        const data = await res.json();
        setPatientContext(prev => prev + "\n" + data.extracted_text);

        setMessages(prev => {
          const newMsgs = [...prev];
          newMsgs[newMsgs.length - 1].content = `✅ File **${file.name}** successfully processed and added to clinical context.`;
          return newMsgs;
        });

      } catch (err) {
        setMessages(prev => {
          const newMsgs = [...prev];
          newMsgs[newMsgs.length - 1].content = `❌ Error processing file: ${file.name}`;
          return newMsgs;
        });
        setFiles(prev => prev.filter(f => f.name !== file.name)); // Revert
      }
    }
  };

  const handleSend = async () => {
    if (!query.trim()) return;

    const userMsg: Message = { role: 'user', content: query, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setQuery('');
    setIsLoading(true);

    try {
      // Use map to create a clean history array
      const history = messages.map(m => ({ role: m.role, content: m.content }));

      const res = await fetch('http://localhost:8000/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userMsg.content,
          history: history,
          context: patientContext,
          json: true
        }),
      });

      const data = await res.json();

      const aiContent = data.answer_text || data.answer || "No response generated.";
      const sources = data.sources || [];

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: aiContent,
        sources: sources,
        timestamp: new Date()
      }]);

    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Detailed clinical analysis unavailable at this moment. Please check system connection.",
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans text-slate-900 overflow-hidden">

      {/* Sidebar */}
      <div className={`${isSidebarOpen ? 'w-80' : 'w-0'} bg-white border-r border-slate-200 transition-all duration-300 flex flex-col`}>
        <div className="p-6 border-b border-slate-100 flex items-center gap-3">
          <div className="bg-sky-100 p-2 rounded-lg">
            <Stethoscope className="w-6 h-6 text-sky-600" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-slate-800">AI-CDSS</h1>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              <span className="text-xs text-slate-500 font-medium">System Online</span>
            </div>
          </div>
        </div>

        <div className="p-6 flex-1 overflow-y-auto">
          <div className="mb-8">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Patient Data</h2>

            <label className="file-drop-zone block group relative">
              <input type="file" className="hidden" onChange={handleFileUpload} accept=".pdf,image/*" />
              <div className="flex flex-col items-center gap-2">
                <div className="p-3 bg-sky-50 rounded-full group-hover:bg-sky-100 transition-colors">
                  <Upload className="w-5 h-5 text-sky-600" />
                </div>
                <div className="text-sm font-medium text-slate-600">Upload Report</div>
                <div className="text-xs text-slate-400">PDF, JPG, PNG</div>
              </div>
            </label>
          </div>

          {files.length > 0 && (
            <div>
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Active Files</h2>
              <div className="space-y-2">
                {files.map((file, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-100 shadow-sm">
                    {file.type.includes('image') ? (
                      <FileImage className="w-8 h-8 text-purple-500" />
                    ) : (
                      <FileText className="w-8 h-8 text-red-500" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate text-slate-700">{file.name}</div>
                      <div className="text-xs text-slate-400">{(file.size / 1024).toFixed(1)} KB</div>
                    </div>
                    <button className="text-slate-400 hover:text-red-500 transition-colors">
                      <X className="w-4 h-4" onClick={() => setFiles(prev => prev.filter(f => f.name !== file.name))} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-3 p-2 rounded hover:bg-white transition-colors cursor-pointer">
            <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 font-bold text-xs">
              JD
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium">Dr. Smith</div>
              <div className="text-xs text-slate-500">Cardiology</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative w-full">
        {/* Header */}
        <header className="h-16 bg-white/80 backdrop-blur-md border-b border-slate-200 flex items-center justify-between px-6 sticky top-0 z-10 w-full">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 hover:bg-slate-100 rounded-lg text-slate-500"
            >
              <Database className="w-5 h-5" />
            </button>
            <h2 className="font-semibold text-slate-700">Clinical Consultation</h2>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-yellow-50 text-yellow-700 border border-yellow-200 rounded-full text-xs font-medium">
            <AlertCircle className="w-3 h-3" />
            <span>Research Preview Mode - Verify all outputs</span>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth bg-slate-50 w-full">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start max-w-4xl'}`}>

              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-sky-600 flex items-center justify-center text-white flex-shrink-0 mt-1 shadow-sm">
                  <Bot className="w-5 h-5" />
                </div>
              )}

              <div className={`flex flex-col gap-2 ${msg.role === 'user' ? 'max-w-[85%]' : 'max-w-[85%]'}`}>
                <div
                  className={`p-5 rounded-2xl shadow-sm leading-relaxed text-[15px] ${msg.role === 'user'
                    ? 'bg-white text-slate-800 border-t border-l border-slate-100 rounded-tr-sm'
                    : 'bg-white text-slate-800 border border-slate-100 rounded-tl-sm'
                    }`}
                >
                  <div className="prose prose-sm max-w-none prose-p:my-2 prose-ul:my-2 prose-li:my-0.5 prose-strong:text-slate-900 prose-headings:text-slate-800 prose-headings:font-bold prose-headings:mt-4 prose-a:text-sky-600">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </div>

                {msg.sources && msg.sources.length > 0 && (
                  <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-sm animate-fade-in">
                    <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      <Activity className="w-3 h-3 text-sky-500" />
                      Clinical Evidence
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {msg.sources.map((src, i) => (
                        <a
                          key={i}
                          href={src.url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex flex-col p-2.5 rounded border border-slate-100 bg-slate-50/50 hover:bg-sky-50 hover:border-sky-100 transition-all group no-underline"
                        >
                          <div className="text-xs font-medium text-sky-700 truncate group-hover:text-sky-800">
                            {src.title || "Medical Document"}
                          </div>
                          <div className="text-[10px] text-slate-400 mt-0.5 flex justify-between">
                            <span>{src.section || "General"}</span>
                            {src.score && <span>{(src.score * 100).toFixed(0)}% Match</span>}
                          </div>
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white flex-shrink-0 mt-1 shadow-md">
                  <User className="w-5 h-5" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-4 max-w-3xl animate-pulse">
              <div className="w-8 h-8 rounded-full bg-sky-600 flex items-center justify-center text-white flex-shrink-0">
                <Bot className="w-5 h-5" />
              </div>
              <div className="space-y-2 w-full">
                <div className="h-4 bg-slate-200 rounded w-1/4"></div>
                <div className="h-10 bg-slate-200 rounded w-3/4"></div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Footer / Input */}
        <div className="p-4 bg-white border-t border-slate-200 w-full">
          <div className="max-w-4xl mx-auto w-full">
            <div className="relative flex items-center shadow-lg rounded-2xl bg-white border border-slate-200 focus-within:border-sky-400 focus-within:ring-4 focus-within:ring-sky-50 transition-all">
              <button className="p-3 text-slate-400 hover:text-slate-600 transition-colors ml-1" onClick={() => document.querySelector<HTMLInputElement>('input[type=file]')?.click()}>
                <Paperclip className="w-5 h-5" />
              </button>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a clinical question or describe a case..."
                className="w-full py-4 px-2 max-h-32 bg-transparent border-none focus:ring-0 resize-none text-slate-700 placeholder:text-slate-400 font-medium"
                rows={1}
                style={{ minHeight: '56px' }}
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !query.trim()}
                className="p-2 mr-2 bg-sky-600 hover:bg-sky-700 text-white rounded-xl shadow-md disabled:opacity-50 disabled:shadow-none transition-all duration-300"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
            <div className="flex items-center justify-center gap-2 mt-3 text-[10px] text-slate-400">
              <ShieldAlert className="w-3 h-3" />
              <p>AI can make mistakes. Verify important clinical findings. Not a substitute for professional judgment.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
