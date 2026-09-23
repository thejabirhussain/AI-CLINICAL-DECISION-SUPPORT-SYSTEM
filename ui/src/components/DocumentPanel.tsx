import { useEffect, useRef, useState } from 'react';
import { Check, Copy, ExternalLink, Minimize2, Printer, X } from 'lucide-react';
import type { Message, PatientContext } from '../types';
import { formatStamp } from '../utils/encounters';
import { hostOf, isWebUrl } from '../utils/citations';
import { Markdown } from './Markdown';
import { PatientOverview } from './PatientOverview';
import { answerTitle } from './ChatColumn';

export const PATIENT_TAB = '__patient__';

interface Props {
  answers: Message[];
  questionFor: (answerId: string) => string | undefined;
  patient?: PatientContext;
  activeTab: string;
  onTab: (id: string) => void;
  onClose: () => void;
}

function IconBtn({ title, onClick, children }: { title: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={onClick}
      className="flex h-8 w-8 items-center justify-center rounded-md text-ink hover:bg-black/5"
    >
      {children}
    </button>
  );
}

const MAX_TABS = 3;

export function DocumentPanel({ answers, questionFor, patient, activeTab, onTab, onClose }: Props) {
  const [copied, setCopied] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [highlight, setHighlight] = useState<number | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);

  const active = answers.find(a => a.id === activeTab);
  const showPatient = activeTab === PATIENT_TAB && patient;

  // Most recent answers get their own tab; older ones (and the active one if older) go into "More".
  const recent = answers.slice(-MAX_TABS);
  const visible = active && !recent.includes(active) ? [...recent.slice(1), active] : recent;
  const overflow = answers.filter(a => !visible.includes(a));

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: 0 });
    setHighlight(null);
  }, [activeTab]);

  const cite = (n: number) => {
    setHighlight(n);
    document.getElementById(`ref-${n}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const copy = () => {
    const text = showPatient ? bodyRef.current?.innerText ?? '' : active?.content ?? '';
    navigator.clipboard?.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    });
  };

  const Tab = ({ id, title, sub }: { id: string; title: string; sub: string }) => {
    const on = id === activeTab;
    return (
      <button
        type="button"
        onClick={() => onTab(id)}
        className={`relative flex h-full min-w-0 max-w-[190px] shrink-0 flex-col justify-center rounded-t-lg px-3 text-left ${
          on ? 'bg-white' : 'hover:bg-black/[0.03]'
        }`}
      >
        <span className="truncate text-[13px] font-medium">{title}</span>
        <span className="truncate text-[11px] text-ink-3">{sub}</span>
      </button>
    );
  };

  return (
    <div className="print-only-doc flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-line bg-white">
      {/* Tab strip */}
      <div className="no-print flex h-[46px] shrink-0 items-end bg-subtle pl-1 pr-2">
        <div className="flex h-[42px] min-w-0 flex-1 items-end">
          {patient && <Tab id={PATIENT_TAB} title="Patient Overview" sub={patient.filename} />}
          {visible.map(a => (
            <Tab key={a.id} id={a.id} title={answerTitle(a)} sub={formatStamp(a.createdAt)} />
          ))}
          {overflow.length > 0 && (
            <div className="relative self-center">
              <button
                type="button"
                onClick={() => setMoreOpen(o => !o)}
                className="ml-2 flex items-center gap-1.5 rounded-md px-2 py-1 text-[13px] font-medium hover:bg-black/[0.04]"
              >
                More
                <span className="rounded-full bg-zinc-400 px-1.5 text-[10px] font-semibold text-white">
                  +{overflow.length}
                </span>
              </button>
              {moreOpen && (
                <div
                  className="absolute left-0 top-9 z-30 w-64 rounded-lg border border-line bg-white p-1 shadow-float"
                  onMouseLeave={() => setMoreOpen(false)}
                >
                  {overflow.map(a => (
                    <button
                      key={a.id}
                      type="button"
                      onClick={() => {
                        onTab(a.id);
                        setMoreOpen(false);
                      }}
                      className="block w-full rounded-md px-2 py-1.5 text-left hover:bg-subtle"
                    >
                      <div className="truncate text-[13px]">{questionFor(a.id) ?? answerTitle(a)}</div>
                      <div className="text-[11px] text-ink-3">{formatStamp(a.createdAt)}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
        <div className="flex h-[46px] items-center gap-0.5">
          <IconBtn title={copied ? 'Copied' : 'Copy'} onClick={copy}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" strokeWidth={1.75} />}
          </IconBtn>
          <IconBtn title="Print" onClick={() => window.print()}>
            <Printer className="h-4 w-4" strokeWidth={1.75} />
          </IconBtn>
          <IconBtn title="Close panel" onClick={onClose}>
            <Minimize2 className="hidden h-4 w-4 lg:block" strokeWidth={1.75} />
            <X className="h-4 w-4 lg:hidden" strokeWidth={1.75} />
          </IconBtn>
        </div>
      </div>

      {/* Body */}
      <div ref={bodyRef} className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[860px] px-5 py-5 sm:px-6">
          {showPatient && patient ? (
            <PatientOverview patient={patient} />
          ) : active ? (
            <article>
              <header className="mb-4 border-b border-line pb-4">
                <h2 className="text-[18px] font-semibold">{answerTitle(active)}</h2>
                {questionFor(active.id) && (
                  <p className="mt-1 text-[14px] leading-snug text-ink-2">{questionFor(active.id)}</p>
                )}
                <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-ink-3">
                  <span>{formatStamp(active.createdAt)}</span>
                  {active.confidence && <span className="capitalize">{active.confidence} confidence</span>}
                  {!!active.sources?.length && <span>{active.sources.length} sources</span>}
                  {active.patientScoped && patient && <span>Grounded on {patient.filename}</span>}
                </div>
              </header>

              <Markdown content={active.content} sources={active.sources} onCite={cite} />

              {!!active.sources?.length && (
                <section className="mt-8 border-t border-line pt-4">
                  <h3 className="mb-3 text-[13px] font-semibold uppercase tracking-wide text-ink-3">References</h3>
                  <ol className="space-y-2">
                    {active.sources.map((s, i) => (
                      <li
                        id={`ref-${i + 1}`}
                        key={`${s.url}-${i}`}
                        className={`flex gap-3 rounded-lg border px-3 py-2.5 transition-colors ${
                          highlight === i + 1 ? 'border-brand/40 bg-brand-soft' : 'border-line'
                        }`}
                      >
                        <span className="mt-0.5 text-[12px] font-medium text-brand">[{i + 1}]</span>
                        <div className="min-w-0 flex-1">
                          {isWebUrl(s.url) ? (
                            <a
                              href={s.url}
                              target="_blank"
                              rel="noreferrer"
                              className="group inline-flex max-w-full items-center gap-1 text-[14px] font-medium hover:text-brand"
                            >
                              <span className="truncate">{s.title || 'Medical reference'}</span>
                              <ExternalLink className="h-3 w-3 shrink-0 opacity-0 group-hover:opacity-100" />
                            </a>
                          ) : (
                            <div className="truncate text-[14px] font-medium">{s.title || 'Medical reference'}</div>
                          )}
                          <div className="mt-0.5 flex flex-wrap gap-x-2 text-[12px] text-ink-3">
                            <span>{hostOf(s.url)}</span>
                            {s.section && <span>· {s.section}</span>}
                            {typeof s.score === 'number' && <span>· relevance {(s.score * 100).toFixed(0)}%</span>}
                          </div>
                          {s.snippet && (
                            <p className="mt-1 line-clamp-2 text-[13px] leading-snug text-ink-2">{s.snippet}</p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>
              )}

              <p className="mt-6 text-[11px] text-ink/40">
                AI-generated clinical decision support. Verify against primary sources and clinical judgment.
              </p>
            </article>
          ) : (
            <p className="text-[14px] text-ink/40">Select an answer to view it here.</p>
          )}
        </div>
      </div>
    </div>
  );
}
