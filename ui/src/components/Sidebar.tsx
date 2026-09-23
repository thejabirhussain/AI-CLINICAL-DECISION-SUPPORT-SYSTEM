import { useMemo, useRef, useState } from 'react';
import {
  FileImage, FileText, FileUp, Loader2, MoreHorizontal, PanelLeft, Plus, Search, Trash2, X,
} from 'lucide-react';
import { isAbnormal, type Encounter } from '../types';

interface Props {
  open: boolean;
  onToggle: () => void;
  encounters: Encounter[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onUpload: (file: File) => void;
  uploading: boolean;
  onClearPatient: () => void;
  onOpenPatient: () => void;
}

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2 select-none">
      <svg viewBox="0 0 24 24" className="h-[22px] w-[22px] text-ink" fill="none" stroke="currentColor" strokeWidth="1.3">
        <circle cx="12" cy="12" r="9.5" />
        <circle cx="12" cy="12" r="6.5" opacity=".55" />
        <path d="M12 8.5v7M8.5 12h7" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
      {!compact && <span className="text-[19px] font-normal tracking-[0.06em] text-ink">AI CDSS</span>}
    </div>
  );
}

function NavItem({
  icon: Icon, label, onClick, open, disabled, spin,
}: { icon: typeof Plus; label: string; onClick: () => void; open: boolean; disabled?: boolean; spin?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      className={`flex h-8 items-center gap-3 rounded-md text-[14px] text-ink transition-colors hover:bg-hover disabled:opacity-60 ${
        open ? 'w-full px-2' : 'w-9 justify-center'
      }`}
    >
      <Icon className={`h-4 w-4 shrink-0 ${spin ? 'animate-spin' : ''}`} strokeWidth={1.75} />
      {open && <span className="truncate">{label}</span>}
    </button>
  );
}

