import React, { useState, useRef, useEffect } from 'react';
import {
  Upload, X, ShieldAlert,
  Database, AlertCircle, FileImage, Stethoscope,
  Paperclip, Brain, CheckCircle2,
  ChevronRight, Loader2, ArrowRight, FileText, Check, Circle
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

type ReasoningStep = 'idle' | 'context' | 'analyzing' | 'retrieving' | 'generating';

function App() {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "Hello. I am your Clinical Decision Support Assistant. I can analyze patient data against medical guidelines. Please upload a patient report or ask a clinical question.",
      timestamp: new Date()
    }
  ]);
  const [reasoningStep, setReasoningStep] = useState<ReasoningStep>('idle');
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [patientContext, setPatientContext] = useState<string>("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, reasoningStep]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const formData = new FormData();
      formData.append('file', file);

      const newFile = { name: file.name, type: file.type, size: file.size };
      setFiles(prev => [...prev, newFile]);

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `**System:** Processing file: _${file.name}_...`,
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
        setFiles(prev => prev.filter(f => f.name !== file.name));
      }
    }
  };

  const handleSend = async () => {
    if (!query.trim()) return;

    const userMsg: Message = { role: 'user', content: query, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setQuery('');

    // Start Reasoning Chain
    setReasoningStep('context');

    try {
      await new Promise(r => setTimeout(r, 800));
      setReasoningStep('analyzing');

      await new Promise(r => setTimeout(r, 1200));
      setReasoningStep('retrieving');

      const history = messages.map(m => ({ role: m.role, content: m.content }));

      const resPromise = fetch('http://localhost:8000/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userMsg.content,
          history: history,
          context: patientContext,
          json: true
        }),
      });

      await new Promise(r => setTimeout(r, 1500));
      setReasoningStep('generating');

      const res = await resPromise;
      const data = await res.json();

      const aiContent = data.answer_text || data.answer || "No response generated.";
      const sources = data.sources || [];

      setReasoningStep('idle');

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: aiContent,
        sources: sources,
        timestamp: new Date()
      }]);

    } catch (error) {
      setReasoningStep('idle');
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Detailed clinical analysis unavailable at this moment. Please check system connection.",
        timestamp: new Date()
      }]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderReasoningSteps = () => {
    if (reasoningStep === 'idle') return null;

    const steps = [
      { id: 'context', label: 'Processing context' },
      { id: 'analyzing', label: 'Analyzing clinical query' },
      { id: 'retrieving', label: 'Retrieving medical evidence' },
      { id: 'generating', label: 'Generating response' },
    ];

    const currentStepIndex = steps.findIndex(s => s.id === reasoningStep);

    return (
      <div className="flex flex-col gap-3 py-4 pl-4 animate-in fade-in duration-500">
        {steps.map((step, idx) => {
          let status: 'completed' | 'active' | 'pending' = 'pending';
          if (idx < currentStepIndex) status = 'completed';
          if (idx === currentStepIndex) status = 'active';

          return (
            <div key={step.id} className="flex items-center gap-3 relative">
              {/* Connecting Line */}
              {idx < steps.length - 1 && (
                <div className="absolute left-[9px] top-6 w-px h-full bg-slate-200" />
              )}

              <div className={`
                    w-5 h-5 rounded-full flex items-center justify-center z-10 bg-[#F8FAFC]
                    ${status === 'completed' ? 'text-slate-900' : ''}
                    ${status === 'active' ? 'text-slate-600' : ''}
                    ${status === 'pending' ? 'text-slate-300' : ''}
                `}>
                {status === 'completed' && <CheckCircle2 className="w-4 h-4 fill-slate-800 text-white" />}
                {status === 'active' && <Loader2 className="w-4 h-4 animate-spin text-slate-600" />}
                {status === 'pending' && <div className="w-2 h-2 rounded-full border border-slate-300 bg-white" />}
              </div>

              <span className={`text-sm ${status === 'active' || status === 'completed' ? 'text-slate-700 font-medium' : 'text-slate-400'}`}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="flex h-screen bg-[#F8FAFC] font-sans text-slate-900 overflow-hidden">

      {/* Sidebar */}
      <div className={`
          ${isSidebarOpen ? 'w-72 border-r' : 'w-0 border-none'} 
          bg-white border-slate-200/80 transition-all duration-300 flex flex-col z-20 
          shadow-[4px_0_24px_-12px_rgba(0,0,0,0.05)] overflow-hidden shrink-0
      `}>
        <div className="w-72 flex flex-col h-full"> {/* Fixed width container to prevent layout shifts */}
          <div className="p-5 border-b border-slate-100 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3">
              <div className="bg-slate-900 p-2 rounded-lg">
                <Stethoscope className="w-4 h-4 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-base text-slate-900 tracking-tight leading-none">AI CDSS</h1>
                <span className="text-[9px] uppercase tracking-widest text-slate-400 font-semibold">Decisions</span>
              </div>
            </div>
          </div>

          <div className="p-5 flex-1 overflow-y-auto custom-scrollbar">
            <div className="mb-6">
              <h2 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 pl-1">
                Patient Data
              </h2>

              <label className="group relative cursor-pointer block">
                <input type="file" className="hidden" onChange={handleFileUpload} accept=".pdf,image/*" />
                <div className="flex flex-col items-center gap-2 p-6 border border-dashed border-slate-300 rounded-xl hover:border-slate-800 transition-all duration-300 bg-slate-50/50">
                  <div className="p-2.5 bg-white rounded-lg shadow-sm border border-slate-100 group-hover:scale-110 transition-transform duration-300">
                    <Upload className="w-4 h-4 text-slate-600" />
                  </div>
                  <div className="text-center">
                    <p className="text-xs font-semibold text-slate-700">Upload Report</p>
                    <p className="text-[9px] text-slate-400 mt-0.5">PDF, JPG, PNG</p>
                  </div>
                </div>
              </label>
            </div>

            {files.length > 0 && (
              <div className="animate-in slide-in-from-left-2 duration-500 space-y-2">
                <h2 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest pl-1">Active Context</h2>
                <div className="space-y-2">
                  {files.map((file, idx) => (
                    <div key={idx} className="flex items-center gap-2.5 p-2.5 bg-white rounded-lg border border-slate-200 shadow-sm transition-all group relative overflow-hidden">
                      {file.type.includes('image') ? (
                        <FileImage className="w-4 h-4 text-slate-400" />
                      ) : (
                        <FileText className="w-4 h-4 text-slate-400" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium truncate text-slate-700">{file.name}</div>
                        <div className="text-[9px] text-slate-400">{(file.size / 1024).toFixed(1)} KB</div>
                      </div>
                      <button className="text-slate-300 hover:text-rose-500 transition-colors">
                        <X className="w-3.5 h-3.5" onClick={() => setFiles(prev => prev.filter(f => f.name !== file.name))} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="p-4 border-t border-slate-100 bg-slate-50/50 shrink-0">
            <div className="flex items-center gap-3 p-2.5 rounded-xl bg-white border border-slate-200 shadow-sm">
              <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center text-slate-600 font-bold text-xs">
                JD
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-bold text-slate-900">Jabir Hussain</div>
                <div className="text-[10px] text-slate-500">AI CDSS</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative w-full h-screen bg-[#F8FAFC]">
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-6 w-full z-10 bg-[#F8FAFC]/90 backdrop-blur-sm sticky top-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 hover:bg-slate-200/50 rounded-lg text-slate-500 transition-colors"
            >
              <Database className="w-4 h-4 transform rotate-90" />
            </button>
            <div className="h-4 w-px bg-slate-300/50 mx-1"></div>
            <div>
              <h2 className="font-semibold text-sm text-slate-800 tracking-tight">New Session</h2>
            </div>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-50 text-amber-700 border border-amber-200/50 rounded-full text-[10px] font-bold shadow-sm">
            <AlertCircle className="w-3 h-3" />
            <span>RESEARCH PREVIEW</span>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 md:px-5 py-6 space-y-6 scroll-smooth w-full max-w-5xl mx-auto">
          {messages.map((msg, idx) => (
            <div key={idx} className={`group flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} animate-in fade-in slide-in-from-bottom-2 duration-500`}>

              <div className={`
                max-w-[85%] md:max-w-2xl rounded-2xl px-4 py-3 shadow-sm relative text-[15px] leading-relaxed
                ${msg.role === 'user'
                  ? 'bg-[#3B82F6] text-white rounded-tr-sm shadow-blue-100' // Changed to a nice medical blue
                  : 'bg-white text-slate-800 rounded-tl-sm border border-slate-200/60 shadow-slate-100'
                }
              `}>
                <div className={`prose prose-sm max-w-none ${msg.role === 'user' ? 'prose-invert' : ''} prose-p:my-1 prose-headings:font-bold prose-a:underline prose-a:underline-offset-2`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                </div>
              </div>

              {/* Source/Metadata Display */}
              {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 ml-1 max-w-2xl w-full">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Evidence Sources</span>
                    <div className="h-px bg-slate-200 flex-1"></div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {msg.sources.map((src, i) => (
                      <a
                        key={i}
                        href={src.url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-2 pl-2.5 pr-2 py-1.5 bg-white border border-slate-100 rounded-md hover:border-blue-300 hover:shadow-sm transition-all group/card no-underline max-w-[220px]"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="text-[11px] font-semibold text-slate-700 truncate group-hover/card:text-blue-600 transition-colors">
                            {src.title || "Medical Document"}
                          </div>
                          <div className="text-[9px] text-slate-400 truncate flex items-center gap-1">
                            {src.score && <span className="text-emerald-600 font-medium">{(src.score * 100).toFixed(0)}% Match</span>}
                            <span>•</span>
                            <span>{src.section || "Ref"}</span>
                          </div>
                        </div>
                        <ArrowRight className="w-3 h-3 text-slate-300 group-hover/card:text-blue-500 -ml-1" />
                      </a>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-1 px-1 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] font-medium text-slate-400">
                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          ))}

          {/* Reasoning Steps (Vertical List) */}
          {renderReasoningSteps()}

          <div ref={messagesEndRef} className="h-2" />
        </div>

        {/* Footer / Input */}
        <div className="p-4 w-full max-w-4xl mx-auto z-10 pb-6">
          <div className="relative shadow-[0_2px_12px_rgba(0,0,0,0.05)] rounded-[1.5rem] bg-white transition-all ring-1 ring-slate-200 hover:ring-slate-300 focus-within:ring-2 focus-within:ring-blue-100 p-1.5 flex items-end gap-2">
            <button
              className="p-3 text-slate-400 hover:text-blue-600 hover:bg-slate-50 rounded-full transition-colors"
              onClick={() => document.querySelector<HTMLInputElement>('input[type=file]')?.click()}
              title="Attach Context"
            >
              <Paperclip className="w-5 h-5" />
            </button>

            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a clinical question or detail a patient case..."
              className="w-full py-3.5 max-h-32 bg-transparent border-none focus:ring-0 resize-none text-slate-700 placeholder:text-slate-400 font-medium leading-relaxed text-[15px]"
              rows={1}
            />

            <button
              onClick={handleSend}
              disabled={reasoningStep !== 'idle' || !query.trim()}
              className="m-1 p-3 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white rounded-full shadow-md shadow-blue-100 disabled:opacity-50 disabled:shadow-none transition-all duration-300"
            >

              <ArrowRight className="w-5 h-5" />
            </button>
          </div>

          <div className="flex justify-center gap-6 mt-3">
            <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
              <ShieldAlert className="w-3 h-3 text-slate-300" />
              <span>HIPAA Compliant</span>
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
              <Brain className="w-3 h-3 text-slate-300" />
              <span>AI-Assisted</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
