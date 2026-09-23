import { useEffect, useRef, useState } from 'react';
import {
  AlertCircle, Check, CheckCircle2, ChevronDown, ClipboardList, Copy, FileCheck2, Loader2, PenLine,
} from 'lucide-react';
import type { Message, ReasoningStep } from '../types';
import { formatStamp } from '../utils/encounters';
import { Composer, type ComposerHandle } from './Composer';
import { QuickActions } from './QuickActions';
import type { RefObject } from 'react';

export const STEPS: { id: Exclude<ReasoningStep, 'idle'>; label: string }[] = [
  { id: 'context', label: 'Reviewing patient context' },
  { id: 'analyzing', label: 'Analyzing the clinical question' },
  { id: 'retrieving', label: 'Retrieving guideline evidence' },
  { id: 'generating', label: 'Composing clinical answer' },
];

export function answerTitle(m: Message) {
  return m.patientScoped ? 'Patient Analysis' : 'Clinical Answer';
}

function Steps({ current, withContext }: { current: ReasoningStep | 'done'; withContext: boolean }) {
  const steps = withContext ? STEPS : STEPS.filter(s => s.id !== 'context');
  const idx = current === 'done' ? steps.length : steps.findIndex(s => s.id === current);
  return (
    <ol className="mt-2 space-y-1.5 border-l border-line pl-3 ml-[7px]">
      {steps.map((s, i) => {
        const done = i < idx;
        const active = i === idx;
        return (
          <li key={s.id} className="flex items-center gap-2 text-[13px]">
            {done ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-ink/70" />
            ) : active ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-ink" />
            ) : (
              <span className="mx-[3px] h-2 w-2 rounded-full border border-line-strong" />
            )}
            <span className={done ? 'text-ink/70' : active ? 'text-ink' : 'text-ink/35'}>{s.label}</span>
          </li>
        );
      })}
    </ol>
  );
}

