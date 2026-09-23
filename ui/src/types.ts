export interface Source {
  title: string;
  url: string;
  section?: string | null;
  snippet?: string;
  score?: number;
}

export type Confidence = 'low' | 'medium' | 'high';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  confidence?: Confidence;
  followUps?: string[];
  error?: boolean;
  /** System notice (e.g. report uploaded) rather than a model answer. */
  note?: boolean;
  /** Whether this answer was grounded on the uploaded patient report. */
  patientScoped?: boolean;
  createdAt: number;
}

export interface Lab {
  test_name: string;
  value: string | number | null;
  unit?: string | null;
  flag?: 'Normal' | 'High' | 'Low' | 'Critical' | string;
  reference_range?: string;
}

const ABNORMAL_FLAGS = ['High', 'Low', 'Critical'];
export const isAbnormal = (l: Lab) => !!l.flag && ABNORMAL_FLAGS.includes(l.flag);

export interface PatientData {
  demographics?: { age?: number | null; gender?: string | null };
  active_problems?: string[];
  medications?: string[];
  allergies?: string[];
  labs?: Lab[];
  unstructured_narrative?: string;
}

export interface PatientContext {
  sessionId: string;
  filename: string;
  fileType: string;
  size: number;
  data: PatientData;
  uploadedAt: number;
}

export interface Encounter {
  id: string;
  title: string;
  messages: Message[];
  patient?: PatientContext;
  createdAt: number;
  updatedAt: number;
}

export type ReasoningStep = 'idle' | 'context' | 'analyzing' | 'retrieving' | 'generating';
