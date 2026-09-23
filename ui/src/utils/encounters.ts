import type { Encounter } from '../types';

const KEY = 'aicdss.encounters.v1';

export const uid = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36);

export function newEncounter(): Encounter {
  const now = Date.now();
  return { id: uid(), title: 'New encounter', messages: [], createdAt: now, updatedAt: now };
}

export function loadEncounters(): Encounter[] {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? (JSON.parse(raw) as Encounter[]) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveEncounters(list: Encounter[]) {
  try {
    // Only keep encounters that have content, newest first, capped.
    const keep = list.filter(e => e.messages.length > 0 || e.patient).slice(0, 50);
    localStorage.setItem(KEY, JSON.stringify(keep));
  } catch {
    /* storage unavailable — history just won't persist */
  }
}

export function titleFrom(text: string) {
  const clean = text.replace(/\s+/g, ' ').trim();
  return clean.length > 60 ? clean.slice(0, 60) + '…' : clean || 'New encounter';
}

export function formatStamp(ts: number) {
  const d = new Date(ts);
  return d.toLocaleString([], { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}
