import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import { ArrowUp, FileUp, Loader2 } from 'lucide-react';

export interface ComposerHandle {
  focus: () => void;
}

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onUpload: (file: File) => void;
  busy: boolean;
  uploading: boolean;
  variant: 'hero' | 'compact';
}

export const Composer = forwardRef<ComposerHandle, Props>(function Composer(
  { value, onChange, onSend, onUpload, busy, uploading, variant },
  ref,
) {
  const taRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const hero = variant === 'hero';

  useImperativeHandle(ref, () => ({
    focus: () => {
      const ta = taRef.current;
      if (!ta) return;
      ta.focus();
      ta.setSelectionRange(ta.value.length, ta.value.length);
    },
  }));

  // Auto-grow
  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, hero ? 240 : 180) + 'px';
  }, [value, hero]);

  const canSend = value.trim().length > 0 && !busy;

  return (
    <div className="rounded-xl border border-line bg-white shadow-card transition-shadow focus-within:shadow-float focus-within:border-line-strong">
      <div className={hero ? 'px-2 pt-1.5' : 'px-1.5 pt-1'}>
        <textarea
          ref={taRef}
          rows={1}
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              if (canSend) onSend();
            }
          }}
          placeholder={hero ? 'What are the latest guidelines for the treatment of…' : 'How else can I help?'}
          className={`block w-full resize-none bg-transparent p-2 outline-none placeholder:text-ink/40 ${
            hero ? 'text-[15px] min-h-[38px]' : 'text-[15px] min-h-[36px]'
          }`}
        />
      </div>

      <div className="flex items-center gap-2 px-2 pb-2 pt-1">
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,image/*"
          className="hidden"
          onChange={e => {
            const f = e.target.files?.[0];
            if (f) onUpload(f);
            e.target.value = '';
          }}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          title="Upload a patient report (PDF or image)"
          className={`inline-flex h-9 items-center gap-2 rounded-lg border border-brand bg-brand text-white text-[13px] transition-colors hover:bg-brand-hover disabled:opacity-60 ${
            hero ? 'px-2.5' : 'w-9 justify-center'
          }`}
        >
          {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
          {hero && <span>{uploading ? 'Reading report…' : 'Upload Report'}</span>}
        </button>

        {hero && (
          <span className="hidden sm:inline text-[12px] text-ink-3">PDF, JPG or PNG · labs, discharge summaries, notes</span>
        )}

        <div className="ml-auto flex items-center gap-2">
          {!hero && <span className="hidden md:inline text-[11px] text-ink-3">⏎ to send</span>}
          <button
            type="button"
            onClick={onSend}
            disabled={!canSend}
            aria-label="Send"
            className={`inline-flex h-9 w-9 items-center justify-center rounded-lg transition-colors ${
              canSend ? 'bg-ink text-white hover:bg-black' : 'bg-black/[0.08] text-ink-2'
            }`}
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  );
});
