import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FileText, FileUp, PanelRight } from 'lucide-react';
import { ApiError, askGeneral, askPatient, uploadPatientFile } from './api';
import { isAbnormal, type Encounter, type Message, type ReasoningStep } from './types';
import { loadEncounters, newEncounter, saveEncounters, titleFrom, uid } from './utils/encounters';
import { Sidebar } from './components/Sidebar';
import { Home } from './components/Home';
import { ChatColumn } from './components/ChatColumn';
import { DocumentPanel, PATIENT_TAB } from './components/DocumentPanel';
import type { ComposerHandle } from './components/Composer';

const isAnswer = (m: Message) => m.role === 'assistant' && !m.note && !m.error;
const wide = () => typeof window !== 'undefined' && window.innerWidth >= 1024;

export default function App() {
  const [encounters, setEncounters] = useState<Encounter[]>(() => {
    const saved = loadEncounters();
    return [newEncounter(), ...saved];
  });
  const [activeId, setActiveId] = useState(() => encounters[0].id);
  const [sidebarOpen, setSidebarOpen] = useState(wide);
  const [draft, setDraft] = useState('');
  const [step, setStep] = useState<ReasoningStep>('idle');
  const [uploading, setUploading] = useState(false);
  const [panelTab, setPanelTab] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(true);
  const composerRef = useRef<ComposerHandle>(null);
  const uploadInputRef = useRef<HTMLInputElement>(null);

  const active = encounters.find(e => e.id === activeId) ?? encounters[0];
  const answers = useMemo(() => active.messages.filter(isAnswer), [active.messages]);
  const busy = step !== 'idle';
  const hasConversation = active.messages.length > 0 || !!active.patient;

  useEffect(() => saveEncounters(encounters), [encounters]);

  // Keep the document panel pointed at something sensible for the current encounter.
  useEffect(() => {
    const valid =
      (panelTab === PATIENT_TAB && active.patient) || (panelTab && answers.some(a => a.id === panelTab));
    if (!valid) {
      const last = answers[answers.length - 1];
      setPanelTab(last ? last.id : active.patient ? PATIENT_TAB : null);
    }
  }, [active.id, active.patient, answers, panelTab]);

  const patch = useCallback((id: string, fn: (e: Encounter) => Encounter) => {
    setEncounters(list => list.map(e => (e.id === id ? { ...fn(e), updatedAt: Date.now() } : e)));
  }, []);

  const pushMessage = useCallback(
    (id: string, m: Message) => patch(id, e => ({ ...e, messages: [...e.messages, m] })),
    [patch],
  );

  const startNew = () => {
    if (busy) return;
    const fresh = newEncounter();
    // Drop other untouched blank encounters so "New" doesn't pile them up.
    setEncounters(list => [fresh, ...list.filter(e => e.messages.length > 0 || e.patient)]);
    setActiveId(fresh.id);
    setDraft('');
    setPanelTab(null);
    setTimeout(() => composerRef.current?.focus(), 30);
  };

  const selectEncounter = (id: string) => {
    if (busy) return;
    setActiveId(id);
    setPanelTab(null);
    setPanelOpen(wide());
    if (!wide()) setSidebarOpen(false);
  };

  const deleteEncounter = (id: string) => {
    if (busy) return;
    if (id === activeId) {
      const fresh = newEncounter();
      setEncounters(list => [fresh, ...list.filter(e => e.id !== id)]);
      setActiveId(fresh.id);
      setPanelTab(null);
    } else {
      setEncounters(list => list.filter(e => e.id !== id));
    }
  };

  const upload = async (file: File) => {
    const encId = active.id;
    setUploading(true);
    try {
      const res = await uploadPatientFile(file);
      const flagged = res.structured_data.labs?.filter(isAbnormal).length ?? 0;
      patch(encId, e => ({
        ...e,
        title: e.messages.some(m => m.role === 'user') ? e.title : `Patient · ${res.filename || file.name}`,
        patient: {
          sessionId: res.session_id,
          filename: res.filename || file.name,
          fileType: file.type,
          size: file.size,
          data: res.structured_data,
          uploadedAt: Date.now(),
        },
      }));
      pushMessage(encId, {
        id: uid(),
        role: 'assistant',
        note: true,
        content: `${file.name} added to clinical context${flagged ? ` — ${flagged} flagged lab${flagged > 1 ? 's' : ''}` : ''}. Ask anything about this patient.`,
        createdAt: Date.now(),
      });
      setPanelTab(PATIENT_TAB);
      setPanelOpen(true);
    } catch (err) {
      pushMessage(encId, {
        id: uid(),
        role: 'assistant',
        error: true,
        content: `Couldn't process ${file.name}: ${err instanceof Error ? err.message : 'unknown error'}`,
        createdAt: Date.now(),
      });
    } finally {
      setUploading(false);
    }
  };

  const send = async (text?: string) => {
    const query = (text ?? draft).trim();
    if (!query || busy) return;
    const enc = active;
    const encId = enc.id;
    const patient = enc.patient;

    const userMsg: Message = { id: uid(), role: 'user', content: query, createdAt: Date.now() };
    patch(encId, e => ({
      ...e,
      title: e.messages.some(m => m.role === 'user') ? e.title : titleFrom(query),
      messages: [...e.messages, userMsg],
    }));
    setDraft('');

    // Visual reasoning trace (the backend isn't streaming, so steps advance on a timer and wait at "generating").
    const order: ReasoningStep[] = patient
      ? ['context', 'analyzing', 'retrieving', 'generating']
      : ['analyzing', 'retrieving', 'generating'];
    setStep(order[0]);
    const timers = order.slice(1).map((s, i) => setTimeout(() => setStep(s), 900 * (i + 1) + i * 400));

    try {
      const res = patient
        ? await askPatient(query, patient.sessionId)
        : await askGeneral(
            query,
            enc.messages
              .filter(m => !m.note && !m.error)
              .map(m => ({ role: m.role, content: m.content })),
          );
      const answer: Message = {
        id: uid(),
        role: 'assistant',
        content: res.answer,
        sources: res.sources,
        confidence: res.confidence,
        followUps: res.followUps,
        patientScoped: !!patient,
        createdAt: Date.now(),
      };
      pushMessage(encId, answer);
      setPanelTab(answer.id);
      setPanelOpen(true);
    } catch (err) {
      const expired = err instanceof ApiError && err.status === 404 && patient;
      pushMessage(encId, {
        id: uid(),
        role: 'assistant',
        error: true,
        content: expired
          ? 'The patient session has expired (the API was restarted). Please upload the report again.'
          : err instanceof Error
            ? err.message
            : 'Clinical analysis is unavailable right now.',
        createdAt: Date.now(),
      });
      if (expired) patch(encId, e => ({ ...e, patient: undefined }));
    } finally {
      timers.forEach(clearTimeout);
      setStep('idle');
    }
  };

  const useTemplate = (text: string) => {
    setDraft(text);
    setTimeout(() => composerRef.current?.focus(), 0);
  };

  const questionFor = (answerId: string) => {
    const i = active.messages.findIndex(m => m.id === answerId);
    for (let j = i - 1; j >= 0; j--) if (active.messages[j].role === 'user') return active.messages[j].content;
    return undefined;
  };

  const showPanel = panelOpen && hasConversation && (answers.length > 0 || !!active.patient) && panelTab !== null;

  return (
    <div className="flex h-full overflow-hidden bg-shell">
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen(o => !o)}
        encounters={encounters}
        activeId={active.id}
        onSelect={selectEncounter}
        onNew={startNew}
        onDelete={deleteEncounter}
        onUpload={upload}
        uploading={uploading}
        onClearPatient={() => patch(active.id, e => ({ ...e, patient: undefined }))}
        onOpenPatient={() => {
          setPanelTab(PATIENT_TAB);
          setPanelOpen(true);
        }}
      />

      <main className="min-w-0 flex-1 py-2 pr-2">
        <div className="relative flex h-full flex-col overflow-hidden rounded-xl border border-line bg-[#fafafa]">
          {/* Top bar */}
          <header className="no-print flex h-12 shrink-0 items-center gap-2 px-3 sm:px-4">
            {hasConversation ? (
              <div className="flex min-w-0 items-center gap-2 text-[14px]">
                <span className="hidden italic text-ink-2 sm:inline">Encounter</span>
                <span className="hidden text-ink/30 sm:inline">/</span>
                <span className="truncate font-medium">{active.title}</span>
              </div>
            ) : (
              <div />
            )}

            {hasConversation && (
              <div className="ml-2 hidden shrink-0 items-center gap-2 md:flex">
                {active.patient ? (
                  <button
                    type="button"
                    onClick={() => {
                      setPanelTab(PATIENT_TAB);
                      setPanelOpen(true);
                    }}
                    className="inline-flex h-8 items-center gap-2 rounded-lg px-2 text-[14px] font-medium hover:bg-black/5"
                  >
                    <FileText className="h-4 w-4" strokeWidth={1.75} />
                    Patient
                  </button>
                ) : (
                  <span className="inline-flex h-8 items-center px-2 text-[14px] font-medium text-ink-2">General</span>
                )}
                <button
                  type="button"
                  onClick={() => uploadInputRef.current?.click()}
                  disabled={uploading}
                  className="inline-flex h-8 items-center gap-2 rounded-lg border border-line bg-white px-2.5 text-[14px] font-medium hover:bg-subtle disabled:opacity-60"
                >
                  <FileUp className="h-4 w-4" strokeWidth={1.75} />
                  {uploading ? 'Reading…' : active.patient ? 'Replace Report' : 'Add Patient Report'}
                </button>
                <input
                  ref={uploadInputRef}
                  type="file"
                  accept=".pdf,image/*"
                  className="hidden"
                  onChange={e => {
                    const f = e.target.files?.[0];
                    if (f) upload(f);
                    e.target.value = '';
                  }}
                />
              </div>
            )}

            <div className="ml-auto flex items-center gap-2">
              {hasConversation && !showPanel && (answers.length > 0 || active.patient) && (
                <button
                  type="button"
                  title="Open document panel"
                  onClick={() => {
                    setPanelOpen(true);
                    if (!panelTab) setPanelTab(answers[answers.length - 1]?.id ?? PATIENT_TAB);
                  }}
                  className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-black/5"
                >
                  <PanelRight className="h-4 w-4" strokeWidth={1.75} />
                </button>
              )}
              <span className="inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md bg-brand px-3 text-[11px] font-medium text-slate-50">
                <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="currentColor">
                  <path d="M8 0l1.8 6.2L16 8l-6.2 1.8L8 16l-1.8-6.2L0 8l6.2-1.8z" />
                </svg>
                Research Preview
              </span>
            </div>
          </header>

          {/* Body */}
          <div className="min-h-0 flex-1">
            {!hasConversation ? (
              <Home
                value={draft}
                onChange={setDraft}
                onSend={() => send()}
                onUpload={upload}
                onAsk={q => send(q)}
                onTemplate={useTemplate}
                busy={busy}
                uploading={uploading}
                patient={active.patient}
                composerRef={composerRef}
              />
            ) : (
              <div className="flex h-full min-h-0">
                <div
                  className={`h-full min-h-0 ${
                    showPanel
                      ? 'w-full lg:w-[380px] xl:w-[420px] lg:shrink-0'
                      : 'mx-auto w-full max-w-[760px]'
                  }`}
                >
                  <ChatColumn
                    messages={active.messages}
                    step={step}
                    activeAnswerId={showPanel ? panelTab ?? undefined : undefined}
                    onOpenAnswer={id => {
                      setPanelTab(id);
                      setPanelOpen(true);
                    }}
                    onFollowUp={q => send(q)}
                    value={draft}
                    onChange={setDraft}
                    onSend={() => send()}
                    onUpload={upload}
                    onAsk={q => send(q)}
                onTemplate={useTemplate}
                    busy={busy}
                    uploading={uploading}
                    hasPatient={!!active.patient}
                    composerRef={composerRef}
                  />
                </div>

                {showPanel && (
                  <div className="absolute inset-0 z-20 bg-[#fafafa] p-2 lg:static lg:z-auto lg:min-w-0 lg:flex-1 lg:bg-transparent lg:pb-2 lg:pl-0 lg:pr-2 lg:pt-0">
                    <DocumentPanel
                      answers={answers}
                      questionFor={questionFor}
                      patient={active.patient}
                      activeTab={panelTab!}
                      onTab={setPanelTab}
                      onClose={() => setPanelOpen(false)}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