function CopyButton({ text }: { text: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button
      type="button"
      title="Copy answer"
      onClick={() => {
        navigator.clipboard?.writeText(text).then(() => {
          setOk(true);
          setTimeout(() => setOk(false), 1200);
        });
      }}
      className="rounded-md p-1.5 text-ink/40 hover:bg-subtle hover:text-ink"
    >
      {ok ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
    </button>
  );
}

function AssistantMessage({
  m, active, onOpen,
}: { m: Message; active: boolean; onOpen: () => void }) {
  const [showSteps, setShowSteps] = useState(false);

  if (m.note) {
    return (
      <div className="animate-rise flex items-start gap-2 text-[13px] text-ink-2">
        <FileCheck2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
        <span>{m.content}</span>
      </div>
    );
  }

  if (m.error) {
    return (
      <div className="animate-rise flex items-start gap-2 rounded-lg border border-red-200 bg-red-50/60 px-3 py-2 text-[13px] text-red-700">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{m.content}</span>
      </div>
    );
  }

  return (
    <div className="animate-rise">
      <button
        type="button"
        onClick={() => setShowSteps(s => !s)}
        className="flex w-full items-center gap-2 text-[14px] text-ink-2 hover:text-ink"
      >
        <PenLine className="h-4 w-4" strokeWidth={1.75} />
        Response generated
        <ChevronDown className={`ml-auto h-4 w-4 transition-transform ${showSteps ? 'rotate-180' : ''}`} />
      </button>
      {showSteps && <Steps current="done" withContext={!!m.patientScoped} />}

      <p className="mt-2 text-[15px]">
        {m.patientScoped
          ? "I've analyzed the patient's report against the guideline evidence:"
          : "Here's the evidence-grounded answer:"}
      </p>

      <button
        type="button"
        onClick={onOpen}
        className={`mt-2 flex w-full max-w-[250px] items-center justify-between rounded-lg border bg-white px-3 py-2.5 text-left shadow-float transition-colors ${
          active ? 'border-ink/30 ring-1 ring-ink/10' : 'border-line hover:border-line-strong'
        }`}
      >
        <div className="min-w-0">
          <div className="truncate text-[14px] font-medium">{answerTitle(m)}</div>
          <div className="text-[12px] text-ink-3">{formatStamp(m.createdAt)}</div>
        </div>
        <ClipboardList className="h-4 w-4 shrink-0 text-ink-2" strokeWidth={1.75} />
      </button>

      <div className="mt-2 flex items-center gap-2 text-[12px] text-ink-3">
        {m.confidence && (
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 ${
              m.confidence === 'high'
                ? 'bg-emerald-50 text-emerald-700'
                : m.confidence === 'medium'
                  ? 'bg-amber-50 text-amber-700'
                  : 'bg-zinc-100 text-zinc-600'
            }`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {m.confidence} confidence
          </span>
        )}
        {!!m.sources?.length && <span>{m.sources.length} sources</span>}
        <span className="ml-auto" />
        <CopyButton text={m.content} />
      </div>
    </div>
  );
}

interface Props {
  messages: Message[];
  step: ReasoningStep;
  activeAnswerId?: string;
  onOpenAnswer: (id: string) => void;
  onFollowUp: (q: string) => void;
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onUpload: (f: File) => void;
  onAsk: (text: string) => void;
  onTemplate: (text: string) => void;
  busy: boolean;
  uploading: boolean;
  hasPatient: boolean;
  composerRef: RefObject<ComposerHandle>;
}

export function ChatColumn(props: Props) {
  const {
    messages, step, activeAnswerId, onOpenAnswer, onFollowUp, value, onChange, onSend, onUpload, onAsk, onTemplate, busy, uploading,
    hasPatient, composerRef,
  } = props;
  const endRef = useRef<HTMLDivElement>(null);
  const [openAction, setOpenAction] = useState<string | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length, step]);

  const lastAnswer = [...messages].reverse().find(m => m.role === 'assistant' && !m.note && !m.error);
  const followUps = !busy && lastAnswer === messages[messages.length - 1] ? lastAnswer?.followUps ?? [] : [];

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto px-4 pt-4">
        <div className="space-y-5 pb-4">
          {messages.map(m =>
            m.role === 'user' ? (
              <div key={m.id} className="animate-rise flex justify-end">
                <div className="max-w-[88%] whitespace-pre-wrap rounded-[8px_8px_4px_8px] bg-subtle px-3 py-2 text-[15px] leading-[1.45]">
                  {m.content}
                </div>
              </div>
            ) : (
              <AssistantMessage
                key={m.id}
                m={m}
                active={m.id === activeAnswerId}
                onOpen={() => onOpenAnswer(m.id)}
              />
            ),
          )}

          {step !== 'idle' && (
            <div className="animate-rise">
              <div className="flex items-center gap-2 text-[14px]">
                <PenLine className="h-4 w-4 text-ink-2" strokeWidth={1.75} />
                <span className="shimmer-text font-medium">Thinking…</span>
              </div>
              <Steps current={step} withContext={hasPatient} />
            </div>
          )}

          {followUps.length > 0 && (
            <div className="animate-rise space-y-1.5">
              <div className="text-[12px] text-ink-3">Suggested follow-ups</div>
              {followUps.map(q => (
                <button
                  key={q}
                  type="button"
                  onClick={() => onFollowUp(q)}
                  className="block w-full rounded-lg border border-line bg-white px-3 py-2 text-left text-[13px] text-ink transition-colors hover:bg-subtle"
                >
                  {q}
                </button>
              ))}
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="no-print shrink-0 space-y-2 px-4 pb-4 pt-1">
        <QuickActions
          variant="compact"
          hasPatient={hasPatient}
          open={openAction}
          onOpenChange={setOpenAction}
          onSend={onAsk}
          onTemplate={onTemplate}
        />
        <Composer
          ref={composerRef}
          variant="compact"
          value={value}
          onChange={onChange}
          onSend={onSend}
          onUpload={onUpload}
          busy={busy}
          uploading={uploading}
        />
      </div>
    </div>
  );
}
