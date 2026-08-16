// Thin client for the FastAPI backend -- mirrors the request/response shapes in
// src/enterprise_rag_knowledge_assistant/api/routes/{documents,query}.py exactly. No state
// management library, no data-fetching framework -- plain fetch, matching "keep it simple"
// (docs/adr/0011-phase2-stack.md).

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type DocumentStatus = "uploaded" | "ingesting" | "ingested" | "failed";

export interface DocumentSummary {
  id: number;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  status: DocumentStatus;
  ingestion_error: string | null;
  source: "cli" | "upload";
  created_at: string;
  chunk_count: number;
}

export interface Citation {
  document: string;
  chunk_id: number;
  similarity: number;
}

export interface QueryResponse {
  question: string;
  answer: string;
  grounded: boolean;
  citations: Citation[];
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_URL}/documents/upload`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function listDocuments(): Promise<DocumentSummary[]> {
  const response = await fetch(`${API_URL}/documents`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function triggerIngest(documentId: number): Promise<DocumentSummary> {
  const response = await fetch(`${API_URL}/documents/${documentId}/ingest`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}

export async function deleteDocument(documentId: number): Promise<void> {
  const response = await fetch(`${API_URL}/documents/${documentId}`, {
    method: "DELETE",
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(await parseErrorDetail(response));
  }
}

export async function askQuestion(question: string): Promise<QueryResponse> {
  const response = await fetch(`${API_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response));
  }
  return response.json();
}
