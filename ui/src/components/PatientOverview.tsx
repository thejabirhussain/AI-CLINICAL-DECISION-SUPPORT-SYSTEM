import type { ReactNode } from 'react';
import { isAbnormal, type Lab, type PatientContext } from '../types';
import { formatStamp } from '../utils/encounters';

function Section({ title, right, children }: { title: string; right?: ReactNode; children: ReactNode }) {
  return (
    <section>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-[15px] font-medium">{title}</h3>
        {right}
      </div>
      <div className="rounded-xl border border-line bg-white px-3 py-2.5 shadow-card">{children}</div>
    </section>
  );
}

function Empty({ text = 'Not found in report' }: { text?: string }) {
  return <p className="text-[14px] text-ink/40">{text}</p>;
}

function Chips({ items }: { items?: string[] }) {
  if (!items?.length) return <Empty />;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map(x => (
        <span key={x} className="rounded-md bg-subtle px-2 py-1 text-[13px]">
          {x}
        </span>
      ))}
    </div>
  );
}

const FLAG_STYLE: Record<string, string> = {
  Critical: 'bg-red-600 text-white',
  High: 'bg-red-50 text-red-700 border border-red-200',
  Low: 'bg-sky-50 text-sky-700 border border-sky-200',
  Normal: 'text-ink/50',
  'Not assessed': 'text-ink/35',
};

function LabRow({ lab }: { lab: Lab }) {
  const flag = lab.flag ?? 'Normal';
  const abnormal = isAbnormal(lab);
  return (
    <tr className={`border-t border-line first:border-t-0 ${flag === 'Critical' ? 'bg-red-50/50' : ''}`}>
      <td className="py-2 pr-3 text-[14px]">{lab.test_name}</td>
      <td className={`py-2 pr-3 text-[14px] tabular-nums ${abnormal ? 'font-semibold' : ''}`}>
        {lab.value ?? '—'} <span className="font-normal text-ink-3">{lab.unit ?? ''}</span>
      </td>
      <td className="py-2 pr-3 text-[12px] text-ink-3">{lab.reference_range ?? ''}</td>
      <td className="py-2 text-right">
        <span className={`inline-block rounded px-1.5 py-0.5 text-[11px] font-medium ${FLAG_STYLE[flag] ?? FLAG_STYLE.Normal}`}>
          {flag}
        </span>
      </td>
    </tr>
  );
}

export function PatientOverview({ patient }: { patient: PatientContext }) {
  const d = patient.data;
  const labs = [...(d.labs ?? [])].sort((a, b) => {
    const rank = (l: Lab) => (l.flag === 'Critical' ? 0 : isAbnormal(l) ? 1 : l.flag === 'Normal' ? 2 : 3);
    return rank(a) - rank(b);
  });
  const flagged = labs.filter(isAbnormal).length;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-[18px] font-semibold">Patient Overview</h2>
        <p className="mt-0.5 text-[12px] text-ink-3">
          Extracted from <span className="font-medium text-ink-2">{patient.filename}</span> · {formatStamp(patient.uploadedAt)}
        </p>
      </div>

      <Section title="Summary">
        <div className="mb-2 flex flex-wrap gap-4 text-[13px]">
          <div>
            <span className="text-ink-3">Age </span>
            <span className="font-medium">{d.demographics?.age ?? '—'}</span>
          </div>
          <div>
            <span className="text-ink-3">Sex </span>
            <span className="font-medium">{d.demographics?.gender ?? '—'}</span>
          </div>
          <div>
            <span className="text-ink-3">Flagged labs </span>
            <span className={`font-medium ${flagged ? 'text-red-700' : ''}`}>{flagged}</span>
          </div>
        </div>
        {d.unstructured_narrative ? (
          <p className="whitespace-pre-wrap text-[14px] leading-relaxed">{d.unstructured_narrative}</p>
        ) : (
          <Empty text="No narrative extracted" />
        )}
      </Section>

      <Section title="Active Problems">
        <Chips items={d.active_problems} />
      </Section>

      <div className="grid gap-5 md:grid-cols-2">
        <Section title="Medications">
          <Chips items={d.medications} />
        </Section>
        <Section title="Allergies">
          <Chips items={d.allergies} />
        </Section>
      </div>

      <Section title="Labs" right={<span className="text-[12px] text-ink-3">{labs.length} results</span>}>
        {labs.length ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <tbody>
                {labs.map((l, i) => (
                  <LabRow key={`${l.test_name}-${i}`} lab={l} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty />
        )}
      </Section>
    </div>
  );
}
