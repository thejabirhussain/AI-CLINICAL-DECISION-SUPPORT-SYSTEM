import type { Confidence, PatientData, Source } from './types';

// Relative by default so the Vite dev proxy forwards to the FastAPI backend.
const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? '';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError('Cannot reach the clinical API. Make sure the backend is running on port 8000.', 0);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof data?.detail === 'string'
        ? data.detail
        : res.status >= 500
          ? `The clinical API returned an error (${res.status}). Check that the backend is running on port 8000.`
          : `Request failed (${res.status})`;
    throw new ApiError(detail, res.status);
  }
  return data as T;
}

export interface AnswerResult {
  answer: string;
  sources: Source[];
  confidence?: Confidence;
  followUps: string[];
}

interface RawAnswer {
  answer_text?: string;
  answer?: string;
  sources?: Source[];
  confidence?: Confidence;
  follow_up_questions?: string[];
}

function normalize(data: RawAnswer): AnswerResult {
  return {
    answer: data.answer_text || data.answer || 'No response generated.',
    sources: data.sources ?? [],
    confidence: data.confidence,
    followUps: data.follow_up_questions ?? [],
  };
}

export async function askGeneral(
  query: string,
  history: { role: 'user' | 'assistant'; content: string }[],
): Promise<AnswerResult> {
  const data = await request<RawAnswer>('/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, history, context: '' }),
  });
  return normalize(data);
}

export async function askPatient(query: string, sessionId: string): Promise<AnswerResult> {
  const data = await request<RawAnswer>('/patient/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id: sessionId }),
  });
  return normalize(data);
}

export interface UploadResult {
  session_id: string;
  structured_data: PatientData;
  filename: string;
}

export async function uploadPatientFile(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append('file', file);
  return request<UploadResult>('/patient/upload', { method: 'POST', body: form });
}
