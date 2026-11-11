// Typed client for the two backend services (proxied under /api/content and /api/practice).

export interface Topic {
  slug: string;
  title: string;
  grade: number;
  order: number;
  description: string;
}

export interface Problem {
  id: string;
  topic: string;
  rating: number;
  prompt: string;
  answer_type: "numeric" | "fraction" | "expression";
  hint: string;
}

export interface NextProblem {
  problem: Problem;
  student_rating: number;
  target_rating: number;
  expected_success: number;
}

export interface AttemptResult {
  attempt_id: string;
  problem_id: string;
  correct: boolean;
  feedback: string;
  correct_answer: string | null;
  rating_before: number;
  rating_after: number;
  mastery: string;
  replayed: boolean;
}

export interface TopicProgress {
  topic: string;
  rating: number;
  attempts: number;
  accuracy: number;
  mastery: string;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    // FastAPI returns {detail}, Flask returns {error}
    const detail = typeof body.detail === "string" ? body.detail : body.error ?? res.statusText;
    throw new ApiError(res.status, detail);
  }
  return body as T;
}

const student = (id: string) => `/api/practice/students/${encodeURIComponent(id)}`;

export const api = {
  topics: () => request<Topic[]>("/api/content/topics"),
  next: (studentId: string, topic: string) => request<NextProblem>(`${student(studentId)}/topics/${topic}/next`),
  submit: (studentId: string, attemptId: string, problemId: string, answer: string) =>
    request<AttemptResult>(`${student(studentId)}/attempts`, {
      method: "POST",
      body: JSON.stringify({ attempt_id: attemptId, problem_id: problemId, answer }),
    }),
  progress: (studentId: string) => request<TopicProgress[]>(`${student(studentId)}/progress`),
};

export const newAttemptId = () => crypto.randomUUID().replace(/-/g, "");
