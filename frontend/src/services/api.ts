import axios from "axios";

// In Phase 8 we'll move this to a .env (VITE_API_BASE_URL). Hardcoded for
// Phase 1 since the backend URL is fixed during local dev.
const API_BASE_URL = "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 90000,
});

export interface HealthResponse {
  status: string;
  app_name: string;
  environment: string;
  openai_key_configured: boolean;
}

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>("/api/health");
  return data;
}

export type DocumentStatus = "UPLOADED" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface DocumentResponse {
  document_id: string;
  document_name: string;
  status: DocumentStatus;
  page_count: number | null;
  error_message: string | null;
  created_at: string;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
}

export async function uploadDocument(file: File): Promise<DocumentResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post<DocumentResponse>(
    "/api/documents/upload",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

export async function listDocuments(): Promise<DocumentResponse[]> {
  const { data } = await apiClient.get<DocumentListResponse>("/api/documents");
  return data.documents;
}

export async function getDocument(documentId: string): Promise<DocumentResponse> {
  const { data } = await apiClient.get<DocumentResponse>(
    `/api/documents/${documentId}`
  );
  return data;
}

export async function deleteDocument(documentId: string): Promise<void> {
  await apiClient.delete(`/api/documents/${documentId}`);
}

export interface Source {
  document_name: string;
  page_number: number;
  chunk_id: string;
}

export interface RetrievedChunkInfo {
  chunk_id: string;
  page_number: number;
  similarity_score: number;
  text: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  retrieved_chunks: RetrievedChunkInfo[];
}

export async function askQuestion(
  documentId: string,
  question: string
): Promise<ChatResponse> {
  const { data } = await apiClient.post<ChatResponse>("/api/chat/query", {
    document_id: documentId,
    question,
  });
  return data;
}

/** Extracts a user-friendly message from an Axios error, falling back to
 * a generic message if the backend didn't send a `detail` field. */
export function extractErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (err.code === "ERR_NETWORK") return "Could not reach the backend.";
  }
  return "Something went wrong. Please try again.";
}