export function Sidebar(props: Props) {
  const {
    open, onToggle, encounters, activeId, onSelect, onNew, onDelete, onUpload, uploading, onClearPatient, onOpenPatient,
  } = props;
  const fileRef = useRef<HTMLInputElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [menuFor, setMenuFor] = useState<string | null>(null);

  const active = encounters.find(e => e.id === activeId);
  const patient = active?.patient;

  const history = useMemo(() => {
    const q = query.trim().toLowerCase();
    return encounters
      .filter(e => e.messages.length > 0 || e.patient)
      .filter(e => !q || e.title.toLowerCase().includes(q) || e.patient?.filename.toLowerCase().includes(q))
      .sort((a, b) => b.updatedAt - a.updatedAt);
  }, [encounters, query]);

  const focusSearch = () => {
    if (!open) onToggle();
    setTimeout(() => searchRef.current?.focus(), 50);
  };

  return (
    <aside
      className={`no-print flex h-full shrink-0 flex-col transition-[width] duration-200 ${open ? 'w-[260px]' : 'w-[52px]'}`}
    >
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

      {/* Header */}
      <div className={`flex h-14 items-center ${open ? 'justify-between pl-3 pr-2' : 'justify-center'}`}>
        {open && <Logo />}
        <button
          type="button"
          onClick={onToggle}
          aria-label="Toggle sidebar"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-zinc-700 hover:bg-hover"
        >
          <PanelLeft className="h-4 w-4" strokeWidth={1.75} />
        </button>
      </div>

      {/* Primary nav */}
      <nav className={`flex flex-col gap-0.5 ${open ? 'px-2' : 'items-center'}`}>
        <NavItem icon={Plus} label="New" onClick={onNew} open={open} />
        <NavItem
          icon={uploading ? Loader2 : FileUp}
          label={uploading ? 'Reading report…' : 'Upload Patient Report'}
          onClick={() => fileRef.current?.click()}
          open={open}
          disabled={uploading}
          spin={uploading}
        />
        <NavItem icon={Search} label="Search" onClick={focusSearch} open={open} />
      </nav>

      {open && (
        <div className="mt-5 flex min-h-0 flex-1 flex-col px-2">
          {/* Patient context */}
          <div className="px-2 pb-2 text-[12px] text-ink-3">Patient Context</div>
          {patient ? (
            <div className="group relative mx-0.5 rounded-lg border border-line bg-white p-2.5 shadow-card">
              <button type="button" onClick={onOpenPatient} className="flex w-full items-start gap-2.5 text-left">
                <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-subtle">
                  {patient.fileType.includes('image') ? (
                    <FileImage className="h-4 w-4 text-ink-2" />
                  ) : (
                    <FileText className="h-4 w-4 text-ink-2" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] font-medium">{patient.filename}</div>
                  <div className="text-[11px] text-ink-3">
                    {[
                      patient.data.demographics?.age ? `${patient.data.demographics.age}y` : null,
                      patient.data.demographics?.gender,
                      `${patient.data.labs?.filter(isAbnormal).length ?? 0} flagged labs`,
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                  </div>
                </div>
              </button>
              <button
                type="button"
                onClick={onClearPatient}
                aria-label="Remove patient context"
                className="absolute right-1.5 top-1.5 rounded p-0.5 text-ink-3 opacity-0 transition-opacity hover:bg-subtle hover:text-ink group-hover:opacity-100"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="flex h-16 items-center justify-center rounded-lg border border-dashed border-line-strong bg-gray-500/5 text-[11px] font-medium text-ink-3 transition-colors hover:bg-gray-500/10"
            >
              {uploading ? 'Reading report…' : 'Upload a patient report'}
            </button>
          )}

          {/* History */}
          <div className="mt-6 flex items-center justify-between px-2 pb-1.5">
            <span className="text-[12px] text-ink-3">All Encounters</span>
          </div>
          <div className="px-0.5 pb-2">
            <input
              ref={searchRef}
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search encounters…"
              className="h-8 w-full rounded-md border border-transparent bg-transparent px-2 text-[13px] outline-none placeholder:text-ink/40 focus:border-line focus:bg-white"
            />
          </div>
          <div className="-mx-1 min-h-0 flex-1 overflow-y-auto px-1 pb-2">
            {history.length === 0 && (
              <div className="px-2 py-1 text-[12px] text-ink/40">{query ? 'No matches' : 'No encounters yet'}</div>
            )}
            {history.map(e => (
              <div
                key={e.id}
                className={`group relative flex h-[29px] items-center rounded-md pl-5 pr-1 ${
                  e.id === activeId ? 'bg-hover' : 'hover:bg-hover'
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelect(e.id)}
                  className="min-w-0 flex-1 truncate text-left text-[14px] text-ink/90"
                  title={e.title}
                >
                  {e.title}
                </button>
                <button
                  type="button"
                  aria-label="Encounter options"
                  onClick={() => setMenuFor(menuFor === e.id ? null : e.id)}
                  className="ml-1 rounded p-0.5 text-ink-3 hover:text-ink"
                >
                  <MoreHorizontal className="h-4 w-4" />
                </button>
                {menuFor === e.id && (
                  <div
                    className="absolute right-0 top-7 z-30 w-36 rounded-lg border border-line bg-white p-1 shadow-float"
                    onMouseLeave={() => setMenuFor(null)}
                  >
                    <button
                      type="button"
                      onClick={() => {
                        setMenuFor(null);
                        onDelete(e.id);
                      }}
                      className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-[13px] text-red-600 hover:bg-red-50"
                    >
                      <Trash2 className="h-3.5 w-3.5" /> Delete
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!open && <div className="flex-1" />}

      {/* Footer */}
      <div className={`border-t border-line py-3 ${open ? 'px-2' : 'flex justify-center'}`}>
        <div className={`flex items-center gap-2 ${open ? 'px-2' : ''}`}>
          <div className="flex h-6 w-6 items-center justify-center rounded-[5px] bg-brand text-[10px] font-semibold text-white">
            JH
          </div>
          {open && (
            <>
              <span className="truncate text-[14px] font-semibold">Clinical workspace</span>
              <span className="ml-auto rounded border border-brand/20 bg-brand-soft px-1.5 text-[11px] font-medium text-brand">
                Preview
              </span>
            </>
          )}
        </div>
      </div>
    </aside>
  );
}
