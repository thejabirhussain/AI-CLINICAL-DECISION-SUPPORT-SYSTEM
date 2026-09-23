import { useEffect, useState, type RefObject } from 'react';
import { FileText } from 'lucide-react';
import { Composer, type ComposerHandle } from './Composer';
import { QuickActions } from './QuickActions';
import type { PatientContext } from '../types';

const TAGLINES = [
  'draft your differential diagnosis',
  'interpret abnormal patient labs',
  'ground answers in clinical guidelines',
  'plan evidence-based next steps',
];

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onUpload: (f: File) => void;
  onAsk: (text: string) => void;
  onTemplate: (text: string) => void;
  busy: boolean;
  uploading: boolean;
  patient?: PatientContext;
  composerRef: RefObject<ComposerHandle>;
}

export function Home({
  value, onChange, onSend, onUpload, onAsk, onTemplate, busy, uploading, patient, composerRef,
}: Props) {
  const [i, setI] = useState(0);
  const [openAction, setOpenAction] = useState<string | null>(null);
  useEffect(() => {
    const t = setInterval(() => setI(n => (n + 1) % TAGLINES.length), 3200);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-1 flex-col items-center justify-center px-4 pb-16">
        <h1 className="text-center text-[28px] font-light leading-[1.15] tracking-[-0.01em] text-ink sm:text-[36px]">
          Clinical Intelligence to
          <br />
          <span key={i} className="animate-swap inline-block text-ink/60">
            {TAGLINES[i]}
          </span>
        </h1>

        <div className="mt-6 mb-3">
          {patient ? (
            <span className="inline-flex h-6 items-center gap-1.5 rounded-full border border-line bg-white px-2.5 text-[11px] text-ink-2">
              <FileText className="h-3 w-3" />
              Patient · {patient.filename}
            </span>
          ) : (
            <span className="inline-flex h-6 items-center rounded-full border border-line bg-white px-2.5 text-[11px] text-ink-2">
              General
            </span>
          )}
        </div>

        <div className="w-full max-w-[672px]">
          <Composer
            ref={composerRef}
            variant="hero"
            value={value}
            onChange={onChange}
            onSend={onSend}
            onUpload={onUpload}
            busy={busy}
            uploading={uploading}
          />
          <div className="mt-6">
            <QuickActions
              hasPatient={!!patient}
              open={openAction}
              onOpenChange={setOpenAction}
              onSend={onAsk}
              onTemplate={onTemplate}
            />
          </div>
        </div>
      </div>

      <footer className="pb-3 text-center text-[11px] text-ink-3/60">
        <div>AI CDSS · Research preview</div>
        <div className="mt-1">
          Decision support only — outputs must be verified by a qualified clinician. Not a diagnostic device.
        </div>
      </footer>
    </div>
  );
}
