import { useEffect, useRef } from 'react';
import {
  ArrowRight, ChevronLeft, CircleHelp, ClipboardList, FlaskConical, PenLine, Pill, Search, ShieldAlert, Stethoscope,
  TrendingUp,
} from 'lucide-react';

export interface QuickAction {
  label: string;
  icon: typeof Search;
  /** Starter text put in the composer by "Write your own…". */
  template: string;
  /** Ready-to-send example prompts shown when the chip is opened (chosen to match the knowledge base). */
  examples: string[];
  /** Only shown when a patient report is loaded. */
  patientOnly?: boolean;
}

export const QUICK_ACTIONS: QuickAction[] = [
  {
    label: 'Ask a Question',
    icon: CircleHelp,
    template: '',
    examples: [
      'What causes glaucoma and how is it diagnosed?',
      "How is Parkinson's disease treated?",
      'What are the symptoms of iron deficiency anemia?',
    ],
  },
  {
    label: 'Draft DDx',
    icon: Search,
    template: 'Draft a differential diagnosis for a patient presenting with ',
    examples: [
      'A 45-year-old woman presents with fatigue, weight gain, cold intolerance, constipation and dry skin. What is the differential diagnosis?',
      'A 60-year-old man presents with a resting tremor in his right hand, slowness of movement and a shuffling gait. What is the differential diagnosis?',
    ],
  },
  {
    label: 'Draft A&P',
    icon: ClipboardList,
    template: 'Draft an assessment & plan for ',
    examples: [
      'Draft an assessment and plan for a 55-year-old man with newly diagnosed type 2 diabetes (HbA1c 8.1%) and high blood pressure.',
      'Draft an assessment and plan for a 30-year-old woman with a new diagnosis of asthma who wakes at night with cough and wheeze twice a week.',
    ],
  },
  {
    label: 'Interpret Labs',
    icon: FlaskConical,
    template: "Interpret this patient's ",
    patientOnly: true,
    examples: [
      "Which of this patient's lab values need urgent attention, and why?",
      "Interpret this patient's abnormal labs and explain their clinical significance.",
      "What could be causing this patient's anemia and how should it be managed?",
    ],
  },
  {
    label: 'Summarize Patient',
    icon: Stethoscope,
    template: 'Summarize this patient ',
    patientOnly: true,
    examples: [
      'Summarize this patient: active problems, key findings, and what needs attention first.',
    ],
  },
  {
    label: 'Treatment Plan',
    icon: TrendingUp,
    template: 'What is the evidence-based first-line management of ',
    examples: [
      'What is the first-line treatment for type 2 diabetes?',
      'How is high blood pressure treated?',
      'What are the treatment options for chronic kidney disease?',
    ],
  },
  {
    label: 'Drug Interactions',
    icon: Pill,
    template: 'Check for clinically significant interactions and contraindications between ',
    examples: [
      "Is metformin safe to continue given this patient's kidney function?",
      'Is ibuprofen safe for this patient given their kidney function?',
      "Should lisinopril be continued with this patient's potassium level?",
    ],
    patientOnly: true,
  },
  {
    label: 'Red Flags',
    icon: ShieldAlert,
    template: 'What red-flag features should prompt urgent escalation in ',
    examples: [
      'What are the warning signs of a stroke?',
      'What are the warning signs of a heart attack that need emergency care?',
    ],
  },
];

interface Props {
  hasPatient: boolean;
  /** Currently opened action label (or null) — lifted so the Home screen can swap the rail for the list. */
  open: string | null;
  onOpenChange: (label: string | null) => void;
  onSend: (text: string) => void;
  onTemplate: (text: string) => void;
  variant?: 'hero' | 'compact';
}

function ExampleList({
  action, onBack, onSend, onTemplate,
}: { action: QuickAction; onBack: () => void; onSend: (t: string) => void; onTemplate: (t: string) => void }) {
  return (
    <div className="animate-rise w-full text-left">
      <button
        type="button"
        onClick={onBack}
        className="mb-1 inline-flex items-center gap-1 rounded-md px-1 py-1 text-[13px] text-ink hover:bg-zinc-100"
      >
        <ChevronLeft className="h-3.5 w-3.5" />
        Back
      </button>
      <div className="divide-y divide-line">
        {action.examples.map(ex => (
          <div key={ex} className="py-1">
            <button
              type="button"
              onClick={() => onSend(ex)}
              className="block w-full cursor-pointer rounded-lg p-2 text-left text-[13px] leading-[1.5] text-ink transition-colors hover:bg-zinc-100"
            >
              <span className="line-clamp-4">{ex}</span>
            </button>
          </div>
        ))}
        <div className="py-1">
          <button
            type="button"
            onClick={() => onTemplate(action.template)}
            className="flex w-full items-center gap-2 rounded-lg p-2 text-left text-[13px] text-ink-3 transition-colors hover:bg-zinc-100 hover:text-ink"
          >
            <PenLine className="h-3.5 w-3.5" strokeWidth={1.75} />
            Write your own…
          </button>
        </div>
      </div>
    </div>
  );
}

export function QuickActions({ hasPatient, open, onOpenChange, onSend, onTemplate, variant = 'hero' }: Props) {
  const railRef = useRef<HTMLDivElement>(null);
  const popRef = useRef<HTMLDivElement>(null);
  const items = QUICK_ACTIONS.filter(a => !a.patientOnly || hasPatient);
  const active = items.find(a => a.label === open) ?? null;

  // Compact popover closes on outside click / Escape.
  useEffect(() => {
    if (variant !== 'compact' || !active) return;
    const onDown = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) onOpenChange(null);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onOpenChange(null);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [variant, active, onOpenChange]);

  const pick = (fn: (t: string) => void) => (t: string) => {
    onOpenChange(null);
    fn(t);
  };

  // Hero: Glass swaps the chip rail for the example list in place.
  if (variant === 'hero' && active) {
    return (
      <ExampleList action={active} onBack={() => onOpenChange(null)} onSend={pick(onSend)} onTemplate={pick(onTemplate)} />
    );
  }

  return (
    <div ref={popRef} className="relative w-full">
      {variant === 'compact' && active && (
        <div className="absolute bottom-full left-0 right-0 z-30 mb-2 max-h-[60vh] overflow-y-auto rounded-xl border border-line bg-white p-2 shadow-float">
          <ExampleList action={active} onBack={() => onOpenChange(null)} onSend={pick(onSend)} onTemplate={pick(onTemplate)} />
        </div>
      )}
      <div ref={railRef} className="no-scrollbar fade-right flex gap-2 overflow-x-auto pr-10">
        {items.map(a => (
          <button
            key={a.label}
            type="button"
            onClick={() => onOpenChange(open === a.label ? null : a.label)}
            aria-expanded={open === a.label}
            className={`inline-flex h-8 shrink-0 items-center gap-2 rounded-lg border px-3 text-[12px] font-medium text-ink transition-colors ${
              open === a.label ? 'border-line-strong bg-zinc-100' : 'border-line bg-white hover:bg-zinc-100'
            }`}
          >
            <a.icon className="h-4 w-4 text-ink-2" strokeWidth={1.75} />
            {a.label}
          </button>
        ))}
      </div>
      <button
        type="button"
        aria-label="Scroll actions"
        onClick={() => railRef.current?.scrollBy({ left: 240, behavior: 'smooth' })}
        className="absolute right-0 top-1/2 -translate-y-1/2 rounded-md p-1 text-ink hover:bg-subtle"
      >
        <ArrowRight className="h-4 w-4" />
      </button>
    </div>
  );
}
